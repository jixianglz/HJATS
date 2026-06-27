# HJATS 当前状態

# HJATS 当前状态

> 最后更新: 2026-06-27
> 维护者: AI 自动更新

## 总体进度

```
src/engine/     ████████████░░░  80%  ✅ 核心完成，需完善
src/data/       ██████████████░  90%  ✅ 基本完成
src/broker/     ██████████░░░░░  65%  ⚠️ 回测Broker完成，实盘需测试
src/server/     ████████████░░░  80%  ✅ 基本完成
src/utils/      ██████████████░  90%  ✅ 基本完成
strategies/     ████████████░░░  80%  ✅ 策略工作，可扩展更多
scripts/        ██████████████░  90%  ✅ 基本完成
reports/        ██████████████░  90%  ✅ 报告生成完善
tests/          ░░░░░░░░░░░░░░░   0%  ❌ 尚未开始
```

## 模块详细状态

### ✅ 已完成的模块

| 模块 | 文件 | 状态 | 说明 |
|------|------|------|------|
| 入口 | `run.py` | ✅ 稳定 | 支持回测/实盘模式切换 |
| 回测运行器 | `run_backtest.py` | ✅ 稳定 | 独立简化版回测引擎 |
| DP引擎 | `src/engine/driver.py` | ✅ 稳定 | 回测/实盘双模式 |
| SM引擎 | `src/engine/strategy.py` | ✅ 稳定 | 策略调度正常 |
| OM引擎 | `src/engine/order_manager.py` | ✅ 稳定 | 订单执行正常 |
| OrderInstance | `src/engine/order_instance.py` | ✅ 稳定 | 持仓管理 |
| DataManager | `src/data/datamanager.py` | ✅ 稳定 | 数据调度 |
| MarketClient | `src/data/market.py` | ✅ 稳定 | Binance API封装 |
| 信号算法 | `strategies/signalAlg.py` | ✅ 稳定 | 双均线交叉 |
| 订单算法 | `strategies/orderAlg.py` | ✅ 稳定 | 多空切换 |
| 数据下载 | `scripts/fetch_data.py` | ✅ 稳定 | 自动分批下载 |
| 报告生成 | `scripts/report_generator.py` | ✅ 稳定 | Plotly HTML |
| 指标库 | `strategies/indicators.py` | ✅ 稳定 | SMA, ROC, KST, BreakOut |

### ⚠️ 部分完成的模块

| 模块 | 文件 | 状态 | 待完成 |
|------|------|------|--------|
| 实盘引擎 | `src/engine/live_engine.py` | 🔄 开发中 | 风控监控需要强化 |
| BinanceBroker | `src/broker/binance_broker.py` | 🔄 需测试 | 实盘接口未充分验证 |
| ATSServer | `src/server/ats_server.py` | 🔄 需强化 | 状态持久化不完整 |
| 账号管理 | `src/broker/account.py` | 🔄 需测试 | API Key管理 |
| DB连接 | `src/data/db_connection.py` | 🔄 需测试 | MongoDB连接 |

### ❌ 未开始的模块

| 模块 | 说明 | 优先级 |
|------|------|--------|
| `tests/` | 单元测试/集成测试 | 🔴 高 |
| GUI可视化 | `src/visualization/gui.py` | 🟡 中 |
| 更多策略 | 其他信号算法 | 🟢 低 |
| 风险管理系统 | 止损/仓位管理 | 🟡 中 |

## 已知问题 & 技术债务

| # | 问题 | 严重度 | 备注 |
|---|------|--------|------|
| 1 | Git仓库无提交记录 | 🟢 低 | ✅ 已提交 |
| 2 | `modules_github/` 旧版代码与新 `src/` 并存 | 🟡 中 | 架构不一致，旧版可删除 |
| 3 | `Inittxt.txt` 为空文件 | 🟢 低 | 可删除或填充内容 |
| 4 | 缺少单元测试 | 🔴 高 | 需要为所有模块编写测试 |
| 5 | 实盘未经过充分测试 | 🔴 高 | 需要模拟盘验证 |
| 6 | config.ini 含明文密码 | 🔴 高 | MongoDB密码应改用环境变量 |
| 7 | 策略参数硬编码（0.01 ETH） | 🟡 中 | 应由配置文件控制 |
| 8 | 日志文件 `modules_github/log.log` 在仓库中 | 🟢 低 | 应清理并加入gitignore |
| 9 | `.env` 已提交到Git？检查gitignore | 🟡 中 | 确保密钥不被提交 |

## 当前 Sprint（进行中）

> 当前焦点：重建项目上下文，确保 AI 工具能快速理解项目

- [x] 创建 `.context/` 目录和所有文档文件
- [x] 初始化 Git 仓库并提交当前代码
- [ ] 清理 `Inittxt.txt` 和空文件
- [ ] 检查 `.env` 是否在 gitignore 中安全
- [x] 规划测试框架
