# HJATS — 项目概要

> **H**igh-frequency **J**ik **A**utomated **T**rading **S**ystem
> 版本: **v2.0.0** | 最后更新: 2026-06-27

## 一句话定位

基于 Python 的多线程自动化交易框架，支持 **回测（Backtest）** 和 **实盘（Realtime）** 两种模式，接入 Binance U本位合约。

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.8+ |
| 并发模型 | threading + queue.Queue **三线程管道** |
| 数据存储 | CSV 文件（本地）/ MongoDB（远程） |
| 可视化 | Plotly（HTML报告）/ matplotlib（实时GUI） |
| 交易所 | Binance Futures（binance-futures-connector） |
| AI集成 | MCP Skills 协议 |

## 核心能力

- ✅ 从 Binance 分批下载历史K线数据（自动处理1000根限制）
- ✅ 使用历史数据回测策略（逐根K线模拟）
- ✅ 生成 Plotly 交互式 HTML 报告（含K线、买卖点、收益曲线、指标）
- ✅ 三线程管道引擎（DriverProcessor → StrategyManager → OrderManager）
- ✅ 手机端查看报告（HTTP服务）
- ✅ MCP AI 接口支持

## 目录结构

```
HJATS/
├── run.py                   # 框架入口（回测/实盘）
├── run_backtest.py          # 独立回测运行器（简化版）
├── requirements.txt         # Python 依赖
├── .env / .env.example      # API Key 配置
├── src/                     # 框架核心代码（v2新架构）
│   ├── engine/              # 三线程引擎
│   │   ├── driver.py        #   DriverProcessor (数据驱动)
│   │   ├── strategy.py      #   StrategyManager (策略执行)
│   │   ├── order_manager.py #   OrderManager (订单管理)
│   │   ├── order_instance.py#   OrderInstance (订单实例)
│   │   └── live_engine.py   #   LiveEngine (实盘引擎)
│   ├── data/                # 数据层
│   │   ├── datamanager.py   #   DataManager (数据调度)
│   │   ├── market.py        #   MarketClient (Binance API)
│   │   └── db_connection.py #   ATSDBClient (MongoDB)
│   ├── broker/              # 交易所适配
│   │   ├── base.py          #   BrokerBase (抽象接口)
│   │   ├── backtest_broker.py # 回测模拟
│   │   ├── binance_broker.py  # 实盘接口
│   │   └── account.py       #   AccountClient (API管理)
│   ├── server/              # 状态管理
│   │   └── ats_server.py    #   ATSServer
│   ├── visualization/       # 可视化
│   │   └── gui.py           #   matplotlib 显示
│   └── utils/               # 工具
│       ├── constants.py     #   常量
│       ├── helpers.py       #   工具函数
│       └── logger.py        #   日志
├── strategies/              # 用户策略（可热插拔）
│   ├── signalAlg.py         #   信号算法（双均线交叉）
│   ├── orderAlg.py          #   订单算法
│   ├── indicators.py        #   技术指标库
│   └── config.ini           #   策略配置
├── scripts/                 # 工具脚本
│   ├── fetch_data.py        #   数据下载
│   ├── report_generator.py  #   报告生成
│   └── live_status.py       #   实盘状态查看
├── data/                    # K线CSV数据
├── reports/                 # 回测报告（每会话独立目录）
├── modules_github/          # 旧版遗留代码（保留参考）
├── bin/tmux-runner.sh       # 后台命令执行
├── logs/                    # 运行日志
├── .context/                # ← 项目上下文（本目录）
└── .gitignore
```

## 策略接口（用户需实现）

```python
# 信号算法 — 输入K线数据，输出交易信号
signalAlg.run({'dataset': df, 'indicatorsdic': ind})
    → (signal: int, indicators: dict, indicators_w2: dict)

# 订单算法 — 输入信号，输出订单列表
orderAlg.run({'c_signal': signal, 'orderpool': pool, 'orderaccount': acct})
    → [{'uid','code','oaction','oside','otype','osize','oprice'}, ...]
```

## 当前策略

**双均线交叉策略（MA Crossover）**
- 快线: MA10 / 慢线: MA30
- 金叉（MA10↑MA30）→ signal=1 → 开多
- 死叉（MA10↓MA30）→ signal=-1 → 开空
- 其他 → signal=0 → 持仓不动
- 仓位: 固定 0.01 ETH（适配 $100 级别资金）
