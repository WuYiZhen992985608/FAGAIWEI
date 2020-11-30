import os
import sys
from scrapy.cmdline import execute

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
execute(['scrapy','crawl','xinwen_1'])
