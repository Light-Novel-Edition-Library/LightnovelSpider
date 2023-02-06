import scrapy
from scrapy.http import Response
from lightnovel.items import LibiBookItem, LibiChapterItem, LibiImageItem
import pymysql
from lightnovel import MysqlPool
import html2text

class LibiSpider(scrapy.Spider):
    name = 'libi'
    custom_settings = {
        'ITEM_PIPELINES': {'lightnovel.pipelines.LibiPipeline': 300},
        'JOBDIR': 'job/libi'
        }

    COOKIES = ''''''
    cookiesDict = {i.split("=")[0]:i.split("=")[-1] for i in COOKIES.split("; ")}

    def start_requests(self):
        yield scrapy.Request('https://www.linovelib.com/top/postdate/1.html', cookies=self.cookiesDict)

    def parse(self, response:Response):
        totalPageNum = int(response.css('a.last::text').get())
        self.logger.info('总页数：%d', totalPageNum)
        for i in range(totalPageNum):
            curPageNum = i+1
            yield scrapy.Request('https://www.linovelib.com/top/postdate/'+str(curPageNum)+'.html', cookies=self.cookiesDict, callback=self.parse_list, dont_filter=True)

    def parse_list(self, response:Response):
        for selector in response.css('.rank_d_list'):
            bid = title = author = category = description = None
            bid = int(selector.css('.rank_d_b_name a::attr(href)').get().split('/')[-1].split('.')[0])
            title = selector.css('.rank_d_b_name a::text').get()
            author = selector.css('.rank_d_b_cate a::text')[0].get()
            category = selector.css('.rank_d_b_cate a::text')[1].get()
            description = selector.css('.rank_d_b_info::text').get()
            libiBookItem = LibiBookItem()
            libiBookItem['bid'] = bid
            libiBookItem['title'] = title
            libiBookItem['author'] = author
            libiBookItem['category'] = category
            libiBookItem['description'] = description
            self.logger.info('%d %s %s %s', bid, title, author, category)
            yield libiBookItem
            yield scrapy.Request('https://www.linovelib.com/novel/'+str(bid)+'/catalog', cookies=self.cookiesDict, callback=self.parse_catalog)

    def parse_catalog(self, response:Response):
        catalogCount = len(response.css('.chapter-list li.col-4 a::attr(href)').getall())
        bid = int(response.request.url.split('/')[-2])
        with MysqlPool.connect() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute('SELECT COUNT(cid) FROM libi_chapters WHERE bid=%s', (bid,))
                    savedCount = cur.fetchone()[0]
                except pymysql.err.Error as e:
                    raise e
        if catalogCount > savedCount:
            url = 'https://www.linovelib.com' + response.css('.chapter-list li.col-4 a::attr(href)').get()
            yield scrapy.Request(url=url, cookies=self.cookiesDict, callback=self.parse_chapter)

    def parse_chapter(self, response:Response, lastLibiChapterItem:LibiChapterItem=None):
        h = html2text.HTML2Text()

        def convertCharaters(s:str):
            '''将pctheme.js文件的218行通过beautifier.io反混淆后得到，共100对转换字符'''
            return s.replace('', '的').replace('', '一').replace('', '是').replace('', '了').replace('', '我').replace('', '不').replace('', '人').replace('', '在').replace('', '他').replace('', '有').replace('', '这').replace('', '个').replace('', '上').replace('', '们').replace('', '来').replace('', '到').replace('', '时').replace('', '大').replace('', '地').replace('', '为').replace('', '子').replace('', '中').replace('', '你').replace('', '说').replace('', '生').replace('', '国').replace('', '年').replace('', '着').replace('', '就').replace('', '那').replace('', '和').replace('', '要').replace('', '她').replace('', '出').replace('', '也').replace('', '得').replace('', '里').replace('', '后').replace('', '自').replace('', '以').replace('', '会').replace('', '家').replace('', '可').replace('', '下').replace('', '而').replace('', '过').replace('', '天').replace('', '去').replace('', '能').replace('', '对').replace('', '小').replace('', '多').replace('', '然').replace('', '于').replace('', '心').replace('', '学').replace('', '么').replace('', '之').replace('', '都').replace('', '好').replace('', '看').replace('', '起').replace('', '发').replace('', '当').replace('', '没').replace('', '成').replace('', '只').replace('', '如').replace('', '事').replace('', '把').replace('', '还').replace('', '用').replace('', '第').replace('', '样').replace('', '道').replace('', '想').replace('', '作').replace('', '种').replace('', '开').replace('', '美').replace('', '乳').replace('', '阴').replace('', '液').replace('', '茎').replace('', '欲').replace('', '呻').replace('', '肉').replace('', '交').replace('', '性').replace('', '胸').replace('', '私').replace('', '穴').replace('', '淫').replace('', '臀').replace('', '舔').replace('', '射').replace('', '脱').replace('', '裸').replace('', '骚').replace('', '唇')

        bid = cid = volume = chapter = content = None
        if lastLibiChapterItem != None:
            bid = lastLibiChapterItem['bid']
            cid = lastLibiChapterItem['cid']
            volume = lastLibiChapterItem['volume']
            chapter = lastLibiChapterItem['chapter']
            content = lastLibiChapterItem['content'] + h.handle(convertCharaters(response.css('#TextContent').get()))
        else:
            bid = int(response.request.url.split('/')[-2])
            cid = int(response.request.url.split('/')[-1].split('.')[0])
            volume = response.css('.chepnav::text')[2].get().replace('>', '').strip()
            chapter = response.css('h1::text').get()
            content = h.handle(convertCharaters(response.css('#TextContent').get()))
        libiChapterItem = LibiChapterItem()
        libiChapterItem['bid'] = bid
        libiChapterItem['cid'] = cid
        libiChapterItem['volume'] = volume
        libiChapterItem['chapter'] = chapter
        libiChapterItem['content'] = content
        nextPageName = response.css('.mlfy_page a::text')[4].get()
        nextPageUrl = 'https://www.linovelib.com' + response.css('.mlfy_page a::attr(href)')[2].get()
        if nextPageName == '下一页':
            yield scrapy.Request(nextPageUrl, cookies=self.cookiesDict, callback=self.parse_chapter, cb_kwargs=dict(lastLibiChapterItem=libiChapterItem))
        else:
            self.logger.info('%d %d %s %s', bid, cid, volume, chapter)
            yield libiChapterItem
            if nextPageName == '下一章':
                yield scrapy.Request(nextPageUrl, cookies=self.cookiesDict, callback=self.parse_chapter)
        imgUrls = response.css('#TextContent img::attr(src)').getall()
        for imgUrl in imgUrls:
            if imgUrl[0:7]=='http://' or imgUrl[0:8]=='https://':
                yield scrapy.Request(imgUrl, cookies=self.cookiesDict, callback=self.parse_image, cb_kwargs=dict(cid=cid))
            elif imgUrl[0:2]=='//':
                yield scrapy.Request('https:' + imgUrl, cookies=self.cookiesDict, callback=self.parse_image, cb_kwargs=dict(cid=cid))
            elif imgUrl[0]=='/':
                yield scrapy.Request('https://www.linovelib.com' + imgUrl, cookies=self.cookiesDict, callback=self.parse_image, cb_kwargs=dict(cid=cid))

    def parse_image(self, response:Response, cid:int):
        filename = response.request.url.split('/')[-1]
        content = response.body
        libiImageItem = LibiImageItem()
        libiImageItem['cid'] = cid
        libiImageItem['filename'] = filename
        libiImageItem['content'] = content
        self.logger.info('%d %s', cid, filename)
        yield libiImageItem