import re
import os
import time
from datetime import datetime
import random
import ast
import json
import hashlib
from pathlib import Path
from urllib.parse import urlsplit
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.webdriver import WebDriver as BrowserWebDriver

csdn_url = "https://www.csdn.net"
csdn_hongbao_url = "https://bbs.csdn.net/?type=4&header=0&utm_source=wwwtab"
csdn_chat_url = "https://i.csdn.net/#/msg/chat"
DEFAULT_COMMENT_TEXT = "{} 也欢迎您来逛逛我的博客哦~~在此提前感谢您对我的互/三/支持~~"
DEFAULT_SEND_TEXT = "13已三，也真诚邀请您来逛逛我的博客"
COMMENT_ENTRY_XPATH = "//*[@class='toolbox-list']//*[@class='tool-item-comment'] | //*[@class='go-side-comment']"
class CSDN:
    def __init__(self, data_dir=None):
        self.curDir = str(Path(data_dir) if data_dir is not None else Path(__file__).resolve().parent)
        self.config = {}
        config_path = Path(self.curDir) / "config.txt"
        if config_path.exists():
            for line in config_path.read_text(encoding="utf-8").splitlines():
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                key, separator, value = line.partition("=")
                if not separator or key.strip() not in ("CHROME_BROWSER_PATH", "CHROME_DRIVER_PATH"):
                    raise ValueError(f"不支持的配置项：{line}")
                parsed = ast.literal_eval(value.strip())
                if not isinstance(parsed, str):
                    raise ValueError(f"路径必须是字符串：{key}")
                self.config[key.strip()] = parsed
        BoKe = "https://Qiuner.blog.csdn.net"
        DianPing = "测试"
        bokeFile = f'{self.curDir}/boke.txt'
        pingFile = f'{self.curDir}/ping.txt'
        if os.path.exists(bokeFile):
            with open(bokeFile, "r", encoding="utf-8") as objFile:
                BoKe = objFile.read()
        if os.path.exists(pingFile):
            with open(pingFile, "r", encoding="utf-8") as objFile:
                DianPing = objFile.read()
        self.myBrowser: BrowserWebDriver | None = None
        self.hongNum = 0
        self.dianNum = 0
        self.dList = DianPing.strip().split("\n")
        self.dNum = len(self.dList) - 1
        self.dianNum_max = 50
        self.bList = BoKe.strip().split("\n")
        if "https://Qiuner.blog.csdn.net" not in self.bList:
            self.bList.append("https://Qiuner.blog.csdn.net")
        self.iframe_flag = False
        self.state_path = None
        self.state = {"date": datetime.now().date().isoformat(), "count": 0, "articles": {}, "messages": {}}

    def start_browser(self):
        driverPath = self.config.get("CHROME_DRIVER_PATH", "")
        if driverPath:
            driverPath = str((Path(self.curDir) / driverPath).resolve())
            if not Path(driverPath).is_file():
                raise FileNotFoundError(f"ChromeDriver 不存在：{driverPath}")
        else:
            for relative in ("Chrome/Application/chromedriver.exe", "Chrome/chromedriver.exe"):
                candidate = Path(self.curDir) / relative
                if candidate.is_file():
                    driverPath = str(candidate)
                    break
        browserPath = f"{self.curDir}/Chrome/Application/chrome.exe"
        browserPath = self.config.get("CHROME_BROWSER_PATH", browserPath)
        if browserPath:
            browserPath = str((Path(self.curDir) / browserPath).resolve())
        if browserPath and not Path(browserPath).is_file():
            if "CHROME_BROWSER_PATH" in self.config:
                raise FileNotFoundError(f"Chrome 不存在：{browserPath}")
            browserPath = ""  # 交由 Selenium 查找系统 Chrome。
        chrome_data_path = str(Path(self.curDir) / "Chrome" / "chromeData")
        browserService = Service(executable_path=driverPath) if driverPath else Service()
        options_chrome = webdriver.ChromeOptions()
        options_chrome.page_load_strategy = 'eager'
        options_chrome.add_argument('--window-size=1920,1080')
        options_chrome.add_argument('--lang=zh_CN.UTF-8')
        options_chrome.add_argument('--disable-infobars')
        options_chrome.add_argument('--disable-gpu')
        options_chrome.add_argument('--log-level=2')
        options_chrome.add_argument("–-allow-running-insecure-content")
        options_chrome.add_argument('ignore-certificate-errors')
        options_chrome.add_argument('--no-sandbox')
        options_chrome.add_argument('--silent')
        options_chrome.add_experimental_option("excludeSwitches", ['enable-automation', "enable-logging"])
        options_chrome.add_argument('--user-data-dir=' + chrome_data_path)
        prefs = {
            "download.prompt_for_download": False,
            "credentials_enable_service": False,  # 禁用密码保存
            "profile.password_manager_enabled": False,  # 禁用密码保存
            'profile.default_content_setting_values': {
                'notifications': 2,  # 显示通知
                "geolocation": 2  # 允许地理位置 1：允许 2：禁止
            }
        }
        options_chrome.add_experimental_option('prefs', prefs)
        if browserPath:
            options_chrome.binary_location = browserPath
        self.myBrowser = BrowserWebDriver(options=options_chrome, service=browserService)
        self.myBrowser.set_page_load_timeout(40)
        self.myBrowser.get(csdn_url)
        input("手动登录后，回车继续：")
        cookie = self.myBrowser.get_cookie("UserName")
        if not cookie or not cookie.get("value"):
            raise RuntimeError("未检测到登录用户，请完成登录后重试")
        account_id = hashlib.sha256(cookie["value"].encode("utf-8")).hexdigest()[:24]
        self.state_path = Path(self.curDir) / "Chrome" / f"bot-state-{account_id}.json"
        if self.state_path.exists():
            self.state = json.loads(self.state_path.read_text(encoding="utf-8"))
            if (not isinstance(self.state, dict) or not isinstance(self.state.get("date"), str)
                    or type(self.state.get("count")) is not int or self.state["count"] < 0
                    or not isinstance(self.state.get("articles"), dict)
                    or not isinstance(self.state.get("messages"), dict)):
                raise ValueError("运行记录格式异常，请检查状态文件，不能自动清零")
            if (any(not isinstance(record, dict) or record.get("comment") not in (None, "pending", "confirmed")
                    for record in self.state["articles"].values())
                    or any(status not in ("pending", "confirmed") for status in self.state["messages"].values())):
                raise ValueError("运行记录状态异常，请检查状态文件")
        self.dianNum = self.state["count"]
        self.refresh_daily_limit()
        return self.myBrowser

    def find_ele(self, xpath, timeout=15):
        xpath = re.sub(r"(@class *= *'([^']+)')", r"contains(concat(' ', @class, ' '),' \2 ')", xpath)
        end_time = time.monotonic() + timeout
        while time.monotonic() <= end_time:
            try:
                for element in self.myBrowser.find_elements(By.XPATH, xpath):
                    if element.is_displayed():
                        return element
            except StaleElementReferenceException:
                pass
            time.sleep(0.2)
        return None

    def find_eles(self, xpath):
        time.sleep(5)
        xpath = re.sub(r"(@class *= *'([^']+)')", r"contains(concat(' ', @class, ' '),' \2 ')", xpath)
        myElements = self.myBrowser.find_elements(By.XPATH, xpath)
        return myElements

    def iframe_in(self, xpath):
        if self.iframe_flag:
            self.iframe_out()
        try:
            if xpath == "//iframe":
                xpath = "//iframe[starts-with(@src, 'https://im.csdn.net/') or starts-with(@src, '//im.csdn.net/')]"
            WebDriverWait(self.myBrowser, 20).until(lambda driver: not any(
                element.is_displayed() for element in driver.find_elements(By.CSS_SELECTOR, ".el-loading-mask")))
            WebDriverWait(self.myBrowser, 30).until(
                EC.frame_to_be_available_and_switch_to_it((By.XPATH, xpath))
            )
            WebDriverWait(self.myBrowser, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".main-chat-list"))
            )
            self.iframe_flag = True
        except Exception as e:
            self.myBrowser.switch_to.default_content()
            self.iframe_flag = False
            raise RuntimeError(f"聊天 iframe 未就绪，xpath: {xpath}") from e
        return True

    def iframe_out(self):
        if self.iframe_flag:
            self.myBrowser.switch_to.default_content()
            self.iframe_flag = False
            time.sleep(2)
        return True

    def page_close(self):
        AllHandles = self.myBrowser.window_handles
        num = len(AllHandles) - 1
        if num > 0:
            for j in range(num):
                self.myBrowser.switch_to.window(AllHandles[j+1])
                self.myBrowser.close()
            self.myBrowser.switch_to.window(AllHandles[0])
        return True

    def page_switch(self):
        AllHandles = self.myBrowser.window_handles
        if len(AllHandles) > 1:
            self.myBrowser.switch_to.window(AllHandles[-1])

    def csdn_hong_bao(self, dry_run=False):
        # 评论红包是懒加载的，先展开面板，再等待目标卡片。
        ele = self.find_ele("//*[@class='redpack-card']", timeout=3)
        if not ele:
            comment_entry = self.find_ele(
                COMMENT_ENTRY_XPATH + " | //*[@class='detail-shell-toolbar__item' and @class='is-comment']", timeout=3)
            if comment_entry and not self.find_ele(
                    "//*[@id='commentSideBoxshadow'] | //*[@class='detail-comment-side-mask']", timeout=1):
                self.myBrowser.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", comment_entry)
                comment_entry.click()
            reward_xpath = "//*[@class='comment-reward-item']"
            comment_id = re.search(r"#comments_(\d+)", str(self.myBrowser.current_url))
            if comment_id:
                reward_xpath += f"[@data-commentid='{comment_id.group(1)}']"
            # 侧栏打开后正文同名卡片仍可见，但已被遮罩覆盖。
            ele = self.find_ele("//*[@class='redpack-card'] | //*[@id='pcCommentSideBox']" + reward_xpath, timeout=10)
            if not ele:
                ele = self.find_ele(reward_xpath, timeout=10)
            if (ele and "redpack-card" not in (ele.get_attribute("class") or "").split()
                    and not ele.get_attribute("data-status")):
                try:
                    WebDriverWait(self.myBrowser, 10).until(lambda driver: ele.get_attribute("data-status"))
                except TimeoutException:
                    print("[红包] 卡片状态未就绪，跳过，不尝试领取")
                    return False
        if not ele:
            print("[红包] 未找到可见红包卡片，跳过")
            return False

        status = ele.get_attribute("data-status")
        card_classes = (ele.get_attribute("class") or "").split()
        if "redpack-card-overdue" in card_classes:
            status = "expired"
        if status in ("completed", "expired", "received"):
            print(f"[红包] 当前状态 {status}，跳过")
            return False
        if dry_run:
            print(f"[红包检查] 卡片已加载，状态：{status or '未知'}；未领取")
            return False

        try:
            if not self.find_ele("//*[@class='env-box']", timeout=1):
                self.myBrowser.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", ele)
                ele.click()
            open_btn = self.find_ele("//*[@class='env-box']//*[@class='red-openbtn']", timeout=15)
            if not open_btn:
                print("[红包] 无可用领取按钮，可能已领取、已结束或需要登录")
                return False
            # 已显示的历史收款结果不能算作本次成功。
            receipt_xpath = "//*[@class='env-box']//*[@class='my-receive']"
            if self.find_ele(receipt_xpath, timeout=1):
                print("[红包] 已有领取结果，跳过")
                return False
            open_btn.click()
            receipt = self.find_ele(receipt_xpath, timeout=20)
            if not receipt or not receipt.text.strip():
                print("[红包] 未确认领取成功，不增加计数")
                return False
            self.hongNum += 1
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 红包 +1 = {self.hongNum}，金额：{receipt.text.strip()}")
            return True
        except Exception as e:
            print(f"[错误] 领取红包时出错：{e}")
            return False
        finally:
            try:
                close_btn = self.find_ele("//*[@class='env-box']//*[@class='close-btn']", timeout=2)
                if close_btn:
                    close_btn.click()
            except Exception as e:
                print(f"[错误] 关闭红包弹窗时出错：{e}")

    def save_state(self):
        if self.state_path is None:
            raise RuntimeError("未加载账号运行记录，禁止提交操作")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.state_path)

    def refresh_daily_limit(self):
        today = datetime.now().date().isoformat()
        if self.state["date"] != today:
            self.state["date"] = today
            self.state["count"] = 0
            self.dianNum = 0
            if self.state_path is not None:
                self.save_state()
        return self.dianNum < self.dianNum_max

    @staticmethod
    def article_url(value):
        if not isinstance(value, str):
            return None
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError:
            return None
        host = parsed.hostname or ""
        standard = host == "blog.csdn.net" and re.fullmatch(r"/[^/]+/article/details/\d+/?", parsed.path)
        custom = re.fullmatch(r"[a-z0-9-]+\.blog\.csdn\.net", host) and re.fullmatch(r"/article/details/\d+/?", parsed.path)
        if (parsed.scheme not in ("http", "https") or not (standard or custom)
                or parsed.username or parsed.password or port not in (None, 80, 443)):
            return None
        return "https://" + host + parsed.path.rstrip("/")

    def csdn_dian_ping(self, bTxt="", comment_text=None):
        if not self.refresh_daily_limit():
            return False
        url = self.article_url(self.myBrowser.current_url) if self.myBrowser else None
        if not url:
            print("[文章] 非 CSDN 文章地址，跳过")
            return False
        record = self.state["articles"].setdefault(url, {})
        if record.get("comment") == "pending":
            print("[文章] 上次评论结果待确认，不自动重发")
            return False
        try:
            for entry_xpath, active_xpath, name in (
                ("//*[@id='is-like']/a | //*[@id='sidebar-like']",
                 "//*[@id='is-like']//img[@class='isactive'] | //*[@id='sidebar-like' and @class='active']", "点赞"),
                ("//*[@class='toolbox-list']//*[@class='is-collection'] | //*[@id='sidebar-collect']",
                 "//*[@id='is-collection-imgactive'] | //*[@id='sidebar-collect' and @class='active']", "收藏"),
            ):
                if self.find_ele(active_xpath, timeout=2):
                    continue
                entry = self.find_ele(entry_xpath)
                if not entry:
                    print(f"[文章] {name}入口不可用")
                    return False
                entry.click()
                if name == "收藏":
                    try:
                        # 默认收藏夹可能直接完成；否则只点尚未收藏的行。
                        if not self.find_ele(active_xpath, timeout=3):
                            button = self.find_ele("//*[@id='csdn-collection']//*[@class='collect-btn' and normalize-space(.)='收藏']", timeout=10)
                            if not button:
                                print("[文章] 无可用收藏夹，请先在网页创建收藏夹")
                                return False
                            button.click()
                        if not self.find_ele(active_xpath, timeout=10):
                            print("[文章] 未确认收藏成功")
                            return False
                    finally:
                        close = self.find_ele("//*[@class='csdn-collection-close']", timeout=1)
                        if close:
                            close.click()
                elif not self.find_ele(active_xpath, timeout=10):
                    print("[文章] 未确认点赞成功")
                    return False
            if record.get("comment") == "confirmed":
                return True
            if not self.find_ele("//*[@id='commentSideBoxshadow']", timeout=1):
                comment_entry = self.find_ele(COMMENT_ENTRY_XPATH)
                if not comment_entry:
                    return False
                self.myBrowser.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", comment_entry)
                comment_entry.click()
            editor = self.find_ele("//*[@class='comment-edit-box']//*[@class='comment-content']")
            submit = self.find_ele("//*[@class='comment-edit-box']//*[@class='btn-comment']")
            if not editor or not submit:
                print("[文章] 评论区不可提交")
                return False
            if (editor.get_attribute("value") or "").strip():
                print("[文章] 存在未发送草稿，保留并跳过")
                return False
            # 页面明确成功提示（包括待审核）才确认；先记录 pending 防止重复提交。
            success_xpath = "//*[not(*) and starts-with(normalize-space(.), '评论成功')]"
            if self.find_ele(success_xpath, timeout=1):
                print("[文章] 存在旧成功提示，本轮跳过")
                return False
            text = comment_text if comment_text is not None else DEFAULT_COMMENT_TEXT.format(random.choice(self.dList))
            editor.send_keys(text)
            WebDriverWait(self.myBrowser, 10).until(lambda driver: submit.is_enabled())
            record["comment"] = "pending"
            record["attempt_date"] = self.state["date"]
            self.dianNum += 1  # 配额按提交尝试计，超时也不自动释放。
            self.state["count"] = self.dianNum
            self.save_state()
            submit.click()
            if not self.find_ele(success_xpath, timeout=15):
                print("[文章] 评论结果待确认，不报告成功、不自动重发")
                return False
            record["comment"] = "confirmed"
            self.save_state()
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 【{bTxt}】文章操作已确认，今日提交次数：{self.dianNum}")
            return True
        except Exception as e:
            print(f"[错误] 文章操作失败：{e}")
            return False

    def visit_article(self, url, label, comment_text=None):
        url = self.article_url(url)
        if not url:
            return False
        origin = self.myBrowser.current_window_handle
        opened = None
        try:
            self.iframe_out()
            self.myBrowser.switch_to.new_window("tab")
            opened = self.myBrowser.current_window_handle
            self.myBrowser.get(url)
            if comment_text is None:
                return self.csdn_dian_ping(label)
            return self.csdn_dian_ping(label, comment_text=comment_text)
        finally:
            if opened in self.myBrowser.window_handles:
                self.myBrowser.switch_to.window(opened)
                self.myBrowser.close()
            if origin in self.myBrowser.window_handles:
                self.myBrowser.switch_to.window(origin)
            self.iframe_flag = False

    def csdn_hu_boke(self):
        for blog in self.bList:
            if not self.refresh_daily_limit():
                break
            if not blog:
                continue
            try:
                self.myBrowser.get(f"{blog}?type=lately")
                link = self.find_ele("//*[@class='blog-list-box']//a[contains(@href, '/article/details/')]")
                if link:
                    self.visit_article(link.get_attribute("href"), "长期")
            except Exception as e:
                print(f"[错误] 处理博客 {blog} 时出错：{e}")
        return True

    def csdn_hu_hong_bao(self, dry_run=False):
        self.myBrowser.get(csdn_hongbao_url)
        list_handle = self.myBrowser.current_window_handle
        list_url = self.myBrowser.current_url
        icon_xpath = "//*[contains(concat(' ', normalize-space(@class), ' '), ' red-packet-icon-mini ')]"
        try:
            WebDriverWait(self.myBrowser, 20).until(
                EC.presence_of_element_located((By.XPATH, icon_xpath))
            )
        except TimeoutException:
            print("[红包] 列表未加载或当前没有红包，结束本轮")
            return False
        claimed = False
        for i in range(30):
            before_handles = set(self.myBrowser.window_handles)
            try:
                icons = self.myBrowser.find_elements(By.XPATH, icon_xpath)
                if i >= len(icons):
                    if not icons:
                        break
                    self.myBrowser.execute_script("arguments[0].scrollIntoView({block:'end'})", icons[-1])
                    try:
                        WebDriverWait(self.myBrowser, 10).until(
                            lambda driver: len(driver.find_elements(By.XPATH, icon_xpath)) > i
                        )
                    except TimeoutException:
                        break
                    icons = self.myBrowser.find_elements(By.XPATH, icon_xpath)
                self.myBrowser.execute_script("arguments[0].scrollIntoView({block:'center'})", icons[i])
                icons[i].click()
                WebDriverWait(self.myBrowser, 15).until(
                    lambda driver: set(driver.window_handles) != before_handles
                    or driver.current_url != list_url
                )
                new_handles = [handle for handle in self.myBrowser.window_handles if handle not in before_handles]
                if new_handles:
                    self.myBrowser.switch_to.window(new_handles[-1])
                WebDriverWait(self.myBrowser, 15).until(
                    lambda driver: driver.current_url != "about:blank"
                    and driver.execute_script("return document.readyState") in ("interactive", "complete")
                )
                if self.csdn_hong_bao(dry_run=dry_run):
                    claimed = True
                    if not dry_run:
                        self.csdn_dian_ping("红包")
            except Exception as e:
                print(f"[错误] 处理第 {i + 1} 个红包图标时出错：{e}")
            finally:
                for handle in list(self.myBrowser.window_handles):
                    if handle not in before_handles:
                        self.myBrowser.switch_to.window(handle)
                        self.myBrowser.close()
                self.myBrowser.switch_to.window(list_handle)
                if self.myBrowser.current_url != list_url:
                    self.myBrowser.get(list_url)
                    try:
                        WebDriverWait(self.myBrowser, 20).until(
                            EC.presence_of_element_located((By.XPATH, icon_xpath))
                        )
                    except TimeoutException:
                        break
        return claimed

    def send_chat_message(self, text, key):
        if key in self.state["messages"]:
            return self.state["messages"][key] == "confirmed"
        editor = self.find_ele("//*[@id='messageText']")
        if not editor or not editor.is_enabled() or (editor.get_attribute("value") or "").strip():
            print("[聊天] 输入框不可用或有草稿，跳过")
            return False
        # 页面先乐观显示气泡，不能据此判成功；仅观察本次表单的服务端响应。
        self.myBrowser.execute_script("""
            const expected = arguments[0];
            if (window.__csdnBotSendObserver) throw new Error('Observer already installed');
            const original = XMLHttpRequest.prototype.send;
            const observer = {original, result: null};
            window.__csdnBotSendObserver = observer;
            observer.wrapper = function(body) {
                if (body instanceof FormData && body.get('toUsername') && body.get('messageBody') === expected) {
                    this.addEventListener('load', function() {
                        try {
                            const data = this.responseType === 'json' ? this.response : JSON.parse(this.responseText);
                            observer.result = this.status >= 200 && this.status < 300
                                && Number(data.code) === 0 && !!(data.data && data.data.messageId);
                        } catch (_) { observer.result = false; }
                    }, {once: true});
                }
                return original.apply(this, arguments);
            };
            XMLHttpRequest.prototype.send = observer.wrapper;
        """, text)
        try:
            editor.send_keys(text)
            self.state["messages"][key] = "pending"
            self.save_state()
            editor.send_keys(Keys.ENTER)
            WebDriverWait(self.myBrowser, 20).until(lambda driver: driver.execute_script(
                "return window.__csdnBotSendObserver && window.__csdnBotSendObserver.result !== null"))
            if not self.myBrowser.execute_script("return window.__csdnBotSendObserver.result"):
                print("[聊天] 服务端未确认发送成功，保留待确认记录")
                return False
            self.state["messages"][key] = "confirmed"
            self.save_state()
            return True
        except Exception as e:
            print(f"[聊天] 发送结果待确认，不自动重发：{e}")
            return False
        finally:
            self.myBrowser.execute_script("""
                const observer = window.__csdnBotSendObserver;
                if (observer) {
                    if (XMLHttpRequest.prototype.send === observer.wrapper)
                        XMLHttpRequest.prototype.send = observer.original;
                    delete window.__csdnBotSendObserver;
                }
            """)

    def csdn_hu_chat(self, dry_run=False, max_conversations=100, max_articles=5):
        if not 1 <= max_conversations <= 100 or not 1 <= max_articles <= 100:
            raise ValueError("会话和文章数量上限必须为 1–100")
        self.myBrowser.get(csdn_chat_url)
        visited = set()
        visited_routes = set()
        try:
            self.iframe_in("//iframe")
            try:
                WebDriverWait(self.myBrowser, 20).until(lambda driver:
                    driver.find_elements(By.CSS_SELECTOR, ".main-chat-list .msg-item_inner"))
            except TimeoutException:
                print("[聊天] 等待后仍无会话，可能列表为空或加载失败，本轮跳过")
                return True
            for _ in range(max_conversations):
                if not self.refresh_daily_limit():
                    break
                candidate = None
                relation = ""
                for item in self.myBrowser.find_elements(By.CSS_SELECTOR, ".main-chat-list .msg-item_inner"):
                    if not item.is_displayed():
                        continue
                    unread = item.find_elements(By.CSS_SELECTOR, ".unread-num")
                    if not any(mark.is_displayed() for mark in unread):
                        continue
                    names = item.find_elements(By.CSS_SELECTOR, ".who-msg")
                    relations = item.find_elements(By.CSS_SELECTOR, ".msg-relation")
                    if not names or not relations:
                        continue
                    relation = relations[0].text.strip()
                    if relation not in ("好友", "粉丝", "已关注"):
                        continue
                    fingerprint = item.id
                    if fingerprint in visited:
                        continue
                    visited.add(fingerprint)
                    candidate = item
                    break
                if candidate is None:
                    break
                previous_route = self.myBrowser.execute_script("return window.location.href")
                already_selected = candidate.find_elements(By.XPATH, "ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' active-msg-item ')]")
                candidate.click()
                if not already_selected:
                    try:
                        WebDriverWait(self.myBrowser, 20).until(lambda driver:
                            driver.execute_script("return window.location.href") != previous_route)
                    except TimeoutException:
                        print("[聊天] 会话切换超时，跳过当前条目")
                        continue
                editor = self.find_ele("//*[@id='messageText']", timeout=20)
                if not editor:
                    continue
                frame_url = self.myBrowser.execute_script("return window.location.href")
                frame_location = urlsplit(frame_url) if isinstance(frame_url, str) else None
                conversation_path = (frame_location.fragment.split("?", 1)[0] or frame_location.path) if frame_location else ""
                if (not frame_location or frame_location.hostname != "im.csdn.net"
                        or not re.fullmatch(r"/(?:i?chat)/[^/?#]+/?", conversation_path)):
                    print("[聊天] 无法确认会话标识，跳过")
                    continue
                if frame_url in visited_routes:
                    continue
                visited_routes.add(frame_url)
                if relation == "已关注":
                    print("[聊天] 处理有未读消息的单向关注会话")
                    if dry_run:
                        print("[聊天检查] 单向关注提醒已跳过，未发送消息")
                        continue
                    key = hashlib.sha256((frame_url + "|follow-reminder").encode()).hexdigest()
                    self.send_chat_message("互关共勉！", key)
                    continue
                try:
                    WebDriverWait(self.myBrowser, 20).until(lambda driver: not any(
                        element.is_displayed() for element in driver.find_elements(By.CSS_SELECTOR, ".msg-content-box .loading")))
                except TimeoutException:
                    print("[聊天] 消息加载超时，跳过当前会话")
                    continue
                urls = []
                for link in self.myBrowser.find_elements(By.CSS_SELECTOR, ".msg-content .msg-item:not(.msg-item-right) a[href]"):
                    url = self.article_url(link.get_attribute("href"))
                    if url and url not in urls:
                        urls.append(url)
                urls = urls[-max_articles:]
                if dry_run:
                    print(f"[聊天检查] 本会话读取到 {len(urls)} 个候选文章链接，未访问文章或发送消息")
                    continue
                for url in urls:
                    if not self.refresh_daily_limit():
                        break
                    key = hashlib.sha256((frame_url + "|" + url).encode()).hexdigest()
                    if key in self.state["messages"]:
                        continue
                    try:
                        complete = self.visit_article(url, "聊天")
                    finally:
                        self.iframe_in("//iframe")
                    if self.myBrowser.execute_script("return window.location.href") != frame_url:
                        raise RuntimeError("当前会话发生变化，停止回复")
                    if complete:
                        self.send_chat_message(DEFAULT_SEND_TEXT, key)
        finally:
            self.iframe_out()
        return True

    def run(self):
        try:
            self.start_browser()
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 开始执行")
            tNum = 0
            failures = 0
            while True:
                try:
                    self.refresh_daily_limit()
                    self.csdn_hu_boke()
                    self.csdn_hu_chat()
                    for _ in range(3):
                        tNum += 1
                        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 第 {tNum} 轮，抢红包！")
                        self.csdn_hu_hong_bao()
                        time.sleep(500 + random.randint(1, 200))
                    failures = 0
                    time.sleep(60)
                except Exception as e:
                    failures += 1
                    delay = min(300, 5 * 2 ** min(failures - 1, 6))
                    print(f"[错误] 主循环异常，{delay} 秒后重试：{e}")
                    time.sleep(delay)
        except KeyboardInterrupt:
            print("已停止运行")
        finally:
            if self.myBrowser is not None:
                try:
                    self.myBrowser.quit()
                except Exception as e:
                    print(f"[错误] 关闭浏览器失败：{e}")


if __name__ == '__main__':
    try:
        CSDN().run()
    except Exception as e:
        print(e.__str__())
