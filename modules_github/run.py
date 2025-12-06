# -*- coding: utf-8 -*-
"""
Created on Sat Feb 19 12:36:42 2022

@author: Administrator
"""

import ATSCore as Core
import queue
import threading
import time

ATS_Run_Config='BackTest'
 


def runbacktest():
    
    
    timeinterval = 0
    visualizationswitch=True  # Can choice vilization for the figure
    manager = Core.ThreadManager()
    
    para={"Init_Balance":200,   #in USD
      "TimeStart":"2022-10-10T00:00:00.000Z",  #T表示分隔符，Z表示的是UTC.
      "TimeStop":"2022-10-12T12:00:00.000Z",   
      "Frequency":"15MINS", 
      "Code":"ETH-USD",
      }
    DM1=Core.DataManager() 
    #DM1.RemoteInit(para)
    DM1.LocalInit(r'D:\JiXiang\HJATS\Main\modules_github\historydata\2022-8-19_2022-8-21_ETH-USD_15MINS.csv',para)
    #DM1.LocalInit(r'D:\Projects\HJATS\HJATS\modules\historydata\dataset2.csv',para)
    #DM1.LocalInit(r'D:\Projects\HJATS\HJATS\modules.\historydata\20220120_20220129_BTCUSD_15MINS.csv',para)
    #DM1.LocalInit(r'D:\JiXiang\HJATS\Main\modules_github\historydata\2022-8-19_2022-8-21_ETH-USD_15MINS.csv',para)
    #DM1.LocalInit(r'D:\JiXiang\HJATS\Main\modules_github\historydata\2022-8-1_2022-8-21_ETH-USD_15MINS.csv',para)
    
    Thdpool=Core.ThreadPool()
    ATS_Server=Core.ATSServer()
    manager.register("server", ATS_Server)
    
    DP1=Core.DriverProcessor(threadID=1,name='DP1',qID=1,qname='Q1',qlength=1,DPtype="backtest",
                        msg_queue=ATS_Server.msg_queue,speed=timeinterval,DataManager=DM1,
                        visualization=visualizationswitch)
    manager.register("driverprocessor", DP1)

    ST1=Core.StrategyManager(strategyID=2, strategyName='ST1',dpCore=DP1)
    manager.register("strategyprocessor", ST1)
    OM1=Core.OrderManager(OrderManagerID=3, OrderManagerName='OM1',StManager=ST1,dpCore=DP1)
    manager.register("orderprocessor", OM1) 
    
    

    
    
    
    Thdpool.pooladd(DP1)
    Thdpool.pooladd(ST1)
    Thdpool.pooladd(OM1)
    #DM1.savetolocal()

    DP1.start()
    ST1.start()
    OM1.start()
    return Thdpool,manager

def runreal():
    ATS_Server=Core.ATSServer()
    DM1=Core.DataManager()         
    Thdpool=Core.ThreadPool()
    DP1=Core.DriverProcessor(threadID=1,name='DP1',qID=1,qname='Q1',qlength=1,DPtype="realtime",
                             msg_queue=ATS_Server.msg_queue,speed=0.1,DataManager=DM1,visualization=False)
    
    
    ST1=Core.StrategyManager(strategyID=2, strategyName='ST1',dpCore=DP1)
    OM1=Core.OrderManager(OrderManagerID=3, OrderManagerName='OM1',StManager=ST1,dpCore=DP1)
    
    Thdpool.pooladd(ATS_Server)
    Thdpool.pooladd(DP1)
    Thdpool.pooladd(ST1)
    Thdpool.pooladd(OM1)

    DP1.start()
    ST1.start()
    OM1.start()
    
    return Thdpool

if __name__=='__main__':
    
    
    Runtype='1'
    
    if Runtype=="1":
        thdpool,manager=runbacktest()
        DP1=thdpool.pool[0]
        ST1=thdpool.pool[1]
        OM1=thdpool.pool[2]
        

        
        #while DP1.thread_stop==True:
        #    ST1.thread_stop=True
        #    OM1.thread_stop=True
            
            #DP1.join()
            #ST1.join()
            #OM1.join()start
            
            
    
    if Runtype == "2":
        
        thdpool=runreal()
        ATS_Server=thdpool.pool[0]
        DP1=thdpool.pool[1]
        ST1=thdpool.pool[2]
        OM1=thdpool.pool[3]
        
        try:
            ATS_Server.run()           
            while DP1.timer.is_alive():
                DP1.stop()
                
            DP1.join()
            print("exit all the threading")
        except (KeyboardInterrupt):
            ATS_Server.msg_queue.put("stop")
            while DP1.timer.is_alive():
                DP1.stop()
            DP1.join()
            print("exit all the threading")
     
    if Runtype == "3":
        
        thdpool=runreal()
        ATS_Server=thdpool.pool[0]
        DP1=thdpool.pool[1]
        ST1=thdpool.pool[2]
        OM1=thdpool.pool[3]
        
        try:
            ATS_Server.run()           
            while DP1.timer.is_alive():
                DP1.stop()
                
            DP1.join()
            print("exit all the threading")
        except (KeyboardInterrupt):
            ATS_Server.msg_queue.put("stop")
            while DP1.timer.is_alive():
                DP1.stop()
            DP1.join()
            print("exit all the threading")    