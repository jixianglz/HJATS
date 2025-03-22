# -*- coding: utf-8 -*-
"""
Created on Tue Jan 25 22:34:31 2022

根据固定赔率，网格策略

@author: Administrator
"""




import logging
import numpy as np

ordernum_limit=1000000
shortid=1
longid=1
orderpara={}
TempTailLossProfitStopLevel_long=-999999999  #TailLoss 功能的中间计算变量 负数（默认起始值）
TempTailLossMaxProfitLevel_long=-999999999
TempTailLossProfitStopLevel_short=-999999999
TempTailLossMaxProfitLevel_short=-999999999
debugcount=0


taillosstrigger=0
tailloss_max_price=-99999
taillosstrigger_bear=0
tailloss_max_price_bear=-999999
taillloss_delback=10


##
grid_width=20 # grid by usd, +/-width total
winlosscal={"winwin_count_bull":0,
        "lossloss_count_bull":0,
        "lossloss_count_bear":0,
        "winrate_10count":0,
        "price_in_bull":0,
        "price_in_bear":0,
        }


"""
单边宽度gridwidth=a
深度deeps = 3
首次开仓单位 = 2
累加器c1=0
   
1. 1st 信号来 建仓 产生 对应 grid 梯度网格 梯度单边宽度为a
if 没有新信号来：

    if 当前价格在梯度内：
    pass
    
    if 当前价格超过梯度：
        if 超过正梯度 level 1：
            c1+=1
            enable tailloss， level=1， win>=a
            
        if 超过负梯度 level 1：
            c1-=1
            减仓-1，loss=10
            
        if 超过正梯度 level 2：
            c1+=1
            是能tailloss， level=2， win>=2*a 
            
        if 超过负梯度 level 2：
            c1-=1
            减仓-1，loss=-2*a
            
if 有新信号来：

    if 加仓信号：
    
        if in level 0 : c1+=1
        
    
    
    if 减仓信号：

"""

  
 


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
    
    ###
    global winlosscal
    global grid_width
    global taillosstrigger
    global tailloss_max_price
    global taillosstrigger_bear
    global tailloss_max_price_bear
    global taillloss_delback
    
    
    ###
    
    
    openpara={}
    orderlist=[]
    
    dataset=parapoll['dataset']   # head last
    tick_lastclose=str(dataset.iloc[0]['close'])
    signal=parapoll['c_signal']
    orderpool=parapoll['orderpool']
    account=parapoll['orderaccount']
    order_statistic=parapoll['order_statistic']
    
    print('------------------order_statistic--------------------')
    print(order_statistic)
    print('-----------------------------------------------------')     
    
    
  
    print('-------------------The order alg started------------------')
    
    print("The last close prcie cal. holding profit is " + str(round(account['h_profit'],2)))
    
    ########### Handinlg the signal  and open ###############

#####################################看多策略######################   
    if(signal==1 and ordernum_limit>=1 and winlosscal['price_in_bull']==0):   
        
        
        winlosscal['price_in_bull']=float(tick_lastclose)
        taillosstrigger=0
        #
        martinrate=2   
        basesize=0.1
        maxlimitcount=4
        if(winlosscal['lossloss_count_bull']<maxlimitcount):
            marting_ordersize=round(basesize*(martinrate**winlosscal['lossloss_count_bull']),2)
        else:
            marting_ordersize=round(basesize*(martinrate**maxlimitcount),2)

        openpara={
              #'uid':str(ordernum_limit),
              'uid':"long"+str(longid),
              'code':'ETH-USD',
              'oaction':'OPEN',    
              'oside':'LONG',
              'otype':'MARKET',
              'osize':str(marting_ordersize),
              'oprice':str(float(tick_lastclose)+20),  #注意再backtest里用的是openprice作为开仓价
             # 'createDatatime':''    
                 }
        orderlist.append(openpara)
        ordernum_limit=ordernum_limit-1



    if(winlosscal['price_in_bull']!=0):
        
        boxlevel=round((float(tick_lastclose)-winlosscal['price_in_bull'])/(2*grid_width))
        #logging.info("float(tick_lastclose:"+str(float(tick_lastclose)))
        #logging.info("winlosscal:"+str(winlosscal['price_in_bull']))
        #logging.info("boxlevel:"+str(boxlevel))
        
        
        if(taillosstrigger==0 and boxlevel>=1):
            
            taillosstrigger=1
            tailloss_max_price=float(tick_lastclose)
            #logging.info("trg=0 tailloss_max_price::"+str(tailloss_max_price))

        if(taillosstrigger==1):
            
            
            if(float(tick_lastclose)>tailloss_max_price):tailloss_max_price=float(tick_lastclose)

            outprice=tailloss_max_price-taillloss_delback
            
            logging.info("trg=1 outprice:"+str(outprice))
            logging.info("trg=1 tailloss_max_price:"+str(tailloss_max_price))
            
            if(float(tick_lastclose)<outprice):
                
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
                
                winlosscal['price_in_bull']=0
                taillosstrigger=0
                
                if(boxlevel<=-1):
                    winlosscal['lossloss_count_bull']+=1
                                
                if(boxlevel>=0):
                    winlosscal['lossloss_count_bull']=0
                
            
            
        
        if(boxlevel<=-1):
     
            
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
            
            winlosscal['price_in_bull']=0
            
            if(boxlevel<=-1):
                winlosscal['lossloss_count_bull']+=1
                            
            if(boxlevel>=1):
                winlosscal['lossloss_count_bull']=0
    
 


