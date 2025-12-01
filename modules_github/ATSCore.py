# -*- coding: utf-8 -*-
"""
Created on Thu Jan 20 07:27:29 2022
20230126:OrderMangeer: 更新订单统计
@author: Administrator
"""

import threading
import queue
import time
import random
from Atsfunc import transFrq2Sec
import ATSlog
import numpy as np
import pandas as pd
from TradeClient import TradeClient
#from AccountClient import myaccountconfig,myaccountconfig2
#from AccountClient import AccountClient
from MarketClient import MarketClient 
from FrontEnd import VisualClient as GUI
import DBconnection as db
import logging
import os
import configparser
import pytz




class ATSServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.msg_queue=queue.Queue(1)
        self.daemon=True
        self.derectlyRun=True
        self.derectlyRunCount=1
    def run(self):
        while True:
            if(self.derectlyRun):
                if(self.derectlyRunCount==1):
                    msg='start'
                    self.msg_queue.put(msg,block=False)
                    self.derectlyRunCount=0
                continue
                             
            msg=input("wait command\n")

            try:
                self.msg_queue.put(msg,block=False)
                print("success send message -->",msg)
            except queue.Full as e:
                print("msg queue is full, clear the queue")
                self.msg_queue.queue.clear()
            if msg=="break":
                break
            

        
class DriverProcessor(threading.Thread):
    def __init__(self, threadID, name, qID,qname,DPtype,DataManager,msg_queue,speed=None,qlength=None,visualization=True):
        threading.Thread.__init__(self)
        #self.start()  # 因为作为一个工具，线程必须永远“在线”，所以不如让它在创建完成后直接运行，省得我们手动再去start它
        self.threadID = threadID
        self.daemon=True
        self.name = name
        self.qID = qID
        self.qName = qname
        self.qlength = qlength
        self.queue = queue.Queue(1)
        self.thread_stop=False 
        self.DPtype=DPtype
        self.dataset=DataManager.rawdata
        self.speed=speed
        self.dataM=DataManager
        self.visualization=visualization       
        if(self.visualization==True):
            self.GUI=GUI()
        self._running=True
        self.msg_queue=msg_queue
        self.msg_hold=None
        self.timer=None
        self.initflag=True
        self.configPath=os.getcwd() + r"/UserCase/"+'config.ini'
        self.conf=configparser.ConfigParser()
        self.conf.read(self.configPath)
        self.marketclient=None
        self.treadclient=None
        self.realtime_run_mode='FreqMode' #'TickMode' or 'FreqMode'
        

        
    def run32_abort(self,name):
    
        print(name,"is running ...")
        
        while self._running:
            try:
                print("wait recieve msg")
                msg= self.msg_queue.get()
                print("success receive mseeage ->",msg)
                
                self.timer.cancel()
                self.timer=threading.Timer(10,self.stop_server,('NONE',))
                self.timer.start()
                print("Timer reseted\n")
            
            except queue.Empty as e:
                print("Queue get time out , type break to exit.")
        
        
    def realtime_init(self): 
        # 获取默认配置文件数据
        self.conf.read(self.configPath)
        initpara={"TimeStop":"Now",
                  "Frequency":self.conf.get('AlgPara','Frequency'),
                  "Code":self.conf.get('AlgPara','Code'),
                  "nHistoryCounts":int(self.conf.get('AlgPara','nHistoryCounts'))           
            }
        if(self.conf.get('DataBase','remote')=='false'):
            dbconfig=None
            logging.info('[DB]mongodb_init_config:Local')
            
        if(self.conf.get('DataBase','remote')=='true'):

            dbconfig={'user':self.conf.get('DataBase','user'),
                      'passwd':self.conf.get('DataBase','passwd'),
                      'host':self.conf.get('DataBase','host'),
                      'port':self.conf.get('DataBase','port'),
                      'authSource':self.conf.get('DataBase','authSource')            
                    }
            logging.info('[DB]mongodb_init_config'+dbconfig['user'])
        try:
            #1 连接市场API 和账号
            
            #多账户例子
            #if(myaccountconfig['dex']=='dydx'):
            #    self.marketclient=MarketClient(dex_name=myaccountconfig['dex']) 
            #    self.treadclientlong=TradeClient(myaccountconfig)
            #    self.treadclientshort=TradeClient(myaccountconfig2)
            #    self.treadclient=self.treadclientlong
            #    initbalace=float(self.treadclientlong.check_balance())+float(self.treadclientshort.check_balance())
            
            # 默认从配置文件初始化账户
            self.treadclient=TradeClient()
            self.dexinfo = self.tradeClient.accountinfo['dex']
            self.marketclient=MarketClient(dex_name=self.dexinfo) 
            self.treadclient=TradeClient()
            initbalace=float(self.treadclient.check_balance())
                
            
            self.dataM.account['asset']=initbalace
            self.dataM.account['assetinit']=initbalace
            print("The init dex balance is \033[0;35m%f\033[0m"%(initbalace))
            logging.info("[INIT]The init dex balance is %f"%(initbalace))
            #2 初始化远程数据组
            self.dataM.RemoteInit(initpara)           
            #3 连接数据库
            self.dataM.ConnectDB(dbconfig)   
            #4 初始数据存储            
            self.dataM.database.df2collection(self.dataM.rawdata, self.dataM.database.namelist_of_collections[1])
            #5 赋值到alg 使用的 storj 数据, head 为最新数据
            self.dataM.storj=self.dataM.rawdata.sort_index(ascending=False)
            
            
            print("Realtime_Init_sucess\n")
            logging.info('[INIT]Realtime_Init_sucess')
        except Exception as e:
            print("Error in init_realTime:")
            print(e) 
            logging.ERROR               
        return
        
    def NewTimer(self,timerpara=None):
        self.timer=threading.Timer(10,self.TimeEngine,(timerpara,))
        self.timer.daemon=True
        self.timer.start()      

    def TimeEngine(self,para=None):
        self.conf.read(self.configPath)
        if self.msg_hold=="start":
            if self.timer.is_alive()==False: 
                print("TimerEngine-->Started")  
        if self.msg_hold=="pause":
            if self.timer.is_alive():          
                self.timer.cancel()
                print("Timer-->pause")
            return
        
        #1. realtime init
        #获取config.ini 初始参数, 连接数据库
        if self.initflag:
            self.realtime_init()           
            self.initflag=False
        
        try:
        #2. 获取最新报价
            self.dataM.storj_NewCandle=self.marketclient.get_price_v1(code=self.conf.get('AlgPara','Code'),count=2,frequency=self.conf.get('AlgPara','Frequency'))
            #print(self.dataM.storj_NewCandle)
        except Exception as e:
            print("Failed Get New Candle")
            print(e)
            
        #3  数据更新模式选择 选择storj 给queue  
        #   TickMode: 按Timer使用最新数据, TickMode 
        #   FreqMode: 按照candle时间戳更新后前一个周期的clsoe价格
        
        if(self.realtime_run_mode=='TickMode'):
            pass
        if(self.realtime_run_mode=='FreqMode'):
            
            #check time stamp
            timestampnow=self.dataM.storj_NewCandle.index[1].value
            timestamplast=self.dataM.storj.index[0].value
            timedif=int((timestampnow-timestamplast)/1e9)
            
            if(timedif==0):
                #print("no tick update")
                pass
            if(timedif==transFrq2Sec(self.conf.get('AlgPara','Frequency'))):
                # 保证每次计算最大长度, 丢弃尾部历史数据
                if(len(self.dataM.storj)>=self.dataM.storj_maxlen):
                    self.dataM.storj=self.dataM.storj.drop(self.dataM.storj.tail(1).index)
                # 新数据放在df头部，新数据为candle更新后前一组数据
                indextemp=str(self.dataM.storj_NewCandle.index[1])
                self.dataM.storj=pd.concat([self.dataM.storj_NewCandle.loc[[indextemp]],self.dataM.storj]) 
                self.dataM.storj=self.dataM.storj.astype(float)
                # 更新 collecion_data 数据库
                self.dataM.database.df2collection(self.dataM.storj_NewCandle.iloc[[1]].astype(float), self.dataM.database.namelist_of_collections[1])
                
                #print("\033[0;32mtick updated\033[0m")
                try:
                    self.queue.put(self.dataM.storj)
                except queue.Full as e:
                    print("DP Queue is full")
                    logging.error("DP Queue is full")
                    #self.msg_queue.queue.clear()
                    print(e)
                    
                    
            #print("FreqMode_mark_done")  
        
        #4  开始下一次timer
        self.NewTimer(timerpara=para)
        #print('Timer Reseted\n')
        
    def stop(self):
        self.thread_stop=True
        print("DP Stoped")
        if self.timer!=None:
            if self.timer.is_alive():          
                self.timer.cancel()
                print("TimeEngine Stoped")        
                
    
    def run(self):
        print('DP INIT')
        
        if(self.DPtype=="realtime"):
            while not self.thread_stop:
                #print("real_thread_re-start")
                try:               
                    self.msg_hold= self.msg_queue.get(block=True)
                    time.sleep(0.05)
                    print("success receive mseeage ->",self.msg_hold)
                    if self.msg_hold=='start':
                        self.NewTimer(timerpara=self.msg_hold)
                    if self.msg_hold=='stop' or self.msg_hold=='break' :
                        self.stop()    
                            
                    self.msg_hold=''
                    
                except queue.Empty as e:
                    pass
                               
                #time.sleep(2) 
                           
        if(self.DPtype=="backtest"):     
             
            while not self.thread_stop:  
                print("thread%d %s: waiting for tast" %(self.ident,self.name))  
                try:
                    for index,row in self.dataset.iterrows():
                        try:             
                            time.sleep(self.speed)
                            
                            #限定数据长度
                            if(len(self.dataM.storj)>=self.dataM.storj_maxlen):
                                self.dataM.storj=self.dataM.storj.drop(str(self.dataM.storj.iloc[-1].name))
                                
                            # 新数据在 Head
                            self.dataM.storj=pd.concat([self.dataset.loc[[str(index)]],self.dataM.storj]) 
                               
                           
                            #注意show的时候已经是当前数据，算法还没处理，上一次结果需要取 -2
                           
                            # Show的新数据在 Tail                                         
                            self.dataM.rawdata_show=pd.concat([self.dataM.rawdata_show,self.dataset.loc[[str(index)]]]) 
                            
                            # front endupdate
                            if(self.visualization==True):
                                #self.GUI.update(self.dataM.rawdata_show,self.dataM.indicator_1)
                                self.GUI.update(self.dataM.rawdata_show,
                                                self.dataM.signal,
                                                self.dataM.indicators,
                                                self.dataM.indicators_w2,
                                                self.dataM.floatingassetline,
                                                self.dataM.assetline,
                                                instantDraw=False
                                                )
                                
                            
                                                          
                            
                            print('\n-----------------------------------\n')
                            #回测速度调节
                            
                            self.queue.put(self.dataM.storj) 

                            
                           
                            
                        except Exception as e:
                            logging.exception(e)
                            print(e)
                            break                             
                    #task = self.queue.get(block=False)    # 如果队列空了，直接结束线程。根据具体场景不同可能不合理，可以修改
                    #time.sleep(random.random())  # 假设处理了一段时间
                    #print('Task %s Done' % task)  # 提示信息而已
                    #self.queue.task_done() #get 后使用的 恢复 Join 阻塞
                    
                    self.thread_stop=True
                    if(self.thread_stop):
                        self.GUI.drawrestuls()
                    print("BackTest engine finished.")
                                        
                except Exception as e:
                    print(e)
                    logging.exception(e)
                    break        
                
