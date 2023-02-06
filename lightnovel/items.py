# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class LightnovelItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass

class Wenku8BookItem(scrapy.Item):
    aid = scrapy.Field()
    title = scrapy.Field()
    author = scrapy.Field()
    category = scrapy.Field()
    tags = scrapy.Field()
    description = scrapy.Field()

class Wenku8ChapterItem(scrapy.Item):
    aid = scrapy.Field()
    cid = scrapy.Field()
    volume = scrapy.Field()
    chapter = scrapy.Field()
    content = scrapy.Field()

class Wenku8ImageItem(scrapy.Item):
    cid = scrapy.Field()
    filename = scrapy.Field()
    content = scrapy.Field()

class LibiBookItem(scrapy.Item):
    bid = scrapy.Field()
    title = scrapy.Field()
    author = scrapy.Field()
    category = scrapy.Field()
    description = scrapy.Field()

class LibiChapterItem(scrapy.Item):
    bid = scrapy.Field()
    cid = scrapy.Field()
    volume = scrapy.Field()
    chapter = scrapy.Field()
    content = scrapy.Field()

class LibiImageItem(scrapy.Item):
    cid = scrapy.Field()
    filename = scrapy.Field()
    content = scrapy.Field()