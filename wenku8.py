import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests
from parsel import Selector
import pymysql
from dbutils.pooled_db import PooledDB
import os
import logging
import threading
from configparser import ConfigParser

COOKIES = ''''''
PROXY = ''
MYSQL_HOST = ''
MYSQL_PORT = 3306
MYSQL_USER = ''
MYSQL_PASSWORD = ''
MYSQL_DATABASE = ''
THREAD_NUM = 8
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.62 LightnovelSpider/4.0'

if __name__ == '__main__':
    config = ConfigParser()
    config.read(os.path.basename(__file__).split(".")[0] + '.ini')
    COOKIES = config.get('REQUEST', 'COOKIES')
    PROXY = config.get('REQUEST', 'PROXY')
    MYSQL_HOST = config.get('MYSQL', 'HOST')
    MYSQL_PORT = config.getint('MYSQL', 'PORT')
    MYSQL_USER = config.get('MYSQL', 'USER')
    MYSQL_PASSWORD = config.get('MYSQL', 'PASSWORD')
    MYSQL_DATABASE = config.get('MYSQL', 'DATABASE')

semaphore = threading.Semaphore(THREAD_NUM)
logging.basicConfig(
    level= logging.INFO,
    datefmt= '%Y-%m-%d %H:%M:%S',
    format= '%(asctime)s %(levelname)s %(message)s'
)

class Request:
    def __init__(self, url:str, referer:str=None, callback=lambda*args:None, cb_kwargs:dict=dict()) -> None:
        self.url = url
        self.referer = referer
        self.callback = callback
        self.cb_kwargs = cb_kwargs

class Mysql:
    _pool = PooledDB(
        creator= pymysql,
        host= MYSQL_HOST,
        port= MYSQL_PORT,
        user= MYSQL_USER,
        password= MYSQL_PASSWORD,
        database= MYSQL_DATABASE
    )
    @classmethod
    def connect(cls):
        return cls._pool.connection()

def start():
    crawl(Request('https://www.wenku8.net/modules/article/articlelist.php', callback=parse_list))

def parse_list(response:requests.Response):
    response.encoding = 'GBK'
    d = Selector(text=response.text)
    for b in d.css('td div div b'):
        aid = int(b.css('a::attr(href)').get().split('/')[-1].split('.')[0])
        crawl(Request('https://www.wenku8.net/modules/article/articleinfo.php?id=%d' % (aid,), referer=response.url, callback=parse_book))
    path = d.css('a.next::attr(href)').get()
    if path:
        crawl(Request('https://www.wenku8.net' + path, referer=response.url, callback=parse_list))

def parse_book(response:requests.Response):
    response.encoding = 'GBK'
    d = Selector(text=response.text)
    aid = int(response.request.url.split('id=')[-1])
    crawl(Request('https://www.wenku8.net/modules/article/reader.php?aid=%d' % (aid,), referer=response.url, callback=parse_catalog))
    title = d.css('span b::text').get()
    author = d.css('td[width="20%"]::text')[1].get().split('：')[-1]
    category = d.css('td[width="20%"]::text')[0].get().split('：')[-1]
    tags = d.css('span.hottext b::text')[0].get().split('：')[-1]
    description = '\n\n'.join(line.strip() for line in d.css('div#content table')[2].css('span')[-1].css('*::text').getall())
    logging.info('%d %s %s %s', aid, title, author, category)
    with Mysql.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT IGNORE INTO wenku8_books(aid,title,author,category,tags,description) VALUES(%s,%s,%s,%s,%s,%s)',
                (aid,title,author,category,tags,description)
            )
            conn.commit()

def parse_catalog(response:requests.Response):
    response.encoding = 'GBK'
    d = Selector(text=response.text)
    for td in d.css('td'):
        if td.css('td::attr(class)').get() == 'vcss':
            volume = td.css('td::text').get()
        elif td.css('td::attr(class)').get() == 'ccss':
            chapter = td.css('a::text').get(None)
            url = td.css('a::attr(href)').get(None)
            if chapter!=None and url!=None:
                cid = int(url.split('cid=')[-1])
                with Mysql.connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute('SELECT COUNT(cid) FROM wenku8_chapters WHERE cid=%s', (cid,))
                        count = cur.fetchone()[0]
                if count == 0:
                    crawl(Request(url, referer=response.url, callback=parse_chapter, cb_kwargs=dict(volume=volume, chapter=chapter)))

def parse_chapter(response:requests.Response):
    response.encoding = 'GBK'
    d = Selector(text=response.text)
    aid = int(response.request.url.split('aid=')[-1].split('&')[0])
    cid = int(response.request.url.split('cid=')[-1])
    volume = response.cb_kwargs['volume']
    chapter = response.cb_kwargs['chapter']
    content = '\n'.join(line.strip() for line in d.css('div#content::text').getall()).strip()
    imgUrls = d.css('div#content img::attr(src)').getall()
    for imgUrl in imgUrls:
        crawl(Request(imgUrl, referer=response.url, callback=parse_image, cb_kwargs=dict(cid=cid)))
    logging.info('%d %d %s %s', aid, cid, volume, chapter)
    with Mysql.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT IGNORE INTO wenku8_chapters(aid,cid,volume,chapter,content) VALUES(%s,%s,%s,%s,%s)',
                (aid,cid,volume,chapter,content)
            )
            conn.commit()

def parse_image(response:requests.Response):
    cid = response.cb_kwargs['cid']
    filename = response.request.url.split('/')[-1]
    content = response.content
    logging.info('%d %s', cid, filename)
    try:
        os.mkdir('./img')
    except FileExistsError:
        pass
    try:
        os.mkdir('./img/wenku8')
    except FileExistsError:
        pass
    try:
        os.mkdir('./img/wenku8/' + str(int(cid/10000)))
    except FileExistsError:
        pass
    try:
        os.mkdir('./img/wenku8/' + str(int(cid/10000)) + '/' + str(cid))
    except FileExistsError:
        pass
    with open('./img/wenku8/' + str(int(cid/10000)) + '/' + str(cid) + '/' + filename, 'wb') as f:
        f.write(content)

def crawl(request:Request):
    def run(request:Request):
        with semaphore:
            headers = {
                'User-Agent': USER_AGENT
            }
            if request.referer:
                headers['Referer'] = request.referer
            try:
                response = requests.get(
                    url= request.url,
                    cookies= {i.split("=")[0]:i.split("=")[-1] for i in COOKIES.split("; ")},
                    proxies= {
                        'http': PROXY,
                        'https': PROXY
                    },
                    headers= headers,
                    timeout= 10,
                    verify= False
                )
                response.cb_kwargs = request.cb_kwargs
                request.callback(response)
            except requests.exceptions.ProxyError:
                crawl(request)
            except requests.exceptions.ConnectTimeout:
                crawl(request)
            except requests.exceptions.ConnectionError:
                crawl(request)
            except requests.exceptions.ReadTimeout:
                crawl(request)
            except requests.exceptions.ChunkedEncodingError:
                crawl(request)
    threading.Thread(target=run, args=(request,)).start()

if __name__ == '__main__':
    start()