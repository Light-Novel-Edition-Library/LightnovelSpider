# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import os
import pymysql
from lightnovel import MysqlPool
# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy import Spider, Item
from lightnovel.items import *

class LightnovelPipeline:
    def process_item(self, item, spider):
        return item

class Wenku8Pipeline:
    def process_item(self, item:Item, spider):
        if isinstance(item, Wenku8BookItem):
            adapter = ItemAdapter(item)
            aid = adapter['aid']
            title = adapter['title']
            author = adapter['author']
            category = adapter['category']
            tags = adapter['tags']
            description = adapter['description']
            with MysqlPool.connect() as conn:
                with conn.cursor() as cur:
                    try:
                        cur.execute('INSERT IGNORE INTO wenku8_books(aid,title,author,category,tags,description) VALUES (%s,%s,%s,%s,%s,%s)', (aid,title,author,category,tags,description))
                        conn.commit()
                    except pymysql.err.Error as e:
                        conn.rollback()
                        raise e
        elif isinstance(item, Wenku8ChapterItem):
            adapter = ItemAdapter(item)
            aid = adapter['aid']
            cid = adapter['cid']
            volume = adapter['volume']
            chapter = adapter['chapter']
            content = adapter['content']
            with MysqlPool.connect() as conn:
                with conn.cursor() as cur:
                    try:
                        cur.execute('INSERT IGNORE INTO wenku8_chapters(aid,cid,volume,chapter,content) VALUES (%s,%s,%s,%s,%s)', (aid,cid,volume,chapter,content))
                        conn.commit()
                    except pymysql.err.Error as e:
                        conn.rollback()
                        raise e
        elif isinstance(item, Wenku8ImageItem):
            adapter = ItemAdapter(item)
            cid = adapter['cid']
            filename = adapter['filename']
            content = adapter['content']
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
        return item

class LibiPipeline:
    def open_spider(self, spider:Spider):
        pass

    def process_item(self, item:Item, spider):
        if isinstance(item, LibiBookItem):
            adapter = ItemAdapter(item)
            bid = adapter['bid']
            title = adapter['title']
            author = adapter['author']
            category = adapter['category']
            description = adapter['description']
            with MysqlPool.connect() as conn:
                with conn.cursor() as cur:
                    try:
                        cur.execute('INSERT IGNORE INTO libi_books(bid,title,author,category,description) VALUES (%s,%s,%s,%s,%s)', (bid,title,author,category,description))
                        conn.commit()
                    except pymysql.err.Error as e:
                        conn.rollback()
                        raise e
        elif isinstance(item, LibiChapterItem):
            adapter = ItemAdapter(item)
            bid = adapter['bid']
            cid = adapter['cid']
            volume = adapter['volume']
            chapter = adapter['chapter']
            content = adapter['content']
            with MysqlPool.connect() as conn:
                with conn.cursor() as cur:
                    try:
                        cur.execute('INSERT IGNORE INTO libi_chapters(bid,cid,volume,chapter,content) VALUES (%s,%s,%s,%s,%s)', (bid,cid,volume,chapter,content))
                        conn.commit()
                    except pymysql.err.Error as e:
                        conn.rollback()
                        raise e
        elif isinstance(item, LibiImageItem):
            adapter = ItemAdapter(item)
            cid = adapter['cid']
            filename = adapter['filename']
            content = adapter['content']
            try:
                os.mkdir('./img')
            except FileExistsError:
                pass
            try:
                os.mkdir('./img/libi')
            except FileExistsError:
                pass
            try:
                os.mkdir('./img/libi/' + str(int(cid/10000)))
            except FileExistsError:
                pass
            try:
                os.mkdir('./img/libi/' + str(int(cid/10000)) + '/' + str(cid))
            except FileExistsError:
                pass
            with open('./img/libi/' + str(int(cid/10000)) + '/' + str(cid) + '/' + filename, 'wb') as f:
                f.write(content)
        return item

    def close_spider(self, spider):
        pass