# -*- coding: utf-8 -*-
"""
Created on Sat Feb 19 16:49:51 2022

@author: Administrator
"""

import os

from dydx3 import Client
from dydx3.constants import MARKET_BTC_USD
from dydx3.constants import MARKET_STATISTIC_DAY_ONE

from tests.constants import DEFAULT_HOST

ADDRESS_1 = '0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C0'
API_HOST = os.environ.get('V3_API_HOST', DEFAULT_HOST)


class TestPublic():

    def test_check_if_user_exists(self):
        public = Client(API_HOST).public
        resp = public.check_if_user_exists(ADDRESS_1)
        assert resp.data == {'exists': False}
        assert resp.headers != {}

    def test_check_if_username_exists(self):
        public = Client(API_HOST).public
        resp = public.check_if_username_exists('foo')
        assert resp.data == {'exists': False}
        assert resp.headers != {}

    def test_get_markets(self):
        public = Client(API_HOST).public
        resp = public.get_markets()
        assert resp.data != {}
        assert resp.headers != {}

    def test_get_orderbook(self):
        public = Client(API_HOST).public
        resp = public.get_orderbook(MARKET_BTC_USD)
        assert resp.data != {}
        assert resp.headers != {}

    def test_get_stats(self):
        public = Client(API_HOST).public
        resp = public.get_stats(
            MARKET_BTC_USD,
            MARKET_STATISTIC_DAY_ONE,
        )
        assert resp.data != {}
        assert resp.headers != {}

    def test_get_trades(self):
        public = Client(API_HOST).public
        resp = public.get_trades(MARKET_BTC_USD)
        assert resp.data != {}
        assert resp.headers != {}

    def test_get_historical_funding(self):
        public = Client(API_HOST).public
        resp = public.get_historical_funding(MARKET_BTC_USD)
        assert resp.data != {}
        assert resp.headers != {}

    def test_get_candles(self):
        public = Client(API_HOST).public
        resp = public.get_candles(MARKET_BTC_USD)
        assert resp.data != {}
        assert resp.headers != {}

    def test_get_fast_withdrawal(self):
        public = Client(API_HOST).public
        resp = public.get_fast_withdrawal()
        assert resp.data != {}
        assert resp.headers != {}

    def test_verify_email(self):
        try:
            public = Client(API_HOST).public
            public.verify_email('token')
        except Exception as e:
            # No userId gotten with token: token so no verification
            # has occurred
            assert e.status_code == 400

    def test_public_retroactive_mining(self):
        public = Client(API_HOST).public
        resp = public.get_public_retroactive_mining_rewards(ADDRESS_1)
        assert resp.data != {}
        assert resp.headers != {}
        
if __name__ == '__main__':   
    
    
    a=TestPublic()
    #a.test_get_markets()
    import requests
    # 引入 requests，实现请求
    #URL = 'http://c.biancheng.net/uploads/course/python_spider/191009.html'
    URL = "https://api.dydx.exchange/v3/candles/BTC-USD?resolution=15MINS&limit=10"
    # 输入在浏览器的网址
    res = requests.get(URL)
    res.encoding = 'utf-8' # 设置可接收的编码为 utf-8
    # 发送 GET 方式的请求，并把返回的结果(响应)存储在 res 变量里头
    print(res.text)
    # res 就是 Response 对象，文本类对象使用.text 把数据转为字符串形式再输出
    
    
    