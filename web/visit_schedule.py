"""按固定或随机间隔采样自己的文章，到期停止；默认仅预览。"""
import argparse
import json
import math
import random
import signal
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from visit_probe import VisitProbe


def run_schedule(bot, article, interval, hours, output, jitter=0, until=None):
    article = bot.article_url(article)
    if not article or type(interval) is not int or not 60 <= interval <= 86400:
        raise ValueError('需要有效文章和 60–86400 秒间隔')
    if type(hours) is not int or not 1 <= hours <= 24:
        raise ValueError('运行时间必须为 1–24 小时')
    if type(jitter) is not int or jitter < 0 or interval - jitter < 50 or interval + jitter > 86400:
        raise ValueError('随机间隔范围必须在 50–86400 秒内')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    origin = time.monotonic()
    duration = hours * 3600
    if until is not None:
        if until.tzinfo is None:
            raise ValueError('截止时间必须包含时区')
        duration = (until - started).total_seconds()
        if not 0 < duration <= hours * 3600:
            raise ValueError('截止时间必须在未来且不超过指定运行时长')
    deadline = origin + duration
    report = {'article': article, 'interval_seconds': interval,
              'jitter_seconds': jitter,
              'started_at': started.isoformat(),
              'ends_at': (started + timedelta(seconds=duration)).isoformat(),
              'status': 'running', 'samples': [], 'observed_delta': None,
              'note': '差值仅为显示变化，不能排除其他读者或统计延迟。错过的采样不补发；异常时停止。'}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)

    def save():
        temporary = output.with_suffix('.tmp')
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(output)

    try:
        bot.start_browser()
        cookie = bot.myBrowser.get_cookie('UserName')
        if not cookie or not cookie.get('value'):
            raise RuntimeError('登录失效，停止任务')
        while time.monotonic() < deadline:
            row = bot.sample(article, cookie['value'])
            first = report['samples'][0]['count'] if report['samples'] else row['count']
            row['observed_delta'] = row['count'] - first if first is not None and row['count'] is not None else None
            report['samples'].append(row)
            report['observed_delta'] = row['observed_delta']
            save()
            print(f"采样 {len(report['samples'])}: {row['display']}; 差值 {row['observed_delta']}", flush=True)
            # 固定时间槽；慢请求或暂停后跳过错过的槽位，不突发补采样。
            now = time.monotonic()
            if jitter:
                # 随机模式从本次采样完成后等待，避免慢请求后突发访问。
                wait_seconds = random.randint(interval - jitter, interval + jitter)
                row['next_wait_seconds'] = wait_seconds
                save()
                next_slot = now + wait_seconds
            else:
                next_slot = origin + (math.floor((now - origin) / interval) + 1) * interval
            time.sleep(max(0, min(next_slot, deadline) - now))
        report['status'] = 'completed'
    except KeyboardInterrupt:
        report['status'] = 'interrupted'
        raise
    except Exception as exc:
        report['status'] = 'failed'
        report['error_type'] = type(exc).__name__
        raise
    finally:
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        save()
        if bot.myBrowser is not None:
            bot.myBrowser.quit()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('article')
    parser.add_argument('--interval', type=int, default=180)
    parser.add_argument('--hours', type=int, default=24)
    parser.add_argument('--jitter', type=int, default=0, help='随机等待幅度，例如 interval=60、jitter=10 表示 50–70 秒')
    parser.add_argument('--until', type=datetime.fromisoformat, help='含时区的绝对截止时间，切换设置时可保留原截止时间')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not VisitProbe.article_url(args.article) or not 60 <= args.interval <= 86400 or not 1 <= args.hours <= 24:
        parser.error('需要有效文章；interval 为 60–86400 秒；hours 为 1–24')
    if args.jitter < 0 or args.interval - args.jitter < 50 or args.interval + args.jitter > 86400:
        parser.error('随机间隔范围必须在 50–86400 秒内')
    if args.until is not None and (args.until.tzinfo is None or not 0 < (args.until - datetime.now(timezone.utc)).total_seconds() <= args.hours * 3600):
        parser.error('截止时间必须带时区、在未来且不超过指定运行时长')
    print(f'每 {args.interval} 秒采样，持续 {args.hours} 小时；报告 {args.output}', flush=True)
    print(f'随机幅度 {args.jitter} 秒；绝对截止时间 {args.until}', flush=True)
    if not args.execute:
        return
    # Linux 上锁定共享浏览器目录，避免同时启动多个定时任务。
    import fcntl
    lock_path = Path(__file__).resolve().parent / 'Chrome' / 'visit-schedule.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

        def stop(signum, frame):
            raise KeyboardInterrupt()

        signal.signal(signal.SIGTERM, stop)
        run_schedule(VisitProbe(), args.article, args.interval, args.hours, args.output, args.jitter, args.until)


if __name__ == '__main__':
    main()
