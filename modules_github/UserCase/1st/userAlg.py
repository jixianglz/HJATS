# -*- coding: utf-8 -*-
"""
Created on Tue Jan 25 22:34:31 2022

@author: Administrator
"""

import logging

ordernum_limit=100





def run(parapoll):
    
    global ordernum_limit
    global algname
    dataset=parapoll['dataset']
    indicators= parapoll['indicatorsdic']  #last indicators for alg use

    openpara={}
    cur_indicators={}
    print('-------------------The alg started------------------')
    print("The last price is " + str(dataset['close'].values[-1]))
    
    
    
    signal=0
    tick_lastclose=str(dataset.iloc[0]['close'])
    series_close=dataset['close'].sort_index()    
    ma60=series_close.rolling(window=60).mean()
    ma30=series_close.rolling(window=30).mean()
    ma10=series_close.rolling(window=10).mean()
    ma5=series_close.rolling(window=5).mean()
    
    cur_indicators['ind1']=ma10[-1]
    cur_indicators['ind2']=ma30[-1]
    cur_indicators['ind3']=ma60[-1]
    cur_indicators['ind4']=ma5[-1]
    
    ############MOVING AVG. STRE ##################
    
    if(ma10[-1]>=ma60[-1] and ma10[-2]<ma60[-2] ):
        signal=1
 
        print('Signal:Buy')
        logging.info('Signal:Buy'+dataset.index[0])

            
    if((ma10[-1]<ma60[-1]) and (ma10[-2]>=ma60[-2]) ): 
        signal=-1
        print('Signal:Sell')
        logging.info('Signal:Sell'+dataset.index[0])
    if(signal==0):
        print('Signal:NA')
    
    
    ########### Handinlg the signal ###############
    
    if(signal==1 and ordernum_limit>=1):        
        openpara={'code':'BTC-USD',
              'oaction':'OPEN',    
              'oside':'BUY',
              'otype':'MARKET',
              'osize':'0.001',
              'oprice':tick_lastclose,
             # 'createDatatime':''    
                 }
        ordernum_limit=ordernum_limit-1
    
    if(signal==-1 and ordernum_limit>=1):        
        openpara={'code':'BTC-USD',
              'oaction':'OPEN',
              'oside':'SELL',
              'otype':'MARKET',
              'osize':'0.001',
              'oprice':tick_lastclose,
             # 'createDatatime':''    
                 }
        ordernum_limit=ordernum_limit-1    
    
    
    print('-------------------The alg ened------------------')
    
    return openpara,cur_indicators
    