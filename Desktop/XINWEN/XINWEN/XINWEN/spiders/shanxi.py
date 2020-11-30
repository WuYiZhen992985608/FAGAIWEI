# -*- coding: utf-8 -*-
import logging
import datetime
import json
import re
import scrapy
import copy
from bs4 import BeautifulSoup
from scrapy import Request
from scrapy.linkextractors import LinkExtractor
from scrapy_redis.spiders import RedisSpider
from ..items import GuojiafagaiweiItem
from ..tools.attachment import get_attachments, get_times
from ..tools.utils import obtain_urllib_request



class ShanxiSpider(scrapy.Spider):
    # class NdSpider(RedisSpider):
    name = 'shanxi'
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

    def __init__(self, pagecount=2, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_count = self.get_input_pagecount(pagecount, 99999)
        self.domain = 'http://fgw.shanxi.gov.cn/'

        # # 政策法规
        # self.home_indexurl = 'http://fgw.shanxi.gov.cn/fggz/wngz/zcfg2/index.shtml'
        # self.page_indexurl = 'http://fgw.shanxi.gov.cn/fggz/wngz/zcfg2/index_{}.shtml' #共11页
        # 规划计划
        # self.home_indexurl = 'http://fgw.shanxi.gov.cn/zcfb/gjjh/index.shtml'
        # self.page_indexurl = 'http://fgw.shanxi.gov.cn/zcfb/gjjh/index_{}.shtml' #共5页
        # 政策解读
        self.home_indexurl = 'http://fgw.shanxi.gov.cn/zcfb/zcjd/index.shtml'
        self.page_indexurl = 'http://fgw.shanxi.gov.cn/zcfb/zcjd/index_{}.shtml'  #共28页


    def get_crawl_pagecount(self, response):
        try:
            totalpagecount = 0
            mh = re.compile('var\scountPage\s=\s(\d+)//')
            nodes = mh.findall(response.text)
            if len(nodes) == 1:
                totalpagecount = (int)(nodes[0])

            if self.page_count > totalpagecount:
                self.page_count = totalpagecount
        except:
            pass
        return self.page_count


    def extract_item_page_link(self, response):
        links = []
        try:
            links = response.xpath('//*[@class="submenu-dropbox_subtabs_content fixmt10"]//a/@href').getall()
            links = [response.urljoin(l) for l in links]
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
        try:
            yield scrapy.Request(self.home_indexurl, callback=self.parse_homeindex, dont_filter=True)
            yield scrapy.Request(self.home_indexurl, callback=self.parse_page_index, dont_filter=True)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_homeindex(self, response):
        try:
            pagecount = self.get_crawl_pagecount(response)
            print('pagecount:' + str(pagecount))
            for page in range(1, pagecount):  # 第二页index_1.htm
                yield self.create_page_index_request(page)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def create_page_index_request(self, page):
        url = self.page_indexurl.format(page)
        return scrapy.Request(url, callback=self.parse_page_index, meta={'page': page}, dont_filter=True)

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
        title = response.css('.common-detail-page-printer h3 ::text').extract_first()
        return title

    def get_content(self, response):
        content = ''
        try:
            content = ''.join(response.xpath('//*[@class="article-body oflow-hd"]//text()').extract())
        except:
            pass
        return content

    def get_text(self, response):
        txt = ''
        try:
            txt = ''.join(response.xpath('//*[@class="article-body oflow-hd"]//text()').extract())
            txt = txt.replace('\xa0', '').replace('\r', '').replace('\n', '').replace('\t', ''). \
                replace('\u3000', '').replace(' ', '')
        except:
            pass
        return txt

    def get_source(self, response):
        source = '山西发展改革委员会'
        return source


    def get_symbol(self, response):
        symbol = ''
        try:
            symbol = response.xpath('//*[@class="article-body oflow-hd"/div[1]/div[1]/p[1]/text()').extract_first()
        except:
            pass
        return symbol


    def get_dates(self, response):
        dates = ''
        try:
            dates = re.search('时间：.+i.(\d+-\d+-\d+)\s',response.text).group(1)
        except:
            pass
        return dates

    def get_province(self, response):
        return '山西省'

    def get_city(self, response):
        return ''

    def get_area(self, response):
        return '山西省'

    def get_website(self, response):
        return '山西省发展改革委员会'

    def get_module_name(self, response):
        return '政策发改'

    def get_appendix_info(self, response):
        return '', ''

    def get_type(self, response):
        return 1

    def get_tags(self, response):
        return ''


