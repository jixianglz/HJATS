# -*- coding: utf-8 -*-
"""
Created on Wed Nov  9 07:45:44 2022

@author: Administrator
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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


def IndSMA(ticks,n):
    
    return sum(ticks[0:n])/n




def KnowTrueThing(ticks):
    ROC10=RateOfChange(ticks, 10)
    ROC15=RateOfChange(ticks, 15)
    ROC20=RateOfChange(ticks, 20)
    ROC30=RateOfChange(ticks, 30)
    ROC10MA=ROC10.rolling(10).mean()
    ROC15MA=ROC15.rolling(10).mean()
    ROC20MA=ROC20.rolling(10).mean()
    ROC30MA=ROC30.rolling(15).mean()
    KST=ROC10MA+2*ROC15MA+3*ROC20MA+4*ROC30MA
    KSTsignal=KST.rolling(9).mean()
    KST.name='KST'
    KSTsignal.name='Signal'
    KSTIND=pd.concat([KST,KSTsignal],axis=1)   
    return KSTIND

def KSTDIF(ticks):
    
    ROC10=RateOfChange(ticks, 10)
    ROC15=RateOfChange(ticks, 15)
    ROC20=RateOfChange(ticks, 20)
    ROC30=RateOfChange(ticks, 30)
    ROC10MA=ROC10.rolling(10).mean()
    ROC15MA=ROC15.rolling(10).mean()
    ROC20MA=ROC20.rolling(10).mean()
    ROC30MA=ROC30.rolling(15).mean()
    KST=ROC10MA+2*ROC15MA+3*ROC20MA+4*ROC30MA
    KSTsignal=KST.rolling(9).mean()
    KST.name='KST'
    KSTsignal.name='Signal'
    KSTdif=KST.copy(deep=True)
    KSTdif.name="KSTSignal"
    
    #check the KST Cross
    #对齐数据
    KST_Array=pd.concat([KSTdif,KST,KSTsignal],axis=1)
    for i in range(1,len(KST_Array)):   
        
        if(pd.isna(KST_Array["Signal"].iloc[i-1])): 
            KST_Array['KSTSignal'].iloc[i]=0
            continue  
        KST_Array['KSTSignal'].iloc[i]=2*KST_Array['KST'].iloc[i]- KST_Array['Signal'].iloc[i]

        

       
    #KSTIND=pd.concat([KSTdif],axis=1)  
   # KSTIND=pd.concat([KSTdif,KST,KSTsignal],axis=1)
    #KSTIND=KSTdif
    return KST_Array


def RateOfChange(ticks,n,fullcal=True):
    #tick tail for last
    ROC=pd.Series(dtype=float)
    na=np.nan
    tickscal=ticks[-n:]
    if(fullcal==True):tickscal=ticks
    
    for sers in tickscal.rolling(n):
        if(len(sers)<n):
            tmp=pd.Series({sers.tail(1).index[0]: na})           
        else:    
            tmpROC=100*(sers[-1]-sers[-n])/sers[-n]
            tmp=pd.Series({sers.tail(1).index[0]: tmpROC})
        ROC=pd.concat([ROC,tmp])
                
    return ROC



if __name__ == '__main__':  
    
    datapath=r'D:\Projects\HJATS\HJATS\modules\historydata\2022-10-10_2022-10-20_ETH-USD_5MINS.csv'
    #datapath=r'D:\Projects\HJATS\HJATS\modules.\historydata\2022-8-19_2022-8-21_ETH-USD_15MINS.csv'
  
    rawdata=pd.read_csv(datapath)
    rawdata.set_index('time',inplace=True)
    ticks=rawdata['close'] 
    #ticks=ticks[0:1000]
    KST=KSTDIF(ticks)
    KST_Array=KST
# =============================================================================
#     fig, axes = plt.subplots(nrows=1, ncols=1)
#     ticks.plot(ax=axes[0])
#     
#     KST.plot(ax=axes[0])
# =============================================================================
    
    fig2,aax1=plt.subplots() #subplots一定要带s
    aax1.plot(ticks,c='black',linewidth=2)
   # ax1.set_ylabel('EXP')
    aax2=aax1.twinx() #twinx将ax1的X轴共用与ax2，这步很重要
    aax2.plot(KST)
    #ax2.set_ylabel('in')
    
    #ax1.axis('off')   
    aax1.axes.get_xaxis().set_visible(False)
    plt.show()
    
    
    
    
    
    # Get the KSTSignal column
    KSTSignal = KST_Array['KSTSignal']
    
    # Create a list of colors for each data point
    colors = ['green' if i > 2 else 'red' for i in KSTSignal]
    
    # Plot the original tick data in the specified colors
    
    aax1.scatter(range(len(ticks)), ticks, c=colors)
    
    # Show the plot
    plt.show()
