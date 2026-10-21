"""从指定文章的直接评论者生成回访名单；默认只预览。"""
import argparse
import hashlib
import json
import random
import re
from pathlib import Path
from urllib.parse import urlsplit

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from csdn_social_automation_bot import CSDN, COMMENT_ENTRY_XPATH


# 只取一级评论的作者，不取回复用户、正文链接或正文中的 @ 用户。
COMMENT_ROWS_JS = """
const panel = document.querySelector('#pcCommentSideBox');
if (!panel) return [];
return Array.from(panel.querySelectorAll('.comment-list > .comment-line-box'))
  .filter(row => !row.parentElement.closest('.comment-line-box'))
  .map(row => {
    const item = Array.from(row.children).find(e => e.matches('.comment-list-item'));
    const link = item && item.querySelector('.user-box .name-href');
    return {id: row.dataset.commentid || '', href: link ? link.href : '',
            name: link ? link.textContent.trim() : ''};
  });
"""

ARTICLE_ROWS_JS = """
return Array.from(document.querySelectorAll('.blog-list-box')).map(row => {
  const link = row.querySelector('a[href*="/article/details/"]');
  const labels = Array.from(row.querySelectorAll('span,i,em,b,img'))
    .filter(e => e.getClientRects().length)
    .map(e => (e.textContent || e.getAttribute('alt') || e.getAttribute('title') || '').trim());
  return {url: link ? link.href : '', title: link ? link.textContent.trim() : '',
          pinned: labels.some(t => /^(置顶|顶)$/.test(t)),
          reprint: labels.some(t => /^(转载|翻译)$/.test(t))};
});
"""

SCROLL_COMMENTS_JS = """
const panel = document.querySelector('#pcCommentSideBox');
if (!panel) return;
for (const el of [panel, ...panel.querySelectorAll('*')]) {
  const style = getComputedStyle(el);
  if (/(auto|scroll)/.test(style.overflowY) && el.scrollHeight > el.clientHeight)
    el.scrollTop = el.scrollHeight;
}
"""


