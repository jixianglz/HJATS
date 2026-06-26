# HJATS — 自动化交易系统

**H**igh-frequency **J**ik **A**utomated **T**rading **S**ystem

一个基于 Python 的多线程自动化交易框架，支持 **回测** 和 **实盘** 两种模式。

---

## 目录

- [一、项目概述](#一项目概述)
- [二、快速开始](#二快速开始)
- [三、目录结构](#三目录结构)
- [四、核心架构：三线程管道模型](#四核心架构三线程管道模型)
- [五、数据流详解](#五数据流详解)
- [六、各模块说明](#六各模块说明)
- [七、策略开发指南](#七策略开发指南)
- [八、回测流程逐步骤详解](#八回测流程逐步骤详解)
- [九、工具脚本](#九工具脚本)
- [十、MCP Skills 接口](#十mcp-skills-接口)
- [十一、手机查看报告](#十一手机查看报告)
- [十二、配置文件说明](#十二配置文件说明)
- [十三、环境变量与安全](#十三环境变量与安全)

---

## 一、项目概述

HJATS 是一个自动化交易框架，核心能力是 **用历史数据测试交易策略**（回测）和 **接入交易所执行实盘交易**。

### 能做什么

| 功能 | 说明 |
|------|------|
| **数据获取** | 从 Binance 下载任意历史 K 线数据，自动分批 |
| **策略回测** | 用历史数据模拟运行策略，输出盈亏、胜率、夏普比率等指标 |
| **可视化报告** | 自动生成带 K 线图、买卖点、收益曲线的 HTML 网页报告 |
| **实盘交易** | 接入 Binance U 本位合约，执行自动交易 |
| **AI 集成** | 通过 MCP 协议，AI 可直接调用数据下载和回测工具 |

---

## 二、快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 下载数据（ETH 5分钟K线，最近1天）
python scripts/fetch_data.py --symbol ETHUSDT --interval 5m --days 1

# 3. 运行回测
python run_backtest.py --data data/xxx.csv --balance 100

# 4. 生成网页报告
python scripts/report_generator.py --data-file data/xxx.csv --report-json reports/backtest_report_xxx.json --trades-csv reports/backtest_report_xxx_trades.csv --equity-csv reports/backtest_report_xxx_equity.csv

# 5. 浏览器打开 reports/bt_xxx/report.html 查看
```

---

## 三、目录结构

```
HJATS/
├── run.py                   # 框架入口（回测/实盘）
├── run_backtest.py          # 独立回测运行器
├── requirements.txt         # Python 依赖
├── .env.example             # API Key 模板
├── src/                     # 框架核心代码
│   ├── engine/              # 三线程引擎
│   │   ├── driver.py        #   DriverProcessor (数据驱动)
│   │   ├── strategy.py      #   StrategyManager (策略执行)
│   │   ├── order_manager.py #   OrderManager (订单管理)
│   │   └── order_instance.py#   OrderInstance (订单实例)
│   ├── data/                # 数据层
│   │   ├── datamanager.py   #   DataManager (数据中心)
│   │   ├── market.py        #   MarketClient (市场数据)
│   │   └── db_connection.py #   ATSDBClient (MongoDB)
│   ├── broker/              # 交易所适配
│   │   ├── base.py          #   BrokerBase (抽象接口)
│   │   ├── backtest_broker.py # BacktestBroker (回测模拟)
│   │   ├── binance_broker.py  # BinanceBroker (实盘)
│   │   └── account.py       #   AccountClient (API Key)
│   ├── server/              # 状态管理
│   │   └── ats_server.py    #   ATSServer (状态持久化)
│   ├── visualization/       # 可视化
│   │   └── gui.py           #   matplotlib 实时显示
│   └── utils/               # 工具
│       ├── constants.py     #   常量
│       ├── helpers.py       #   工具函数
│       └── logger.py        #   日志
├── strategies/              # 用户策略
│   ├── signalAlg.py         #   信号算法
│   ├── orderAlg.py          #   订单算法
│   ├── indicators.py        #   技术指标
│   └── config.ini           #   配置
├── scripts/                 # 工具脚本
│   ├── fetch_data.py        #   数据下载
│   └── report_generator.py  #   报告生成
├── data/                    # K线CSV
├── reports/                 # 回测报告(每会话独立目录)
├── bin/tmux-runner.sh       # 后台命令执行
├── logs/                    # 日志
├── tests/                   # 测试
└── modules_github/          # 旧版代码(保留)
```

---

## 四、核心架构：三线程管道模型

系统核心是 **三线程管道（Pipeline）模式**，三个线程通过 `queue.Queue` 串联：

```
┌────────────────┐   queue.put(storj)   ┌──────────────────┐
│ DriverProcessor│ ────────────────────→ │ StrategyManager   │
│  (数据驱动)     │                        │  (策略计算)        │
│ 回测: for循环    │                        │ signalAlg → signal │
│ 实时: Timer     │                        │ orderAlg → orders │
└────────────────┘                        └────────┬─────────┘
                                                    │ queue.put()
                                                    ↓
                                            ┌──────────────────┐
                                            │  OrderManager     │
                                            │  (订单执行)        │
                                            │ processOrder()    │
                                            │ 更新订单池+账户    │
                                            └──────────────────┘
```

### 回测同步机制

每根K线严格串行：DP → queue.join() 等待SM → oderqueue.join() 等待OM → 下一根K线

### 实时异步机制

DP 由 `threading.Timer(10秒)` 驱动，定时拉取最新K线，消息队列控制启停。

---

## 五、数据流详解

### 核心数据结构：storj

- **类型**: `pd.DataFrame`，列 `[open, high, low, close, volume]`
- **排列**: **时间倒序**（index[0]=最新）
- **最大长度**: 100 根K线

```python
# storj 示例 (head=最新)
                     open    high     low   close
time
2026-06-25 04:35:00  1762.0  1766.3  1759.2  1764.7   ← 最新
2026-06-25 04:30:00  1758.5  1762.8  1757.1  1761.9
...
2026-06-21 17:20:00  1727.1  1727.1  1725.7  1726.9   ← 最旧
```

### 完整流水线

```
原始CSV → DataManager.rawdata
    ↓ (逐行)
DriverProcessor 构建 storj
    ↓ queue.put(storj)
StrategyManager:
  1. signalAlg.run() → signal
  2. orderAlg.run() → orderlist
    ↓ oderqueue.put(orderlist)
OrderManager:
  1. processOrder() 开/平仓
  2. 更新 orderpool + account
    ↓
同步到 DataManager
```

### 关键数据字典

| 变量 | 类型 | 位置 | 说明 |
|------|------|------|------|
| `storj` | DataFrame | DataManager | 最新N根K线(倒序) |
| `signal` | list[int] | DataManager | 信号历史 |
| `indicators` | dict | DataManager | 主窗口指标 |
| `orderpool` | dict | DataManager/OM | 订单池 {uid:OrderInstance} |
| `orderframe` | DataFrame | DataManager/OM | 订单历史 |
| `account` | dict | DataManager | 账户 {asset,profit,...} |

---

## 六、各模块说明

### 6.1 引擎层 (src/engine/)

#### DriverProcessor (driver.py)

**职责**: 数据推送引擎。

| 模式 | 数据源 | 驱动方式 |
|------|--------|----------|
| `backtest` | CSV 文件 | `for 循环 + queue.join()` |
| `realtime` | 交易所 API | `threading.Timer` 递归 |

```python
# 回测核心逻辑
for index, row in dataset.iterrows():
    self.dataM.storj = pd.concat([new_data, storj])  # 新数据插头
    self.queue.put(self.dataM.storj)                  # 推给策略
    self.queue.join()                                 # 等策略处理完
```

#### StrategyManager (strategy.py)

**职责**: 策略计算线程，执行 signalAlg + orderAlg。

```python
def _run_algorithms(self):
    signal, ind, w2 = signalAlg.run(parapoll)    # 计算信号
    parapoll['c_signal'] = signal
    orderlist = orderAlg.run(parapoll)            # 生成订单
    if orderlist:
        self.oderqueue.put(orderlist)             # 推给 OM
    return signal, ind, w2
```

#### OrderManager (order_manager.py)

**职责**: 订单执行线程。

```python
def _process_order(self, forder):
    if oaction == 'OPEN':
        self.orderpool[uid] = OrderInstance(forder)
        ret = self.orderpool[uid].inc_position(forder)
    elif oaction == 'CLOSE':
        profit, ret = self.orderpool[uid].dec_position(forder)
        account['asset'] += profit
```

#### OrderInstance (order_instance.py)

**职责**: 单个订单生命周期。

```python
# 开多(LONG): 盈利 = (当前价 - 均价) × 数量
# 开空(SHORT): 盈利 = (均价 - 当前价) × 数量
if self.side == 'LONG':
    self.closeprofit = (tick_price - self.aveprice) * close_size
```

### 6.2 数据层 (src/data/)

#### DataManager

全局数据中心，管理所有运行时共享状态：storj、signal、indicators、account、orderpool。

#### MarketClient

从 Binance 获取K线：

```python
client = MarketClient(dex_name='binance')
df = client.get_price_v1(code='ETHUSDT', count=100, frequency='5m')
```

### 6.3 交易所适配层 (src/broker/)

```
BrokerBase (抽象接口)
    ├── BacktestBroker  (回测模拟，立即成交)
    └── BinanceBroker   (实盘，API挂单)
```

### 6.4 状态管理 (src/server/)

ATSServer: 每10秒自动保存状态到 JSON，支持崩溃恢复。

---

## 七、策略开发指南

只需修改 `strategies/` 下的两个文件。

### 7.1 signalAlg.py 接口

```python
def run(parapoll) -> (signal: int, indicators: dict, indicators_w2: dict)
```

| 入参 | 类型 | 说明 |
|------|------|------|
| `dataset` | DataFrame | 最新K线(倒序, head=最新) |
| `indicatorsdic` | dict | 主窗口指标历史 `{'ind1':[]}` |

| 返回 | 类型 | 说明 |
|------|------|------|
| `signal` | int | 1=看多, -1=看空, 0=无操作 |
| `cur_indicators` | dict | 本K线指标值 `{'ind1':val}` |

### 7.2 orderAlg.py 接口

```python
def run(parapoll) -> list[dict]
```

| 入参 | 类型 | 说明 |
|------|------|------|
| `c_signal` | int | 当前信号 |
| `orderpool` | dict | 当前持仓 {uid: OrderInstance} |
| `orderaccount` | dict | 账户 {asset: float} |

订单格式:
```python
{
    'uid': str,      # 唯一ID
    'code': 'ETH-USD',# 交易对
    'oaction': str,   # OPEN / CLOSE
    'oside': str,     # LONG / SHORT
    'otype': 'MARKET',# MARKET / LIMIT
    'osize': str,     # 数量
    'oprice': str,    # 价格
}
```

### 7.3 双均线策略示例

```
signalAlg:
  计算 ma10(快线) 和 ma30(慢线)
  ma10 上穿 ma30 → signal=1 (金叉，开多)
  ma10 下穿 ma30 → signal=-1 (死叉，开空)
  其他 → signal=0 (不动)

orderAlg:
  signal=1: 平空(如有) → 开多 0.01 ETH
  signal=-1: 平多(如有) → 开空 0.01 ETH
  signal=0: 持仓不动
```

---

## 八、回测流程逐步骤详解

### 第1步: 加载数据
```python
df = pd.read_csv(csv_path)
df.set_index('time', inplace=True)
```

### 第2步: 初始化
```python
balance = 100.0; order_pool = {}
indicators = {'ind1':[], ..., 'ind10':[]}
```

### 第3步: 逐根K线循环
```python
for idx, row in df.iterrows():
    storj = build_storj(idx, row)            # 构建倒序K线
    signal, c = signalAlg.run({'dataset':storj})  # 计算信号
    orders = orderAlg.run({'c_signal':signal})    # 生成订单
    for o in orders:                          # 执行订单
        if o['oaction']=='OPEN': create_position(o)
        else: balance += close_position(o)
    equity = balance + floating_pl             # 当前权益
    equity_curve.append((idx, equity))         # 记录权益
```

### 第4步: 计算统计
```
总盈亏 = final_equity - initial_balance
收益率 = 总盈亏 / 初始资金 × 100%
最大回撤 = max(峰值 - 当前权益)
夏普比率 = mean(收益)/std(收益) × √年化K线数
胜率 = 盈利次数 / 总交易次数
盈亏比 = 平均盈利 / 平均亏损
```

### 第5~7步: 保存数据 → 生成HTML报告 → 手机查看

---

## 九、工具脚本

### fetch_data.py
```bash
python scripts/fetch_data.py --symbol ETHUSDT --interval 5m --days 1
```
自动分批拉取（Binance限制每次1000根），直到覆盖整个时间范围。

### run_backtest.py
```bash
python run_backtest.py --data data/xxx.csv --balance 100
```
输出 JSON + trades.csv + equity.csv。

### report_generator.py
```bash
python scripts/report_generator.py --data-file data/xxx.csv --report-json reports/xxx.json --trades-csv reports/xxx.csv --equity-csv reports/xxx.csv
```
输出 Plotly 交互式 HTML 报告到 `reports/bt_xxx/`。

---

## 十、MCP Skills 接口

### hjats-data
| Tool | 功能 |
|------|------|
| `fetch_klines` | 下载 Binance K线到 data/ |
| `list_data_files` | 列出 CSV 数据 |

### hjats-backtest
| Tool | 功能 |
|------|------|
| `run_backtest` | 回测 → 自动生成 HTML 报告 |
| `list_csv_data` | 列出所有可用数据 |
| `list_reports` | 列出 reports/ 下的报告 |

配置位置: `~/.local/share/code-server/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

---

## 十一、手机查看报告

```bash
# 启动 HTTP 服务
python3 -m http.server 8080 --directory reports/
# 手机连同一WiFi，访问 http://服务器IP:8080/bt_xxx/report.html
```

或用小龙虾等工具配置指向 `reports/bt_xxx/report.html`。

---

## 十二、配置文件

### config.ini
```ini
[AlgPara]
Code = ETH-USD
Frequency = 15MINS
nHistoryCounts = 100
StrategyName = MyStrategy

[Dexinfo]
dexname = binance
```

### .env (API密钥，不要提交到Git)
```
BINANCE_API_KEY=xxx
BINANCE_API_SECRET=xxx
```

---

## 十三、环境变量与安全

| 信息 | 位置 | 注意事项 |
|------|------|----------|
| API Key | `.env` 或环境变量 | **不要提交到Git** |
| MongoDB密码 | `config.ini` | 建议改用环境变量 |
| 策略参数 | `config.ini` | 可提交到Git |

`.gitignore` 已忽略: `.env`, `data/*.csv`, `logs/`, `reports/`, `runninghistory/`

---

## API 速查

### 命令行

| 命令 | 功能 |
|------|------|
| `python scripts/fetch_data.py --symbol ETHUSDT --interval 5m --days 1` | 下载数据 |
| `python run_backtest.py --data data/xxx.csv --balance 100` | 运行回测 |
| `python scripts/report_generator.py ...` | 生成报告 |
| `python -m http.server 8080 --directory reports/` | HTTP查看报告 |

### Python API

| 类 | 关键方法 |
|----|----------|
| `DriverProcessor` | `run()`, `stop()` |
| `StrategyManager` | `run()` |
| `OrderManager` | `run()` |
| `OrderInstance` | `inc_position()`, `dec_position()` |
| `DataManager` | `local_init()`, `remote_init()` |
| `MarketClient` | `get_price_v1()` |

### 策略接口

```python
signalAlg.run({'dataset':df, 'indicatorsdic':ind}) → (signal, indicators, w2)
orderAlg.run({'c_signal':signal, 'orderpool':pool, 'orderaccount':acct}) → [orders]
```

---

*最后更新: 2026-06-26*