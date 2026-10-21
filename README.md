# 该脚本仅用于学习！

> 本脚本仅用于学习和技术研究目的，旨在帮助他人理解评论功能的实现原理。
>
> 请勿将本脚本用于刷评论、骚扰他人或任何违反平台规定的行为。
>
> 使用者请遵守相关法律法规和平台服务协议，因不当使用造成的后果与作者无关。

> This script is for educational and technical research purposes only.
>
> It is intended to help others understand how automated comment systems work.
>
> Do not use this script for spam, harassment, or any actions that violate platform policies.
>
> The author is not responsible for any misuse or consequences arising from its use.



# csdn-automation-bot

基于 Python + Selenium 的 CSDN 浏览器自动化工具。当前功能及验证范围统一记录在下表，下面的截图主要展示历史界面。

## 功能总览

| 功能 | 入口 / 行为 | 当前状态与限制 |
| --- | --- | --- |
| 指定博客文章互动 | 主脚本读取 `web/boke.txt`，处理主页文章 | 支持点赞、收藏、评论及状态防重；新版页面定位已只读实测，真实提交未重新验证 |
| 聊天文章处理 | 主脚本扫描有未读消息的会话 | 每个会话默认最多取末尾 5 个去重链接；支持 `dry_run=True` 和会话数量上限；3 个会话的只读扫描已实测 |
| 单向关注提醒 | 聊天中的“已关注”关系 | 只覆盖有未读消息的会话，不是完整关注列表；只读模式不发送提醒 |
| 红包互动 | 主脚本读取红包列表并检查详情 | 支持只读检查及过期跳过；新版社区侧栏已适配，但实测样本无可见红包卡片，真实领取未验证 |
| 按评论者回访 | `web/comment_revisit.py` | 默认预览一级评论者及其非置顶原创文章；已实测提取候选；执行需要显式参数和选择对象 |
| 自有文章访问计数验证 | `web/visit_probe.py` | 默认预览计划；显式执行后有限次数、固定间隔采样阅读数，仅允许核实属于登录账号的文章；本地验证通过，尚未线上计数实测 |
| 页面定位诊断 | `tools/check_dom.py` | 读取新旧页面 DOM 匹配数量，不提交互动操作 |
| 消息中心评论通知自动回复 | — | 尚未实现 |

“访问计数验证”记录页面显示变化，不承诺增加有效访问量，也不将打开次数等同于真实读者数。主脚本仍是会执行互动的入口；需要只读验证时使用对应只读入口或参数。

## 功能介绍

### 红包互动

+ 红包互动会进入csdn红包页面抢红包，再对发红包的人进行互三互关，是比较重要的功能。

