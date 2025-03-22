# -*- coding: utf-8 -*-
"""
Created on Tue Jan 25 22:34:31 2022

@author: Administrator
"""

import logging


AlgParas={'maxlongnum':3,
          'maxshortnum':3}


def Ind_BREAK(ticks,win):
    # By head last
    if(len(ticks)>=win):
        
        High=max(ticks[0:win+1])
        Low=min(ticks[0:win+1])
        Last=ticks[0]
        BullLine=1-abs(Last-High)/abs(High-Low)
        BearLine=1-abs(Last-Low)/abs(High-Low)
        return BullLine,BearLine
    return 0,0




def run(parapoll):
    
    global AlgParas
    dataset=parapoll['dataset']   # head last
    indicators= parapoll['indicatorsdic']  #last indicators for alg use
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
    
    
    BullLine,BearLine=Ind_BREAK(ma5.sort_index(ascending=False),50)
    
    w2_indicators['ind1']=BullLine
    w2_indicators['ind2']=BearLine
    
    
    if(len(ma60)>60):
        FilterLine=(ma60[-1]-ma60[-30])
        if(FilterLine)>0: FilterLine=1
        if(FilterLine)<0: FilterLine=-1
        
    else:
        FilterLine=0
    
    w2_indicators['ind3']=FilterLine


    ############MOVING AVG. STRE ##################
    BullLine_ind=indicators_w2['ind1']
    BearLine_ind=indicators_w2['ind2']

   
    #if(ma10[-1]>=ma60[-1] and ma10[-2]<ma60[-2] ):
    if(len(BullLine_ind)>0 and len(BearLine_ind)>0):     
        if(len(BullLine_ind)>50 and BullLine>0.6 and BullLine_ind[-1]<=0.6 and FilterLine>0): 
            
            
            if(AlgParas['maxlongnum']>0):
                signal=1
                AlgParas['maxlongnum']=AlgParas['maxlongnum']-1
                AlgParas['maxshortnum']=3
        
        
     
            print('Signal:Buy')
            #logging.info('Signal:Buy'+dataset.index[0])
    
                
        #if((ma10[-1]<ma60[-1]) and (ma10[-2]>=ma60[-2]) ): 
        if(len(BearLine_ind)>50 and BearLine>0.6 and BearLine_ind[-1]<=0.6 and FilterLine<0): 
                          
            if(AlgParas['maxshortnum']>0):
                signal=-1
                AlgParas['maxshortnum']=AlgParas['maxshortnum']-1
                AlgParas['maxlongnum']=3
    
            
            
            print('Signal:Sell')
            #logging.info('Signal:Sell'+dataset.index[0])
            
        
        
    if(signal==0):
        print('Signal:NA')
    

          
    print(signal)
    print(cur_indicators)
    print(w2_indicators)
    
    print('-------------------The alg ened------------------')
    
    return signal,cur_indicators,w2_indicators
    