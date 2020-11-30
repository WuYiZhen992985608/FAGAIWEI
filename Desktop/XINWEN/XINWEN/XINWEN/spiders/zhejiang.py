# -*- coding: utf-8 -*-
import logging
import datetime
import json
import re
import scrapy
import copy
from bs4 import BeautifulSoup
from scrapy import Request, FormRequest
from scrapy.linkextractors import LinkExtractor
from scrapy_redis.spiders import RedisSpider
from ..items import GuojiafagaiweiItem
from ..tools.attachment import get_attachments, get_times
from ..tools.utils import obtain_urllib_request



class ZhejiangSpider(scrapy.Spider):
    # class NdSpider(RedisSpider):
    name = 'zhejiang'
    custom_settings = {
        'CONCURRENT_REQUESTS': 10,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 10,
        'CONCURRENT_REQUESTS_PER_IP': 10,
        'DOWNLOAD_DELAY': 2,
        'ITEM_PIPELINES': {
            'XINWEN.pipelines.MysqlTwistedPipeline': 600,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': None,
            'XINWEN.middlewares.XINWEN_DeduplicateMiddleware': 730,

            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'XINWEN.middlewares.MyUserAgentMiddleware': 120,

            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'XINWEN.middlewares.MyRetryMiddleware': 90,
        },
        'COOKIES_ENABLED': False

    }

    def __init__(self, itemcount=5,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item_count = itemcount  #控制获取item的数量
        self.domain = 'http://fzggw.zj.gov.cn/'
        # 法律法规
        # self.home_indexurl = 'http://fzggw.zj.gov.cn/col/col1599551/index.html'
        # self.page_indexurl = 'http://fzggw.zj.gov.cn/module/jpage/dataproxy.jsp?startrecord=1&endrecord={}&perpage={}' \
        #                      '&unitid=4892867&columnid=1599551&sourceContentType=1'
        # 规划计划
        self.home_indexurl = 'http://fzggw.zj.gov.cn/col/col1599552/index.html'
        self.page_indexurl = 'http://fzggw.zj.gov.cn/module/jpage/dataproxy.jsp?startrecord=1&endrecord={}&perpage={}' \
                             '&unitid=5043600&columnid=1599552&sourceContentType=1'
        # 政策解读
        # self.home_indexurl = 'http://fzggw.zj.gov.cn/col/col1599554/index.html'
        # self.page_indexurl = 'http://fzggw.zj.gov.cn/module/jpage/dataproxy.jsp?startrecord=1&endrecord={}&perpage={}' \
        #                      '&unitid=5043863&columnid=1599554&sourceContentType=3'



    def get_item_count(self, response):
        totalRecord = 0
        try:
            mh = re.compile(',totalRecord:(.*),open')
            nodes = mh.findall(response.text)
            if len(nodes) != 0:
                totalRecord = (int)(nodes[0].split(':')[-1])
        except:
            pass
        return totalRecord


    def extract_item_page_link(self, response):
        links = []
        try:
            links = re.findall('href="/(art/\d+/\d+/\d+/art_\d+_\d+.html)"\s',response.text)
            links = [self.domain + l for l in links]
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

        links = list(set(links))
        return links

    def get_input_itemcount(self, snumber, defnum):
        number = defnum
        try:
            if snumber:
                number = int(snumber)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)
        if number <= 0:
            number = defnum
        return number

    def start_requests(self):
        header = {'Host': 'http://fzggw.jiangsu.gov.cn/',
                  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36',
                  'Referer': 'http://fzggw.zj.gov.cn/col/col1599551/index.html?uid=4892867&pageNum=9',
                  'Origin': 'http://fzggw.zj.gov.cn',
                  'Cookie': 'JSESSIONID=B35104F4A1AC1BE7DD84B21D573E9599; zh_choose_undefined=s; SERVERID=bc6beea6e995cecb42c7a1341ba3517f|1606642338|1606641360',
                  }
        try:
            yield scrapy.Request(self.home_indexurl, callback=self.parse_homeindex,headers=header, dont_filter=True)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_homeindex(self, response):
        try:
            itemcount = self.get_item_count(response)
            print('itemcount:' + str(itemcount))
            yield self.create_page_index_request(itemcount)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def create_page_index_request(self, itemcount):
        url = self.page_indexurl.format(itemcount,itemcount)
        customerData = {'col': '1','appid':'1','webid':'3185','path':'/',
                        'webname':'浙江省发展和改革委员会','permissiontype': '0'}
        return FormRequest(url, formdata=customerData,callback=self.parse_page_index, dont_filter=True)

    def parse_page_index(self, response):
        try:
            item_page_links = self.extract_item_page_link(response)
            if self.item_count:
                for url in item_page_links[:self.item_count]:
                    yield self.create_item_request(url)
            else:
                for url in item_page_links:
                    yield self.create_item_request(url)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def create_item_request(self, url):
        return scrapy.Request(url, callback=self.parse_item, dont_filter=True)

    def parse_item(self, response):
        try:
            item = GuojiafagaiweiItem()
            item['title'] = self.get_title(response)
            item['content'] = self.get_content(response)
            item['source'] = self.get_source(response)
            item['symbol'] = self.get_symbol(response)
            item['dates'] = self.get_dates(response)
            item['province'] = self.get_province(response)
            item['city'] = self.get_city(response)
            item['area'] = self.get_area(response)
            item['website'] = self.get_website(response)
            item['href'] = response.url
            item['spider_name'] = self.name
            item['module_name'] = self.get_module_name(response)
            item['appendix'], item['appendix_name'] = self.get_appendix_info(response)
            item['txt'] = self.get_text(response)
            item['type'] = self.get_type(response)
            item['tags'] = self.get_tags(response)
            yield item
        except Exception as e:
            logging.error(self.name + " in parse_item: url=" + response.request.url + ", exception=" + e.__str__())
            logging.exception(e)

    def get_title(self, response):
        title = response.xpath('//div[@class="con"]/p[1]//text()').extract_first()
        return title

    def get_content(self, response):
        content = ''
        try:
            content = ''.join(response.xpath('//div[@class="con"]/*[@class="main-txt"]//text()').extract())
        except:
            pass
        return content

    def get_text(self, response):
        txt = ''
        try:
            txt = ''.join(response.xpath('//div[@class="con"]/*[@class="main-txt"]//text()').extract())
            txt = txt.replace('\xa0', '').replace('\r', '').replace('\n', '').replace('\t', ''). \
                replace('\u3000', '').replace(' ', '')
        except:
            pass
        return txt

    def get_source(self, response):
        source = '浙江省发展改革委员会'
        return source


    def get_symbol(self, response):
        symbol = ''
        try:
            symbol = re.search('来源：(.+)<',response.text).group(1)
        except:
            pass
        return symbol


    def get_dates(self, response):
        dates = ''
        try:
            dates = re.search('发布日期：(\d+-\d+-\d+)<', response.text).group(1)
        except:
            pass
        return dates

    def get_province(self, response):
        return '浙江省'

    def get_city(self, response):
        return ''

    def get_area(self, response):
        return '浙江省'

    def get_website(self, response):
        return '浙江省发展改革委员会'

    def get_module_name(self, response):
        return '政策发改'

    def get_appendix_info(self, response):
        return '', ''

    def get_type(self, response):
        return 1

    def get_tags(self, response):
        return ''


