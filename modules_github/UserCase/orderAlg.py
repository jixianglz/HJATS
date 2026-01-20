# -*- coding: utf-8 -*-
"""
Created on Tue Jan 25 22:34:31 2022

根据固定赔率，网格策略

@author: Administrator
"""

import logging
import numpy as np
import time
from Atsfunc import print_colored

ordernum_limit=5


longid=1
shortid=1



def run(parapoll):
    
    
    ###算法自用的参数
    global ordernum_limit

    
    ###固定参数
    global longid
    global shortid
    pclr ='blue'
    openpara={}  # fix当前单个订单参数
    orderlist=[] # order输出多个订单参数的集合
    ###消息传参分解
    ##order 能拿到的参数
    dataset=parapoll['dataset']   # head last
    tick_lastclose=str(dataset.iloc[0]['close'])
    ## order 基本参数
    signal=parapoll['c_signal']  # 本次算法拿到的信号结果，确认是否要开仓指示
    orderpool=parapoll['orderpool']   # 当前的订单池
    account=parapoll['orderaccount']   # 当前的账户状态
    order_statistic=parapoll['order_statistic']  # 当前订单的统计结果
    
    print_colored('------------------order_c_signal--------------------',bg_color=pclr)
    print_colored(signal,bg_color=pclr)
    print_colored('------------------order_orderpool--------------------',bg_color=pclr)
    print_colored(orderpool,bg_color=pclr)
    print_colored('------------------order_account--------------------',bg_color=pclr)
    print_colored(account,bg_color=pclr)
    print_colored('------------------order_statistic--------------------',bg_color=pclr)
    #print_colored(order_statistic,bg_color=pclr)
    
    
    
    print_colored('[oAlg]-------------------The order alg started------------------',bg_color=pclr)
   
    
    #print("The last close prcie cal. holding profit is " + str(round(account['h_profit'],2)))
    
    ########### Handinlg the signal  and open ###############

#####################################看多策略######################   
    if(signal==1 and ordernum_limit>0):   


        openpara={
              #'uid':str(ordernum_limit),
              'uid':"long"+str(longid),
              'code':'ETH-USD',
              'oaction':'OPEN',    
              'oside':'LONG',
              'otype':'MARKET',
              'osize':'0.1',
              'oprice':str(float(tick_lastclose)+20),  #注意再backtest里用的是openprice作为开仓价
              'createDatatime':time.ctime()
                 }
        orderlist.append(openpara)
        ordernum_limit=ordernum_limit-1
        longid+=1
        ordernum_limit=ordernum_limit-1
        print(longid)
 

    print_colored('[oAlg]-------------------The order alg ended------------------',bg_color=pclr)
    
    return orderlist
    