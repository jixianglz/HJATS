# -*- coding: utf-8 -*-
"""
Created on Tue Jan 25 22:34:31 2022

@author: Administrator
"""

import logging
import pandas as pd

from UserCase import indicators 
#from indicators import KSTDIF as KSTDIF


AlgParas={'maxlongnum':3,
          'maxshortnum':3,
          "testcount":0}



def run(parapoll):
    
    global AlgParas
    dataset=parapoll['dataset']   # head last
    indicators_main= parapoll['indicatorsdic']  #last indicators for alg use
    indicators_w2= parapoll['indicatorsdic_w2']  #last indicators in minor for alg use

    openpara={}
    cur_indicators={}
    w2_indicators={}
    print('-------------------The alg started------------------')
    print("The last price is " + str(dataset['close'].values[0]))
    #print(dataset)
    
    
    signal=0
    
    series_close=dataset['close'].sort_index()    
    ma60=series_close.rolling(window=60).mean()
    ma30=series_close.rolling(window=30).mean()
    ma10=series_close.rolling(window=10).mean()
    ma5=series_close.rolling(window=5).mean()
    
    cur_indicators['ind1']=ma10[-1]
    cur_indicators['ind2']=ma30[-1]
    cur_indicators['ind3']=ma60[-1]    
    
    
    KSTDIFLINE=indicators.KSTDIF(series_close)
    
    #if(pd.isna(KSTDIFLINE[-1])):KSTDIFLINE[-1]=0
    w2_indicators['ind1']=KSTDIFLINE[-1]
    print(KSTDIFLINE[-1])
    
    if(KSTDIFLINE[-1]>0 and KSTDIFLINE[-2]<0):
        signal=1 
        print('Signal:Buy')
        
    if(KSTDIFLINE[-1]<0 and KSTDIFLINE[-2]>0):
        signal=-1 
        print('Signal:Sell')  
        
    if(signal==0):
        print('Signal:NA')
    

    
    print('-------------------The alg ened------------------')
    
    return signal,cur_indicators,w2_indicators
    