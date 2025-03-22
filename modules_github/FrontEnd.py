import matplotlib.pyplot as plt

from matplotlib.pyplot import MultipleLocator
from multiprocessing import  Process

import numpy as np
import time

import logging

####画图的Tick 是 DP 核一收到 tick 变画 ，后续执行 算法 ，所以 当前 tick 下不会有算法输出结果

class VisualClient():
    def __init__(self):
        
      
        ## Init the figure 
        #plt.ion()
        plt.ioff()
        plt.rcParams['figure.figsize']=(12,12)
        plt.rcParams['font.sans-serif']=['SimHei']
        plt.rcParams['axes.unicode_minus']=False
        plt.rcParams['lines.linewidth']=0.5
        #self.fig, self.axs = plt.subplots(2,1,figsize=(10,8))
        self.fig =plt.figure(figsize=(10,8))
        self.mainlinewidth=1
        
        self.fig.tight_layout()
        
        self.rect1=[0.10,0.5,0.8,0.45]  # 左上点（距左），左下点（距下）宽高
        self.rect2=[0.10,0.3,0.8,0.15]
        self.rect3=[0.10,0.1,0.8,0.15]
        
        self.axs1=plt.axes(self.rect1)                    
       # plt.tick_params(labelsize=8)            
        self.axs2=plt.axes(self.rect2)
        self.axs3=plt.axes(self.rect3)
       # plt.xticks(rotation=90)
       
       ###--Here for signals------------#
        self.count=1
        self.x_axis=[1]
        self.y_axis_tick=[]
        
        self.x_signal_buy_tick=[]
        self.y_signal_buy_tick=[]
        
        self.x_signal_sell_tick=[]
        self.y_signal_sell_tick=[]
        
        self.x_order_buy_tick=[]
        self.y_order_buy_tick=[]
        
        self.x_order_sell_tick=[]
        self.y_order_sell_tick=[]
        
        

        self.x_indicators={
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
        self.y_indicators={
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
        
        self.x_indicators_w2={
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
        self.y_indicators_w2={
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
        
        self.x_profit=[]
        self.y_profit=[] 
        self.x_asset=[]
        self.y_asset=[] 
        
        

        
        plt.show()
        
    def __del__(self):

        print("Inside the __del__ method.")
      
           
    def drawrestuls(self):
        plt.draw()
    
    def update(self,rawdata_show,signal,indicators,indicators_w2,profitline,assetline,instantDraw=True):
        
        
        self.fig.clf()
        
        #self.axs1.cla()
        #self.axs2.cla()

        self.axs1=plt.axes(self.rect1)
        self.axs2=plt.axes(self.rect2)
        self.axs3=plt.axes(self.rect3)
        
        # draw main
        self.y_axis_tick.append(rawdata_show['close'].values[-1])

        self.axs1.plot(self.x_axis,self.y_axis_tick,lw=self.mainlinewidth)
        
        self.axs1.text(0.1, 0.9,"Tick:"+str(self.y_axis_tick[-1]), ha='center', va='center', transform=self.axs1.transAxes)   
       
        # signal mark  on Tick
        
        if(len(signal)>0):
            
            if(signal[-1]==1):             
                
                #self.x_signal_buy_tick.append(self.count-1)      
                #self.y_signal_buy_tick.append(rawdata_show['close'].values[-2])
                self.x_signal_buy_tick.append(self.count-1)      
                self.y_signal_buy_tick.append(rawdata_show['close'].values[-2])
                
            if(signal[-1]==-1):              
                #self.x_signal_sell_tick.append(self.count-1)      
                #self.y_signal_sell_tick.append(rawdata_show['close'].values[-2]) 
                self.x_signal_sell_tick.append(self.count-1)      
                self.y_signal_sell_tick.append(rawdata_show['close'].values[-2])  
       
        self.axs1.scatter(self.x_signal_buy_tick,self.y_signal_buy_tick,color='green',marker="^",s=80)
        self.axs1.scatter(self.x_signal_sell_tick,self.y_signal_sell_tick,color='red',marker="v",s=80)
       
        
       
        #order mark  on Tick
        #draw the order[Buy, sell] Mark 画图具有超前性，取 -2  , 
        if('Signal' in rawdata_show.columns):
            
            if(rawdata_show['Signal'].values[-2]=='LONG'):             
                self.x_order_buy_tick.append(self.count-1)      
                self.y_order_buy_tick.append(rawdata_show['close'].values[-2])

                
                
            if(rawdata_show['Signal'].values[-2]=='SHORT'):              
                self.x_order_sell_tick.append(self.count-1)      
                self.y_order_sell_tick.append(rawdata_show['close'].values[-2])     

        
            
        
        self.axs1.scatter(self.x_order_buy_tick,self.y_order_buy_tick,color='black',marker=r'$B$',s=100)
        self.axs1.scatter(self.x_order_sell_tick,self.y_order_sell_tick,color='black',marker=r'$S$',s=100)
      
        
       
        #indicators on tick
        for ind_index in indicators:
            
            if(len(indicators[ind_index])>0):
                
                 #draw the signal 画图具有超前性，取-1
                self.x_indicators[ind_index].append(self.count-1)
                self.y_indicators[ind_index].append(indicators[ind_index][-1])   
                
                self.axs1.plot(self.x_indicators[ind_index],self.y_indicators[ind_index])
        
            
        self.count+=1
        self.x_axis.append(self.count)
        
        self.axs1.set(xlabel='Times in count', ylabel='Price usd',
        title='HJATS BackTest')
        #self.axs1.grid()
                
        
        
        
        # Draw Minor window
        
        
        #indicators minor on tick
        for ind_index in indicators_w2:
            
            if(len(indicators_w2[ind_index])>0):
                
                 #draw the signal 画图具有超前性，取-1
                self.x_indicators_w2[ind_index].append(self.count-1)
                self.y_indicators_w2[ind_index].append(indicators_w2[ind_index][-1])   
                
                self.axs2.plot(self.x_indicators_w2[ind_index],self.y_indicators_w2[ind_index])            

        # draw asset and profit
        
        if(len(profitline)>1):
            
            self.x_profit.append(self.count-1)
            self.y_profit.append(profitline[-1])  
            self.axs3.plot(self.x_profit,self.y_profit)
            self.x_asset.append(self.count-1)
            self.y_asset.append(assetline[-1])  
            self.axs3.plot(self.x_asset,self.y_asset)
        
            self.axs3.text(0.1, 0.9,"HoldingProfit:"+str(round(self.y_profit[-1]-self.y_asset[-1],2)), ha='left', va='center', transform=self.axs3.transAxes)
            self.axs3.text(0.1, 0.8,"Asset:"+str(round(self.y_asset[-1],2)), ha='left', va='center', transform=self.axs3.transAxes)
        ## add text
        

        
        if(instantDraw):plt.draw()

        


if __name__ == '__main__':  
    
    
    VC=VisualClient()
    
    
    #VC.update(a)

    
    
    