class StrategyManager(threading.Thread):
    
    def __init__(self, strategyID, strategyName,dpCore):
        
        threading.Thread.__init__(self)
        #self.start()  # 因为作为一个工具，线程必须永远“在线”，所以不如让它在创建完成后直接运行，省得我们手动再去start它
        self.threadID = strategyID
        self.daemon=True
        self.name = strategyName
        self.queue = dpCore.queue
        self.oderqueue = queue.Queue(1)
        
        self.thread_stop=False     
        self.core=dpCore
        self.DPtype=self.core.DPtype
        self.eventdata=None
        self.count=1

    def run(self):
        print('ST INIT')
        
        if(self.core.DPtype=="realtime"):
            while not self.thread_stop:  
                print("[Strategy] - thread%d %s: waiting for data trg." %(self.ident,self.name))         
                try:
                    
                    # 获得计算数据更新
                    self.task = self.queue.get()
                    print('[Strategy] ----------Alg Task Come------------\n')  
                    
                    #Profit Asset 
                    self.ProfitCal()
                    
                    signal,indicators,indicators_w2=self.func(
                                                       interCount=self.count,
                                                       storj=self.task,
                                                       indicators=self.core.dataM.indicators,
                                                       indicators_w2=self.core.dataM.indicators_w2,
                                                       orderqueue=self.oderqueue,
                                                       orderpool=self.core.dataM.orderpool,
                                                       orderaccount=self.core.dataM.account,
                                                       order_statistic=self.core.dataM.order_statistic)
                    
                    if(len(self.core.dataM.signal)>=self.core.dataM.max_signal_ind_lenth):
                        del(self.core.dataM.signal[0])      
                    self.core.dataM.signal.append(signal)
                    
                    for ind_index in indicators:
                        # 算法计算结果插入到Data管理器中 主窗口 需要 ind_index 内部dict Key与外部Key一致
                        if(len(self.core.dataM.indicators[ind_index])>=self.core.dataM.max_signal_ind_lenth):
                            del(self.core.dataM.indicators[ind_index][0])
                        self.core.dataM.indicators[ind_index].append(indicators[ind_index])
                    for ind_index in indicators_w2:
                        # 算法计算结果插入到Data管理器中 次窗口 ind_index 内部dict Key与外部Key一致
                        if(len(self.core.dataM.indicators_w2[ind_index])>=self.core.dataM.max_signal_ind_lenth):
                            del(self.core.dataM.indicators_w2[ind_index][0])
                        self.core.dataM.indicators_w2[ind_index].append(indicators_w2[ind_index])
                              
                    
                    #Profit_into_database
                    dbcollectionlist=[self.core.dataM.account['asset'],
                                      self.core.dataM.account['h_profit'],
                                      self.core.dataM.account['h_profit']+self.core.dataM.account['asset']]
                    #timeindex=self.core.dataM.storj.index[0]
                    timeindex=self.task.index[0]
                    dbcollectionSer=pd.Series(index=self.core.dataM.df_profit_dbcollections.columns,
                                              data=dbcollectionlist,
                                              name=timeindex)
                    
                    #self.core.dataM.df_profit_dbcollections=self.core.dataM.df_profit_dbcollections.concat(dbcollectionSer)
                    self.core.dataM.df_profit_dbcollections=self.core.dataM.df_profit_dbcollections.append(dbcollectionSer)
                    self.core.dataM.database.df2collection(self.core.dataM.df_profit_dbcollections, self.core.dataM.database.namelist_of_collections[3])
                
                    self.core.dataM.df_profit_dbcollections=self.core.dataM.df_profit_dbcollections.drop(self.core.dataM.df_profit_dbcollections.head(1).index)
                    
                    
                    
                    print('Task %s Done at Count: %s' %(self.name,str(self.count)))  # 提示信息而已
                    self.count+=1
                    
                    print('[Strategy] ----------Alg Task Done------------\n') 
                except Exception as e:
                    print(e)
                    logging.exception(e)
                    break 
        
        if(self.core.DPtype=="backtest"):     
            
            while not self.thread_stop:  
                print("Strategy - thread%d %s: waiting for data trg." %(self.ident,self.name))  
                try:
    
                  
                    #event got            
                    self.task = self.queue.get()    # 如果队列空了，直接结束线程。根据具体场景不同可能不合理，可以修改
                    
                    #Profit Asset 
                    self.ProfitCal()
                  
                    #signal cal run
                  
                    signal,indicators,indicators_w2=self.func(
                                                       interCount=self.count,
                                                       storj=self.task,
                                                       indicators=self.core.dataM.indicators,
                                                       indicators_w2=self.core.dataM.indicators_w2,
                                                       orderqueue=self.oderqueue,
                                                       orderpool=self.core.dataM.orderpool,
                                                       orderaccount=self.core.dataM.account,
                                                       order_statistic=self.core.dataM.order_statistic)
                     
                    if(len(self.core.dataM.signal)>=self.core.dataM.max_signal_ind_lenth):
                        del(self.core.dataM.signal[0])                    
                    self.core.dataM.signal.append(signal)
                    
                    for ind_index in indicators:
                        # 算法计算结果插入到Data管理器中 主窗口 需要 ind_index 内部dict Key与外部Key一致
                        if(len(self.core.dataM.indicators[ind_index])>=self.core.dataM.max_signal_ind_lenth):
                            del(self.core.dataM.indicators[ind_index][0])
                        self.core.dataM.indicators[ind_index].append(indicators[ind_index])
                    for ind_index in indicators_w2:
                        # 算法计算结果插入到Data管理器中 次窗口 ind_index 内部dict Key与外部Key一致
                        if(len(self.core.dataM.indicators_w2[ind_index])>=self.core.dataM.max_signal_ind_lenth):
                            del(self.core.dataM.indicators_w2[ind_index][0])
                        self.core.dataM.indicators_w2[ind_index].append(indicators_w2[ind_index])
                    
                    
                    #asset cal run
                    
                    
                    print('Task %s Done at Count: %s' %(self.name,str(self.count)))  # 提示信息而已
                    self.count+=1

                    if(self.core.thread_stop==True):
                        self.thread_stop=True
                        self.oderqueue.put("stop")   # 主进程结束，給Order get 抛出结束，结束阻塞
                        print("StrateThreading Stoped")
                        
                except Exception as e:
                    print(e)
                    logging.exception(e)
                    break     
                
    def func(*args,**kwargs):

        #print(args)
        #print(kwargs)
        from UserCase import signalAlg
        from UserCase import orderAlg
        if 'storj' in kwargs: 
            print('[sAlg] SignalAlg got the task')      
            interCount=kwargs['interCount']
            dataset=kwargs['storj']
            orderqueue=kwargs['orderqueue']
            orderpool=kwargs['orderpool']
            orderaccount=kwargs['orderaccount']
            indicatorsdic=kwargs['indicators']
            indicatorsdic_w2=kwargs['indicators_w2']
            order_statistic=kwargs['order_statistic']
            
            #set for signal
            parapoll={}
            parapoll['dataset']=dataset
            parapoll['indicatorsdic']=indicatorsdic
            parapoll['indicatorsdic_w2']=indicatorsdic_w2            
            signal,cur_ind_dic,w2_ind_dic=signalAlg.run(parapoll)
            
            print('[oAlg] OrderAlg got the task')  
            #set for order
            parapoll['c_signal']=signal 
            parapoll['orderpool']=orderpool
            parapoll['orderaccount']=orderaccount
            parapoll['order_statistic']=order_statistic
            
            orderlist=orderAlg.run(parapoll)
            
            if(len(orderlist)!=0):
                orderqueue.put(orderlist)
                print('Get The order in count:%d'%interCount)
                print('Order List:'+str(orderlist))
            return signal,cur_ind_dic,w2_ind_dic
    
    def ProfitCal(self):
        #1. got the latest price , as close
        latest_price=self.task['close'].values[0]
        balance=self.core.dataM.account['asset']
        AllFloatingPL_long=0
        AllFloatingPL_long_size=0
        AllFloatingPL_long_cost=0
        AllFloatingPL_short=0
        AllFloatingPL_short_size=0
        AllFloatingPL_short_cost=0
        AllFloatingPL=0
        
        #2. got the holding orders
        holding=self.core.dataM.orderpool
              
        #3. Cal the profit   同一code 下 所有订单遍历， 还未支持多品种
        if(len(holding)!=0):
            for orderuid in holding:
                
                if(holding[orderuid].side=='LONG' and holding[orderuid].size>0 ):
                    AllFloatingPL_long_size=AllFloatingPL_long_size+holding[orderuid].size
                    AllFloatingPL_long_cost=AllFloatingPL_long_cost+holding[orderuid].size*float(holding[orderuid].aveprice)            
                    holding[orderuid].floatingPL=(latest_price-holding[orderuid].aveprice)*holding[orderuid].size
                    
                    
                if(holding[orderuid].side=='SHORT' and holding[orderuid].size>0):
                    AllFloatingPL_short_size=AllFloatingPL_short_size+holding[orderuid].size
                    AllFloatingPL_short_cost=AllFloatingPL_short_cost+holding[orderuid].size*float(holding[orderuid].aveprice)            
                    holding[orderuid].floatingPL=(holding[orderuid].aveprice-latest_price)*holding[orderuid].size
           
            AllFloatingPL_long=AllFloatingPL_long_size*latest_price-AllFloatingPL_long_cost
            AllFloatingPL_short=AllFloatingPL_short_cost-AllFloatingPL_short_size*latest_price
            


            AllFloatingPL=AllFloatingPL_long+AllFloatingPL_short
            #logging.debug('%s'%AllFloatingPL_short)
        
        
        #4. Updte profit and asset and profitlin in DB.
        
        if(len(self.core.dataM.assetline)>self.core.dataM.max_aplen):
            del(self.core.dataM.assetline[0])
        if(len(self.core.dataM.floatingPLline)>self.core.dataM.max_aplen):
            del(self.core.dataM.floatingPLline[0])
        if(len(self.core.dataM.floatingassetline)>self.core.dataM.max_aplen):
            del(self.core.dataM.floatingassetline[0])
        
        self.core.dataM.assetline.append(balance)
        self.core.dataM.floatingassetline.append(AllFloatingPL+balance)
        self.core.dataM.floatingPLline.append(AllFloatingPL)
        self.core.dataM.account['h_profit']=AllFloatingPL
        self.core.dataM.account['h_profit_long']=AllFloatingPL_long
        self.core.dataM.account['h_profit_short']=AllFloatingPL_short

        
        return 
    
    


