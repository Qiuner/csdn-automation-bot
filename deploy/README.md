# 服务器部署

独立 Docker 项目：`csdn-automation-bot`。部署目录：`/home/fmops/csdn-automation-bot`。
容器以非 root 用户运行，限制 1 CPU、1 GiB 内存；独立命名卷保存浏览器登录资料及运行报告。
容器启动只运行虚拟桌面，不自动执行主脚本或定时访问。不要同时启动多个使用同一浏览器配置目录的脚本。

## Windows 连接桌面

在本机 PowerShell 中执行并保留窗口：

```powershell
& 'D:/Code/csdn-automation-bot/deploy/Open-Desktop.ps1'
```

浏览器打开 `http://127.0.0.1:16088/vnc.html`，点击 Connect。
隧道沿用本机 fmops 密钥及 ASKPASS，不读取或输出密钥口令。
服务只映射到服务器 `127.0.0.1:6088`，不需要开放公网防火墙端口。
桌面刚启动时是空白的；启动下面的 Python 脚本后才会出现浏览器。

## 执行访问计数验证

通过已有 `Connect-FutureMaker.ps1` 登录服务器后执行：

```sh
cd /home/fmops/csdn-automation-bot
sudo docker compose -p csdn-automation-bot -f deploy/compose.yaml exec bot \
  python web/visit_probe.py '自己的文章URL' --samples 3 --interval 300
```

以上只预览计划。需要实际运行时追加 `--execute`：在远程桌面完成 CSDN 登录，再回 SSH 终端按回车继续。
默认含基线共 3 次访问，每次读取后等待 300 秒。不会执行评论、私信或领红包。
不自动复制本机 Cookie；登录会话及 JSON 报告保留在容器 `/app/web/Chrome` 对应的命名卷中。
SSH 终端必须保持连接；这里没有安装无人值守定时任务。

## 24 小时后台采样

`web/visit_schedule.py` 使用现有登录会话，按固定时间槽读取自己的文章阅读数。
`deploy/start-visit-day.sh` 启动文章 `166116044` 的单次后台任务：每 180 秒一次，持续 24 小时，正常情况下最多 480 次采样。
任务独立于 SSH 连接；到期停止，不会每天重复。不要重复运行启动脚本。
报告逐次原子更新，记录采样时间、阅读数和相对基线差值；错过的时间槽不补发。
账号失效、文章归属不符或页面错误会停止并保留报告。容器或服务器重启会中断任务，不会自动恢复；此时报告可能保留 `running`，需结合进程及日志判断。

本次任务：2026-10-21 00:10 至 2026-10-22 00:10（America/Los_Angeles）。
报告：`/app/web/Chrome/visit-day-20261021T071013Z.json`；日志：同路径 `.log`。
启动后首次实际读数为 422。查看进度：

```sh
cd /home/fmops/csdn-automation-bot
sudo docker compose -p csdn-automation-bot -f deploy/compose.yaml exec -T bot \
  cat /app/web/Chrome/visit-day-20261021T071013Z.json
```

后台任务运行期间不要运行其他共享浏览器配置的脚本或重建容器。

### 本次随机间隔调整

2026-10-21 05:09（America/Los_Angeles）按用户要求切换为每次采样完成后随机等待 50–70 秒。
旧任务已停止，旧报告保留；新任务仍于 2026-10-22 00:10 结束，没有延长运行窗口。
新报告：`/app/web/Chrome/visit-random-20261021T120908Z.json`，日志同名 `.log`。
新阶段基线为 523 阅读，旧阶段基线为 422；两个阶段分别记录变化。
每条记录的 `next_wait_seconds` 保存所选随机等待时间，实际访问间隔还包含页面加载耗时。
启动入口为 `deploy/start-visit-random.sh <含时区的原截止时间>`；不要在任务运行期间重复执行。
读取当前进度时，将上面的报告文件名替换为新报告文件名。

## 检查与维护

```sh
cd /home/fmops/csdn-automation-bot
sudo docker compose -p csdn-automation-bot -f deploy/compose.yaml ps
sudo docker compose -p csdn-automation-bot -f deploy/compose.yaml exec -T bot python - < deploy/smoke.py
sudo docker compose -p csdn-automation-bot -f deploy/compose.yaml exec -T bot \
  python -B -m unittest discover -s tools -p 'test_*.py'
```

服务器单元测试不默认开启可选 Playwright DOM 浏览器测试；有界面 Chromium 实际启动由 smoke.py 单独验证。
查看日志使用 `logs --tail 80`；暂停桌面使用 `stop`，恢复使用 `start`。不要使用 `down -v` 删除登录和运行数据。

更新代码后运行 `build` 和 `up -d`；更新前先停止正在执行的任务，并记录当前镜像 ID 供回滚。
上传源代码时只选择 Python 源码、测试、部署文件和 README；不要上传 `web/Chrome`、Windows `config.txt`、私钥或口令文件。
