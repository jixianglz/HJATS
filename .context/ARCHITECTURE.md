# HJATS 核心架构：三线程管道模型

## 概述

系统核心是 **三线程管道（Pipeline）模式**，三个线程通过 `queue.Queue` 串联：

```
┌────────────────┐   storj(数据包)   ┌──────────────────┐   orders(订单)   ┌──────────────┐
│ DriverProcessor│ ───────────────→ │ StrategyManager  │ ─────────────→ │ OrderManager │
│    (DP)        │   queue.put      │      (SM)        │   queue.put    │    (OM)      │
│  数据驱动线程   │                  │   策略执行线程     │                │  订单管理线程  │
└────────────────┘                  └──────────────────┘                └──────────────┘
        │                                   │                                  │
        │ 倒序推送K线                        │ 计算信号→生成订单                  │ 执行订单→管理持仓
        │ speed=0(回测)逐根同步               │ 调用signalAlg+orderAlg             │ 更新账户状态
        │ speed>0(实盘)定时轮询               │                                  │
```

## 三线程详解

### 1. DriverProcessor (DP) — 数据驱动线程

| 属性 | 说明 |
|------|------|
| 基类 | `threading.Thread` |
| 文件 | `src/engine/driver.py` |
| 职责 | 从 DataManager 获取K线数据，打包成 `storj` 推送给 StrategyManager |
| 回测模式 | 从本地CSV读取数据，倒序排列，逐根推送。每推一根 `queue.join()` 等待消费 |
| 实盘模式 | 由 Timer 驱动定时轮询 MarketClient，获取最新K线 |
| 输出 | `storj` 数据包从 `self.queue` (queue.Queue) 传给 SM |

**回测数据流：**
```python
# DriverProcessor._run_backtest() 内部
for idx in range(len(self.data)):
    storj = build_storj(idx, self.data)     # 取最新N根K线（倒序）
    self.queue.put(storj)                    # 推给SM
    self.queue.join()                        # 等待SM处理完成
    # SM内部：signalAlg → orderAlg → 订单推给OM
    # OM内部：执行订单，更新持仓
```

### 2. StrategyManager (SM) — 策略执行线程

| 属性 | 说明 |
|------|------|
| 基类 | `threading.Thread` |
| 文件 | `src/engine/strategy.py` |
| 职责 | 从DP获取数据 → 调用 `signalAlg.run()` 计算信号 → 调用 `orderAlg.run()` 生成订单 → 推送给OM |
| 内部队列 | `self.queue` (从DP接收)，`self.oderqueue` (向OM发送) |
| 循环 | 每次从队列取storj，执行策略，订单推给OM |

**处理流程：**
```python
# StrategyManager.run() 主循环
while not self.thread_stop:
    storj = self.queue.get()                 # 从DP取数据
    signal, ind, w2 = signalAlg.run(storj)   # 计算信号
    orders = orderAlg.run({'c_signal': signal, ...})  # 生成订单
    self.oderqueue.put(orders)               # 推给OM
    self.queue.task_done()                   # 通知DP继续
```

### 3. OrderManager (OM) — 订单管理线程

| 属性 | 说明 |
|------|------|
| 基类 | `threading.Thread` |
| 文件 | `src/engine/order_manager.py` |
| 职责 | 从SM接收订单 → 通过 Broker 执行 → 管理 OrderInstance 持仓 → 更新账户 |
| 回测模式 | 直接调用 BacktestBroker 模拟成交（按收盘价） |
| 实盘模式 | 调用 BinanceBroker 发送真实订单到交易所 |

## 数据流详解

### storj 数据包结构

DP 推送给 SM 的数据包：

```python
storj = {
    'dataset': df,           # DataFrame, 倒序K线（head=最新）
    'dataset_original': df,  # 完整原始数据
    'tick_num': int,         # 当前K线序号（回测用）
    'time': datetime,        # 当前K线时间
    'frequency': str,        # 周期（如 '15MINS'）
    'code': str,             # 交易对（如 'ETH-USD'）
    'indicatorsdic': {},     # 主窗口指标历史
    'orderpool': {},         # 当前订单池
    'orderaccount': {},      # 当前账户状态
    'dp_type': str,          # 'backtest' / 'realtime'
}
```

## 回测 vs 实盘模式差异

| 维度 | 回测模式 | 实盘模式 |
|------|---------|---------|
| 数据源 | 本地CSV文件 | Binance API 实时数据 |
| 驱动方式 | 逐根同步（queue.join） | Timer 定时（5秒轮询） |
| Broker | BacktestBroker（模拟） | BinanceBroker（真实API） |
| 速度 | speed=0（尽可能快） | speed=0.1（控制频率） |
| 可视化 | matplotlib 实时显示 | 可选关闭 |
| 风险管理 | 无（历史数据） | LiveEngine 监控止损 |

## 核心循环（回测）

```python
# 伪代码：回测逐K线执行流程
for idx, row in df.iterrows():
    storj = build_storj(idx, row)                   # 构建倒序K线包
    signal, indicators = signalAlg.run(storj)       # 信号算法
    orders = orderAlg.run({'c_signal': signal, ...}) # 订单算法
    for o in orders:
        if o['oaction'] == 'OPEN':
            create_position(o)                      # 开仓
        else:
            balance += close_position(o)            # 平仓
    equity = balance + floating_pl                  # 当前权益
```

## ATSServer（状态管理）

`src/server/ats_server.py` 提供：
- `msg_queue` — 消息队列，接收UI/外部命令
- `run()` — 主循环，处理消息
- 状态持久化支持
