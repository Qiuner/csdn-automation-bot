# 单独测试代理连通性

`check_proxies.py` 仅对明确指定的公共 IP 代理执行 HTTPS 测试，不改系统、Docker 或浏览器代理设置。
每次 curl 子进程显式指定代理，禁用 curl 配置文件，保留 TLS 证书校验，不带 Cookie、不访问 CSDN，也不在代理失败时回退直连。
SOCKS5 使用远端 DNS。每轮最多 12 个候选，4 路并发，每请求最多 15 秒。

```sh
python3 tools/check_proxies.py --proxy http://PUBLIC_IP:PORT --output new-proxy-report.json
```

候选来源：https://github.com/proxifly/free-proxy-list

2026-10-21 从部署服务器实测 4 个 HTTP 和 4 个 SOCKS5 代理，每个分别访问 api.ipify.org 和 httpbin.org 的 HTTPS IP 回显地址：

- 没有候选同时通过两项测试。
- 3 个 HTTP 代理连接失败或超时。
- 1 个 HTTP 代理首次对 ipify 成功、对 httpbin 超时；复测两个地址均连接超时。
- 4 个 SOCKS5 代理均至少出现一次 TLS 证书校验失败，未放宽校验。
- 服务器直连两个测试地址均成功，并返回服务器出口 IP。

没有将这些候选接入正在运行的采样浏览器。测试通过只能说明当时对指定目标连通，不代表能访问 CSDN、可靠性长期有效或会增加阅读数。
测试报告存放于服务器项目目录 `proxy-check-20261021.json`、`proxy-check-retest-20261021.json`，未提交运行数据。