class OrderManager(threading.Thread):
    
    def __init__(self, OrderManagerID, OrderManagerName,StManager,dpCore,func=None):
        
        threading.Thread.__init__(self)
        #self.start()  # 因为作为一个工具，线程必须永远“在线”，所以不如让它在创建完成后直接运行，省得我们手动再去start它
        self.threadID = OrderManagerID
        self.daemon=True
        self.name = OrderManagerName
        self.oderqueue = StManager.oderqueue
        self.thread_stop=False 
        self.core=StManager        
        self.func=func
        self.DPtype=StManager.DPtype
        self.orderID_inter=0
        
        # ！！！order frame 长度溢出注意
        self.orderframe=pd.DataFrame([],columns=['STname',
                                                 'ID_inter',
                                                 'UID',
                                                 'OrderAction', #Open or Close
                                                 'OrderType', #Market or Limit  #MarketOnly
                                                 'Status',  #Pending,sucess or fail
                                                 'CreatedTime',
                                                 'Market',
                                                 'Side',  
                                                 'Size',
                                                 'ExpetedPrice',
                                                 'DealPrice',
                                                 'TickPrice'])
        self.orderpool={}  
        self.debugorder=None
        
        ##2023.01.26 update the 胜率统计
        self.order_statistic={"totalnumber":0,
                              "win_num":0,
                              "win_win_count":0,
                              "loss_num":0,
                              "loss_loss_count":0,
                              "finish_num":0,
                              "holding_num":0,}
                                             

    def run(self):
        print('OderM INIT')
        
        if(self.DPtype=="realtime"):   # 应该和backtest 一样
            count = 1
            while not self.thread_stop: 
                print("[OrderManage] - thread%d %s: waiting for order trg." %(self.ident,self.name))  
                try:
                    ordertask_list = self.oderqueue.get()    # 如果队列空了，直接结束线程。根据具体场景不同可能不合理，可以修改
                    print('[OrderManage]---------Order Task Come------------\n')  
                    if(ordertask_list=="stop"): #先检验st发出的推出阻塞指令
                        self.thread_stop=True
                        print("order get block stop, OrderThreading exit")
                        continue
                    if(type(ordertask_list)!=list):
                        print('error order type')                        
                    if(len(ordertask_list)==0):
                        print('no new order')
                    if(len(ordertask_list)!=0):
                        print('order handled')
                        logging.debug(ordertask_list)
                        for i in range(0,len(ordertask_list)):
                    
                            ordertask=ordertask_list[i]
                            logging.info('[OrderManager]:ordertask:'+str(ordertask))
                            # format the order from the alg
                            forder=self.formatOrder(ordertask)
                            self.debugorder=forder                                                                  
                            #prcess the order 
                            dexname=self.core.core.treadclient.dexname
                            ret=self.processOrder(forder,dexname=dexname)
                            if(ret==0): #无异常
                                forder[5]=self.orderpool[forder[2]].status
                                forder[11]=self.orderpool[forder[2]].dealprice
                            logging.info('[OrderManager]:results:'+str(ret)+"_details:"+str(forder))
                            
                            #record the order frame
                            #timeindex=self.core.core.dataM.storj.index[0]
                            timeindex=self.core.task.index[0]
                            orderSer=pd.Series(index=self.orderframe.columns,data=forder,name=timeindex)
                            
                            if(len(self.orderframe)>=self.core.core.dataM.max_orderframe_len):
                                self.orderframe=self.orderframe.drop(self.orderframe.head(1).index) 
                            self.orderframe=self.orderframe.append(orderSer)
                            
  
                            
                            # Make the copy to the datamanager
                            self.core.core.dataM.orderframe=self.orderframe
                            self.core.core.dataM.orderpool=self.orderpool
                            
                            self.core.core.dataM.database.df2collection(self.orderframe.tail(1), self.core.core.dataM.database.namelist_of_collections[2])
                            #if(ret==0):
                            #insert rawdata_show_ mark, 多订单显示覆盖最后一单
                            #    self.core.core.dataM.rawdata_show.loc[timeindex,'Signal']=ordertask['oside']                      
                                #logging.info(ordertask['oside']+timeindex)  
                            self.orderID_inter+=1
                    print('\n---------End of Order Task----------\n')  
                    print('Order Task %s Done. Count: %s' %(self.name,str(count)))  # 提示信息而已
                    count+=1        
                                    
                except Exception as e:    
                    print(e)
                    logging.exception(e)
                    break    
        
        if(self.DPtype=="backtest"):     
            count = 1
            while not self.thread_stop:  
                print("[OrderManage] - thread%d %s: waiting for order trg." %(self.ident,self.name))  
                try:
                    print('[OrderManage]---------Order Task Comewarit------------\n') 
                    ordertask_list = self.oderqueue.get()    # 如果队列空了，直接结束线程。根据具体场景不同可能不合理，可以修改
                    print('[OrderManage]---------Order Task Come------------\n')                      
                    #order 合法性 检验
                    
                    if(ordertask_list=="stop"): #先检验st发出的推出阻塞指令
                        self.thread_stop=True
                        print("order get block stop, OrderThreading exit")
                        continue
                        
                    
                    if(type(ordertask_list)!=list):
                        print('error order type')
                        
                    if(len(ordertask_list)==0):
                        print('no new order')

                
                    if(len(ordertask_list)!=0):
                        print('order handled')
                        logging.debug(ordertask_list)
                        for i in range(0,len(ordertask_list)):
                        
                            ordertask=ordertask_list[i]
                            
                            # format the order from the alg
                            forder=self.formatOrder(ordertask)
                            
                            self.debugorder=forder
                            
                            
                            
                            #prcess the orcer 
                            ret=self.processOrder(forder)
                            
                            logging.debug('detail:'+str(ordertask)+"restuls:"+str(ret))
                            
                            #record the order frame
                            #timeindex=self.core.core.dataM.storj.index[1]  #:backtest DP1 put 后马上更新第二次数据,此时已经是二次更新的数据
                            timeindex=self.core.task.index[0]
                            orderSer=pd.Series(index=self.orderframe.columns,data=forder,name=timeindex)
                            self.orderframe=self.orderframe.append(orderSer)
                            
                            # Make the copy to the datamanager
                            self.core.core.dataM.orderframe=self.orderframe
                            self.core.core.dataM.orderpool=self.orderpool
                            self.core.core.dataM.order_statistic=self.order_statistic
                            
                            if(ret==0):
                            #insert rawdata_show_ mark, 多订单显示覆盖最后一单
                                self.core.core.dataM.rawdata_show.loc[timeindex,'Signal']= ordertask['oside']             
                                #logging.info(ordertask['oside']+timeindex)  
                            self.orderID_inter+=1
                                      
                    
                    print('\n---------End of Order Task----------\n')  
                    
                    # 获得ordertask 类型分别处理
                    #time.sleep(random.random())  # 假设处理了一段时间
                    #外部func调用 or 内部func 调用
                    #self.func(storj=ordertask)
                                        
                    print('Order Task %s Done. Count: %s' %(self.name,str(count)))  # 提示信息而已
                    count+=1
                    #self.queue.task_done()  # oder 不需要阻塞， 下单后马上处理队列
   
                                                            
                except Exception as e:    
                    print(e)
                    logging.exception(e)
                    break
                
    def formatOrder(self,order):
        
        orderstatus=''
        createtime=pd.Timestamp.utcnow()
        if(self.DPtype=="backtest"): 
            orderstatus='SUCCESS'
            orderdealprice=order['oprice']
        if(self.DPtype=="realtime"): 
            orderstatus='NA'
            orderdealprice='NA'
        
        raw=[self.core.name,     #0
             self.orderID_inter,  #1
             order['uid'],      #2
             order['oaction'], #3
             order['otype'], #4
             orderstatus, #5
             createtime, #6
             order['code'], #7
             order['oside'], #8
             order['osize'], #9
             order['oprice'], #10
             orderdealprice, #11
             #self.core.core.dataM.storj.head(2).close[1] #12, tickprice only for back test :backtest DP1 put 后马上更新第二次数据,此时已经是二次更新的数据
             self.core.task.head(1).close[0]
             ] 
        return raw
    
    def processOrder(self,forder,dexname=None):
        
        oaction=forder[3]
        ouid=forder[2]
        oside=forder[8]
        
             
        if(self.DPtype=="backtest" or self.DPtype=="realtime" ):
            
            print("Order Processing......")
            

            if(oaction=='OPEN'):
               
                if ouid not in self.orderpool:

                    print('Creating New order:%s' %ouid)
                    logging.info('[Order]NewOrder created: uid:%s' %ouid)                    
                    
                    NewOrder=OrderInstance(forder,dex=dexname,dpCore=self.core.core)
                    self.orderpool[ouid]=NewOrder
                    self.order_statistic['totalnumber']+=1
                    self.order_statistic['holding_num']+=1
                    #return 0
                
                if self.orderpool[ouid].side != oside:
                    print('order side name is not Match!')
                    logging.error('order side name is not Match!')
                    
                    return 0x3  
                
                
                ret=self.orderpool[ouid].incPosition(forder)
                return ret
                
            if(oaction=='CLOSE'):
               
                if ouid not in self.orderpool:

                    print('[Order]The order is not in Pool:%s' %ouid)
                    logging.error('[Order]The order is not in Pool: uid:%s' %ouid)                    
                             
                    return 0x4
                
                if self.orderpool[ouid].side != oside:
                    print('order side name is not Match!')
                    logging.error('order side name is not Match!')
                    return 0x3            
                closeprofit,ret=self.orderpool[ouid].decPosition(forder) 
                self.core.core.dataM.account['asset']=self.core.core.dataM.account['asset']+closeprofit
                self.core.core.dataM.account['profit']=self.core.core.dataM.account['profit']+closeprofit
                
                #update the statics 更新统计信息
                if(self.orderpool[ouid].size==0):
                    self.order_statistic['holding_num']-=1
                    self.order_statistic['finish_num']+=1
                    if(self.orderpool[ouid].closeprofit>=0):
                        self.order_statistic['win_num']+=1
                        self.order_statistic['win_win_count']+=1
                        self.order_statistic['loss_loss_count']=0
                    if(self.orderpool[ouid].closeprofit<0):
                        self.order_statistic['loss_num']+=1
                        self.order_statistic['win_win_count']=0
                        self.order_statistic['loss_loss_count']+=1
                        
                
                
                return ret
            
            logging.error('[OrderInstance]DecreaseOrder Do nothing!') 
            ret=0x1  #0x1  订单 open close 异常: 无处理
            
        return ret
    
    
        

