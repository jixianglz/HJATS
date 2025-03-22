import numpy as np
import matplotlib.pyplot as plt

# Heston模型的参数
S0 = 5000.0  # 标的资产初始价格
r = 0.00  # 无风险利率
kappa = 1.0  # 回归速度
theta = 0.003  # 长期波动率
sigma = 0.2  # 波动率方差
rho = -0.1  # 标的资产价格和波动率之间的相关系数
v0 = 0.0004  # 波动率初始值

# 期权参数
K = 100.0  # 期权行权价格
T = 10.0  # 期权到期时间

# Monte Carlo模拟的参数
N = 10  # 模拟次数
M = 252  # 每年的交易日数
dt = T / M  # 时间步长
T_vec = np.linspace(0, T, M+1)  # 时间网格

# 用欧拉方法进行Monte Carlo模拟
S = np.zeros((N, M+1))
v = np.zeros((N, M+1))
S[:,0] = S0
v[:,0] = v0
for j in range(M):
    Z1 = np.random.normal(size=N)
    Z2 = rho * Z1 + np.sqrt(1 - rho**2) * np.random.normal(size=N)
    S[:,j+1] = S[:,j] * np.exp((r - 0.5 * v[:,j]) * dt + np.sqrt(v[:,j] * dt) * Z1)
    v[:,j+1] = v[:,j] + kappa * (theta - v[:,j]) * dt + sigma * np.sqrt(v[:,j] * dt) * Z2
    v[:,j+1] = np.maximum(v[:,j+1], 0.0)  # 保证波动率非负

# 计算期权价格
discount_factor = np.exp(-r * T)
payoff = np.maximum(S[:,-1] - K, 0)
option_price = discount_factor * np.mean(payoff)

# 画1000条价格曲线
plt.figure(figsize=(8,6))
plt.plot(T_vec, S[:1000,:].T)
plt.xlabel('Time')
plt.ylabel('Price')
plt.title('Simulated Heston Stock Prices')
plt.show()

print("Heston Model Option Price: ", option_price)