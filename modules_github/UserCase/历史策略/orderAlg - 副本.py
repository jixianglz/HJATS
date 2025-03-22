# -*- coding: utf-8 -*-
"""
Created on Tue Jan 25 22:34:31 2022

@author: Administrator
"""

import logging

ordernum_limit=1000000
shortid=1
longid=1
orderpara={}
TempTailLossProfitStopLevel_long=-999999999  #TailLoss 功能的中间计算变量 负数（默认起始值）
TempTailLossMaxProfitLevel_long=-999999999
TempTailLossProfitStopLevel_short=-999999999
TempTailLossMaxProfitLevel_short=-999999999

debugcount=0

def run(parapoll):
    
    global ordernum_limit
    global algname
    global shortid
    global longid
    global TempTailLossProfitStopLevel_long
    global TempTailLossMaxProfitLevel_long
    global TempTailLossProfitStopLevel_short
    global TempTailLossMaxProfitLevel_short
    global debugcount
    
    openpara={}
    orderlist=[]
    
    dataset=parapoll['dataset']   # head last
    tick_lastclose=str(dataset.iloc[0]['close'])
    signal=parapoll['c_signal']
    orderpool=parapoll['orderpool']
    account=parapoll['orderaccount']
    
  
    print('-------------------The order alg started------------------')
    
    print("The last close prcie cal. holding profit is " + str(round(account['h_profit'],2)))
    
    ########### Handinlg the signal  and open ###############
    
    if(signal==1 and ordernum_limit>=1):    

        openpara={
              #'uid':str(ordernum_limit),
              'uid':"long"+str(longid),
              'code':'ETH-USD',
              'oaction':'OPEN',    
              'oside':'LONG',
              'otype':'MARKET',
              'osize':'0.05',
              'oprice':str(float(tick_lastclose)+20),  #注意再backtest里用的是openprice作为开仓价
             # 'createDatatime':''    
                 }
        orderlist.append(openpara)
        ordernum_limit=ordernum_limit-1
    
    if(signal==-1 and ordernum_limit>=1):        
        openpara={
              #'uid':str(ordernum_limit),
              'uid':"short"+str(shortid),
              'code':'ETH-USD',
              'oaction':'OPEN',
              'oside':'SHORT',
              'otype':'MARKET',
              'osize':'0.05',
              'oprice':str(float(tick_lastclose)-20), #注意再backtest里用的是openprice作为开仓价
             # 'createDatatime':''    
                 }
        orderlist.append(openpara)
        ordernum_limit=ordernum_limit-1    
    
    #Below is the tail loss alg, real-time 还不支持
    TailLossEn=True
    if(TailLossEn==True):
        TailLossProfitTrigPercent_long=0.005  # trig to start   in %
        TailLossStopLossPercent_long=0.01   # drawback stop Loss Level in %
        TailLossProfitTrigPercent_short=0.005  # trig to start   in %
        TailLossStopLossPercent_short=0.001   # drawback stop Loss Level in %
        maxpercentLoss=-0.05      #资产止损
        UseAccountTotalBalance= False    # 使用总资产作为tailloss的回退计算基准
        if(UseAccountTotalBalance==True):
            basevalue=account['asset']
            basePL_long=account['h_profit_long']
            basePL_short=account['h_profit_short']
            
        if(UseAccountTotalBalance==False):
            if "long"+str(longid) in orderpool:
                basevalue=orderpool["long"+str(longid)].totalvalue
                basePL_long=orderpool["long"+str(longid)].floatingPL
            else:
                basevalue=-1
                basePL_long=0
                   
        if(basePL_long/basevalue > TailLossProfitTrigPercent_long and basePL_long/basevalue>TempTailLossMaxProfitLevel_long):
            TempTailLossProfitStopLevel_long=basePL_long/basevalue-TailLossStopLossPercent_long
            TempTailLossMaxProfitLevel_long=basePL_long/basevalue
            
        if(basePL_long/basevalue<TempTailLossProfitStopLevel_long or basePL_long/basevalue < maxpercentLoss):
               
            if "long"+str(longid) in orderpool:
                
                longsize=orderpool["long"+str(longid)].size      
                openpara={
                      #'uid':str(ordernum_limit),
                      'uid':"long"+str(longid),
                      'code':'ETH-USD',
                      'oaction':'CLOSE',
                      'oside':'LONG',
                      'otype':'MARKET',
                      'osize':str(longsize),
                      'oprice':str(float(tick_lastclose)-20),
                     # 'createDatatime':''    
                         } 
                orderlist.append(openpara)
                longid=longid+1
                
            TempTailLossProfitStopLevel_long=-999999999
            TempTailLossMaxProfitLevel_long=-999999999

        if(UseAccountTotalBalance==False):
            if "short"+str(shortid) in orderpool:
                basevalue=orderpool["short"+str(shortid)].totalvalue
                basePL_short=float(orderpool["short"+str(shortid)].floatingPL) 
            else:
                basevalue=-1
                basePL_short=0
            
        if(basePL_short/basevalue > TailLossProfitTrigPercent_short and basePL_short/basevalue>TempTailLossMaxProfitLevel_short):
            TempTailLossProfitStopLevel_short=basePL_short/basevalue-TailLossStopLossPercent_short
            TempTailLossMaxProfitLevel_short=basePL_short/basevalue
            
        if(basePL_short/basevalue<TempTailLossProfitStopLevel_short or basePL_short/basevalue <maxpercentLoss): 
            if "short"+str(shortid) in orderpool:
                
                shortsize=orderpool["short"+str(shortid)].size
                openpara={
                  #'uid':str(ordernum_limit),
                  'uid':"short"+str(shortid),
                  'code':'ETH-USD',
                  'oaction':'CLOSE',
                  'oside':'SHORT',
                  'otype':'MARKET',
                  'osize':str(shortsize),
                  'oprice':str(float(tick_lastclose)+20),
                 # 'createDatatime':''    
                     }
                orderlist.append(openpara)
                
                shortid=shortid+1    
            TempTailLossProfitStopLevel_short=-999999999
            TempTailLossMaxProfitLevel_short=-999999999  
                
    #logging.info("Max:"+str(TempTailLossMaxProfitLevel_short))
    #logging.info("THD:"+str(TempTailLossProfitStopLevel_short))
    #logging.info("Current:"+str(basePL_short/basevalue))
# =============================================================================
#     debugcount=debugcount+1    
#     if "short1" in orderpool:
#         shortsize=orderpool["short"+str(shortid)].size
#     if(debugcount==-1):
#         openpara={
#                   #'uid':str(ordernum_limit),
#                   'uid':"short"+str(shortid),
#                   'code':'ETH-USD',
#                   'oaction':'CLOSE',
#                   'oside':'SHORT',
#                   'otype':'MARKET',
#                   'osize':str(shortsize),
#                   'oprice':str(float(tick_lastclose)+20),
#                  # 'createDatatime':''    
#                      }
#         orderlist.append(openpara)    
# =============================================================================
    
    
    print('-------------------The order ened------------------')
    
    return orderlist
    