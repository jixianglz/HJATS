# -*- coding: utf-8 -*-
"""
Created on Tue Nov  9 07:10:57 2021

@author: Administrator
"""

from Constants import *
from Atsfunc import *
import pandas as pd
import numpy as np
import threading
import queue
from MarketClient import MarketClient


# 初始化需要 参数. 1 资金 2. 时间. 3 算法. 4. 回测的数据


para={"Init_Balance":10000,   #in USD
      "TimeStart":"2022-1-20T16:00:00.000Z",  #T表示分隔符，Z表示的是UTC.
      "TimeStop":"2022-1-24T16:00:00.000Z",   
      "Frequency":FREQ_15MINS, 
      "Code":"BTC-USD",
      }

# 数据初始化和检查
# 1. check Time
timestart=pd.to_datetime(para["TimeStart"])
if(para["TimeStop"]=="Now"):
    timestop=pd.Timestamp.now()
else:
    timestop=pd.to_datetime(para["TimeStop"])

ntick=int(((timestop.value-timestart.value)/1e9)/transFrq2Sec(para["Frequency"]))


## check the data not in database
Rawdata=pd.DataFrame()

## if not from dydx

client=MarketClient(dex_name='dydx')

data_cyc=int(ntick/100)
data_rem=np.mod(ntick,100)
data_cyc_rev=0
while(data_cyc+1):   
    counttemp=100
    if(data_cyc==1): counttemp=data_rem
    market_res=client.get_price_v1(code=para["Code"],
                          frequency=para["Frequency"],
                          stop=pd.Timestamp(timestop.value-data_cyc_rev*100*transFrq2Sec(para["Frequency"])*1e9),
                          count=counttemp
                          )
    Rawdata=pd.concat([Rawdata,market_res])                                             
    data_cyc_rev=data_cyc_rev+1
    data_cyc=data_cyc-1
print("Market data init sucess")



# 调运算法 记录结果



# 输出回测报告


class BackTestEngine:
    
    
    def __init__(self, threadID, name, counter):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.counter = counter
    def run(self):
        print ("Starting " + self.name)
       # 获得锁，成功获得锁定后返回True
       # 可选的timeout参数不填时将一直阻塞直到获得锁定
       # 否则超时后将返回False
        threadLock.acquire()
        print_time(self.name, self.counter, 3)
        # 释放锁
        threadLock.release()


import random

class MyThread(threading.Thread):
  '''
  线程模型
  '''
  def __init__(self,queue):
    threading.Thread.__init__(self)
    self.queue = queue
    self.start()  # 因为作为一个工具，线程必须永远“在线”，所以不如让它在创建完成后直接运行，省得我们手动再去start它

    def run(self):
        while True:  # 除非确认队列中已经无任务，否则时刻保持线程在运行
            try:
                task = self.queue.get(block=False)    # 如果队列空了，直接结束线程。根据具体场景不同可能不合理，可以修改
                time.sleep(random.random())  # 假设处理了一段时间
                print('Task %s Done' % task)  # 提示信息而已
                self.queue.task_done()
            except (Exception,e):
                break

class MyThreadPool():
    def __init__(self,queue,size):
        self.queue = queue
        self.pool = []
        for i in range(size):
            self.pool.append(MyThread(queue))

    def joinAll(self):
        for thd in self.pool:
            if thd.is_alive():  
                thd.join()    
    
    
    
    
if __name__ == '__main__':  
    print("engine test")
    Rawdata.astype(float)['close'].plot()
