"""有限次数访问自己的文章，记录页面阅读数；默认只预览计划。"""
import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from csdn_social_automation_bot import CSDN


COUNTER_JS = """
return Array.from(document.querySelectorAll(
  '.simple-meta-row .simple-meta-entry, .article-info-box .read-count'))
  .filter(e => e.getClientRects().length &&
    (e.matches('.read-count') || /阅读/.test(e.textContent)))
  .map(e => ({text: e.textContent.trim(), title: e.getAttribute('title') || ''}));
"""


def parse_counter(text):
    text = text.strip()
    match = re.fullmatch(
        r'(?:阅读(?:量|数)?\s*[:：]?\s*)?'
        r'((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*([kKwW万千]?)\s*(\+?)'
        r'\s*(?:次?阅读|次)?', text)
    if not match:
        return None
    number, unit, plus = match.groups()
    exact = not unit and not plus and '.' not in number
    return {'display': text, 'count': int(number.replace(',', '')) if exact else None,
            'approximate': not exact}


class VisitProbe(CSDN):
    def read_counter(self):
        readings = []
        for row in self.myBrowser.execute_script(COUNTER_JS):
            for text in (row['title'], row['text']):
                reading = parse_counter(text)
                if reading:
                    readings.append(reading)
        return next((row for row in readings if row['count'] is not None),
                    readings[0] if readings else None)

    def sample(self, article, account):
        self.myBrowser.get(article)
        current = self.article_url(self.myBrowser.current_url)
        if not current or current.rsplit('/', 1)[-1] != article.rsplit('/', 1)[-1]:
            raise RuntimeError('文章发生跳转或未正常打开，停止验证')
        cookie = self.myBrowser.get_cookie('UserName')
        if not cookie or cookie.get('value', '').casefold() != account.casefold():
            raise RuntimeError('登录账号发生变化或登录失效，停止验证')
        canonical = self.myBrowser.find_elements(By.CSS_SELECTOR, 'link[rel="canonical"]')
        target = self.article_url(canonical[0].get_attribute('href')) if canonical else current
        if not target or target.rsplit('/', 1)[-1] != article.rsplit('/', 1)[-1]:
            raise RuntimeError('无法核对文章标识，停止验证')
        parsed = urlsplit(target)
        if parsed.hostname != 'blog.csdn.net' or parsed.path.split('/')[1].casefold() != account.casefold():
            raise RuntimeError('无法确认文章属于登录账号，停止验证')
        reading = WebDriverWait(self.myBrowser, 15).until(lambda driver: self.read_counter())
        return {'observed_at': datetime.now(timezone.utc).isoformat(), 'article': target, **reading}

    def probe(self, article, samples, interval, output):
        article = self.article_url(article)
        if not article or type(samples) is not int or not 2 <= samples <= 10:
            raise ValueError('需要有效文章 URL，采样次数必须为 2–10')
        if type(interval) is not int or not 60 <= interval <= 86400:
            raise ValueError('访问间隔必须为 60–86400 秒')
        cookie = self.myBrowser.get_cookie('UserName')
        if not cookie or not cookie.get('value'):
            raise RuntimeError('请先登录')
        report = {'article': article, 'planned_samples': samples, 'interval_seconds': interval,
                  'status': 'running', 'samples': [], 'observed_delta': None,
                  'note': '差值仅代表页面显示变化，不能证明本次访问被计数，也不能排除其他读者或统计延迟。'}
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        # 独占创建，避免覆盖已有验证记录；访问前先确认报告可写。
        with output.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
        try:
            for index in range(samples):
                if index:
                    print(f'等待 {interval} 秒后进行下一次采样；Ctrl+C 可停止。', flush=True)
                    time.sleep(interval)
                row = self.sample(article, cookie['value'])
                report['samples'].append(row)
                first = report['samples'][0]['count']
                report['observed_delta'] = row['count'] - first if first is not None and row['count'] is not None else None
                output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
                print(f"采样 {index + 1}/{samples}：{row['display']}；显示差值：{report['observed_delta']}", flush=True)
            report['status'] = 'completed'
        except KeyboardInterrupt:
            report['status'] = 'interrupted'
            raise
        except Exception as exc:
            report['status'] = 'failed'
            report['error_type'] = type(exc).__name__
            raise
        finally:
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('article', help='自己的 CSDN 文章 URL')
    parser.add_argument('--samples', type=int, default=3, help='采样次数 2–10，包含首次基线访问，默认 3')
    parser.add_argument('--interval', type=int, default=300, help='相邻采样间隔秒数 60–86400，默认 300')
    parser.add_argument('--output', type=Path, help='新的 JSON 报告路径，不覆盖已有文件')
    parser.add_argument('--execute', action='store_true', help='启动浏览器并执行；省略则只预览配置')
    args = parser.parse_args()
    article = CSDN.article_url(args.article)
    if not article or not 2 <= args.samples <= 10 or not 60 <= args.interval <= 86400:
        parser.error('需要有效 CSDN 文章 URL；samples 为 2–10；interval 为 60–86400 秒')
    output = args.output or Path(__file__).resolve().parent / 'Chrome' / (
        'visit-probe-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    print(f'文章：{article}\n计划：{args.samples} 次采样（含基线），间隔 {args.interval} 秒\n报告：{output}')
    if not args.execute:
        print('仅预览；未启动浏览器或访问文章。加 --execute 才执行。')
        return
    if output.exists():
        parser.error('报告文件已存在，请指定新路径')
    bot = VisitProbe()
    try:
        bot.start_browser()
        bot.probe(article, args.samples, args.interval, output)
    except KeyboardInterrupt:
        print('已停止，已有采样保留在报告中。')
    finally:
        if bot.myBrowser is not None:
            bot.myBrowser.quit()


if __name__ == '__main__':
    main()
