# HJATS 交易策略文档

> 最后更新: 2026-06-27

## 当前策略：双均线交叉

### 概述

当前系统运行一个经典的趋势跟踪策略：**双均线交叉（MA Crossover）**。

### 信号算法 (`strategies/signalAlg.py`)

```python
def run(parapoll) -> (signal, indicators, indicators_w2)
```

**输入：**
- `parapoll['dataset']` — DataFrame，最新 N 根K线（倒序，head=最新）

**计算逻辑：**
```
ma10 = close.rolling(10).mean()   # 快线：10周期均线
ma30 = close.rolling(30).mean()   # 慢线：30周期均线

if ma10_prev <= ma30_prev and ma10_curr > ma30_curr:
    signal =  1   # 🟢 金叉 → 看多
elif ma10_prev >= ma30_prev and ma10_curr < ma30_curr:
    signal = -1   # 🔴 死叉 → 看空
else:
    signal =  0   # 无信号 → 持仓不动
```

**输出：**
- `signal`: `1`=金叉开多, `-1`=死叉开空, `0`=无操作
- `indicators`: `{'ind1': ma10值, 'ind2': ma30值}`
- `indicators_w2`: 副窗口指标（当前为空）

### 订单算法 (`strategies/orderAlg.py`)

```python
def run(parapoll) -> list[dict]
```

**逻辑：**
| 信号 | 当前持仓 | 操作 |
|------|---------|------|
| 1 (金叉) | 无 | 开多 0.01 ETH |
| 1 (金叉) | 多单 | 不动 |
| 1 (金叉) | 空单 | 平空 → 开多 |
| -1 (死叉) | 无 | 开空 0.01 ETH |
| -1 (死叉) | 空单 | 不动 |
| -1 (死叉) | 多单 | 平多 → 开空 |
| 0 | 任意 | 不动 |

**订单结构：**
```python
# 开仓订单
{
    'uid': 'ma_long_1',          # 订单唯一ID
    'code': 'ETH-USD',           # 交易对
    'oaction': 'OPEN',           # OPEN / CLOSE
    'oside': 'LONG',             # LONG / SHORT
    'otype': 'MARKET',           # MARKET 市价单
    'osize': '0.01',             # 数量（固定0.01 ETH）
    'oprice': '1900.00',         # 价格
}
```

### 配置 (`strategies/config.ini`)

```ini
[AlgPara]
Code = ETHUSDT              # 交易对
Frequency = 15m             # K线周期
nHistoryCounts = 100        # 历史K线数量
StrategyName = HJATS_Strategy

[LiveEngine]
strategy_interval = 300          # 策略执行间隔（秒）
monitor_interval = 30            # 监控间隔（秒）
risk_max_daily_loss_pct = 5      # 单日最大亏损比例
risk_max_position = 0.05         # 最大持仓数量
```

## 如何开发新策略

### 1. 创建信号算法

在 `strategies/` 下创建新文件，实现 `run(parapoll)` 接口：

```python
# strategies/my_signal.py
def run(parapoll):
    dataset = parapoll['dataset']
    # ... 你的策略逻辑
    signal = 1  # 或 -1, 0
    indicators = {'my_ind': 123.45}
    return signal, indicators, {}
```

### 2. 创建订单算法

```python
# strategies/my_order.py
def run(parapoll):
    c_signal = parapoll['c_signal']
    orderpool = parapoll['orderpool']
    orderaccount = parapoll['orderaccount']
    # ... 你的订单逻辑
    orders = [...]
    return orders
```

### 3. 修改入口

在 `src/engine/strategy.py` 中导入你的策略：

```python
# 替换
from strategies import signalAlg, orderAlg
# 为
from strategies import my_signal as signalAlg
from strategies import my_order as orderAlg
```

### 可用技术指标 (`strategies/indicators.py`)

| 函数 | 说明 | 参数 |
|------|------|------|
| `sma(ticks, n)` | 简单移动平均 | 价格序列, 周期 |
| `rate_of_change(ticks, n)` | 变化率 ROC | 价格序列, 周期 |
| `kst(ticks)` | KST 指标 | 价格序列 |
| `break_out(ticks, win)` | 突破指标 | 价格序列, 窗口 |
