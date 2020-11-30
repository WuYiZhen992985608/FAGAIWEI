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



class FujianSpider(scrapy.Spider):
    # class NdSpider(RedisSpider):
    name = 'fujian'
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

    def __init__(self, itemcount=20, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item_count = itemcount  #控制获取item的数量
        self.domain = 'http://fgw.fujian.gov.cn/'

        # 政策法规
        # self.home_indexurl = 'http://fgw.fujian.gov.cn/was5/web/search?channelid=217025&templet=docs1.jsp&sortfield=-docreltime&classsql=chnlid%3D9374&page=1&prepage=150'
        # self.page_indexurl = 'http://fgw.fujian.gov.cn/was5/web/search?channelid=217025&templet=docs1.jsp&sortfield=-docreltime&classsql=chnlid%3D9374&page=1&prepage={}'
        # 规范性文件
        # self.home_indexurl = 'http://fgw.fujian.gov.cn/was5/web/search?channelid=217025&templet=docs1.jsp&sortfield=-docreltime&classsql=chnlid%3D9375&page=1&prepage=150'
        # self.page_indexurl = 'http://fgw.fujian.gov.cn/was5/web/search?channelid=217025&templet=docs1.jsp&sortfield=-docreltime&classsql=chnlid%3D9375&page=1&prepage={}'
        # 规划计划
        # self.home_indexurl = 'http://fgw.fujian.gov.cn/was5/web/search?channelid=217025&templet=docs1.jsp&sortfield=-docreltime&classsql=chnlid%3D9407&page=1&prepage=150'
        # self.page_indexurl = 'http://fgw.fujian.gov.cn/was5/web/search?channelid=217025&templet=docs1.jsp&sortfield=-docreltime&classsql=chnlid%3D9407&page=1&prepage={}'
        # 政策解读
        # self.home_indexurl = 'http://fgw.fujian.gov.cn/was5/web/search?channelid=217025&templet=docs1.jsp&sortfield=-docreltime&classsql=chnlid%3D9377&page=1&prepage=150'
        # self.page_indexurl = 'http://fgw.fujian.gov.cn/was5/web/search?channelid=217025&templet=docs1.jsp&sortfield=-docreltime&classsql=chnlid%3D9377&page=1&prepage={}'
        # 建设项目
        self.home_indexurl = 'http://fgw.fujian.gov.cn/was5/web/search?channelid=217025&templet=docs1.jsp&sortfield=-docreltime&classsql=chnlid%3D9395&page=1&prepage=150'
        self.page_indexurl = 'http://fgw.fujian.gov.cn/was5/web/search?channelid=217025&templet=docs1.jsp&sortfield=-docreltime&classsql=chnlid%3D9395&page=1&prepage={}'

    def get_item_count(self, response):
        data = json.loads(response.text)
        itemcount = int(data['count'])
        return itemcount


    def extract_item_page_link(self, response):
        links = []
        try:
            data = json.loads(response.text)
            links = [ l['url'] for l in data['docs']]
            # print(links)
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
        url = self.page_indexurl.format(itemcount)
        return scrapy.Request(url, callback=self.parse_page_index, dont_filter=True)

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
        title = response.css('.xl_tit h4 ::text').extract_first().strip()
        return title

    def get_content(self, response):
        content = ''
        try:
            content = ''.join(response.xpath('//div[@class="xl_content"]/div[2]//text()').extract())
        except:
            pass
        return content

    def get_text(self, response):
        txt = ''
        try:
            txt = ''.join(response.xpath('//div[@class="xl_content"]/div[2]//text()').extract())
            txt = txt.replace('\xa0', '').replace('\r', '').replace('\n', '').replace('\t', ''). \
                replace('\u3000', '').replace(' ', '')
        except:
            pass
        return txt

    def get_source(self, response):
        source = '福建省发展改革委员会'
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
            dates = re.search('发布时间：\s(\d+年\d+月\d+日)\s',response.text).group(1)
        except:
            pass
        return dates

    def get_province(self, response):
        return '福建省'

    def get_city(self, response):
        return ''

    def get_area(self, response):
        return '福建省'

    def get_website(self, response):
        return '福建省发展改革委员会'

    def get_module_name(self, response):
        return '政策发改'

    def get_appendix_info(self, response):
        return '', ''

    def get_type(self, response):
        return 1

    def get_tags(self, response):
        return ''


