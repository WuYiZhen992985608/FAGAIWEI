# -*- coding: utf-8 -*-
from scrapy.exceptions import IgnoreRequest
import pymysql
import logging
class DataBaseFilter(object):
    def __init__(self, settings, mw):
        #加载已经爬取过的Url - Key
        self.mw = mw
        self.crawlCount = 0
        self.filterCount = 0
        self.crawlkey = set()
        self.loadcrawlkey(settings)


    def process_request(self, request, spider):
        url = self.geturl(request)
        if self.mw.is_filter_url(url):
            pagekey = self.mw.get_url_key(url)
            if len(pagekey) != 0:
                if pagekey in self.crawlkey:
                    self.filterCount += 1
                    logging.info('filter count:' + str(self.filterCount))
                    raise IgnoreRequest("Duplicate item found:%s" % request.url)
                self.crawlkey.add(pagekey)
                self.crawlCount += 1
                logging.info('crawl count:' + str(self.crawlCount))
                logging.info('crawl all count:' + str(len(self.crawlkey)))
            return None
        return None

    def geturl(self, request):
        url = ''
        try:
            url = request.meta['splash']['args']['url']
        except:
            url = request.url
        return url

    def loadcrawlkey(self, settings):
        dbparms = dict(
            host=settings["MYSQL_HOST"],
            port=settings['MYSQL_PORT'],
            db=settings["MYSQL_DB"],
            user=settings["MYSQL_USER"],
            passwd=settings["MYSQL_PASSWORD"],
            charset=settings['MYSQL_CHRSET'],
            use_unicode=True,
        )
        con = pymysql.connect(**dbparms)

        cursor = con.cursor()
        #读取有多少条
        cursor.execute(self.mw.sqlcount)
        num = (int)(cursor.fetchone()[0])
        logging.info('item count in db:' + str(num))
        m = 1000
        totalpage = (int)((num + m - 1) / m)
        for n in range(totalpage):
            start = str(n * m)
            sql = self.mw.sqlselect + ' limit ' + start + ',' + str(m)
            cursor.execute(sql)
            results = cursor.fetchall()
            for row in results:
                try:
                    link = row[0]
                    key = self.mw.get_url_key(link)
                    if len(key) != 0:
                        self.crawlkey.add(key)
                except:
                    pass
        logging.info('item count in set:' + str(len(self.crawlkey)))

