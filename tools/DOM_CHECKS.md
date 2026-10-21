# DOM 检查与修复记录

## 只读检查

`check_dom.py` 只导航页面、检查元素数量与可见性，不点击按钮、输入内容或提交操作。

依赖：Python、Playwright，以及 Playwright Chromium。首次安装：

```powershell
python -m pip install playwright
python -m playwright install chromium
```

在项目根目录运行，手动登录后回到终端按回车：

```powershell
python tools/check_dom.py --login --output dom-report.json 'https://i.csdn.net/#/msg/chat' 'https://bbs.csdn.net/?type=4&header=0&utm_source=wwwtab'
```

文章检查可追加实际文章 URL。登录会话默认保存在本机 `%LOCALAPPDATA%/csdn-automation-bot/inspection-profile`，不放入仓库；后续可省略 `--login` 复用。不要同时运行两个使用同一 profile 的检查进程。

报告区分 HTTP 状态、导航超时、登录跳转，以及每个 iframe 内的元素数量和可见数量。不记录聊天正文、输入内容或 Cookie。匹配为零不等于选择器失效：页面可能尚未加载、需要登录，或者弹窗尚未打开。

## 2026-10-20 新版页面只读复核

- 新版文章使用 `#sidebar-like`、`#sidebar-collect`、`.go-side-comment`；旧入口在本次样本中均不存在。已增加兼容定位，并根据侧栏 `active` 状态判断已有点赞/收藏。
- 原创标记使用 `.simple-meta-row .simple-meta-entry`；回访预览实际提取到 2 位直接评论者，并找到其中一位符合条件的原创文章。
- 社区评论入口为 `.detail-shell-toolbar__item.is-comment`，展开 `.detail-comment-side` 后再检查红包卡片。样本 `620522732` 展开后仍无可见红包卡片，安全跳过；不能据此确认真实领取功能可用。
- 聊天出现过外层 `.el-loading-mask` 遮挡 iframe 点击，已在切换前等待消失。跟踪还确认单会话包含大量历史文章链接，逐篇处理导致长时间运行；现默认每个会话最多处理末尾 5 个去重链接。
- `csdn_hu_chat(dry_run=True, max_conversations=3, max_articles=2)` 真实运行约 37.9 秒完成，3 个会话各读取 2 个候选链接，没有访问候选文章或发送消息。打开会话可能改变平台未读状态。
- 42 项测试通过，包含本地真实浏览器 DOM 回归。此次未点赞、收藏、评论、发送私信或领取红包；真实提交链路仍未验证。
- 现场报告：`D:/DevCache/codex-home/visualizations/2026/10/21/01a15d04-9ef0-74f3-9fb6-fe41b5dd0b47/verify_fixes.json`。

## 2026-10-15 实际检查

- 公开博客主页的旧文章选择器仍能匹配，红包列表的旧图标选择器也能匹配。
- 未登录的文章检查返回过 HTTP 403；登录后的同一文章返回 HTTP 200。
- 登录后的文章页面仍含点赞入口、收藏入口、评论入口、评论框和提交按钮。
- 评论框和提交按钮初始隐藏；点击评论入口展开面板后两者均可见。该检查未输入或提交内容。
- 聊天 iframe 地址为 `https://im.csdn.net/ichat`；早期采样为零，等待列表加载完成后 `.main-chat-list` 和 `.msg-item_inner` 存在。
- 点赞图标采用 `display:none` 等样式格式，不能依赖 `style='display: block;'` 的精确字符串判断。

## 已实施修复

两个主脚本同步修改：查找可见元素、依据图标可见性识别已点赞、定向进入聊天 iframe、等待聊天列表挂载、iframe 失败时恢复顶层并报告错误。

红包流程还会先展开评论区，读取 `data-status` 并跳过 `completed`、`expired`、`received`，点击后必须看到 `.my-receive` 金额才计数；红包列表遍历会等待图标加载、处理新标签页并返回列表。

```powershell
python -B -m unittest discover -s tools -p 'test_*.py' -v
```

## 尚未验证

### 2026-10-15 红包专项复查

