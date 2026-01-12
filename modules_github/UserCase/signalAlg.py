# -*- coding: utf-8 -*-
"""
Created on Tue Jan 25 22:34:31 2022

@author: Administrator
"""

import logging
import pandas as pd
from Atsfunc import print_colored

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
    print_colored('[sAlg]-------------------The alg started------------------',bg_color='green')
    print_colored("[sAlg]The last index is " + str(dataset['close'].index[0])+" value:" + str(dataset['close'].values[0]),bg_color='green')
    
    
    
    signal = 0
    
    # 入参排序， head 为历史数据
    series_close=dataset['close'].sort_index() 
   
    
    ma60=series_close.rolling(window=60).mean()
    ma30=series_close.rolling(window=30).mean()
    ma10=series_close.rolling(window=10).mean()
    #ma5=series_close.rolling(window=5).mean()
    cur_indicators['ind1']=ma10.iloc[-1]
    cur_indicators['ind2']=ma30.iloc[-1]
    cur_indicators['ind3']=ma60.iloc[-1]
 
 
    #KSTDIFLINE=indicators.KSTDIF(series_close)
    #ROCLINE=indicators.RateOfChange(series_close,20)
    
    #if(pd.isna(KSTDIFLINE[-1])):KSTDIFLINE[-1]=0
    #w2_indicators['ind1']=KSTDIFLINE['KSTSignal'][-1]


    
        
    if(signal==0):
        print_colored('[sAlg]Signal:NA',bg_color='green')
    signal=1

    
    print_colored('[sAlg]-------------------The alg ened------------------',bg_color='green')
    
    return signal,cur_indicators,w2_indicators
    