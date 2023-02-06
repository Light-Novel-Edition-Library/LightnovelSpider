import scrapy
from scrapy.http import Response
from lightnovel.items import Wenku8BookItem, Wenku8ChapterItem, Wenku8ImageItem
import pymysql
from lightnovel import MysqlPool

class Wenku8Spider(scrapy.Spider):
    name = 'wenku8'
    custom_settings = {
        'ITEM_PIPELINES': {'lightnovel.pipelines.Wenku8Pipeline': 300},
        'JOBDIR': 'job/wenku8'
        }

    COOKIES = ''''''
    cookiesDict = {i.split("=")[0]:i.split("=")[-1] for i in COOKIES.split("; ")}

    def start_requests(self):
        yield scrapy.Request('https://www.wenku8.net/modules/article/articlelist.php', cookies=self.cookiesDict)

    def parse(self, response:Response):
        totalPageNum = int(response.css('a.last::text').get())
        self.logger.info('总页数：%d', totalPageNum)
        for i in range(totalPageNum):
            curPageNum = i+1
            yield scrapy.Request('https://www.wenku8.net/modules/article/articlelist.php?page=%d' % (curPageNum,), cookies=self.cookiesDict, callback=self.parse_list, dont_filter=True)

    def parse_list(self, response:Response):
        for selector in response.css('td div div b'):
            aid = int(selector.css('a::attr(href)').get().split('/')[-1].split('.')[0])
            yield scrapy.Request('https://www.wenku8.net/modules/article/articleinfo.php?id=%d' % (aid,), cookies=self.cookiesDict, callback=self.parse_info)

    def parse_info(self, response:Response):
        aid = title = author = category = tags = description = None
        aid = int(response.request.url.split('id=')[-1])
        title = response.css('span b::text').get()
        author = response.css('td[width="20%"]::text')[1].get().split('：')[-1]
        category = response.css('td[width="20%"]::text')[0].get().split('：')[-1]
        tags = response.css('span.hottext b::text')[0].get().split('：')[-1]
        description = '\n\n'.join(textline.strip() for textline in response.css('div#content table')[2].css('span')[-1].css('*::text').getall())
        wenku8BookItem = Wenku8BookItem()
        wenku8BookItem['aid'] = aid
        wenku8BookItem['title'] = title
        wenku8BookItem['author'] = author
        wenku8BookItem['category'] = category
        wenku8BookItem['tags'] = tags
        wenku8BookItem['description'] = description
        self.logger.info('%d %s %s %s', aid, title, author, category)
        yield wenku8BookItem
        yield scrapy.Request('https://www.wenku8.net/modules/article/reader.php?aid=%d' % aid, cookies=self.cookiesDict, callback=self.parse_catalog)

    def parse_catalog(self, response:Response):
        volume = chapter = url = None
        for td in response.css('td'):
            if td.css('td::attr(class)').get() == 'vcss':
                volume = td.css('td::text').get()
            elif td.css('td::attr(class)').get() == 'ccss':
                chapter = td.css('a::text').get(None)
                url = td.css('a::attr(href)').get(None)
                if chapter!=None and url!=None:
                    cid = int(url.split('cid=')[-1])
                    with MysqlPool.connect() as conn:
                        with conn.cursor() as cur:
                            try:
                                cur.execute('SELECT COUNT(cid) FROM wenku8_chapters WHERE cid=%s', (cid,))
                                savedCount = cur.fetchone()[0]
                            except pymysql.err.Error as e:
                                raise e
                    if savedCount == 0:
                        yield scrapy.Request(url, cookies=self.cookiesDict, callback=self.parse_chapter, cb_kwargs=dict(volume=volume, chapter=chapter))

    def parse_chapter(self, response:Response, volume:str, chapter:str):
        aid = cid = content = None
        aid = int(response.request.url.split('aid=')[-1].split('&')[0])
        cid = int(response.request.url.split('cid=')[-1])
        content = '\n'.join(textline.strip() for textline in response.css('div#content::text').getall()).strip()
        wenku8ChapterItem = Wenku8ChapterItem()
        wenku8ChapterItem['aid'] = aid
        wenku8ChapterItem['cid'] = cid
        wenku8ChapterItem['volume'] = volume
        wenku8ChapterItem['chapter'] = chapter
        wenku8ChapterItem['content'] = content
        self.logger.info('%d %d %s %s', aid, cid, volume, chapter)
        yield wenku8ChapterItem
        imgUrls = response.css('div#content img::attr(src)').getall()
        for imgUrl in imgUrls:
            yield scrapy.Request(imgUrl, cookies=self.cookiesDict, callback=self.parse_image, cb_kwargs=dict(cid=cid))

    def parse_image(self, response:Response, cid:int):
        filename = response.request.url.split('/')[-1]
        content = response.body
        wenku8ImageItem = Wenku8ImageItem()
        wenku8ImageItem['cid'] = cid
        wenku8ImageItem['filename'] = filename
        wenku8ImageItem['content'] = content
        self.logger.info('%d %s', cid, filename)
        yield wenku8ImageItem