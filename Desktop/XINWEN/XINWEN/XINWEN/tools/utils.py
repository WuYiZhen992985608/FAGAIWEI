# -*- coding: utf-8 -*-
import logging
from lxml import etree
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import urllib3
import re
import json

def obtain_text(url, xpath_str, coding='utf-8'):
    try:
        # return obtain_text_phantomJs(url, xpath_str)
        return obtain_text_Chrome(url, xpath_str,coding)
    except Exception as e:
        logging.error(e.__str__())
        logging.exception(e)

def obtain_text_firefox(url, xpath_str, coding='utf-8'):
    profile = webdriver.FirefoxOptions()
    profile.add_argument('--headless')
    profile.add_argument('--no-sandbox')
    # 设置代理服务器
    profile.set_preference('network.proxy.type', 1)
    #本地火狐浏览器配置
    browser = webdriver.Firefox(options=profile,
                                executable_path=r'D:\software\FireFoxPortable_v680_x32\Firefox 68.0.x32\geckodriver.exe')

    browser.get(url)
    html = etree.HTML(browser.page_source)
    hrefs = html.xpath(xpath_str)
    print(hrefs)
    browser.close()
    return str(hrefs)

def obtain_text_phantomJs(url, xpath_str, coding='utf-8'):
    dcap = webdriver.DesiredCapabilities.PHANTOMJS
    dcap["phantomjs.page.settings.userAgent"] = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36"
    )
    dcap["phantomjs.page.settings.resourceTimeout"] = 1000
    driver = webdriver.PhantomJS(desired_capabilities=dcap,
                                 executable_path=r'D:\software\phantomjs-2.1.1-windows\bin\phantomjs.exe')
    driver.get(url)
    data = driver.page_source
    html = etree.HTML(data)
    hrefs = html.xpath(xpath_str)
    driver.quit()
    return str(hrefs)

def obtain_text_Chrome(url, xpath_str, coding='utf-8'):
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 使用无头谷歌浏览器模式
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    # driver = webdriver.Chrome(r'HY_NEWS/util_custom/chromedriver', chrome_options=chrome_options)
    # 123 service
    driver = webdriver.Chrome(r'/root/chrome/chromedriver', chrome_options=chrome_options) # 123service
    # ZLB test home
    # driver = webdriver.Chrome(r'C:\Program Files\Google\Chrome\Application\chromedriver.exe', chrome_options=chrome_options)
    driver.get(url)
    data = driver.page_source
    html = etree.HTML(data)
    hrefs = html.xpath(xpath_str)
    driver.quit()
    return str(hrefs)

def text_in_digital(text):
    s = filter(str.isdigit, text)
    return "".join(list(s))

def obtain_urllib_request(url, match, coding='utf-8'):
    try:
        http = urllib3.PoolManager()
        r = http.request('GET', url)
        page = re.compile(match)
        strData = str(r.data,coding)
        return page.findall(strData)
    except Exception as e:
        logging.error(e.__str__())
        logging.exception(e)

def obtain_urllib_xpath(url, xpath, coding='utf-8'):
    '''
    :param url:访问的路径
    :param xpath: 提取的xpath值
    :param coding: 编码格式
    :return: xpath提取的代码
    '''
    try:
        http = urllib3.PoolManager()
        r = http.request('GET', url)
        return obtain_str_xpath(r.data, xpath)
    except Exception as e:
        logging.error(e.__str__())
        logging.exception(e)

def obtain_str_xpath(page, xpath):
    '''
    :param page:网页的html代码
    :param xpath: xpath路径
    :return: 提取代码
    '''
    html = etree.HTML(page)
    hrefs = html.xpath(xpath)
    return hrefs

if __name__ == '__main__':
    ss = obtain_text("http://fgw.beijing.gov.cn/gzdt/tztg", u'/html/body/div[3]/div[3]/div[2]/span[2]/text()')
    s = text_in_digital(ss)
    print(s)
