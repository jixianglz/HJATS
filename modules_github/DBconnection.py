# -*- coding: utf-8 -*-
"""
Created on Sun Apr 10 12:00:37 2022

@author: Administrator
"""
from pymongo import MongoClient
import pandas as pd
import json
import logging

# =============================================================================
# # 连接数据库
# dbclient = MongoClient(host='localhost', port=27017)
# print(dbclient)
# 
# #查看已有数据库    
# dblist = dbclient.list_database_names()
# print(dblist)
# 
# 
# #创建一个数据库
# mydb = dbclient["mydatabase"]
# print(mydb)
# 
# dblist = dbclient.list_database_names()
# if "mydatabase" in dblist:
#   print("The database exists.") 
#   
# #创建一个集合
# 
# mycol = mydb["customers"]
#   
# collist = mydb.list_collection_names()
# if "customers" in collist:
#   print("The collection exists.") 
# =============================================================================


class ATSDB_Client():
    def __init__(self,dbconfig=None):
        self.dbclient=None
        self.database=None
        
        self.databasename='HJATS'
        self.OpenDB(dbconfig)
        self.namelist_of_collections=None     # need confige
        self.collection_data=None
        self.collection_trade=None
        self.collection_profit=None
        
        
        # DB: HJATS
        #      ----Cllecton->策略名+时间+数据
        #      ----Cllecton->策略名+时间+交易记录
        #      ----Cllecton->策略名+时间+资产记录
    
        
    def OpenDB(self,dbconfig=None):
        if(dbconfig==None):
            uri='mongodb://localhost:27017/'
        else:
            print('remote init db')
            user=dbconfig['user']
            passwd=dbconfig['passwd']
            host=dbconfig['host']
            port=dbconfig['port']
            authSource=dbconfig['authSource']
            uri='mongodb://'+user+":"+passwd+"@"+host+":"+port+"/"+'?authSource='+authSource
            
        self.dbclient = MongoClient(uri) #
        self.database=self.dbclient[self.databasename] # 指定数据库
        
        #print(self.dbclient.list_database_names())
        #print(self.database)
        logging.info('[DB]:'+self.databasename+" Connected!")
    
    def CreateRecordcollections(self,basename):
        self.namelist_of_collections=basename,basename+"_data",basename+"_trade",basename+"_profit"
        self.collection_data = self.database[basename+"_data"]
        self.collection_trade = self.database[basename+"_trade"]
        self.collection_profit = self.database[basename+"_profit"]
        
        #collist = self.database.list_collection_names()
        
        #print(self.collection_data)
        #print(self.collection_trade)
        #print(self.collection_profit)
        
    def closeDB(self):
        self.con.close
    
    def df2collection(self,df_data,collection_name,db_name=None):

        """DataFrame数据写入mongodb"""

        def df2bson(df):

            """DataFrame类型转化为Bson类型"""
            dftemp=df.reset_index()
            data = json.loads(dftemp.T.to_json(date_unit = 'ns')).values()
            return data
        
        if db_name==None:  db_name=self.databasename
        my_db = self.dbclient[db_name]
        bson_data = df2bson(df_data)
        my_posts = my_db[collection_name]
        result = my_posts.insert_many(bson_data)
        return result
    
    def collection2df(self,collection_name, query={}, db_name=None,no_id=True):

        
        """查询数据库，导出DataFrame类型数据
        （db_name：数据库名 collection_name：集合名 
         query：查询条件式 no_id：不显示ID,默认为不显示ID）"""
         
        #db = self.my_mongo_client[db_name]
        if db_name==None:  db_name=self.databasename
        collection = self.dbclient[db_name][collection_name]
        cursor = collection.find(query)
        df = pd.DataFrame(list(cursor))
        if no_id:
            del df['_id']
        return df
    
    def list_all_collections(self):
        db=self.dbclient[self.databasename]
        print(db.list_collection_names())
    
    def drop_collection(self,cname):
        db=self.dbclient[self.databasename]
        colleciont=db[cname]
        colleciont.drop()
        print("delete suceefully")
  
        
if __name__ == '__main__':  

    ifremote=0

    if(ifremote==0):    

        dbATS= ATSDB_Client() 
        dbATS.CreateRecordcollections('a_20220914')
        #dbATS.dbclient.list_database_names()
        dicts={'one':[1,2,3],'two':[2,3,4],'tree':[1,3,4]}
        dicts={'one':[1]}
        
        df=pd.DataFrame(dicts)
        #dbATS.collection.insert_one(json.loads(df.T.to_json()).values())
        #dbATS.closeDB()
        #print(json.loads(df.T.to_json).values())
        dbATS.collection2df('HJATS','a_20220914_data',{}) 
        #dbATS.collection_data.drop()
    
    if(ifremote==1):
        dbconfig={"user":"admin",
                  "passwd":"123456",
                  "host":"111.229.229.135",
                  "port":'27017',
                  "authSource":"admin"}
    
        dbATS= ATSDB_Client(dbconfig=dbconfig) 
        
        dicts={'one':[1,2,3],'two':[2,3,4],'tree':[1,3,4]}
        
        df=pd.DataFrame(dicts)
        
        
        dbATS.df2collection(df,'a_20220914_data')
        print(dbATS.collection2df('a_20220914_data'))
    