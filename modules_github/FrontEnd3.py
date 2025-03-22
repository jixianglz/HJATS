# -*- coding: utf-8 -*-
"""
Created on Sat Feb 19 21:00:22 2022

@author: Administrator
"""

# Author: 浅若清风
# Date: 2020/12/11

import threading
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.lines as line
import numpy as np
import ATSCore as Core
import os, time, random
CHUNK = 2048  # 初始数据量
data=[]  # 存放数据，用于绘制图像，数据类型可为列表

# 定义画布
fig = plt.figure()
ax = plt.subplot(111)
line = line.Line2D([], [])  # 绘制直线

# 初始化图像
def plot_init():
    ax.add_line(line)
    return line, # 必须加逗号,否则会报错（TypeError: 'Line2D' object is not iterable）

# 更新图像(animation会不断调用此函数刷新图像，实现动态图的效果)
def plot_update(i):
    global data  # data为全局变量
    data_copy = data.copy()  # 为避免线程不同步导致获取到的data在绘制图像时被更新，这里复制数据的副本，否则绘制图像的时候可能会出现x和y的数据维度不相等的情况
    #x_data=np.arange(0,data_copy.shape[0],1)  # x轴根据y轴数据自动生成（可根据需要修改）
    #ax.set_xlim(0,data_copy.shape[0])  # 横坐标范围（横坐标的范围和刻度可根据数据长度更新）
    ax.set_title("title",fontsize=8)  # 设置title
    #line.set_xdata(x_data)  # 更新直线的数据
    line.set_ydata(data_copy)  # 更新直线的数据
	# 大标题（若有多个子图，可为其设置大标题）
    plt.suptitle('Suptitle',fontsize=8)
    # 重新渲染子图
    ax.figure.canvas.draw()  # 必须加入这一行代码，才能更新title和坐标!!!
    return line,  # 必须加逗号,否则会报错（TypeError: 'Line2D' object is not iterable）

def plot_update2(rawdata_show):

    data_copy = rawdata_show['close'].values
    x_data=np.arange(0,data_copy.shape[0],1)  # x轴根据y轴数据自动生成（可根据需要修改）
    ax.set_xlim(0,data_copy.shape[0])  # 横坐标范围（横坐标的范围和刻度可根据数据长度更新）
    ax.set_title("title",fontsize=8)  # 设置title
    line.set_xdata(x_data)  # 更新直线的数据
    line.set_ydata(data_copy)  # 更新直线的数据
	# 大标题（若有多个子图，可为其设置大标题）
    plt.suptitle('Suptitle',fontsize=8)
    # 重新渲染子图
    ax.figure.canvas.draw()  # 必须加入这一行代码，才能更新title和坐标!!!
    return line,  # 必须加逗号,否则会报错（TypeError: 'Line2D' object is not iterable）




# 绘制动态图
ani = animation.FuncAnimation(fig,   # 画布
							  plot_update,  # 图像更新
                              init_func=plot_init,  # 图像初始化
                              frames=1,
                              interval=300,  # 图像更新间隔
                              blit=True)

# 数据更新函数
def dataUpdate_thead(DM):
    global data
    # 为了方便理解代码，这里生成正态分布的随机数据
    while True:  # 为了方便测试，让数据不停的更新
	    #data=np.random.normal(0,1,CHUNK)
        data=DM.rawdata_show['close'].values.copy()
        time.sleep(1)

        print(data)


if __name__ == '__main__': 
# 为数据更新函数单独创建一个线程，与图像绘制的线程并发执行

    
    
    
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
                        speed=0.1,DataManager=DM1)
    
    
    ST1=Core.StrategyManager(strategyID=2, strategyName='ST1',dpCore=DP1,func=Core.func)
    OM1=Core.OrderManager(OrderManagerID=3, OrderManagerName='OM1',StManager=ST1)
    
    Thdpool.pooladd(DP1)
    Thdpool.pooladd(ST1)
    Thdpool.pooladd(OM1)
    
    DP1.start()
    ST1.start()
    OM1.start()
#DP1.join()
    
    ad_rdy_ev = threading.Event()
    ad_rdy_ev.set()  # 设置线程运行
    t = threading.Thread(target=dataUpdate_thead, args=(DM1,)) # 更新数据，参数说明：target是线程需要执行的函数，args是传递给函数的参数）
    t.daemon = True
    t.start()  # 线程执行
    
    plt.show() # 显示图像(0,1,CHUNK)





