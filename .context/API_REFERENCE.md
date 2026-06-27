# HJATS API 参考

> 快速查找核心类、方法和参数

---

## 命令行接口

### 数据下载
```bash
python scripts/fetch_data.py --symbol ETHUSDT --interval 5m --days 1
python scripts/fetch_data.py --symbol BTCUSDT --interval 15m --start 2026-06-01 --end 2026-06-24
```

### 回测运行
```bash
# 简化版（推荐）
python run_backtest.py --data data/xxx.csv --balance 100

# 完整版
python run.py   # 修改 run.py 中 Runtype='1'
```

### 报告生成
```bash
python scripts/report_generator.py \
    --data-file data/xxx.csv \
    --report-json reports/xxx.json \
    --trades-csv reports/xxx_trades.csv \
    --equity-csv reports/xxx_equity.csv
```

### 实盘状态查看
```bash
python scripts/live_status.py          # 完整状态
python scripts/live_status.py --json   # JSON 格式
python scripts/live_status.py --watch  # 持续监控
```

### 手机查看报告
```bash
python3 -m http.server 8080 --directory reports/
# 手机访问: http://服务器IP:8080/bt_xxx/report.html
```

---

## Python API

### `src.engine.driver.DriverProcessor`

三线程管道的数据驱动端。

```python
dp = DriverProcessor(
    thread_id=1, name='DP1',
    q_id=1, q_name='Q1', q_length=1,
    dp_type='backtest',        # 'backtest' | 'realtime'
    msg_queue=msg_queue,
    speed=0,                   # 0=回测最快, >0=实盘间隔秒
    data_manager=dm1,
    visualization=True,
)
dp.start()    # 启动线程
dp.stop()     # 停止线程
dp.join()     # 等待结束
```

**内部队列：** `self.queue` (queue.Queue) — 输出 storj 数据包

### `src.engine.strategy.StrategyManager`

三线程管道的策略执行端。

```python
sm = StrategyManager(
    strategy_id=2, strategy_name='ST1',
    dp_core=dp1,               # 引用 DriverProcessor
)
sm.start()
```

**内部队列：** `self.queue` (来自DP)，`self.oderqueue` (输出给OM)

### `src.engine.order_manager.OrderManager`

三线程管道的订单执行端。

```python
om = OrderManager(
    order_manager_id=3, order_manager_name='OM1',
    st_manager=sm,
    dp_core=dp1,
)
om.start()
```

### `src.engine.order_instance.OrderInstance`

持仓管理。

```python
oi = OrderInstance(
    uid='ma_long_1',
    code='ETH-USD',
    side='LONG',        # LONG / SHORT
    size=0.01,
    open_price=1900.0,
    tick_price=1900.0,
)
oi.inc_position(size, price)   # 加仓
oi.dec_position(size, price)   # 减仓 → 返回盈利
```

### `src.data.datamanager.DataManager`

数据管理。

```python
dm = DataManager()
dm.local_init(csv_path, para)    # 从本地CSV加载
dm.remote_init(para)             # 从远程（MongoDB）加载
```

### `src.data.market.MarketClient`

Binance API 封装。

```python
client = MarketClient(dex_name='binance')
df = client.get_price_v1(
    code='ETHUSDT',
    count=1000,           # 最多1000根
    frequency='5m',
    stop='2026-06-25 00:00:00',
)
# 返回 DataFrame, columns: ['open','high','low','close','volume']
```

### `src.data.db_connection.ATSDBClient`

MongoDB 连接。

```python
db = ATSDBClient()
# 配置在 config.ini [DataBase] 段
```

### `src.server.ats_server.ATSServer`

状态管理服务器。

```python
server = ATSServer(if_autorun=0, data_manager=dm1)
server.run()                # 主循环
server.stop()               # 停止
server.msg_queue            # 消息队列
```

### `src.broker.base.BrokerBase`

交易所适配抽象基类。

| 实现 | 文件 | 说明 |
|------|------|------|
| `BacktestBroker` | `src/broker/backtest_broker.py` | 回测模拟，按收盘价成交 |
| `BinanceBroker` | `src/broker/binance_broker.py` | 实盘，接入Binance API |

---

## 策略接口（用户需要实现）

### 信号算法
```python
# 文件位置: strategies/signalAlg.py
def run(parapoll) -> tuple:
    """
    Args:
        parapoll['dataset']: DataFrame (倒序K线, head=最新)
        parapoll['indicatorsdic']: dict (指标历史)
    Returns:
        signal: int        1=看多, -1=看空, 0=持仓
        indicators: dict   主窗口指标
        indicators_w2: dict 副窗口指标
    """
```

### 订单算法
```python
# 文件位置: strategies/orderAlg.py
def run(parapoll) -> list:
    """
    Args:
        parapoll['c_signal']: int         当前信号
        parapoll['orderpool']: dict       订单池 {uid: OrderInstance}
        parapoll['orderaccount']: dict    账户状态 {'asset': float}
        parapoll['dataset']: DataFrame    当前K线
    Returns:
        orderlist: list[dict]             订单列表
    """
```

---

## MCP Skills 接口

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
