
import Constants
from AccountClient import AccountClient as Account
import os
import configparser
import time
import logging
import platform
## here only for test

##

from binance.error import ClientError

class TradeClient(Account):
        def __init__(self,accountdic=None):
            
            #Setting the accont 
            
            Account.__init__(self,accountdic)
            print('Account and Pravite init in %s'%(accountdic['dex']))
            
        
            
            self.orderRet={'corename':None,
                           'id':None,
                           'market':None,
                           'side':None,
                           'price':None,
                           'createdPrice':None,
                           'createdTime':None,
                           'createdDataTime':None}
            
                
                
        
        # start api define here
            
        def check_balance(self):
                        
            #if(self.dexname=='dydx'):    
            #    if(platform.system()=='Windows'):
            #        ret = self.dex_client.private.get_account(self.dydx_default_ethereum_address)                                
            #    if(platform.system()=='Linux'):
            #        ret = self.dex_client.private.get_account(self.dydx_default_ethereum_address)
            #        ret = ret.data
            #    balance=ret['account']['freeCollateral']         
            #    return balance
        
            if(self.dexname=='binance'):    
                
                try:
                   
                    if(platform.system()=='Windows'):
                        ret=self.dex_client.balance()
                               
                    if(platform.system()=='Linux'):
                        ret=self.dex_client.balance()
                        ret = ret.data
                    balance=ret[5]['balance']   
                    logging.info(ret)
                    return balance
                except ClientError as error:
                    logging.error(
                        "Found error. status: {}, error code: {}, error message: {}".format(
                            error.status_code, error.error_code, error.error_message
                        ))
            
        def check_position(self,code=None):
            
            if(self.dexname=='dydx'):        
                if(platform.system()=='Windows'):
                    ret = self.dex_client.private.get_positions(market=code,status='OPEN')  
                if(platform.system()=='Linux'): 
                    ret = self.dex_client.private.get_positions(market=code,status='OPEN')  
                    ret = ret.data
                position=ret['positions'][0]       
            return position            
            
        
        def check_orders(self):
            return
        
        def get_fills(self,orderid):
            if(self.dexname=='dydx'):
                ret=self.dex_client.private.get_fills(order_id=orderid)
                if(platform.system()=='Linux'):
                    ret = ret.data
            return ret
        
        def order_open(self,code=None,oside=None,otype=None,osize=None,oprice=None,oaction=None):           
            if(self.dexname=='dydx'):                                       
                ret_order = self.dex_client.private.create_order(
                            position_id=self.dydx_position_id, # required for creating the order signature
                            market=code,
                            side=oside,
                            order_type=otype,
                            post_only=False,
                            size=osize,
                            price=oprice,
                            limit_fee='0.015',
                            expiration_epoch_seconds=time.time() + 100,
                            time_in_force='IOC',
                            )
                if(platform.system()=='Linux'):
                    ret_order = ret_order.data
                    
                orderid=ret_order["order"]["id"]
                logging.info("OrderCreated:"+str(ret_order["order"]))
                #self.orderRet['market']=ret_order["order"]["market"]
                return ret_order
                
            if(self.dexname=='binance'): 
                
                if oaction=="OPEN": oaction="BUY"
                if oaction=="CLOSE": oaction="SELL"
                          
                if otype=='MARKET':
                                            
                    ret_order = self.dex_client.new_order(
                        
                                symbol=code,
                                side=oaction,
                                positionSide=oside,
                                type=otype,
                                quantity=float(osize),
                                #timeInForce="GTC",
                                #price=59808,                               
                        )    
                    if(platform.system()=='Linux'):
                        ret_order = ret_order.data

                       
                return ret_order
            
                            
        def order_get(self):
                        
            if(self.dexname=='dydx'):                  
                all_orders = self.dex_client.private.get_orders()      
                if(platform.system()=='Linux'):
                    all_orders = all_orders.data
                
            return all_orders 
        
        def order_get_by_id(self,orderid=None):
                        
            if(self.dexname=='dydx'):                  
                order = self.dex_client.private.get_order_by_id(orderid)  
                if(platform.system()=='Linux'):
                    order =order.data                   
            return order 
        
        def order_get_by_symbol(self,symbol=None):
            
            if(self.dexname=='binance'):                  
                order = self.dex_client.get_all_orders(symbol=symbol)
                if(platform.system()=='Linux'):
                    order =order.data                   
            return order 
             
        def order_close(self):
            return
        

# 从config 文件导入 一个 account 实体，然后生产 交易管理实体
configPath=os.getcwd() + r"/UserCase/"+'config.ini'     
        
conf=configparser.ConfigParser()
conf.read(configPath)
dexname=conf.get('Dexinfo','dexname')
  
if dexname == 'binance':
    binance_api_key=conf.get('Dexinfo','binance_api_key')
    binance_api_secret=conf.get('Dexinfo','binance_api_secret')
    binancekeydic={    
        "binance_api_key":binance_api_key,
        "binance_api_secret":binance_api_secret   
        }
  
    myaccountconfig={"dex":dexname,
                      "keys":binancekeydic,
                      }        
        
        
        
        
        

if __name__ == '__main__':    
    

  
      tradeClient=TradeClient(myaccountconfig)
      tradeClient.check_balance()
       #treadClient.order_open(code='ETHUSDT',oside="LONG",otype='MARKET',osize="0.01",oaction="OPEN")
      print(tradeClient.order_get_by_symbol(symbol='ETHUSDT'))
    
    
    
    
    