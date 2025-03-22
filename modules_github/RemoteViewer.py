# -*- coding: utf-8 -*-
"""
Created on Sun Oct 30 20:42:55 2022

@author: Administrator
"""

# -*- coding: utf-8 -*-
"""
Created on Sun Apr 10 12:00:37 2022

@author: Administrator
"""
from pymongo import MongoClient
import pandas as pd
import json
import logging
from DBconnection import ATSDB_Client
import matplotlib

        
if __name__ == '__main__':  


    dbconfig={"user":"admin",
              "passwd":"123456",
              "host":"111.229.229.135",
              "port":'27017',
              "authSource":"admin"}

    dbATS= ATSDB_Client(dbconfig=dbconfig) 
    
   
    
    
    a=dbATS.collection2df('HJATS_1 2022-11-05 01:39:13.704741_profit')
    
    b=dbATS.collection2df('HJATS_1 2022-11-05 01:39:13.704741_trade')
    
    print(b)
    print(a)
    a.plot('index','FloatingAsset')
    a.plot('index','Asset')
    a.plot('index','FloatingPL')