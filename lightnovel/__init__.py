import pymysql
from dbutils.persistent_db import PersistentDB
import requests

class MysqlPool:
    _pool = None

    @classmethod
    def connect(cls):
        if cls._pool == None:
            cls._pool = PersistentDB(
                creator=pymysql,
                host='127.0.0.1',
                port=3306,
                user='root',
                password='',
                database='lightnovel_spider'
            )
        return cls._pool.connection()

def isOnline(proxy:str=None) -> bool:
    if proxy == None:
        PROXIES = None
    else:
        PROXIES = {
            'http': proxy,
            'https': proxy
        }
    def test(url:str) -> bool:
        try:
            requests.get(url, timeout=1, proxies=PROXIES)
            return True
        except requests.RequestException as e:
            return False
    return test('http://www.baidu.com') or test('http://www.bing.com')