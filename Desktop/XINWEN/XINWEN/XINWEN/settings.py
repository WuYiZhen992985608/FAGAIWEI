# -*- coding: utf-8 -*-

# Scrapy settings for CYZC project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://doc.scrapy.org/en/latest/topics/settings.html
#     https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://doc.scrapy.org/en/latest/topics/spider-middleware.html
# from fake_useragent import UserAgent

BOT_NAME = 'XINWEN'


SPIDER_MODULES = ['XINWEN.spiders']
NEWSPIDER_MODULE = 'XINWEN.spiders'

# Crawl responsibly by identifying yourself (and your website) on the user-agent


# Obey robots.txt rules
ROBOTSTXT_OBEY = False




#MYSQL_HOST = '10.8.32.156'
#MYSQL_PASSWORD = 'zw123456'
#MYSQL_USER = 'root'
#MYSQL_DB = 'engineering-brain'
#MYSQL_CHRSET = 'utf8'
#LOG_LEVEL = 'INFO'
#MYSQL_PORT = 3361

# local test
MYSQL_HOST = 'localhost'
MYSQL_DB = 'python'
MYSQL_USER = 'root'
MYSQL_PORT = 3306
# MYSQL_PASSWORD = '1'
MYSQL_PASSWORD = '123'
MYSQL_CHRSET = 'utf8'