#####################################沽空策略######################  

    if(signal==-1 and ordernum_limit>=1 and  winlosscal['price_in_bear']==0):   
            
        #
        winlosscal['price_in_bear']=float(tick_lastclose)
        taillosstrigger_bear=0
        #
        martinrate=2   
        basesize=0.1
        maxlimitcount_bear=4
        
        
        if(winlosscal['lossloss_count_bear']<maxlimitcount_bear):
            marting_ordersize=round(basesize*(martinrate**winlosscal['lossloss_count_bear']),2)
        else:
            marting_ordersize=round(basesize*(martinrate**maxlimitcount_bear),2)
        
        
        openpara={
              #'uid':str(ordernum_limit),
              'uid':"short"+str(shortid),
              'code':'ETH-USD',
              'oaction':'OPEN',
              'oside':'SHORT',
              'otype':'MARKET',
              'osize':str(marting_ordersize),
              'oprice':str(float(tick_lastclose)-20), #注意再backtest里用的是openprice作为开仓价
             # 'createDatatime':''    
                 }
        orderlist.append(openpara)
        ordernum_limit=ordernum_limit-1    
    





    if(winlosscal['price_in_bear']!=0):
        
        boxlevel=round((float(tick_lastclose)-winlosscal['price_in_bear'])/(2*grid_width))
        #logging.info("float(tick_lastclose:"+str(float(tick_lastclose)))
        #logging.info("winlosscal:"+str(winlosscal['price_in_bear']))
        #logging.info("boxlevel:"+str(boxlevel))
        
        
        
        
        
        if(taillosstrigger_bear==0 and boxlevel<=-1):
            
            taillosstrigger_bear=1
            tailoss_max_price_bear=float(tick_lastclose)
            
        if(taillosstrigger_bear==1):
            
            if(float(tick_lastclose)<tailoss_max_price_bear):
                tailoss_max_price_bear=float(tick_lastclose)
            
            outprice_bear=tailloss_max_price_bear+taillloss_delback
        
            if(float(tick_lastclose)>outprice_bear):
                                
     
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

            
                winlosscal['price_in_bear']=0
                taillosstrigger_bear=0
            
                if(boxlevel<=-1):
                    winlosscal['lossloss_count_bear']=0
                                
                if(boxlevel>=1):
                    winlosscal['lossloss_count_bear']+=1


  

    
    
    
    
    
    #Below is the tail loss alg, real-time 还不支持
    TailLossEn=False
    if(TailLossEn==True):
        TailLossProfitTrigPercent_long=0.01  # trig to start   in %
        TailLossStopLossPercent_long=0.02   # drawback stop Loss Level in %
        TailLossProfitTrigPercent_short=0.01  # trig to start   in %
        TailLossStopLossPercent_short=0.02   # drawback stop Loss Level in %
        maxpercentLoss=-0.10      #资产止损
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
                

    print('-------------------The order ened------------------')
    
    return orderlist
    