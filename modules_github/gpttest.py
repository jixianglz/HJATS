import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.arima_model import ARIMA
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from MarketClient import *

# 创建示例时间序列数据
def hurst_exponent(ts):
    """
    计算时间序列的 Hurst 指数。
    
    参数:
    ts (array-like): 时间序列数据。
    
    返回:
    float: Hurst 指数。
    """
    N = len(ts)
    T = np.arange(1, N + 1)
    Y = np.cumsum(ts - np.mean(ts))
    R = np.max(Y) - np.min(Y)
    S = np.std(ts)
    
    if S == 0:
        return 0.5  # 避免除以零
    
    R_S = R / S
    H = np.log(R_S) / np.log(N)
    
    return H
client=MarketClient(dex_name='binance')
#starttime="2024-4-19 00:00:00"
#stoptime="2024-4-20 00:00:00"




#b=client.get_price_v1(code="ETHUSDT",frequency="1m",start=starttime,stop=stoptime)
b=client.get_price_v1(code="BTCUSDT",count=150,frequency="5m")
np.random.seed(42)
data = pd.Series(np.random.randn(50).cumsum())
data=b['close'].iloc[0:150].astype(float)
data=data.reset_index(drop=True)

# 绘制时间序列数据
f=plt.figure(figsize=(10, 4))
plt.plot(data)
plt.title('Time Series Data')
plt.show()

# 绘制自相关图和偏自相关图
plot_acf(data)
plot_pacf(data)
plt.show()

# 拟合ARIMA模型
model = ARIMA(data, order=(4, 1, 2))  # 这里的order参数需要根据自相关图和偏自相关图确定
model_fit = model.fit(disp=0)

# 打印模型摘要
print(model_fit.summary())

# 进行预测
forecast, stderr, conf_int = model_fit.forecast(steps=10)
forecast_series = pd.Series(forecast, index=range(len(data), len(data) + len(forecast)))

# 绘制预测结果
plt.figure(figsize=(10, 4))
plt.plot(data, label='Original Data')
plt.plot(forecast_series, label='Forecast', color='red')
plt.plot(b['close'].astype(float).reset_index(drop=True))
plt.fill_between(forecast_series.index, conf_int[:, 0], conf_int[:, 1], color='red', alpha=0.3)
plt.legend()
plt.show()


H = hurst_exponent(data)
print(f"Hurst 指数: {H}")
