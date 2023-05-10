# coding: utf-8
from json import loads
from time import sleep, time
from pickle import dump, load
from os.path import exists
from seleniumwire import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.common import exceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.service import Service
import gzip, json

class Concert(object):
    def __init__(self, driver_path, target_url):
        self.driver_path = driver_path  # 浏览器驱动地址
        self.target_url = target_url
        self.driver = None

    # 获取账号的cookie信息
    def get_cookie(self):
        self.driver.get(self.damai_url)
        print(u"###请点击登录###")
        self.driver.find_element(by=By.CLASS_NAME, value='login-user').click()
        while self.driver.title.find('大麦网-全球演出赛事官方购票平台') != -1:  # 等待网页加载完成
            sleep(1)
        print(u"###请扫码登录###")
        while self.driver.title == '大麦登录':  # 等待扫码完成
            sleep(1)
        dump(self.driver.get_cookies(), open("cookies.pkl", "wb"))
        print(u"###Cookie保存成功###")

    def set_cookie(self):
        try:
            cookies = load(open("cookies.pkl", "rb"))  # 载入cookie
            for cookie in cookies:
                cookie_dict = {
                    'domain': '.damai.cn',  # 必须有，不然就是假登录
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                    "expires": "",
                    'path': '/',
                    'httpOnly': False,
                    'HostOnly': False,
                    'Secure': False}
                self.driver.add_cookie(cookie_dict)
            print(u'###载入Cookie###')
        except Exception as e:
            print(e)

    def login(self):
        print(u'###开始登录###')
        self.driver.get(self.target_url)
        WebDriverWait(self.driver, 10, 0.1).until(EC.title_contains('商品详情'))
        self.set_cookie()

    def enter_concert(self):
        print(u'###打开浏览器，进入大麦网###')
        if not exists('cookies.pkl'):   # 如果不存在cookie.pkl,就获取一下
            self.driver = webdriver.Chrome(executable_path=self.driver_path)
            self.get_cookie()
            print(u'###成功获取Cookie，重启浏览器###')
            self.driver.quit()

        options = webdriver.ChromeOptions()
        # 禁止图片、js、css加载
        prefs = {"profile.managed_default_content_settings.images": 2,
                 "profile.managed_default_content_settings.javascript": 1,
                 'permissions.default.stylesheet': 2}
        mobile_emulation = {"deviceName": "Nexus 6"}
        options.add_experimental_option("prefs", prefs)
        options.add_experimental_option("mobileEmulation", mobile_emulation)
        # 就是这一行告诉chrome去掉了webdriver痕迹，令navigator.webdriver=false，极其关键
        options.add_argument("--disable-blink-features=AutomationControlled")

        # 更换等待策略为不等待浏览器加载完全就进行下一步操作
        capa = DesiredCapabilities.CHROME
        # normal, eager, none
        capa["pageLoadStrategy"] = "eager"
        driverP = Service(self.driver_path)
        self.driver = webdriver.Chrome(
            executable_path=self.driver_path, options=options, desired_capabilities=capa,service=driverP)
        # 登录到具体抢购页面
        self.login()
        self.driver.refresh()
        self.driver.get(self.target_url)

        # 确认页面刷新成功
        try:
            box = WebDriverWait(self.driver, 3, 0.1).until(
                EC.presence_of_element_located((By.ID, 'app')))
        except:
            raise Exception(u"***Error: 页面刷新出错***")

        try:
            buybutton = box.find_element(by=By.CLASS_NAME, value='buy__button')
            # 元素未加载完成会出现 buybutton.text = '' 的情况
            while True:
                if not buybutton.text :
                    sleep(0.1)
                else:
                    break
            buybutton_text: str = buybutton.text
        except Exception as e:
            raise Exception(f"***Error: buybutton 位置找不到***: {e}")


        buybutton.click()
        box = WebDriverWait(self.driver, 2, 0.1).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.sku-pop-wrapper')))

        try:
            # 日期选择
            toBeClicks = []
            # 选定场次
            session = WebDriverWait(self.driver, 2, 0.1).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'sku-times-card')))    # 日期、场次和票档进行定位
            session_list = session.find_elements(
                by=By.CLASS_NAME, value='bui-dm-sku-card-item')
            for i in session_list:
                i.click()
                sleep(0.5)
        except:
            print("遍历场次失败")

        details = []
        results = []
        for request in self.driver.requests:
            if request.response:
                if "mtop.alibaba.detail.subpage.getdetail" in request.url:
                    try:
                        _content = gzip.decompress(request.response.body).decode('utf-8')# 获取接口返回内容
                    except:
                        continue
                    try:
                        json_content = json.loads(_content)
                        details.append(json.loads(json_content['data']['result']))
                    except:
                        raise
        for i in details:
            try:
                performName = i['perform']['performName']
                for j in i['perform']['skuList']:
                    buyParam = j['itemId'] + "_1_" + j['skuId']
                    results.append(performName + " " + j['priceName'] + " 购买链接为：    " r"https://m.damai.cn/app/dmfe/h5-ultron-buy/index.html?buyParam=" + buyParam + r"&buyNow=true&exParams=%257B%2522channel%2522%253A%2522damai_app%2522%252C%2522damai%2522%253A%25221%2522%252C%2522umpChannel%2522%253A%2522100031004%2522%252C%2522subChannel%2522%253A%2522damai%2540damaih5_h5%2522%252C%2522atomSplit%2522%253A1%257D&spm=a2o71.project.0.bottom&from=appshare&sqm=dianying.h5.unknown.value.hlw_a2o71_28004194")
            except:
                raise
        for i in results:
            print(i)
        self.driver.quit()

if __name__ == '__main__':
    try:
        with open('./config.json', 'r', encoding='utf-8') as f:
            config = loads(f.read())
        con = Concert(config['driver_path'],config['target_url'])
        con.enter_concert()  # 进入到具体抢购页面
    except Exception as e:
        print(e)
        exit(1)
