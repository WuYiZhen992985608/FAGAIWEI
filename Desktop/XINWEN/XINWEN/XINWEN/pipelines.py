# -*- coding: utf-8 -*-
# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import copy
import datetime
import time
import pymysql
import redis
from scrapy.exceptions import DropItem
from twisted.enterprise import adbapi
from .BloomFilter import PyBloomFilter
import logging

class FgwNewsPipeline:
    def process_item(self, item, spider):
        return item

class DuplicatesPipeline(object):
    def __init__(self):
        return
        # host = '47.106.239.73'
        host = 'localhost'
        port = 6379
        pool = redis.ConnectionPool(host=host, port=port, db=1)
        print('去重')
        conn = redis.StrictRedis(connection_pool=pool)
        print(type(conn))
        self.bf =PyBloomFilter(conn=conn)

    def process_item(self, item, spider):
        return item
        bf2 = self.bf.is_exist(item['href'])
        # bf2 = self.bf.is_exist(item['link'])
        if bf2:
            raise DropItem("Duplicate item found:%s" % item['href'])
            # raise DropItem("Duplicate item found:%s" % item['link'])
        self.bf.add(item['href'])
        # self.bf.add(item['link'])
        logging.info("=====================================================item inserted, added!")
        return item

class MysqlTwistedPipeline(object):

    def __init__(self, dbpool):
        self.dbpool = dbpool

    @classmethod
    def from_settings(cls, settings):
        dbparms = dict(
            host=settings["MYSQL_HOST"],
            port=settings['MYSQL_PORT'],
            db=settings["MYSQL_DB"],
            user=settings["MYSQL_USER"],
            passwd=settings["MYSQL_PASSWORD"],
            charset=settings['MYSQL_CHRSET'],
            cursorclass=pymysql.cursors.DictCursor,
            use_unicode=True,
        )
        dbpool = adbapi.ConnectionPool("pymysql", **dbparms)

        return cls(dbpool)

    def open_spider(self, spider):
        self.spider = spider

    def process_item(self, item, spider):
        try:
            # 使用twisted将mysql插入变成异步执行
            asynItem = copy.deepcopy(item)
            query = self.dbpool.runInteraction(self.do_insert, asynItem)
            query.addErrback(self.handle_error, item, spider)  # 处理异常
        except Exception as e:
            logging.error("Got exception {}, {}".format(e,e.args))
        return item

    def handle_error(self, failure, item, spider):
        # 处理异步插入的异常
        logging.error("spider {} on item failed: {}".format(self.spider.name, str(failure)))

    def do_insert(self, cursor, item):
        logging.info(self.spider.name + ": " + "insert into mysql........")
        try:
            sql = f'''
                replace into `topic_info_government_policy`(
                `title`,
                `content`,
                `source`,
                `symbol`,
                `dates`,
                `province`,
                `city`,
                `area`,
                `website`,
                `href`,
                `spider_name`,
                `module_name`,
                `appendix`,
                `appendix_name`,
                `txt`,
                `type`,
                `tags`
                )
                values ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
            # create_time = time.time()
            parm = (
                item['title'],
                item['content'],
                item['source'],
                item['symbol'],
                item['dates'],
                item['province'],
                item['city'],
                item['area'],
                item['website'],
                item['href'],
                item['spider_name'],
                item['module_name'],
                item['appendix'],
                item['appendix_name'],
                item['txt'],
                item['type'],
                item['tags']
            )
            cursor.execute(sql, parm)
            logging.info(self.spider.name + ": " + "insert into mysql success")
        except Exception as e:
            print(e)
            logging.error("Spider insert item failed: {}, {}".format(e, e.args))
            raise DropItem("Spider insert item failed, item txt: %s" % item)

    def close_spider(self, spider):
        self.dbpool.close() 
        self.spider = None