class OrderInstance:
    def __init__(self,forder,dex=None,dpCore=None):
      self.dpCore=dpCore
      self.precision=3
      self.name=forder[0]
      self.idinter=forder[1]
      self.uid=forder[2]
      self.action=forder[3]
      self.otype=forder[4]
      self.status=None  # 需要API 刷新当前订单状状态
      self.market=forder[7]
      self.side=forder[8]   # 方向
      self.osize=round(float(forder[9]),self.precision)  #current order size
      self.size=0 #total size record
      self.dex=dex
      self.createtime=forder[6]
      self.openprice=round(float(forder[10]),6)
      self.dealprice=None
      self.aveprice=0
      self.closeprice=None
      self.closeprofit=0
      self.floatingPL=0     #由stratgy profile cal 刷新
      #self.totalvalue=round(float(forder[10]),6)*self.size
      self.totalvalue=0
      self.createOrder()
      print('New order created --uid:'+str(self.uid))
    
    def __updatebyforder(self,forder):
      self.name=forder[0]
      self.idinter=forder[1]
      self.uid=forder[2]
      self.action=forder[3]
      self.otype=forder[4]
      self.createtime=forder[6]
      self.market=forder[7]
      self.side=forder[8]
      self.osize=round(float(forder[9]),self.precision)
      self.openprice=round(float(forder[10]),6)
      

    def createOrder(self):
        if(self.dex==None):
            self.dex='backtest'
            self.status='processing'           
        return 0   
        
    
    def show(self):
        infos={
            "name":self.name,
            "InternalID":self.idinter,
            "UID":self.uid,
            "LastAction":self.action,
            "Status":self.status,
            "Market":self.market,
            "Side":self.side,
            "Size":self.size,
            "OpenPrice":self.openprice,
            "ClosePrice":self.closeprice,     
            "AveagePrice":self.aveprice,
            "FloatingPL":self.floatingPL,
            }
        print(infos)
        return
    
    def incPosition(self,forder):
      self.__updatebyforder(forder)
      if(self.dex=='backtest' and self.status=='processing'):
        self.size=round(self.size+float(forder[9]),self.precision)
        self.totalvalue=self.totalvalue+round(float(forder[12])*float(forder[9]),6)
        self.aveprice=self.totalvalue/self.size
        self.action='OPEN'
        self.dealprice=forder[12]
        return 0
      
      if(self.dex=="dydx"):
             
        if(self.side=='LONG'):
            
            
            treadclientlong=self.dpCore.treadclientlong
            dexret=treadclientlong.order_open(code=self.market,
                                       oside='BUY',
                                       otype=self.otype,
                                       osize=str(self.osize),
                                       oprice=str(self.openprice))
            
            dexorderID=dexret['order']['id']
            self.status=dexret['order']['status']
            recheckret=treadclientlong.order_get_by_id(dexorderID)
            self.status=recheckret['order']['status']
            dotimes=0
            while(self.status=='PENDING' and dotimes<3):               
                recheckret=treadclientlong.order_get_by_id(dexorderID)
                self.status=recheckret['order']['status']
                dotimes=dotimes+1
                time.sleep(3)
                if(dotimes==3):logging.error('[OrderInst]Pending Order waiting %d times'%dotimes)
            if(self.status=='FILLED'):
                self.size=self.size+self.osize
                fills_ret=treadclientlong.get_fills(dexorderID)
                self.dealprice=fills_ret['fills'][0]['price']
                self.totalvalue=self.totalvalue+float(self.dealprice)*float(self.osize)
                self.aveprice=round(self.totalvalue/self.size,self.precision)
           
            if(self.status=='CANCELED'):
                logging.info('[Order]OrderOpen Failed,Dex Canceled -->Retry')
                dexret=treadclientlong.order_open(code=self.market,
                                       oside='BUY',
                                       otype=self.otype,
                                       osize=str(self.osize),
                                       oprice=str(self.openprice))
            
                dexorderID=dexret['order']['id']
                self.status=dexret['order']['status']
                recheckret=treadclientlong.order_get_by_id(dexorderID)
                self.status=recheckret['order']['status']
                dotimes=0
                while(self.status=='PENDING' and dotimes<3):               
                    recheckret=treadclientlong.order_get_by_id(dexorderID)
                    self.status=recheckret['order']['status']
                    dotimes=dotimes+1
                    time.sleep(3)
                    if(dotimes==3):logging.error('[OrderInst]Pending Order waiting %d times'%dotimes)
                if(self.status=='FILLED'):
                    self.size=self.size+self.osize
                    fills_ret=treadclientlong.get_fills(dexorderID)
                    self.dealprice=fills_ret['fills'][0]['price']
                    self.totalvalue=self.totalvalue+float(self.dealprice)*float(self.osize)
                    self.aveprice=round(self.totalvalue/self.size,self.precision)
                if(self.status=='CANCELED'):   
                    logging.error('[Order]OrderOpen Failed,Dex Canceled twice')
                    return 0x2 #open fail
                
         
            return 0x0
    
        if(self.side=='SHORT'):
            treadclientshort=self.dpCore.treadclientshort
            dexret=treadclientshort.order_open(code=self.market,
                                       oside='SELL',
                                       otype=self.otype,
                                       osize=str(self.osize),
                                       oprice=str(self.openprice))
            dexorderID=dexret['order']['id']
            self.status=dexret['order']['status']
            recheckret=treadclientshort.order_get_by_id(dexorderID)
            self.status=recheckret['order']['status']
            dotimes=0
            while(self.status=='PENDING' and dotimes<3):               
                recheckret=treadclientshort.order_get_by_id(dexorderID)
                self.status=recheckret['order']['status']
                dotimes=dotimes+1
                time.sleep(3)
                if(dotimes==3):logging.error('[OrderInst]Pending Order waiting %d times'%dotimes)
            
            if(self.status=='FILLED'):
                self.size=self.size+self.osize
                fills_ret=treadclientshort.get_fills(dexorderID)
                self.dealprice=fills_ret['fills'][0]['price']
                self.totalvalue=self.totalvalue+float(self.dealprice)*float(self.osize)
                self.aveprice=round(self.totalvalue/self.size,self.precision)
            if(self.status=='CANCELED'):
                logging.info('[Order]OrderOpen Failed,Dex Canceled -->Retry')
                dexret=treadclientlong.order_open(code=self.market,
                                       oside='BUY',
                                       otype=self.otype,
                                       osize=str(self.osize),
                                       oprice=str(self.openprice))
            
                dexorderID=dexret['order']['id']
                self.status=dexret['order']['status']
                recheckret=treadclientlong.order_get_by_id(dexorderID)
                self.status=recheckret['order']['status']
                dotimes=0
                while(self.status=='PENDING' and dotimes<3):               
                    recheckret=treadclientshort.order_get_by_id(dexorderID)
                    self.status=recheckret['order']['status']
                    dotimes=dotimes+1
                    time.sleep(3)
                    if(dotimes==3):logging.error('[OrderInst]Pending Order waiting %d times'%dotimes)
                if(self.status=='FILLED'):
                    self.size=self.size+self.osize
                    fills_ret=treadclientlong.get_fills(dexorderID)
                    self.dealprice=fills_ret['fills'][0]['price']
                    self.totalvalue=self.totalvalue+float(self.dealprice)*float(self.osize)
                    self.aveprice=round(self.totalvalue/self.size,self.precision)
                if(self.status=='CANCELED'):   
                    logging.error('[Order]OrderOpen Failed,Dex Canceled twice')
                    return 0x2 #open fail
            
            return 0x0
                
      return 0x1  # 异常
     
    def decPosition(self,forder):
      self.__updatebyforder(forder)
      
      if(self.dex=='backtest' and self.status=='processing'):
        
          
        if(round(self.size-float(forder[9]),self.precision)!=0):      
            if(self.side=='LONG'):            
                self.closeprofit=(round(float(forder[12]),6)-self.aveprice)*float(forder[9])                       
            if(self.side=='SHORT'):    
                self.closeprofit=-(round(float(forder[12]),6)-self.aveprice)*float(forder[9])
            self.size=round(self.size-float(forder[9]),self.precision)
            self.totalvalue=self.totalvalue-round(float(forder[12])*float(forder[9]),6)
            self.aveprice=self.totalvalue/self.size
            self.action='CLOSE'
            self.dealprice=forder[12]
            return self.closeprofit,0
        
        if(round(self.size-float(forder[9]),self.precision)==0):            
            self.closeprice=round(float(forder[10]),6)
            
            if(self.side=='LONG'):            
                self.closeprofit=(round(float(forder[12]),6)-self.aveprice)*self.size                         
            if(self.side=='SHORT'):    
                self.closeprofit=-(round(float(forder[12]),6)-self.aveprice)*self.size          
            self.status='finished'
            self.action='CLOSE'
            self.size=round(self.size-float(forder[9]),self.precision)
            self.totalvalue=0
            self.dealprice=forder[12]
            return self.closeprofit,0
        
        if(round(self.size-float(forder[9]),self.precision)<0):
            logging.error('[ORDER]Close Size is lager than holding! siez:'+str(self.size)+",req.:"+forder[9])
            print('[ORDER]Close Size is lager than holding!')
            return self.closeprofit,0x6
         
        return self.closeprofit,0x1

      if(self.dex=="dydx"):
          
        if(round(self.size-float(forder[9]),self.precision)<0):
            logging.error('[ORDER]Close Size is lager than holding! siez:'+str(self.size)+",req.:"+forder[9])
            print('[ORDER]Close Size is lager than holding!')
            return self.closeprofit,0x6
             
        if(self.side=='LONG'):
            
            treadclientlong=self.dpCore.treadclientlong
            dexret=treadclientlong.order_open(code=self.market,
                                       oside='SELL',
                                       otype=self.otype,
                                       osize=str(self.osize),
                                       oprice=str(self.openprice))
            
            dexorderID=dexret['order']['id']
            self.status=dexret['order']['status']
            recheckret=treadclientlong.order_get_by_id(dexorderID)
            self.status=recheckret['order']['status']
            if(self.status=='FILLED'):
                self.size=self.size-self.osize
                fills_ret=treadclientlong.get_fills(dexorderID)
                self.dealprice=fills_ret['fills'][0]['price']
                self.closeprofit=self.closeprofit+(float(self.dealprice)-self.aveprice)*float(self.osize)
                self.totalvalue=self.totalvalue-float(self.aveprice)*float(self.osize)
            if(self.status=='CANCELED'):
                logging.info('[Order]OrderClose Failed,Dex Canceled -->Retry')
                dexret=treadclientlong.order_open(code=self.market,
                                       oside='SELL',
                                       otype=self.otype,
                                       osize=str(self.osize),
                                       oprice=str(self.openprice))
            
                dexorderID=dexret['order']['id']
                self.status=dexret['order']['status']
                recheckret=treadclientlong.order_get_by_id(dexorderID)
                self.status=recheckret['order']['status']
                if(self.status=='FILLED'):
                    self.size=self.size-self.osize
                    fills_ret=treadclientlong.get_fills(dexorderID)
                    self.dealprice=fills_ret['fills'][0]['price']
                    self.closeprofit=self.closeprofit+(float(self.dealprice)-self.aveprice)*float(self.osize)
                    self.totalvalue=self.totalvalue-float(self.aveprice)*float(self.osize)
                if(self.status=='CANCELED'):   
                    logging.error('[Order]OrderClose Failed,Dex Canceled twice')
                    
                    return self.closeprofit,0x2 #Closen fail
            
         
            return self.closeprofit,0x0
    
        if(self.side=='SHORT'):           
            treadclientshort=self.dpCore.treadclientshort
            dexret=treadclientshort.order_open(code=self.market,
                                       oside='BUY',
                                       otype=self.otype,
                                       osize=str(self.osize),
                                       oprice=str(self.openprice))           
            dexorderID=dexret['order']['id']
            self.status=dexret['order']['status']
            recheckret=treadclientshort.order_get_by_id(dexorderID)
            self.status=recheckret['order']['status']
            if(self.status=='FILLED'):
                self.size=self.size-self.osize
                fills_ret=treadclientshort.get_fills(dexorderID)
                self.dealprice=fills_ret['fills'][0]['price']               
                self.closeprofit=self.closeprofit+(self.aveprice-float(self.dealprice))*float(self.osize)
                self.totalvalue=self.totalvalue-float(self.aveprice)*float(self.osize)
            if(self.status=='CANCELED'):
                logging.info('[Order]OrderClose Failed,Dex Canceled -->Retry')
                dexret=treadclientlong.order_open(code=self.market,
                                       oside='BUY',
                                       otype=self.otype,
                                       osize=str(self.osize),
                                       oprice=str(self.openprice))
            
                dexorderID=dexret['order']['id']
                self.status=dexret['order']['status']
                recheckret=treadclientlong.order_get_by_id(dexorderID)
                self.status=recheckret['order']['status']
                if(self.status=='FILLED'):
                    self.size=self.size-self.osize
                    fills_ret=treadclientlong.get_fills(dexorderID)
                    self.dealprice=fills_ret['fills'][0]['price']
                    self.closeprofit=self.closeprofit+(self.aveprice-float(self.dealprice))*float(self.osize)
                    self.totalvalue=self.totalvalue-float(self.aveprice)*float(self.osize)
                if(self.status=='CANCELED'):   
                    logging.error('[Order]OrderClose Failed,Dex Canceled twice')
                    return self.closeprofit,0x2 #Closen fail
            return self.closeprofit,0x0
      
      logging.error('[OrderInstance]DecreaseOrder Do nothing!')    
      return self.closeprofit,0x1  # 异常










                
