import scrapy
import logging
import re
from parsel import Selector


def get_attachments(response):
    valid_extensions = [".doc", ".docx", ".xlsx", ".xls", ".pdf", ".zip", ".wps", ".rar"]
    # 取所有超链接
    url = response.css("a:link")
    appendix=""
    appendix_name=""
    for a in url:
        # 取超链接文本
        href = a.css('::attr(href)').extract_first()
        name = a.css('::text').extract_first()
        if href and name:
            for ext in valid_extensions:
                if href.endswith(ext) or name.endswith(ext):
                    appendix = appendix + response.urljoin(href) + ","
                    appendix_name = appendix_name + name + ","
    return appendix, appendix_name


#时间格式化
def get_times(srcTime):
    result = srcTime
    if isinstance(srcTime, str):
        list = re.findall(r'([1-9]\d*?\d*)', srcTime)
        if len(list) == 1 and len(list[0]) == 8:  # eg:20190810
            result = list[0][:4] + '-' + list[0][4:6] + '-' + list[0][6:]
        elif len(list) > 2:
            result = list[0] + '-' + list[1].zfill(2) + '-' + list[2].zfill(2)
        else:
            if srcTime != '':
                logging.error('时间格式化异常：' + srcTime)
    return result

def get_symbol(srcsymbol):
    result=str(srcsymbol)
    #中华人民共和国国家发展和改革委员会 2019年第29号令
    fz_symbol =re.findall('(\d+年第\d+号令)',result)
    if fz_symbol:
        return fz_symbol
    elif re.findall('(发改.*〔\d+〕\d+号)',result):
        return re.findall('(发改.*〔\d+〕\d+号)',result)
    else:
        return re.findall('(发改.*〔\d+〕\d+号)', result)
def get_url(response):
    res_html = Selector(response)
    titles = []
    p_times = []
    urls = []
    for res_html in res_html.css('td'):
        title = res_html.css('td > a ::text').extract_first()
        if title:
            titles.append(title)
        p_time = res_html.css('.bt_time ::text').extract_first()
        if p_time:
            p_times.append(p_time)
        url = res_html.css('a::attr(href)').extract_first()
        if url:
            urls.append(url)
    for res_details in zip(titles,p_times,urls):
        title = res_details[0]
        p_time = res_details[1]
        url = res_details[2]
        return title,p_time,url
