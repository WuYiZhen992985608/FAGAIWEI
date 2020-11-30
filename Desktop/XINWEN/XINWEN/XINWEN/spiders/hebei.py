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



class HebeiSpider(scrapy.Spider):
    # class NdSpider(RedisSpider):
    name = 'hebei'
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
        self.domain = 'http://hbdrc.hebei.gov.cn'

        # 政策法规
        # self.home_indexurl = 'http://hbdrc.hebei.gov.cn/web/web/xxgkzcfg/index.htm'
        # self.page_indexurl = 'http://hbdrc.hebei.gov.cn/web/web/xxgkzcfg/index_{}.htm' #共11页
        # 政策解读
        self.home_indexurl = 'http://hbdrc.hebei.gov.cn/web/web/xxgkzcjd/index.htm'
        self.page_indexurl = 'http://hbdrc.hebei.gov.cn/web/web/xxgkzcjd/index_{}.htm'  #共7页


    def get_crawl_pagecount(self, response):
        print(response.url)
        try:
            totalpagecount = 0
            mh = re.compile('href=".+_(\d+).htm".尾页')
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
            links = response.css(".xxgk_rightwrap ul a::attr(href)").getall()
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

    # 通常无需关注 - 提交每页请求 - 但是有的网站第一页不是按这个顺序来的 就需要修改一下
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
        title = (response.xpath('//*[@class="maintitle"]//text()')
                 or response.xpath('//*[@class="xl_tit"]//text()')).extract_first()
        return title

    def get_content(self, response):
        content = ''
        try:
            content = ''.join((response.xpath('//*[@class="xxgk_rightwrap"]/div[3]//text()')
                               or response.xpath('//*[@class="zhengwen"]/div[2]//text()')).extract())
        except:
            pass
        return content

    def get_text(self, response):
        txt = ''
        try:
            txt = ''.join((response.xpath('//*[@class="xxgk_rightwrap"]/div[3]//text()')
                     or response.xpath('//*[@class="zhengwen"]/div[2]//text()')).extract())
            txt = txt.replace('\xa0', '').replace('\r', '').replace('\n', '').replace('\t', ''). \
                replace('\u3000', '').replace(' ', '')
        except:
            pass
        return txt

    def get_source(self, response):
        source = '河北发展改革委员会'
        return source

    def get_symbol(self, response):
        symbol = ''
        try:
            symbol = response.xpath('//tbody/tr[3]/td[1]/text()').extract_first()
        except:
            pass
        return symbol

    def get_dates(self, response):
        dates = ''
        try:
            dates = response.xpath('//tbody/tr[4]/td[1]/text()').extract_first()
        except:
            pass
        return dates

    def get_province(self, response):
        return '河北省'

    def get_city(self, response):
        return ''

    def get_area(self, response):
        return '河北省'

    def get_website(self, response):
        return '河北发展改革委员会'

    def get_module_name(self, response):
        return '政策发改'

    def get_appendix_info(self, response):
        return '', ''

    def get_type(self, response):
        return 1

    def get_tags(self, response):
        return ''