- 实际成功领取仍为 0；不能将此前点赞、收藏、评论、私信成功推及红包到账。
- 首页向底部滚动后红包图标从 10 增至 20，先前检查的 8 个文章样本不代表全部记录。
- 社区帖 620522732 明确显示已过期，已领取 130/150 个、41.75/50.00 元；修复后主脚本识别 redpack-card-overdue 并跳过。
- 社区帖 620510087 仍显示“开”，页面已加载的数据却显示 receiveAmount=sendAmount=50、receiveMoney=totalMoney=50.00、myReceiveMoney 为空。执行一次授权领取点击后没有出现收款结果，主脚本返回 False、计数 0；未重复提交。无法据此确认具体服务端错误或到账。
- 新发现的兼容问题：社区弹窗使用 .pre-open / .opened 而不是文章页 #preOpen / #opened；改为在可见 .env-box 内定位领取按钮和个人收款结果；已打开的弹窗不再重复点击背景卡片。两份脚本同步。
- 新增社区弹窗及过期状态回归用例，30 项自动化测试通过，git diff --check 通过。测试输出中的 0.12 元是模拟值，不是真实领取收入。
- 仍需要一个确实可领取的红包及成功收款结果，才能完成到账验收。社区红包领取提示会自动关注发布者并加入社区。

### 2026-10-15 授权真实操作验证（17:06–17:16）

- 用户指定文章：`https://qiuner.blog.csdn.net/article/details/157251513`，评论及私信均使用“测试”。主脚本 `csdn_dian_ping` 返回 True，点赞和收藏激活图标均可见；评论页面明确提示“评论成功,审核后显示”，状态记录为 confirmed。该结果确认提交成功，不代表审核通过。
- 从该文章已有评论选取“千逐68”（2502_92709686），核对会话路由后调用主脚本 `send_chat_message`，服务端响应确认成功，状态记录为 confirmed，页面显示一条本次“测试”消息。未继续向其他用户发送。
- 红包列表提取的 8 个文章红包均为 completed，最终均被脚本跳过；领取计数为 0，真实到账仍未验证。
- 实测修复：支持自定义博客域名文章；评论红包优先选择侧栏内卡片、等待 data-status 加载，避免正文卡片被遮罩挡住；侧栏已打开时不重复点击入口。两份脚本同步。
- 28 项自动化测试通过；`git diff --check` 通过。新增侧栏遮罩与延迟状态回归覆盖。
- 成功截图保存在本机 `D:/DevCache/codex-home/visualizations/2026/10/16/01a14255-d557-7ec0-a1c6-463258207672/csdn-live-test/`：`article-after.png` 含评论成功提示及点赞收藏状态；`message-success.png` 含发送结果；`reward-ended.png` 为已结束红包检查现场，不能作为领取成功证明。
- 下方只读检查记录为此前阶段，真实操作验证以本节为准。

### 2026-10-15 主脚本实跑补充

- 默认 Selenium 启动成功，系统 Chrome 为 155；项目自己的 chromeData 尚未登录。
- 用匹配的 ChromeDriver 145 和此前手动登录的检查 profile，实际执行 start_browser、iframe_in、csdn_hong_bao(dry_run=True)。未复制或输出 Cookie。
- 聊天列表容器挂载时会话数为 0，等待后为 40；补充列表数据等待，避免过早结束。受限运行 csdn_hu_chat 后确认会话输入框可见；文章操作及发送方法被测试替身拦截，本次未发送消息。
- 文章评论面板展开后，真实 Selenium 能找到可见输入框和提交按钮。
- 红包文章的评论入口曾被固定顶部栏遮挡，真实点击报 ElementClickInterceptedException；两份脚本均改为先将入口滚动至视口中央。重跑红包 dry-run 能加载卡片，领取计数保持 0；卡片状态未知不能视为可领取。
- Playwright 只读报告识别到 10 个红包列表入口。tools/live-dom-report.json 保留该次页面检查结果。
- 本次没有真实点赞、收藏、评论、私信或领取红包，不能据此认定服务端提交链路已验证。

后续修复：配置路径固定到 web；登录后同一浏览器复用；账号隔离的原子状态文件；50 次提交尝试限额及跨天重置；文章动作分别确认；评论 pending 防重；聊天只接受对方发来的 CSDN 文章链接；私信通过本次页面 XHR 响应确认而非乐观气泡；文章标签页定向清理；主循环退避和退出关闭。

已读取当前收藏组件，确认收藏夹行内仍使用 collect-btn（“收藏”或“已收藏”）；实际账号弹窗未显示可用收藏夹行，代码会停止该篇操作并提示，未自动创建收藏夹。已读取当前评论脚本的“评论成功,审核后显示”提示和聊天发送响应格式。私信观察器已用离线浏览器模拟成功、拒绝、缺少消息 ID 和还原监听器；未真实发送。

尚未执行真实点赞、收藏确认、评论提交、私信发送或领红包。红包流程只完成了 DOM 和状态逻辑验证，没有用真实红包确认服务端领取结果。收藏确认按钮依赖弹窗，不能根据未打开弹窗时的零匹配直接判定失效。聊天输入框还需在选中具体会话后检查。测试通过仅覆盖定位与等待等基础行为，不代表完整业务链路恢复。
