"""Only test explicit public proxies against HTTPS IP echo services; no cookies."""
import argparse
import ipaddress
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


def check(proxy):
    parsed = urlsplit(proxy)
    if (parsed.scheme not in ('http', 'socks5') or parsed.username or parsed.password
            or not parsed.port or parsed.path or parsed.query or parsed.fragment
            or not ipaddress.ip_address(parsed.hostname).is_global):
        raise ValueError('Only explicit public http://IP:port or socks5://IP:port endpoints are allowed')
    curl_proxy = proxy.replace('socks5://', 'socks5h://', 1)
    results = []
    for url, key in [('https://api.ipify.org?format=json', 'ip'), ('https://httpbin.org/ip', 'origin')]:
        result = subprocess.run(['curl', '--disable', '--silent', '--show-error', '--fail',
            '--connect-timeout', '8', '--max-time', '15', '--max-filesize', '4096',
            '--noproxy', '', '--proxy', curl_proxy, url], capture_output=True, text=True, timeout=20)
        row = {'url': url, 'curl_exit': result.returncode, 'ok': False}
        if result.returncode == 0:
            try:
                value = json.loads(result.stdout)[key]
                addresses = [str(ipaddress.ip_address(item.strip())) for item in value.split(',')]
                row.update(ok=True, exit_ips=addresses)
            except (ValueError, KeyError, TypeError, AttributeError):
                row['error'] = 'Unexpected IP echo response'
        else:
            row['error'] = result.stderr.strip()[:250]
        results.append(row)
    return {'proxy': proxy, 'https_passed': all(row['ok'] for row in results), 'checks': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proxy', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= len(args.proxy) <= 12:
        parser.error('Test 1–12 explicitly selected proxies per run')
    if args.output.exists():
        parser.error('Output already exists')
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(check, args.proxy))
    report = {'checked_at': datetime.now(timezone.utc).isoformat(),
              'scope': 'per-request proxy only; TLS verification enabled; no login cookies; no CSDN visits',
              'results': rows}
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