class DataManager:
    
    def __init__(self):
        
      self.initpara=None
      self.rawdata=None
      self.rawdata_show=None
      self.database=None
      self.db_strategyName=None
      self.configPath=os.getcwd() + r"/UserCase/"+'config.ini'
      self.conf=configparser.ConfigParser()

      
      # ！！！ 长度溢出注意， 需要后续修改
      self.max_signal_ind_lenth=100
      self.indicator_1=[]
      self.signal=[]     # 长度保护ok
      self.indicators={   # 长度保护ok
          'ind1':[],
          'ind2':[],
          'ind3':[],
          'ind4':[],
          'ind5':[],
          'ind6':[],
          'ind7':[],
          'ind8':[],
          'ind9':[],      
          'ind10':[],    
          }
      self.indicators_w2={   # 长度保护ok
          'ind1':[],
          'ind2':[],
          'ind3':[],
          'ind4':[],
          'ind5':[],
          'ind6':[],
          'ind7':[],
          'ind8':[],
          'ind9':[],      
          'ind10':[],    
          }      

      
      self.storj=pd.DataFrame()
      self.storj_show=None
      self.storj_maxlen=100
      self.storj_NewCandle=None
      
      self.account={
          'asset':1000,
          'assetinit':1000,
          'profit':0,
          'h_profit':0,
          'h_profit_long':0,
          'h_profit_short':0,        
          }
      self.df_profit_dbcollections=pd.DataFrame([],columns=['Asset',
                                                 'FloatingPL',
                                                 'FloatingAsset',
                                                 ])      
      self.max_orderframe_len=20   # 长度保护ok
      self.orderframe=pd.DataFrame()    #copy OM  长度保护ok
      self.orderpool={}                 #copy OM   需要做一个完成删除
      self.order_statistic={}
      
      self.max_aplen=100
      self.floatingPLline=[]   # 长度保护ok
      self.floatingassetline=[]    # 长度保护ok
      self.assetline=[]   # 长度保护ok
      
    def ConnectDB(self,dbconfig=None):
        self.database=db.ATSDB_Client(dbconfig)
        print('database Connected!')
        logging.info('database Connected!')
        self.conf.read(self.configPath)
        self.db_strategyName=self.conf.get('AlgPara','StrategyName')
        self.db_strategyName=self.db_strategyName+" "+str(pd.Timestamp.now())
        
        self.database.CreateRecordcollections(self.db_strategyName)
        #连接后根据名字生成3张表, 名字是策略名+时间戳

    def LocalInit(self,path,initpara):
        self.initpara=initpara
        self.account['asset']=initpara["Init_Balance"]
        self.account['assetinit']=initpara["Init_Balance"]
        #rawdata=pd.read_csv('D:\Projects\HJATS\HJATS\modules\dataset.csv')
        self.rawdata=pd.read_csv(path)
        self.rawdata.set_index('time',inplace=True)
        
    def RemoteInit(self,initpara=None):
        
        self.initpara=initpara
        para=initpara
        
        if(para==None):
            para={"Init_Balance":1000,   #in USD
                  "TimeStart":"2022-10-20T16:00:00.000Z",  #T表示分隔符，Z表示的是UTC.
                  "TimeStop":"2022-1-28T16:00:00.000Z",   
                  "Frequency":"15MINS", 
                  "Code":"BTC-USD",
                  "nHistoryCounts":100,                  
                  }
        if 'Init_Balance' in para.keys():
            self.account['asset']=para["Init_Balance"] 
            
        #from MarketClient import MarketClient     
        # 数据初始化和检查
        # 1. check Time
        if(para["TimeStop"]=="Now"):
            timestop=pd.Timestamp.now()
            #pd.Timestamp.now(pytz.timezone('utc'))
        else:
            timestop=pd.to_datetime(para["TimeStop"])
        if 'TimeStart' in para.keys():
            timestart=pd.to_datetime(para["TimeStart"])
            ntick=int(((timestop.value-timestart.value)/1e9)/transFrq2Sec(para["Frequency"]))
            self.ntick=ntick      
        

        if 'nHistoryCounts' in para.keys():
            self.ntick=int(para['nHistoryCounts'])
            ntick=self.ntick
        
        ## check the data not in database
        Rawdata=pd.DataFrame()
        
        ## if not from dydx
        
        client=MarketClient(dex_name='dydx')
        
        data_cyc=int(ntick/100)
        data_rem=np.mod(ntick,100)
        data_cyc_rev=0
        
        while(data_cyc+1):   
            counttemp=100
            if(data_cyc==0): counttemp=data_rem
            if(data_cyc==0 and data_rem==0): break
            market_res=client.get_price_v1(code=para["Code"],
                                  frequency=para["Frequency"],
                                  stop=pd.Timestamp(timestop.value-data_cyc_rev*100*transFrq2Sec(para["Frequency"])*1e9),
                                  count=counttemp
                                  )
            Rawdata=pd.concat([Rawdata,market_res])                                             
            data_cyc_rev=data_cyc_rev+1
            data_cyc=data_cyc-1
            
        print("Market data init sucess")
        self.rawdata=Rawdata.sort_index()
        self.rawdata=self.rawdata.astype(float)
        self.rawdata=self.rawdata.drop(self.rawdata.tail(1).index) #去尾部最新变化数据
        #self.rawdata.set_index('time',inplace=True)
        #file=self.savetolocal()
        #self.LocalInit(file, initpara)
        #self.rawdatatest=Rawdata.sort_index()
        
    def savetolocal(self):
        filename="%s_%s_%s_%s"%(self.initpara['TimeStart'].split('T')[0],
                                     self.initpara['TimeStop'].split('T')[0],
                                     self.initpara['Code'],
                                     self.initpara['Frequency'])
        curdir=os.getcwd()
        fulfile=curdir+r".\historydata\%s.csv"%(filename)
        self.rawdata.to_csv(fulfile)
        
        print("Local cave sucess:[%s]"%(fulfile))

        return fulfile
    