![image-20250625160120679](https://raw.githubusercontent.com/Qiu-JW/tokens/main/2025/6/image-20250625160120679.png)

### 聊天界面互三

![image-20250625160139741](https://raw.githubusercontent.com/Qiu-JW/tokens/main/2025/6/image-20250625160139741.png)

+ 会自动去找链接进行互三，但是个君子功能。因为你给别人互了，别人可能不给你互。

### 找到单项关注

![image-20250625160201405](https://raw.githubusercontent.com/Qiu-JW/tokens/main/2025/6/image-20250625160201405.png)

+ 互关显示为好友，否则为已关注
+ 找到单项关注后会发句互关共勉

### 评论区回复

![image-20250625160206478](https://raw.githubusercontent.com/Qiu-JW/tokens/main/2025/6/image-20250625160206478.png)

+ 有时候你给别人三了，别人却不给你三，占了你每天互三名额。
+ 新增独立入口：从指定文章提取直接评论者，预览其最新非置顶原创文章，再选择对象回访。用法见下方“按文章评论者回访”。消息中心的评论通知自动回复尚未实现。

![image-20250625160213416](https://raw.githubusercontent.com/Qiu-JW/tokens/main/2025/6/image-20250625160213416.png)

+ 在这个页面进行回复，设计原则为尽量少请求，多用模拟方式（模拟方式不会被封，用一年多了（仅测试，为学习。））



## 使用方式

### 自有文章访问计数验证

先预览计划，不启动浏览器、不访问文章：

```powershell
python web/visit_probe.py "自己的文章URL" --samples 3 --interval 300
```

确认计划后，增加 `--execute`，手动登录后开始采样：

```powershell
python web/visit_probe.py "自己的文章URL" --samples 3 --interval 300 --execute
```

- 默认共 3 次访问（包括首次基线），每次读取结束后等待 300 秒，再开始下一次；不创建系统定时任务，进程退出即停止。
- `--samples` 支持 2–10，`--interval` 支持 60–86400 秒。只使用同一个浏览器会话，不接入主程序循环。
- 每次核对登录账号、文章 ID 和 canonical 作者。无法确认归属、读取失败或跳转异常时停止，不自动重试；首次归属检查本身需要打开文章。
- 报告默认保存在 `web/Chrome/visit-probe-时间戳.json`；可通过 `--output` 指定新路径，不覆盖已有报告。Ctrl+C 后保留已有采样。
- 报告记录采样时间、显示阅读数和可计算的显示差值；`1.7k`、`2万` 等取整值标为近似值，不计算精确增量。显示差值无法排除其他读者、缓存或统计延迟，不能据此证明测试访问被平台计数。
- 不点赞、不收藏、不评论、不私信、不领取红包。本地测试不代表线上有效访问量已经增加。

### 按文章评论者回访（2026-10-17）

在项目根目录运行。默认只读取页面和生成候选名单，不执行点赞、收藏、评论：

    python web/comment_revisit.py "https://qiuner.blog.csdn.net/article/details/157251513" --max-users 5

确认候选规则符合预期后，准备 web/ping.txt（UTF-8，每行一条完整评论），运行：

    python web/comment_revisit.py "https://qiuner.blog.csdn.net/article/details/157251513" --max-users 5 --execute

登录后会生成带序号的候选名单，输入 1,3 等序号执行选中的对象；直接回车取消。评论随机选择文件中的一行原文，不附加默认宣传文本。可用 --comment-file 路径 指定其他文本文件，用 --select 1,3 代替交互输入；序号仅对应本次生成的名单，不跨运行保存选择。

- 只读取一级评论作者，不处理楼中楼回复、评论正文链接或 @ 用户；按账号去重，排除登录用户和来源文章作者。--blacklist 路径 可指定每行一个账号的黑名单。
- 评论区滚动及“加载更多/查看更多评论/展开全部评论/下一页”均有次数上限。默认最多 20 轮；连续两轮等待未发现新评论时结束，并明确提示名单可能未完整加载，不能据此保证已读取全部评论。
- 主页按 ?type=lately 顺序扫描，跳过明确标记置顶、转载、翻译的卡片，再访问详情确认作者和“原创”标记；默认检查最多 20 篇候选文章、最多加载 3 批主页列表。不符合条件或页面异常的用户会跳过并记录原因。
- --max-users、--max-loads、--max-articles 可调整对应上限，范围均为 1–100。每次执行有限结束，不接入原主脚本的无限循环，不发送私信、不领取红包。
- 共用账号状态及每天 50 次评论提交尝试额度。按来源文章、评论者、目标文章保存回访结果；同一来源中已完成或评论待确认的用户不再进入名单。失败对象可在之后重新预览，已提交但结果不明的评论不自动重发。
- 预览和执行汇总写入 web/Chrome/bot-state-账号摘要-revisit-plan.json；账号状态中的 revisits 保存回访历史，articles 保存评论防重记录。

验证范围：已通过本地真实浏览器 DOM 测试和回访流程单元测试；2026-10-20 线上只读验证提取了 2 位评论者，并找到其中一位符合条件的原创文章。真实端到端提交尚未重新验证；当前站点若发生变化会跳过或报错，需结合预览结果核对。

### 修复版启动与状态记录（2026-10-15）

以下说明优先于后文旧版便携浏览器说明：

- 需要 Python 3.10+ 和 Selenium：先运行 `python -m pip install selenium`。
- 两个主脚本都从脚本所在的 web 目录读取 config.txt、boke.txt 和 ping.txt，不再依赖终端工作目录。
- tools/install_gui.py 将浏览器配置保存到 web/config.txt，主程序自动读取；手动配置支持 CHROME_BROWSER_PATH 和 CHROME_DRIVER_PATH，值为带引号的路径字符串。
- 未指定路径时，优先查找原有便携浏览器/驱动；找不到则交给 Selenium 查找系统 Chrome 和管理驱动，首次可能需要联网。指定的配置路径无效时明确报错。
- 登录后复用同一浏览器，不再关闭重开；运行记录按账号保存在 web/Chrome/bot-state-*.json，勿上传这些文件或同时运行多个实例。
- 每天最多 50 次评论提交尝试，按电脑本地日期重置；超时也占用一次配额，避免重复提交。重启不会清零。
- 点赞、收藏分别确认状态；已点赞仍可继续完成收藏和评论。没有可用收藏夹时停止该篇操作，请先在网页创建收藏夹。
- 评论看到成功提示才确认；私信观察本次发送响应的成功码及消息 ID，不把输入框清空或气泡出现当作发送成功。
- 评论/私信在提交前记录 pending；结果不明时不自动重发。人工核对后，可在停止程序的情况下备份并检查对应账号状态文件：确认成功改为 confirmed，确认未发送才删除对应记录。不要删除整个文件清空配额。
- 聊天只处理收到的 CSDN 文章链接，按会话和文章去重；“单向关注提醒”仍仅覆盖有未读消息的已关注会话，不是完整关注列表扫描。
- 聊天每个会话默认只检查页面中末尾 5 个去重文章链接，避免一次遍历大量历史链接；可通过 `csdn_hu_chat(max_articles=...)` 调整（1–100）。`max_conversations` 限制本轮会话条数；`dry_run=True` 只读取候选，不访问候选文章、不发送私信或关注提醒。打开会话仍可能使平台将消息标为已读。
- 已兼容新版文章侧栏入口、原创标记和社区评论侧栏；进入聊天 iframe 前等待外层加载遮罩消失。浏览器采用 DOM 就绪加载策略，并设置 40 秒导航上限，避免长期等待图片、广告等资源。
- Ctrl+C 可退出并关闭自动化浏览器；主循环异常会退避重试。文章处理仅关闭本次创建的标签页。
- 评论区自动回复尚未实现；真实评论、私信与红包到账仍需单独实测。

测试命令：python -B -m unittest discover -s tools -p "test_*.py" -v（DOM 检查相关测试还需要 Playwright，见 tools/DOM_CHECKS.md）。

### 一、通用要求

- 在 `web/` 目录下添加与你当前 Chrome 版本匹配的 **便携版 Chrome**（包含 `chrome.exe` 和 `chromedriver.exe`）。
- 或手动修改代码中 `CHROME_BROWSER_PATH` 的路径，指向本地 Chrome 安装地址。

### 二、下载对应版本的 ChromeDriver：

访问以下任意链接，下载与你的 Chrome 浏览器版本一致的 `ChromeDriver`：

- https://googlechromelabs.github.io/chrome-for-testing/ （官方推荐）
- https://chromedriver.chromium.org/downloads

在页面中搜索你的浏览器版本（如 `131.0.6778.86`）并下载对应驱动。

示例目录结构如下：

```
Chrome/
├── Application/
│   ├── chrome.exe
├── chromedriver.exe  ← 用新下载的覆盖此处
```

------

## `csdn_social_automation_bot.py` 使用方式

该版本默认使用相对路径方式启动内嵌浏览器，适合将便携版 Chrome 放置于项目目录下 `Chrome/` 目录中。

### 使用步骤：

1. 将便携版 Chrome 解压到 `web/Chrome/` 下。

2. 确保结构如下：

   ```
   web/
   ├── csdn_social_automation_bot.py
   ├── Chrome/
       ├── Application/
       │   ├── chrome.exe
       ├── chromedriver.exe
   ```

3. 直接运行脚本：

   ```
   python csdn_social_automation_bot.py
   ```

+ 无需额外配置，自动从默认路径读取浏览器和驱动。

------

## `csdn_social_automation_bot1.py` 

该版本新增了浏览器路径常量 `CHROME_BROWSER_PATH`，支持显式指定 Chrome 安装位置。

### 使用步骤：

1. 修改文件顶部的常量值为你 Chrome 浏览器的实际路径：

   ```
   CHROME_BROWSER_PATH = "C:/Users/Administrator/AppData/Local/Google/Chrome/Application/chrome.exe"
   ```

2. 确保你下载了与你浏览器匹配的 `chromedriver.exe`，并放置在：

   ```
   web/Chrome/Application/chromedriver.exe
   ```

3. 运行脚本：

   ```
   python csdn_social_automation_bot1.py
   ```



+ 或使用tools目录下的**install_gui.py**辅助完成

![image-20250625160224044](https://raw.githubusercontent.com/Qiu-JW/tokens/main/2025/6/image-20250625160224044.png)

## 我不会使用，怎么办？

+ 给项目点个星星，然后扫下面二维码进入群聊，群里大佬云集，公告有具体办法，也可也在群里找我让我帮你配置。
![Uploading 微信图片_20251010203704_143_319 - 副本.jpg…]()


$$
本脚本仅用于学习和技术研究目的，旨在帮助他人理解评论功能的实现原理。
请勿将本脚本用于刷评论、骚扰他人或任何违反平台规定的行为。
使用者请遵守相关法律法规和平台服务协议，因不当使用造成的后果与作者无关。
脚本仅用于学习，不得用于任何商业或非法用途。
$$

