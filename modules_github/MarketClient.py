# -*- coding: utf-8 -*-
"""
Created on Sun Oct 24 10:17:26 2021

@author: Administrator
"""
"""
MarketClient定义了所以市场获取参数的方法
"""

import Constants
import pandas as pd
import json
import datetime
import logging
import platform



class MarketClient:
    
    
    sourceUrldic={"dydx":Constants.DYDX_API_HOST_MAINNET,
                  "binance":""};
    


    
    def __init__(self,
                 dex_name=None,
                 ):
        
        self.source_api=dex_name, 
        self.change_APIsource(dex_name),
        
        if(self.source_api=='dydx'): 
            from dydx3 import Client
            self.dydx_client=Client(host=self.sourceUrldic['dydx'])
        if(self.source_api=='binance'): 
            from binance.um_futures import UMFutures
            self.binance_client=UMFutures()           
        return 
    
    
    def getMarketinfo(self,code):
        if(self.source_api=='dydx'):
            ret=self.dydx_client.public.get_markets(code)
            if(platform.system()=='Linux'):
                ret=ret.data
            return ret

    
    def change_APIsource(self,dexname):
        
        if (self.sourceUrldic.get(dexname,-1)==-1):
            logging.error('the dex is not support.')
        self.source_api=dexname
        return 1    
            

    def get_price_v1(self,code=None,count=None,frequency=None,start=None,stop=None):       
    # =============================================================================  
    #     Descrption:获得市场数据参数, 数据源依据souceAPI 确定
    #     Parameters：
    #         @param_1:code  : eg. BTC-USD
    #         @param_2:count : return numbers
    #         @param_3:frequency
    #     Returns: the dataframe  index:timestamp, field: OHLC,volume]   
    # =============================================================================\
        if(self.source_api=='dydx'):

            res = self.dydx_client.public.get_candles(
                market=code,
                resolution=frequency,
                limit=count,
                from_iso=start, #"2021-10-24T02:30:00.000Z",
                to_iso=stop #"2021-10-24T05:30:00.000Z"                
                )
            if(platform.system()=='Linux'):
                res=res.data
            res=pd.DataFrame.from_dict(res['candles'])
            res.rename(columns={"startedAt":"time"},inplace=True)
            res.rename(columns={"usdVolume":"volume"},inplace=True)
            res=res.set_index(pd.to_datetime(res['time']))
            res.drop(labels=['time','market','resolution','startingOpenInterest','baseTokenVolume','trades'],axis=1,inplace=True)
            res=res.loc[:,['open','high','low','close','volume']]
            return res
        if(self.source_api=='binance'):
            
            if(start!=None and stop!=None): 
                starttime=start
                stoptime=stop
                starttime_stamp = int(datetime.datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S').timestamp() * 1000)
                stoptime_stamp = int(datetime.datetime.strptime(stoptime, '%Y-%m-%d %H:%M:%S').timestamp() * 1000)
            
            if(start==None): starttime_stamp=None
            if(stop==None): stoptime_stamp=None    
            
            
            
            res  = self.binance_client.klines(
                symbol=code, 
                interval=frequency,
                startTime=starttime_stamp,
                endTime=stoptime_stamp,
                limit=count,
                )
            if(platform.system()=='Linux'):
                res=res.data
                
            res=pd.DataFrame.from_dict(res)
            res.rename(columns={0:"time"},inplace=True)
            res.rename(columns={1:"open"},inplace=True)
            res.rename(columns={2:"high"},inplace=True)
            res.rename(columns={3:"low"},inplace=True)
            res.rename(columns={4:"close"},inplace=True)
            res.rename(columns={5:"volume"},inplace=True)
            res.rename(columns={8:"Numberoftrades"},inplace=True)
            res.rename(columns={9:"TakerVolume"},inplace=True)
            
            res['time']=res['time'].astype('datetime64[ms]')
            res=res.set_index(pd.to_datetime(res['time']))
            res.drop(labels=['time',6,7,10,11],axis=1,inplace=True)
            
            return res
            
        else:
            logging.error('price get error: the api source is nor right.')
           
        return 1
    

if __name__ == '__main__':    
    
    Test='2'
    if(Test=='1'):
        client=MarketClient(dex_name='dydx')
        a=client.get_price_v1(code="ETH-USD",count=10,frequency='15MINS')
        print(a)
    
    if(Test=='2'):
        client=MarketClient(dex_name='binance')
        starttime="2024-3-7 00:00:00"
        stoptime="2024-3-8 00:00:00"

    
        b=client.get_price_v1(code="ETHUSDT",frequency="5m",start=starttime,stop=stoptime)
       # b=client.get_price_v1(code="ETHUSDT",count=200,frequency="15m")

  
    