class CommentRevisit(CSDN):
    def commenters(self, source, max_users=5, max_loads=20, blacklist=()):
        source = self.article_url(source)
        if not source:
            raise ValueError("请输入有效的 CSDN 文章链接")
        self.iframe_out()
        self.myBrowser.get(source)
        canonical = self.myBrowser.find_elements(By.CSS_SELECTOR, 'link[rel="canonical"]')
        source = (self.article_url(canonical[0].get_attribute("href")) if canonical else None) or source
        excluded = {name.casefold() for name in blacklist}
        cookie = self.myBrowser.get_cookie("UserName")
        if not cookie or not cookie.get("value"):
            raise RuntimeError("登录状态已失效")
        excluded.add(cookie["value"].casefold())
        source_path = urlsplit(source)
        if source_path.hostname == "blog.csdn.net":
            excluded.add(source_path.path.split("/")[1].casefold())
        history = self.state.get("revisits", {})
        if not isinstance(history, dict) or any(not isinstance(r, dict) for r in history.values()):
            raise ValueError("回访记录格式异常，请检查账号状态文件")
        for record in history.values():
            if record.get("source") == source and record.get("status") in ("confirmed", "pending"):
                excluded.add(str(record.get("username", "")).casefold())
        if not self.find_ele("//*[@id='commentSideBoxshadow']", timeout=1):
            entry = self.find_ele(COMMENT_ENTRY_XPATH)
            if not entry:
                raise RuntimeError("未找到评论入口，不能把 DOM 失效当作没有评论")
            self.myBrowser.execute_script(
                "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", entry)
            entry.click()
        WebDriverWait(self.myBrowser, 15).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "#pcCommentSideBox .comment-list"))
        users = {}
        seen_comments = set()
        stalled = 0
        stop_reason = "达到加载轮数上限，名单可能不完整"
        for _ in range(max_loads):
            rows = self.myBrowser.execute_script(COMMENT_ROWS_JS)
            before = len(seen_comments)
            for row in rows:
                if row["id"]:
                    seen_comments.add(row["id"])
                try:
                    parsed = urlsplit(row["href"])
                except ValueError:
                    continue
                if (parsed.scheme not in ("https", "http") or parsed.hostname != "blog.csdn.net"
                        or parsed.username or parsed.password
                        or not re.fullmatch(r"/[A-Za-z0-9_-]+/?", parsed.path)):
                    continue
                username = parsed.path.strip("/")
                key = username.casefold()
                if key in excluded or key in users:
                    continue
                users[key] = {"username": username, "name": row["name"],
                              "profile": "https://blog.csdn.net/" + username}
                if len(users) >= max_users:
                    return source, list(users.values()), "达到用户数量上限，名单可能不完整"
            stalled = stalled + 1 if len(seen_comments) == before else 0
            if stalled >= 2:
                stop_reason = "连续等待未发现更多一级评论（可能已到底或加载失败）"
                break
            panel = self.myBrowser.find_element(By.ID, "pcCommentSideBox")
            more = panel.find_elements(By.XPATH,
                ".//*[self::button or self::a or self::div or self::span]"
                "[normalize-space(.)='加载更多' or normalize-space(.)='查看更多评论'"
                " or normalize-space(.)='展开全部评论' or normalize-space(.)='下一页']")
            more = [e for e in more if e.is_displayed() and e.is_enabled()
                    and not e.find_elements(By.XPATH, "ancestor::*[contains(@class,'comment-line-box')]")]
            if more:
                self.myBrowser.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", more[-1])
                more[-1].click()
            self.myBrowser.execute_script(SCROLL_COMMENTS_JS)
            try:
                WebDriverWait(self.myBrowser, 4).until(lambda d: any(
                    row["id"] and row["id"] not in seen_comments
                    for row in d.execute_script(COMMENT_ROWS_JS)))
            except TimeoutException:
                pass
        return source, list(users.values()), stop_reason

    def latest_article(self, user, max_articles=20):
        """按主页 latest 顺序检查，置顶/非原创/所有者不匹配均跳过。"""
        self.myBrowser.get(user["profile"] + "?type=lately")
        WebDriverWait(self.myBrowser, 15).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, ".blog-list-box"))
        candidates = []
        seen = set()
        for _ in range(3):
            rows = self.myBrowser.execute_script(ARTICLE_ROWS_JS)
            for row in rows:
                url = self.article_url(row["url"])
                if url and url not in seen:
                    seen.add(url)
                    if not row["pinned"] and not row["reprint"]:
                        candidates.append((url, row["title"]))
            if len(seen) >= max_articles:
                break
            self.myBrowser.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            try:
                WebDriverWait(self.myBrowser, 3).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, ".blog-list-box")) > len(rows))
            except TimeoutException:
                break
        for url, title in candidates[:max_articles]:
            self.myBrowser.get(url)
            canonical = self.myBrowser.find_elements(By.CSS_SELECTOR, 'link[rel="canonical"]')
            target = (self.article_url(canonical[0].get_attribute("href")) if canonical else None)
            target = target or self.article_url(self.myBrowser.current_url)
            if not target:
                continue
            parsed = urlsplit(target)
            if (parsed.hostname != "blog.csdn.net"
                    or parsed.path.split("/")[1].casefold() != user["username"].casefold()):
                continue
            # 不仅依赖主页标签；文章正文页必须明确标记“原创”。
            original = self.find_ele(
                "//*[contains(@class,'article-info-box')]"
                "//*[contains(@class,'type') and normalize-space(.)='原创']"
                " | //*[@class='simple-meta-row']/*[@class='simple-meta-entry' and normalize-space(.)='原创']", timeout=3)
            if original:
                return {"url": target, "title": title or self.myBrowser.title}
        return None

    def build_plan(self, source, max_users=5, max_loads=20, max_articles=20, blacklist=()):
        source, users, stop_reason = self.commenters(source, max_users, max_loads, blacklist)
        plan = {"source": source, "collection_status": stop_reason, "candidates": []}
        for number, user in enumerate(users, 1):
            row = {"number": number, **user, "status": "skipped"}
            try:
                article = self.latest_article(user, max_articles)
                if article:
                    row.update(article)
                    existing = self.state["articles"].get(article["url"], {}).get("comment")
                    row["status"] = existing if existing in ("pending", "confirmed") else "ready"
                else:
                    row["reason"] = "扫描范围内未确认非置顶原创文章"
            except Exception as exc:
                row["status"] = "error"
                row["reason"] = f"{type(exc).__name__}: {str(exc)[:180]}"
            plan["candidates"].append(row)
            print(f"[预览 {number}] {user['name']} ({user['username']})：{row['status']} "
                  f"{row.get('url', row.get('reason', ''))}", flush=True)
        return plan

    def execute_plan(self, plan, selected, comments):
        if not comments or any(not isinstance(t, str) or not t.strip() for t in comments):
            raise ValueError("必须提供非空的完整评论文本")
        if self.state_path is None:
            raise RuntimeError("尚未加载登录账号状态")
        known = {row["number"] for row in plan["candidates"]}
        if not selected or not selected <= known:
            raise ValueError("选择序号必须来自本次预览名单")
        results = []
        for row in plan["candidates"]:
            if row["number"] not in selected or row["status"] != "ready":
                continue
            if not self.refresh_daily_limit():
                print("[回访] 今日评论额度已用完")
                break
            target = row["url"]
            existing = self.state["articles"].get(target, {}).get("comment")
            if existing in ("pending", "confirmed"):
                results.append({**row, "status": existing})
                continue
            record_key = hashlib.sha256(
                (plan["source"] + "|" + row["username"].casefold() + "|" + target).encode()).hexdigest()
            record = {"source": plan["source"], "username": row["username"], "url": target,
                      "status": "started", "date": self.state["date"]}
            self.state.setdefault("revisits", {})[record_key] = record
            self.save_state()
            try:
                success = self.visit_article(target, "评论者回访", comment_text=random.choice(comments))
                status = self.state["articles"].get(target, {}).get("comment")
                record["status"] = "confirmed" if success else (status or "incomplete")
            except Exception as exc:
                record["status"] = self.state["articles"].get(target, {}).get("comment") or "error"
                record["error"] = f"{type(exc).__name__}: {str(exc)[:180]}"
            self.save_state()
            results.append({**row, "status": record["status"]})
            print(f"[回访] {row['username']}：{record['status']}", flush=True)
        return results


