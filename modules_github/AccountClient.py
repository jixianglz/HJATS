# -*- coding: utf-8 -*-
"""
Created on Mon Nov  1 22:07:12 2021

@author: Administrator
"""
from web3 import Web3
import logging
import Constants
import platform
from binance.um_futures import UMFutures
import os
import configparser



#### Sugget to fetch from database

## binance keys

binancekeydic={    
    "binance_api_key":'gV197J8sk98FJPIg9GPeJ8ioaOwD776YMD52CaLKYPOVE1FiPt0lXA1MrD1RGz83',
    "binance_api_secret":'boWu8BthROkTQq9Ul9eGUevehmRlX9U0UIJx45xdFK9ePB044hY6kztVnsXLwSo6'    
    }
     
myaccountconfig={"dex":"dydx",
                 "keys":dydxkeydic_main,
                 }
myaccountconfig2={"dex":"dydx",
                 "keys":dydxkeydic_main_2,
                 }


configPath=os.getcwd() + r"/UserCase/"+'config.ini'
conf=configparser.ConfigParser()
conf.read(configPath)
dexname=conf.get('Dexinfo','dexname')

binance_api_key=conf.get('Dexinfo','binance_api_key')
binance_api_secret=conf.get('Dexinfo','binance_api_secret')
binancekeydic={    
    "binance_api_key":binance_api_key,
    "binance_api_secret":binance_api_secret   
    }

myaccountconfig={"dex":dexname,
                  "keys":binancekeydic,
                  }




class AccountClient(object):
    
    def __init__(self,
                 accountdic=None
                 ):
        self.dexname=accountdic['dex']

        
        
        
        if(accountdic==None): logging.error("None Account infomation imported.")
        
        if(self.dexname=='dydx'):
            from dydx3 import Client
            self.__dydx_stark_private_key=accountdic['keys']['stark_private_key']
            self.__dydx_stark_public_key=accountdic['keys']['stark_public_key']
            self.__dydx_stark_public_key_y_coordinate=accountdic['keys']['stark_public_key_y_coordinate']
            self.__dydx_api_key_credentials=accountdic['keys']['api_key_credentials']
            self.dydx_default_ethereum_address=accountdic['keys']['default_ethereum_address']
            #connect to dex
            self.dex_client = Client(
                
            network_id=Constants.NETWORK_ID_MAINNET, #Net work select 
            host=Constants.DYDX_API_HOST_MAINNET,
            web3=Web3(Web3.HTTPProvider(Constants.RPC_ETH_PROVIDER_URL)),
            default_ethereum_address=self.dydx_default_ethereum_address,

            stark_private_key=self.__dydx_stark_private_key,
            stark_public_key=self.__dydx_stark_public_key,
            stark_public_key_y_coordinate=self.__dydx_stark_public_key_y_coordinate,
            api_key_credentials=self.__dydx_api_key_credentials
            )
            
            #export ID
            ret = self.dex_client.private.get_account(self.dydx_default_ethereum_address) 
            if(platform.system()=='Linux'):
                ret=ret.data
            
            self.dydx_position_id = ret['account']['positionId']
            
            logging.info("[Acccount] Dex-Dydx Login sucessful,ID:"+str(self.dydx_position_id))
            return
           
        if(self.dexname=='binance'):
            from binance.um_futures import UMFutures
            binance_api_key=accountdic['keys']['binance_api_key']
            binance_api_secret=accountdic['keys']['binance_api_secret']           
            self.dex_client = UMFutures(key=binance_api_key, secret=binance_api_secret)
      

            
    
if __name__ == '__main__':    
    
  
    myaccount=AccountClient(myaccountconfig)

