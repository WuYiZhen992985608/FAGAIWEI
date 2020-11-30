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



class ShandongSpider(scrapy.Spider):
    # class NdSpider(RedisSpider):
    name = 'shandong'
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

    def __init__(self, pagecount=2,category='SD020203',*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_count = self.get_input_pagecount(pagecount, 99999)
        self.domain = 'http://www.jiangxi.gov.cn/'
        self.category = category # 规范性文件'：'SD020203';政策解读':'SD020207';'规划计划':'SD0401';

        self.home_indexurl = 'http://fgw.shandong.gov.cn/module/xxgk/tree.jsp?divid=div91105&area='
        self.page_indexurl = 'http://fgw.shandong.gov.cn/module/xxgk/search.jsp?standardXxgk=1&isAllList=1' \
                             '&texttype=&fbtime=&vc_all=&vc_filenumber=&vc_title=&vc_number=&currpage={}' \
                             '&sortfield=createdatetime:0&fields=&fieldConfigId=&hasNoPages=&infoCount='


    def get_crawl_pagecount(self, response):
        if self.page_count and self.page_count != 99999:
            return self.page_count
        else:
            return 4


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
        header = {'Host': 'fgw.shandong.gov.cn',
                  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36',
                  'Referer': 'http://fgw.shandong.gov.cn/col/col162799/index.html?vc_xxgkarea=113700000045024031',
                  'Origin': 'http://fgw.shandong.gov.cn',
                  'Cookie': 'cod=22366.22367.22370.22428.22379.22397.22415; zh_choose_408=s; wondersLog_sdywtb_sdk=%7B%22persistedTime%22%3A1606665988610%2C%22updatedTime%22%3A1606666035648%2C%22sessionStartTime%22%3A1606665989846%2C%22sessionReferrer%22%3A%22http%3A%2F%2Ffgw.shandong.gov.cn%2Fcol%2Fcol91102%2Findex.html%22%2C%22deviceId%22%3A%220dcf3d2a8002377c2d54167d7fad8746-9350%22%2C%22LASTEVENT%22%3A%7B%22eventId%22%3A%22wondersLog_pv%22%2C%22time%22%3A1606666035646%7D%2C%22sessionUuid%22%3A3493268483739094%2C%22costTime%22%3A%7B%7D%7D',
                  }
        try:
            yield scrapy.Request(self.home_indexurl, callback=self.parse_homeindex, dont_filter=True)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_homeindex(self, response):
        try:
            pagecount = self.get_crawl_pagecount(response)
            print('pagecount:' + str(pagecount))
            for page in range(1, pagecount+1):
                yield self.create_page_index_request(page)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def create_page_index_request(self, page):
        url = self.page_indexurl.format(page)
        customerData = {'infotypeId': self.category, 'jdid':'408','divid':'div91105',
                        'standardXxgk': '1', 'sortfield':'createdatetime:0'}
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
        title = response.xpath('//*[@class="htitle"]//text()')
        return title

    def get_content(self, response):
        content = ''
        try:
            content = ''.join(response.css('.art_con ::text').extract())
        except:
            pass
        return content

    def get_text(self, response):
        txt = ''
        try:
            txt = ''.join(response.css('.art_con ::text').extract())
            txt = txt.replace('\xa0', '').replace('\r', '').replace('\n', '').replace('\t', ''). \
                replace('\u3000', '').replace(' ', '')
        except:
            pass
        return txt

    def get_source(self, response):
        source = '山东省发展改革委员会'
        return source


    def get_symbol(self, response):
        symbol = ''
        try:
            symbol = ''.join(response.xpath('//*[@class="art_con"]/p[1]/a//text() ').extract_first())
        except:
            pass
        return symbol


    def get_dates(self, response):
        dates = ''
        try:
            dates = re.search('发布日期：(\d+-\d+-\d+)\s',response.text).group(1)
        except:
            pass
        return dates

    def get_province(self, response):
        return '山东省'

    def get_city(self, response):
        return ''

    def get_area(self, response):
        return '山东省'

    def get_website(self, response):
        return '山东省发展改革委员会'

    def get_module_name(self, response):
        return '政策发改'

    def get_appendix_info(self, response):
        return '', ''

    def get_type(self, response):
        return 1

    def get_tags(self, response):
        return ''


