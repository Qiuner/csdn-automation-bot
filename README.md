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

 一个csdn自动支持好友的脚本。有红包互动、私信链接回复、评论区回复等多种功能。

+ 该脚本目前有几个模块
  + 红包互动
  + 聊天界面互三
  + 找到单项关注
  + 评论区回复（未实现）

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
+ 这时候就要根据自己评论区来回复了（功能尚未完成），评论区回复，能使得回复你的人一定会回复到

![image-20250625160213416](https://raw.githubusercontent.com/Qiu-JW/tokens/main/2025/6/image-20250625160213416.png)

+ 在这个页面进行回复，设计原则为尽量少请求，多用模拟方式（模拟方式不会被封，用一年多了（仅测试，为学习。））



## 使用方式

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

![image-20250625160914444](https://raw.githubusercontent.com/Qiu-JW/tokens/main/2025/6/image-20250625160914444.png)

$$
本脚本仅用于学习和技术研究目的，旨在帮助他人理解评论功能的实现原理。
请勿将本脚本用于刷评论、骚扰他人或任何违反平台规定的行为。
使用者请遵守相关法律法规和平台服务协议，因不当使用造成的后果与作者无关。
脚本仅用于学习，不得用于任何商业或非法用途。
$$

