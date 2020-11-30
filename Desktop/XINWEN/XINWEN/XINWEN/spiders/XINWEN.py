# -*- coding: utf-8 -*-
import copy
import datetime
import json
import re
import scrapy
from scrapy import Request
from bs4 import BeautifulSoup

from XINWEN.items import XINWEN_Item
from scrapy_redis.spiders import RedisSpider
import logging
# ====================新闻类爬虫模板======================
# - 不支持动态
# - 不支持反扒
# ====================新闻类网站特点======================
# - 结构相对固定
# - 页面相对较规范
# ====================是否动态判定？======================
# 1、 禁用浏览器js
# 2、 禁用浏览器cookie
# 3、 清除浏览器cookie
# 4、 浏览器打开爬取链接-观察有无内容-与正常打开页面做对比
#     4.1、有内容 - 过 是静态
#     4.2、无内容 - 查看 网页源码
#        4.2.1、有内容 - 可以当做静态来爬 - 需要关注提取页码等内容，可能需要使用正则
#        4.2.2、无内容 - 动态网页 - 上splash
# ====================是否反扒判定？======================
# 视情况而定， 静态的一般都无反扒
# 待续-----

class XINWEN_Spider(scrapy.Spider):
    # class NdSpider(RedisSpider):
    name = 'XINWEN'
    custom_settings = {
        'CONCURRENT_REQUESTS': 10,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 10,
        'CONCURRENT_REQUESTS_PER_IP': 10,
        'DOWNLOAD_DELAY': 2,
        'ITEM_PIPELINES': {
            'XINWEN.pipelines.MysqlTwistedPipeline': 600,
            # 'XINWEN.pipelines.DuplicatesPipeline': 100,
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

        #为爬虫指定爬取多少页，因为新闻都是按时间来的，通常第一次需要整站爬取
        #每天跟新的新闻数量不是太多，正常情况下后续只需要定时爬取前几页就足够了
        #pagenum就是为了设定爬取多少页，一般认为新闻是最新的在前面页面
        self.page_count = self.get_input_pagecount(pagecount, 99999)
        # print('page_count',self.page_count)
        # print('pagecount',pagecount)
        #网站域名
        self.domain = 'http://www.xinjiang.gov.cn'
        # 下面以新疆网站为例
        #homeindexurl - 待爬取的网址 - 可通过网站观察获取到 -或者从需求文档中直接提取
        # 通过这个网址应能获取到当前网站的本模块下有多少页 -对于新闻网站来说-一般会有页数和条目数
        self.home_indexurl = 'http://www.xinjiang.gov.cn/xinjiang/xjyw/common_list.shtml'

        #pageIndexurl - 待爬取指定也的链接 - 一般通过浏览器点击跳页观察获取
        # 通过这个网址应能获取到指定页码的页面内容-通常内容与上面homeindexurl获取到的一致
        # 注意下此是不是从第一页开始的 如果不是可能需要对create_page_index_request- 做一些调整
        self.page_indexurl = 'http://www.xinjiang.gov.cn/xinjiang/xjyw/common_list_%d.shtml'

        #通常情况下新闻网站数据都是按时间排序的
        # homeindexurl 获取到的就是pageIndexurl指定的第一页 -可以需要再次爬取不过为了简单-忽略掉

    ######################################################################################################
    #需要关注更改 - 在此函数中获取网站文章总的页数
    def get_crawl_pagecount(self, response):
        try:
            totalpagecount = 0
            mh = re.compile('\'page-div\',(\d+),')
            nodes = mh.findall(response.text)
            if len(nodes) == 1:
                totalpagecount = (int)(nodes[0])

            if self.page_count > totalpagecount:
                self.page_count = totalpagecount
        except:
            pass
        return self.page_count

    #需要关注更改 - 提取页面上的链接 - 可关注下去重，提示下效率-个别网站会重复链接
    #此可以使用 response.follow 不过为了更了解网站结构 -建议自己组
    def extract_item_page_link(self, response):
        links = []
        try:
            links = response.css("ul.list a::attr(href)").getall()
            links = [self.domain + l for l in links]
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

        #为了方便 统一返回列表
        links = list(set(links))
        return links

    ##################################################################################
    #通常无需关注 - 对输入参数进行简单提取和校验
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


    #通常无需关注 - 提交首页请求
    def start_requests(self):
        try:
            #提交第一个请求 - 通常用来获取本模块下有多少页新闻
            yield scrapy.Request(self.home_indexurl, callback=self.parse_homeindex, dont_filter=True)

            ##############
            #新疆比较特殊 第一页不是编号为1 -为了简单偷懒-直接再爬取一遍到解析 - 其他身份可能没有
            yield scrapy.Request(self.home_indexurl, callback=self.parse_page_index, dont_filter=True)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    #通常无需关注 - 提交每页请求 - 但是有的网站第一页不是按这个顺序来的 就需要修改一下
    def parse_homeindex(self, response):
        try:
            pagecount = self.get_crawl_pagecount(response)
            print('pagecount:' + str(pagecount))
            for page in range(2, pagecount + 1):
                yield self.create_page_index_request(page)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    # 通常无需关注 - 提交指定页面的请求
    def create_page_index_request(self, page):
        url = self.page_indexurl % (page)
        return scrapy.Request(url, callback=self.parse_page_index, meta={'page':page}, dont_filter=True)

    # 无需关注 - 提交新闻页面
    def parse_page_index(self, response):
        try:
            item_page_links = self.extract_item_page_link(response)
            for url in item_page_links:
                yield self.create_item_request(url)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    #无需关注 - 指定新闻内容页面
    def create_item_request(self, url):
        return scrapy.Request(url, callback=self.parse_item, dont_filter=True)

    #插入数据库表不变 无需关注 - 字段不变
    def parse_item(self, response):
        try:
            item = XINWEN_Item()
            item['title'] = self.get_title(response)
            print('title',item['title'])
            item['content'] = self.get_content(response)
            print(item['content'])
            item['source'] = self.get_source(response)
            item['article_num'] = self.get_article_num(response)
            item['time'] = self.get_time(response)
            item['province'] = self.get_province(response)
            item['city'] = self.get_city(response)
            item['area'] = self.get_area(response)
            item['website'] = self.get_website(response)
            item['link'] = response.url
            item['spider_name'] = self.name
            item['module_name'] = self.get_module_name(response)
            item['appendix'], item['appendix_name'] = self.get_appendix_info(response)
            item['txt'] = self.get_text(response)
            item['news_type'] = self.get_news_type(response)
            item['create_time'] = self.get_create_time(response)
            yield item
        except Exception as e:
            logging.error(self.name + " in parse_item: url=" + response.request.url + ", exception=" + e.__str__())
            logging.exception(e)

    #无需关注
    def get_create_time(self, response):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    #需要关注 重要的字段，这里不可以不加异常，为的是重要字段都没获取到插入也没啥意义
    #抛出异常有利于排查错误 比如Title
    def get_title(self, response):
        title = response.xpath('//div[@class="detail"]//h1//text()').get()
        return title

    #需要关注  网站的内容不一定规范，需要根据情况多做验证
    def get_article_num(self, response):
        return ''

    #需要关注  网站的内容不一定规范，需要根据情况多做验证
    def get_content(self, response):
        content = ''
        try:
            content = ''.join(response.xpath('//div[@id="NewsContent"]//p//text()').getall())
        except:
           pass
        return content

    #需要关注  网站的内容不一定规范，需要根据情况多做验证
    def get_source(self, response):
        source = ''
        try:
            source = response.xpath('//p[@class="source"]//text()').get()
        except:
           pass
        return source


    #需要关注  网站的内容不一定规范，需要根据情况多做验证
    def get_text(self, response):
        txt = ''
        try:
            txt = ''.join(response.xpath('//div[@id="NewsContent"]//p//text()').getall())
            txt = txt.replace('\xa0', '').replace('\r', '').replace('\n', '').replace('\t', ''). \
                replace('\u3000', '').replace(' ', '')
        except:
            pass
        return txt

    #需要关注  网站的内容不一定规范，需要根据情况多做验证
    def get_time(self, response):
        tm = ''
        try:
            y = response.xpath("//p[@class='yyyy']//text()").get()
            m = response.xpath("//p[@class='mmdd']//text()").get().replace('/', '-')
            h = response.xpath("//p[@class='hhmm']//text()").get()
            tm = y + '-' + m + ' ' + h
        except:
            pass
        return tm

    def get_website(self, response):
        return '新疆维吾尔自治区政府'

    def get_module_name(self, response):
        return '新疆维吾尔自治区政府-政务动态'

    def get_appendix_info(self, response):
        return '',''

    def get_province(self, response):
        return '新疆'

    def get_city(self, response):
        return ''

    def get_area(self, response):
        return ''
    def get_news_type(self, response):
        return 1
