# HJATS 常用命令速查

> 快速参考 — 所有命令在 HJATS 项目根目录执行

---

## 环境管理

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install pytest pytest-cov flake8 mypy
```

## 数据下载

```bash
# 基本用法
python scripts/fetch_data.py --symbol ETHUSDT --interval 5m --days 1

# 指定日期范围
python scripts/fetch_data.py --symbol BTCUSDT --interval 15m --start 2026-06-01 --end 2026-06-24

# 最近7天
python scripts/fetch_data.py --symbol ETHUSDT --interval 1h --days 7

# 可用的周期: 1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d
```

## 回测

```bash
# 简化回测（推荐）
python run_backtest.py --data data/2026-06-24_2026-06-25_ETHUSDT_5m.csv --balance 100

# 简化回测（更多资金）
python run_backtest.py --data data/xxx.csv --balance 1000

# 完整回测（三线程引擎）
# 修改 run.py 中的 Runtype='1'
python run.py
```

## 报告生成

```bash
# 完整命令
python scripts/report_generator.py \
    --data-file data/xxx.csv \
    --report-json backtest_report_xxx.json \
    --trades-csv backtest_report_xxx_trades.csv \
    --equity-csv backtest_report_xxx_equity.csv

# 输出到 reports/bt_xxx/report.html
```

## 查看报告

```bash
# 启动 HTTP 服务（手机可看）
python3 -m http.server 8080 --directory reports/

# 浏览器打开
# http://localhost:8080/bt_xxx/report.html
```

## 实盘

```bash
# 启动实盘（需要配置 .env API密钥）
# 修改 run.py 中的 Runtype='2'
python run.py

# 查看实盘状态
python scripts/live_status.py
python scripts/live_status.py --watch   # 持续监控
```

## 后台运行

```bash
# 使用 tmux
tmux new -s hjats
python scripts/fetch_data.py --symbol ETHUSDT --interval 5m --days 7
# Ctrl+B, D 分离

# 或使用 bin/tmux-runner.sh
bash bin/tmux-runner.sh

# 使用 nohup
nohup python run.py > output.log 2>&1 &
```

## Git 操作

```bash
# 初始化（如果尚未）
git init
git add .
git commit -m "v2.0.0: 初始提交 - 三线程管道重构"

# 检查状态
git status
git diff

# 忽略检查
git check-ignore .env
```

## 测试（计划中）

```bash
# 运行所有测试
pytest tests/

# 带覆盖率
pytest tests/ --cov=src --cov-report=html

# 运行特定测试
pytest tests/test_signal.py -v
```

## 代码质量

```bash
# 语法检查
flake8 src/ strategies/ scripts/

# 类型检查
mypy src/ --ignore-missing-imports

# 代码格式化
black src/ strategies/ scripts/
```
