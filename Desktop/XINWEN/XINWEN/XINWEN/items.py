# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class XINWEN_Item(scrapy.Item):
    # define the fields for your item here like:
    title = scrapy.Field()
    article_num = scrapy.Field()
    content = scrapy.Field()
    source = scrapy.Field()
    time = scrapy.Field()
    province = scrapy.Field()
    city = scrapy.Field()
    area = scrapy.Field()
    website = scrapy.Field()
    link = scrapy.Field()
    create_time = scrapy.Field()
    spider_name = scrapy.Field()
    module_name = scrapy.Field()
    appendix_name = scrapy.Field()
    appendix = scrapy.Field()
    txt = scrapy.Field()
    news_type = scrapy.Field()


class GuojiafagaiweiItem(scrapy.Item):
    title = scrapy.Field()
    content =scrapy.Field()
    source =scrapy.Field()
    symbol = scrapy.Field()
    dates =scrapy.Field()
    province =scrapy.Field()
    city =scrapy.Field()
    area =scrapy.Field()
    website =scrapy.Field()
    href=scrapy.Field()
    spider_name=scrapy.Field()
    module_name=scrapy.Field()
    appendix =scrapy.Field()
    appendix_name =scrapy.Field()
    txt =scrapy.Field()
    type =scrapy.Field()
    tags =scrapy.Field()
