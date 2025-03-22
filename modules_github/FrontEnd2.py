from multiprocessing import Process, Queue
import os, time, random
import sys
import logging
import matplotlib.pyplot as plt

from matplotlib.pyplot import MultipleLocator

import ATSCore as Core

import numpy as np




####Abonded CLASS
class VisualClient():
    def __init__(self):
        plt.ion()
        #plt.ioff()
        plt.rcParams['figure.figsize']=(10,10)
        plt.rcParams['font.sans-serif']=['SimHei']
        plt.rcParams['axes.unicode_minus']=False
        plt.rcParams['lines.linewidth']=0.5
        #self.fig, self.axs = plt.subplots(2,1,figsize=(10,8))
        self.fig =plt.figure(figsize=(13,8))
        self.mainlinewidth=1
        
        self.fig.tight_layout()
        
        self.rect1=[0.10,0.46,0.77,0.5]  # 上下宽高
        self.rect2=[0.10,0.11,0.77,0.2]
        
        self.axs1=plt.axes(self.rect1)

       # plt.tick_params(labelsize=8)    
        
        #self.axs2=plt.axes(self.rect2)
       # plt.xticks(rotation=90)
        
    def update(self,rawdata_show):
        
        
        self.fig.clf()
        
        #self.axs1.cla()

        
        x=rawdata_show.index.to_numpy()

        y=rawdata_show['close'].values
        
        length=len(rawdata_show)
        self.axs1=plt.axes(self.rect1)
        self.axs1.plot(x, y,lw=self.mainlinewidth)
        plt.xticks(rotation=270)
        self.axs1.get_xaxis().set_visible(False)
        
        if(length<20):
            x_major_locator=MultipleLocator(1)
        else:
            x_major_locator=MultipleLocator(int(length/20))
        #y_major_locator=MultipleLocator(1)

        self.axs1.xaxis.set_major_locator(x_major_locator)
        #ax.yaxis.set_major_locator(y_major_locator)
        self.axs1.set(xlabel='time (s)', ylabel='voltage (mV)',
        title='About as simple as it gets, folks')
        self.axs1.grid()

def write(q):
    
    print('Process to write: %s' % os.getpid())
    for value in ['A', 'B', 'C']:
        print('Put %s to queue...' % value)

        q.put(value)
        time.sleep(2)
      

def read(q):
    plt.ion()
    #plt.ioff()
    plt.rcParams['figure.figsize']=(10,10)
    plt.rcParams['font.sans-serif']=['SimHei']
    plt.rcParams['axes.unicode_minus']=False
    plt.rcParams['lines.linewidth']=0.5
    #self.fig, self.axs = plt.subplots(2,1,figsize=(10,8))
    fig =plt.figure(figsize=(13,8))
    mainlinewidth=1
    
    fig.tight_layout()
    
    rect1=[0.10,0.46,0.77,0.5]  # 上下宽高
    rect2=[0.10,0.11,0.77,0.2]
    
    axs1=plt.axes(rect1)
    print('Process to read: %s' % os.getpid())
    while True:
        
        value = q.get()
        print('VALUE GOT')
        print(value)
        fig.clf()
        
        #self.axs1.cla()

        
        x=value.index.to_numpy()

        y=value['close'].values
        
        length=len(value)
        axs1=plt.axes(rect1)
        axs1.plot(x, y,lw=mainlinewidth)
        plt.xticks(rotation=270)
        axs1.get_xaxis().set_visible(False)
        
        if(length<20):
            x_major_locator=MultipleLocator(1)
        else:
            x_major_locator=MultipleLocator(int(length/20))
        #y_major_locator=MultipleLocator(1)

        axs1.xaxis.set_major_locator(x_major_locator)
        #ax.yaxis.set_major_locator(y_major_locator)
        axs1.set(xlabel='time (s)', ylabel='voltage (mV)',
        title='About as simple as it gets, folks')
        axs1.grid()

def main(q):
    
 
    para={"Init_Balance":10000,   #in USD
      "TimeStart":"2022-1-20T12:00:00.000Z",  #T表示分隔符，Z表示的是UTC.
      "TimeStop":"2022-1-29T16:00:00.000Z",   
      "Frequency":"15MINS", 
      "Code":"BTC-USD",
      }
    DM1=Core.DataManager() 
    #DM1.RemoteInit(para)
    DM1.LocalInit('D:\Projects\HJATS\HJATS\modules\dataset.csv',para)
    Thdpool=Core.ThreadPool()
    DP1=Core.DriverProcessor(threadID=1,name='DP1',qID=1,qname='Q1',qlength=1,DPtype="backtest",
                        speed=0.1,DataManager=DM1,Pqueue=q)
    

    ST1=Core.StrategyManager(strategyID=2, strategyName='ST1',dpCore=DP1,func=Core.func)
    OM1=Core.OrderManager(OrderManagerID=3, OrderManagerName='OM1',StManager=ST1)
    
    Thdpool.pooladd(DP1)
    Thdpool.pooladd(ST1)
    Thdpool.pooladd(OM1)

    DP1.start()
    ST1.start()
    OM1.start()
    #DP1.join()
             




if __name__=='__main__':
    
    q = Queue()
    corerun = Process(target=main, args=(q,))
    pr = Process(target=read, args=(q,))

    corerun.start()

    pr.start()


    logging.info('main')
    #pr.terminate()
    print('end')
        
    

    

  