import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web"))
from comment_revisit import CommentRevisit, COMMENT_ROWS_JS, ARTICLE_ROWS_JS

SOURCE = "https://blog.csdn.net/owner/article/details/1"
TARGET = "https://blog.csdn.net/person/article/details/2"


class RevisitTests(unittest.TestCase):
    def test_collects_next_batch_dedupes_and_excludes_self_blacklist_and_bad_links(self):
        bot = CommentRevisit()
        bot.myBrowser = Mock()
        bot.myBrowser.find_elements.side_effect = lambda by, value: [] if "canonical" in value else [Mock()]
        bot.myBrowser.get_cookie.return_value = {"value": "self"}
        bot.state["revisits"] = {"done": {"source": SOURCE, "username": "visited", "status": "confirmed"}}
        bot.myBrowser.find_element.return_value.find_elements.return_value = []
        bot.find_ele = Mock(return_value=Mock())
        def row(number, user):
            return {"id": str(number), "href": "https://blog.csdn.net/" + user, "name": user}
        first = [row(1, "self"), row(2, "owner"), row(3, "blocked"), row(4, "person"), row(5, "person"),
                 row(7, "visited"), {"id": "8", "href": "https://evil.test/person", "name": "evil"}]
        second = [row(6, "second")]
        calls = 0
        def execute(script):
            nonlocal calls
            if script != COMMENT_ROWS_JS:
                return None
            calls += 1
            return first if calls == 1 else second
        bot.myBrowser.execute_script.side_effect = execute
        source, users, reason = bot.commenters(SOURCE, max_users=2, blacklist=["blocked"])
        self.assertEqual(source, SOURCE)
        self.assertEqual([u["username"] for u in users], ["person", "second"])
        self.assertIn("上限", reason)
        bot.find_ele.return_value.click.assert_not_called()

    def test_latest_skips_pinned_reprint_and_wrong_owner_and_requires_original(self):
        bot = CommentRevisit()
        driver = bot.myBrowser = Mock()
        rows = [
            {"url": TARGET + "0", "title": "pinned", "pinned": True, "reprint": False},
            {"url": TARGET + "1", "title": "reprint", "pinned": False, "reprint": True},
            {"url": "https://blog.csdn.net/other/article/details/22", "title": "other", "pinned": False, "reprint": False},
            {"url": TARGET, "title": "original", "pinned": False, "reprint": False},
        ]
        driver.execute_script.return_value = rows
        def get(url):
            driver.current_url = url
        driver.get.side_effect = get
        driver.find_elements.side_effect = lambda by, selector: [] if "canonical" in selector else [Mock()]
        bot.find_ele = Mock(return_value=Mock())
        result = bot.latest_article({"username": "person", "profile": "https://blog.csdn.net/person"}, max_articles=4)
        self.assertEqual(result, {"url": TARGET, "title": "original"})
        visited = [call.args[0] for call in driver.get.call_args_list]
        self.assertNotIn(TARGET + "0", visited)
        self.assertNotIn(TARGET + "1", visited)

    def test_execution_records_pending_never_repeats_and_uses_exact_text(self):
        with tempfile.TemporaryDirectory() as directory:
            bot = CommentRevisit(data_dir=directory)
            bot.state_path = Path(directory) / "state.json"
            plan = {"source": SOURCE, "candidates": [
                {"number": 1, "username": "person", "url": TARGET, "status": "ready"},
                {"number": 2, "username": "other", "url": TARGET + "3", "status": "ready"},
            ]}
            def visit(url, label, comment_text):
                self.assertEqual(comment_text, "测试")
                bot.state["articles"][url] = {"comment": "pending"}
                return False
            bot.visit_article = Mock(side_effect=visit)
            result = bot.execute_plan(plan, {1}, ["测试"])
            self.assertEqual(result[0]["status"], "pending")
            bot.execute_plan(plan, {1}, ["测试"])
            bot.visit_article.assert_called_once()
            saved = json.loads(bot.state_path.read_text(encoding="utf-8"))
            record = next(iter(saved["revisits"].values()))
            self.assertEqual(record["source"], SOURCE)
            self.assertEqual(record["username"], "person")
            self.assertEqual(record["status"], "pending")

    def test_failure_does_not_stop_next_person_and_quota_stops_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            bot = CommentRevisit(data_dir=directory)
            bot.state_path = Path(directory) / "state.json"
            plan = {"source": SOURCE, "candidates": [
                {"number": n, "username": str(n), "url": TARGET + str(n), "status": "ready"} for n in (1, 2)]}
            bot.visit_article = Mock(side_effect=[RuntimeError("navigation failure"), True])
            results = bot.execute_plan(plan, {1, 2}, ["测试"])
            self.assertEqual([r["status"] for r in results], ["error", "confirmed"])
            bot.dianNum = bot.state["count"] = 50
            bot.visit_article.reset_mock()
            bot.execute_plan(plan, {1}, ["测试"])
            bot.visit_article.assert_not_called()
            with self.assertRaises(ValueError):
                bot.execute_plan(plan, {3}, ["测试"])


@unittest.skipUnless(os.environ.get("CSDN_DOM_BROWSER_TESTS") == "1", "可选本地浏览器 DOM 测试")
class BrowserDomTests(unittest.TestCase):
    def test_top_level_comments_and_article_labels_in_real_browser(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.set_content("""
                <div id="pcCommentSideBox"><ul class="comment-list">
                  <li class="comment-line-box" data-commentid="1"><div class="comment-list-item">
                    <div class="user-box"><a class="name-href" href="https://blog.csdn.net/person">Person</a></div>
                    <a href="https://blog.csdn.net/not_author">body link</a>
                  </div><ul class="comment-list"><li class="comment-line-box" data-commentid="2">
                    <div class="comment-list-item"><div class="user-box">
                    <a class="name-href" href="https://blog.csdn.net/reply">Reply</a>
                    </div></div></li></ul></li></ul></div>
                <div class="comment-list"><li class="comment-line-box" data-commentid="3">background duplicate</li></div>
                <div class="blog-list-box"><span>置顶</span><a href="https://blog.csdn.net/person/article/details/1">A</a></div>
                <div class="blog-list-box"><span>转载</span><a href="https://blog.csdn.net/person/article/details/2">B</a></div>
                <div class="blog-list-box"><span>原创</span><a href="https://blog.csdn.net/person/article/details/3">C</a></div>
                """)
                rows = page.evaluate("() => {" + COMMENT_ROWS_JS + "}")
                self.assertEqual(rows, [{"id": "1", "href": "https://blog.csdn.net/person", "name": "Person"}])
                articles = page.evaluate("() => {" + ARTICLE_ROWS_JS + "}")
                self.assertTrue(articles[0]["pinned"])
                self.assertTrue(articles[1]["reprint"])
                self.assertFalse(articles[2]["pinned"])
                self.assertFalse(articles[2]["reprint"])
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
