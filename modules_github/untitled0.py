# -*- coding: utf-8 -*-
"""
Created on Tue Aug  6 11:59:31 2024

@author: Administrator
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm

# 加载数据
data = pd.read_csv('btc_price.csv', parse_dates=['Date'], index_col='Date')
data = data['Price']

# 定义SARIMA模型
model = sm.tsa.SARIMAX(data, order=(p, d, q), seasonal_order=(P, D, Q, s))
results = model.fit()

# 进行预测
forecast = results.get_forecast(steps=30)
forecast_mean = forecast.predicted_mean
forecast_conf_int = forecast.conf_int()

# 绘图
import matplotlib.pyplot as plt
plt.figure(figsize=(10, 6))
plt.plot(data, label='历史价格')
plt.plot(forecast_mean, label='预测价格', color='red')
plt.fill_between(forecast_conf_int.index, 
                                  forecast_conf_int.iloc[:, 0], 
                                                   forecast_conf_int.iloc[:, 1], color='pink')
plt.legend()