class ThreadPool():
    def __init__(self):
        self.pool = []
    def joinAll(self):
        for thd in self.pool:
            if thd.is_alive():  thd.join()    
    def pooladd(self,thd):
        self.pool.append(thd)
    
    
     
    
if __name__ == '__main__':  
    

    para={"Init_Balance":200,   #in USD
      "TimeStart":"2022-1-20T12:00:00.000Z",  #T表示分隔符，Z表示的是UTC.
      "TimeStop":"2022-2-19T16:00:00.000Z",   
      "Frequency":"15MINS", 
      "Code":"BTC-USD",
      }
    DM1=DataManager() 
    #DM1.RemoteInit(para)
    DM1.LocalInit(r'D:\Projects\HJATS\HJATS\modules\historydata\20220120_20220219_BTCUSD_15MINS.csv',para)
    #DM1.LocalInit(r'D:\Projects\HJATS\HJATS\modules\historydata\dataset2.csv',para)
    Thdpool=ThreadPool()
    DP1=DriverProcessor(threadID=1,name='DP1',qID=1,qname='Q1',qlength=1,DPtype="backtest",
                        speed=0.1,DataManager=DM1)
    

    ST1=StrategyManager(strategyID=2, strategyName='ST1',dpCore=DP1)
    OM1=OrderManager(OrderManagerID=3, OrderManagerName='OM1',StManager=ST1,dpCore=DP1)
    
    Thdpool.pooladd(DP1)
    Thdpool.pooladd(ST1)
    Thdpool.pooladd(OM1)

    DP1.start()
    ST1.start()
    OM1.start()
    #DP1.join()
    #ST1.join()  # DP 运行玩即可，不阻塞程序
    #OM1.join()
    
    
       