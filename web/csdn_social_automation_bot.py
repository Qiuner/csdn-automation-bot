import re
import os
import time
from datetime import datetime
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.webdriver import WebDriver as BrowserWebDriver

csdn_url = "https://www.csdn.net"
csdn_hongbao_url = "https://bbs.csdn.net/?type=4&header=0&utm_source=wwwtab"
csdn_chat_url = "https://i.csdn.net/#/msg/chat"
DEFAULT_COMMENT_TEXT = "{} 也欢迎您来逛逛我的博客哦~~在此提前感谢您对我的互/三/支持~~"
DEFAULT_SEND_TEXT = "13已三，也真诚邀请您来逛逛我的博客"
class CSDN:
    def __init__(self):
        self.curDir = os.getcwd().replace("\\", "/")
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

    def start_browser(self):
        if not os.path.exists(f"{self.curDir}/Chrome"):
            raise Exception("ERROR: 未发现浏览器")
        driverPath = f"{self.curDir}/Chrome/Application/chromedriver.exe"
        browserPath = f"{self.curDir}/Chrome/Application/chrome.exe"
        chrome_data_path = f'{self.curDir}/Chrome/chromeData'
        browserService = Service(executable_path=driverPath)
        options_chrome = webdriver.ChromeOptions()
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
        options_chrome.binary_location = browserPath
        myBrowser = BrowserWebDriver(options=options_chrome, service=browserService)
        myBrowser.get(csdn_url)
        input("手动登录后，回车继续：")
        myBrowser.quit()
        # options_chrome.add_argument('--headless')  # 谷歌无头模式
        self.myBrowser = BrowserWebDriver(options=options_chrome, service=browserService)
        return self.myBrowser

    def find_ele(self, xpath, timeout=15):
        xpath = re.sub(r"(@class *= *'([^']+)')", r"contains(concat(' ', @class, ' '),' \2 ')", xpath)
        myElement = None
        end_time = time.time() + timeout
        while time.time() <= end_time:
            try:
                myElement = self.myBrowser.find_element(By.XPATH, xpath)
            except:
                myElement = None
                time.sleep(0.2)
            if myElement:
                break
        return myElement

    def find_eles(self, xpath):
        time.sleep(5)
        xpath = re.sub(r"(@class *= *'([^']+)')", r"contains(concat(' ', @class, ' '),' \2 ')", xpath)
        myElements = self.myBrowser.find_elements(By.XPATH, xpath)
        return myElements

    def iframe_in(self, xpath):
        if self.iframe_flag:
            self.iframe_out()
        try:
            self.myBrowser.switch_to.frame(self.find_ele(xpath))
            self.iframe_flag = True
        except Exception as e:
            print(f"[错误] 切换至iframe失败，xpath: {xpath}，异常信息：{e}")
        time.sleep(2)
        return True

    def iframe_out(self):
        if self.iframe_flag:
            self.myBrowser.switch_to.parent_frame()
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

    def csdn_hong_bao(self):
        ele = self.find_ele("//*[@class='redpack-card']", timeout=10)
        if not ele:
            ele = self.find_ele("//*[@class='comment-reward-item']", timeout=10)
        if ele:
            ele.click()
            time.sleep(5)
            try:
                self.find_ele("//*[@class='red-openbtn']", timeout=10).click()
                self.hongNum += 1
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 红包 +1 = {self.hongNum}")
                time.sleep(10)
            except Exception as e:
                print(f"[错误] 打开红包时出错：{e}")
            try:
                self.find_ele("//*[@class='env-box']//*[@class='close-btn']").click()
            except Exception as e:
                print(f"[错误] 关闭弹窗时出错：{e}")
            time.sleep(1)
        return True

    def csdn_dian_ping(self, bTxt=""):
        flag = False
        if self.dianNum > self.dianNum_max:
            return flag
        try:
            like_xpath = "//*[@id='is-like']/a"
            collection_xpath = "//*[@class='toolbox-list']//*[@class='is-collection']"
            collection_btn_xpath = "//*[@class='collect-btn']"
            comment_xpath = "//*[@class='toolbox-list']//*[@class='tool-item-comment']"
            content_xpath = "//*[@class='comment-edit-box']//*[@class='comment-content']"
            btnContent_xpath = "//*[@class='comment-edit-box']//*[@class='btn-comment']"

            if self.find_ele(like_xpath):
                like_active_check = "//*[@id='is-like']//img[@class='isactive' and @style='display: block;']"
                if self.find_ele(like_active_check, timeout=3):
                    return False
                else:
                    dp = self.dList[random.randint(0, self.dNum)]
                    time.sleep(2)
                    self.find_ele(like_xpath).click()
                    time.sleep(2)
                    self.find_ele(collection_xpath).click()
                    time.sleep(2)
                    self.find_ele(collection_btn_xpath).click()
                    time.sleep(2)
                    self.find_ele(comment_xpath).click()
                    time.sleep(1)
                    # self.find_ele(content_xpath).send_keys(
                    #     f"{dp} 也欢迎您来逛逛我的博客哦~~在此提前感谢您对我的互/三/支持~~")
                    self.find_ele(content_xpath).send_keys(DEFAULT_COMMENT_TEXT.format(dp))
                    time.sleep(1)
                    self.find_ele(btnContent_xpath).click()
                    self.dianNum += 1
                    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 【{bTxt}】互三 +1 = {self.dianNum}")
                    time.sleep(10 + random.randint(1, 10))
                    flag = True
        except Exception as e:
            print(f"[错误] 执行点赞/评论/收藏操作时出错：{e}")
        return flag

    def csdn_hu_boke(self):
        # 指定的博客主页进行点赞
        if self.dianNum > self.dianNum_max:
            return True
        for b in self.bList:
            if not b:
                continue
            try:
                self.myBrowser.get(f"{b}?type=lately")
                time.sleep(5)
                bo_first_xpath = "//*[@class='navList-box']//*[@class='mainContent']//*[@class='blog-list-box']//*[@class='blog-list-box-top']"
                self.find_ele(bo_first_xpath).click()
                time.sleep(5)
                self.page_switch()
                self.csdn_dian_ping("长期")
                time.sleep(2)
            except Exception as e:
                print(f"[错误] 处理博客 {b} 时出错：{e}")
            self.page_close()
        return True

    def csdn_hu_hong_bao(self):
        self.myBrowser.get(csdn_hongbao_url)
        time.sleep(5)
        for i in range(30):
            try:
                eleObj = self.find_ele(f"(//*[@class='red-packet-icon-mini'])[{i + 1}]", timeout=20)
                if not eleObj:
                    eleObj = self.find_ele(f"(//*[@class='red-packet-icon-mini'])[{i}]", timeout=20)
                    self.myBrowser.execute_script("arguments[0].scrollIntoView({block:'center'})", eleObj)
                    time.sleep(2)
                    eleObj = self.find_ele(f"(//*[@class='red-packet-icon-mini'])[{i + 1}]", timeout=20)
                if eleObj:
                    eleObj.click()
                    time.sleep(5)
                    self.page_switch()
                    time.sleep(2)
                    self.csdn_hong_bao()
                    time.sleep(2)
                    self.csdn_dian_ping("红包")
            except Exception as e:
                print(f"[错误] 处理第 {i + 1} 个红包图标时出错：{e}")
            self.page_close()

    def csdn_hu_chat(self):
        self.myBrowser.get(csdn_chat_url)
        time.sleep(5)
        item_xpath = (
            "//*[@class='msg-item_inner' and (.//span[contains(text(),'好友')] or .//span[contains(text(),'粉丝')]) and .//*[@class='unread-num']]"
        )
        item_no_xpath = "//*[@class='main-chat-list']//*[@class='msg-item_inner' and (.//*[@class='unread-num']) and (.//*[normalize-space(text())='已关注'])]"
        print("寻找单向关注")
        self.iframe_in("//iframe")
        while True:
            eleObj = self.find_ele(item_no_xpath, timeout=10)
            if eleObj:
                eleObj.click()
                time.sleep(5)
                sendEle = self.find_ele("//*[@id='messageText']")
                if sendEle:
                    time.sleep(1)
                    sendEle.send_keys("互关共勉！")
                    time.sleep(1)
                    sendEle.send_keys(Keys.ENTER)
                    time.sleep(2)
            else:
                break
        self.iframe_out()
        print("好友粉丝互三")

        while True:
            if self.dianNum > self.dianNum_max:
                return True
            self.iframe_in("//iframe")
            eleObj = self.find_ele(item_xpath, timeout=10)
            if eleObj:
                eleObj.click()
                time.sleep(5)
                eles = self.find_eles("//*[@class='msg-content']//a")
                if eles:
                    eles[-1].click()
                    time.sleep(5)
                    self.iframe_out()
                    self.page_switch()
                    dian_flag = self.csdn_dian_ping("聊天")
                    time.sleep(2)
                    self.page_close()

                    if dian_flag:
                        self.iframe_in("//iframe")
                        sendEle = self.find_ele("//*[@id='messageText']")
                        if sendEle:
                            time.sleep(1)
                            sendEle.send_keys(DEFAULT_SEND_TEXT)
                            # sendEle.send_keys("13已三，也真诚邀请您来逛逛我的博客")
                            time.sleep(1)
                            sendEle.send_keys(Keys.ENTER)
                            time.sleep(2)
                    self.iframe_out()
            else:
                break
        self.iframe_out()
        return True

    def run(self):
        self.start_browser()
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 开始执行")
        tNum = 0
        while True:
            try:
                self.csdn_hu_boke()
                print("开始聊天互三")
                self.csdn_hu_chat()
                for i in range(3):
                    tNum += 1
                    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 第 {tNum} 轮，抢红包！")
                    self.csdn_hu_hong_bao()
                    time.sleep(500 + random.randint(1, 200))
                time.sleep(60)
            except Exception as e:
                print(f"[错误] 主循环中发生异常：{e}")


if __name__ == '__main__':
    try:
        CSDN().run()
    except Exception as e:
        print(e.__str__())
    print("60秒后自动关闭")
    time.sleep(60)
