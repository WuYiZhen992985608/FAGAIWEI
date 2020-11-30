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



class JiangxiSpider(scrapy.Spider):
    # class NdSpider(RedisSpider):
    name = 'jiangxi'
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

    def __init__(self, pagecount=2,category='1003',*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_count = self.get_input_pagecount(pagecount, 99999)
        self.domain = 'http://www.jiangxi.gov.cn/'
        self.category = category # 政策文件'：'0202';解读材料':'0208';'规划计划':'03';'重大建设项目’:'1003';

        self.home_indexurl = 'http://www.jiangxi.gov.cn/module/xxgk/tree.jsp?divid=div435&area=014500858'
        self.page_indexurl = 'http://www.jiangxi.gov.cn/module/xxgk/search.jsp?standardXxgk=0&isAllList=1' \
                             '&texttype=0&fbtime=&vc_all=&vc_filenumber=&vc_title=&vc_number=&currpage={}' \
                             '&sortfield=compaltedate:0,orderid:0&fields=&fieldConfigId=&hasNoPages=&infoCount='


    def get_crawl_pagecount(self, response,category):
        totalpagecount = 0
        data = self.get_categoryitem_count(response)
        if category == '0202':
            totalpagecount = data['政策文件']//20 +1
        elif category == '0208':
            totalpagecount = data['解读材料'] // 20 + 1
        elif category == '03':
            totalpagecount = data['规划计划'] // 20 + 1
        elif category == '1003':
            totalpagecount = data['重大建设项目'] // 20 + 1
        if self.page_count > totalpagecount:
            self.page_count = totalpagecount
        return self.page_count

    def get_categoryitem_count(self, response):
        data = {}
        data['政策文件'] = int(re.search('>政策文件\((\d+)\)', response.text).group(1))
        data['解读材料'] = int(re.search('>解读材料\((\d+)\)',response.text).group(1))
        data['规划计划'] = int(re.search('>规划计划\((\d+)\)',response.text).group(1))
        data['重大建设项目'] = int(re.search('>重大建设项目\((\d+)\)',response.text).group(1))
        return data

    def extract_item_page_link(self, response):
        links = []
        try:
            links = re.findall("(http://.+.html)",response.text)
            links = [l for l in links]
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

        links = list(set(links))
        return links

    def get_input_pagecount(self, snumber, defnum):
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
        header = {'Host': 'www.jiangxi.gov.cn',
                  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36',
                  'Referer': 'http://www.jiangxi.gov.cn/col/col4928/index.html?vc_xxgkarea=014500858',
                  'Origin': 'http://www.jiangxi.gov.cn',
                  'Cookie': 'cod=5.81.123; zh_choose_3=s',
                  }
        try:
            yield scrapy.Request(self.home_indexurl, callback=self.parse_homeindex, headers= header,dont_filter=True)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_homeindex(self, response):
        try:
            pagecount = self.get_crawl_pagecount(response,self.category)
            print('pagecount:' + str(pagecount))
            for page in range(1, pagecount+1):
                yield self.create_page_index_request(page)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def create_page_index_request(self, page):
        url = self.page_indexurl.format(page)
        customerData = {'infotypeId': self.category, 'jdid':'3',
                        'area': '014500858', 'divid':'div435'}
        return FormRequest(url, formdata=customerData,callback=self.parse_page_index, meta={'page': page}, dont_filter=True)

    def parse_page_index(self, response):
        try:
            item_page_links = self.extract_item_page_link(response)
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
        title = ''.join(response.css('.sp_title ::text').extract())
        return title

    def get_content(self, response):
        content = ''
        try:
            content = ''.join(response.xpath('//*[@id="zoom"]//text()').extract())
        except:
            pass
        return content

    def get_text(self, response):
        txt = ''
        try:
            txt = ''.join(response.xpath('//*[@id="zoom"]//text()').extract())
            txt = txt.replace('\xa0', '').replace('\r', '').replace('\n', '').replace('\t', ''). \
                replace('\u3000', '').replace(' ', '')
        except:
            pass
        return txt

    def get_source(self, response):
        source = '江西省发展改革委员会'
        return source


    def get_symbol(self, response):
        symbol = ''
        try:
            symbol = re.findall('赣.*\d+号',response.text)[0]
        except:
            pass
        return symbol


    def get_dates(self, response):
        dates = ''
        try:
            dates = re.findall('\d+-\d+-\d+',response.text)[0]
        except:
            pass
        return dates

    def get_province(self, response):
        return '江西省'

    def get_city(self, response):
        return ''

    def get_area(self, response):
        return '江西省'

    def get_website(self, response):
        return '江西省发展改革委员会'

    def get_module_name(self, response):
        return '政策发改'

    def get_appendix_info(self, response):
        return '', ''

    def get_type(self, response):
        return 1

    def get_tags(self, response):
        return ''