def positive_int(value):
    number = int(value)
    if not 1 <= number <= 100:
        raise argparse.ArgumentTypeError("请输入 1–100 的整数")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("article", help="来源文章 URL")
    parser.add_argument("--max-users", type=positive_int, default=5)
    parser.add_argument("--max-loads", type=positive_int, default=20)
    parser.add_argument("--max-articles", type=positive_int, default=20)
    parser.add_argument("--blacklist", type=Path, help="每行一个用户名")
    parser.add_argument("--comment-file", type=Path, help="完整评论文本，每行一条，默认 web/ping.txt")
    parser.add_argument("--execute", action="store_true", help="预览后执行选中的对象")
    parser.add_argument("--select", help="本次预览序号，如 1,3；省略则预览后输入")
    args = parser.parse_args()
    if args.select and not args.execute:
        parser.error("--select 需与 --execute 一起使用")
    bot = CommentRevisit()
    if not bot.article_url(args.article):
        parser.error("来源必须是有效的 CSDN 文章 URL")
    blacklist = (args.blacklist.read_text(encoding="utf-8-sig").splitlines() if args.blacklist else [])
    comments = []
    if args.execute:
        path = args.comment_file or Path(bot.curDir) / "ping.txt"
        if not path.is_file():
            parser.error(f"评论文件不存在：{path}；请先填写完整评论文本")
        comments = [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        if not comments:
            parser.error("评论文件不能为空")
    try:
        bot.start_browser()
        bot.myBrowser.set_page_load_timeout(40)
        plan = bot.build_plan(args.article, args.max_users, args.max_loads,
                              args.max_articles, [name.strip() for name in blacklist if name.strip()])
        output = bot.state_path.with_name(bot.state_path.stem + "-revisit-plan.json")
        output.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n{plan['collection_status']}\n预览记录：{output}")
        if not args.execute:
            print("仅预览：未点赞、收藏、评论或私信。")
            return
        if not any(row["status"] == "ready" for row in plan["candidates"]):
            print("本次没有可执行的对象。")
            return
        print("评论文本（随机选取一条原文，不追加话术）：")
        for comment in comments:
            print(f"  {comment}")
        selection = args.select or input("输入要执行的序号（逗号分隔；回车取消）：").strip()
        if not selection:
            print("已取消。")
            return
        selected = {int(value.strip()) for value in selection.split(",")}
        plan["results"] = bot.execute_plan(plan, selected, comments)
        output.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        if bot.myBrowser is not None:
            bot.myBrowser.quit()


if __name__ == "__main__":
    main()
