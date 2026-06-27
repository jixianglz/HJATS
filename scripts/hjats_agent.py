#!/usr/bin/env python3
"""
HJATS AI Agent 协同接口

让不同 AI agent（Cline、OpenClaw 等）通过命令行协作：
  OpenClaw 运行实盘引擎 → Cline 查看状态/分析结果

用法:
  python3 scripts/hjats_agent.py status        # 查看实盘状态
  python3 scripts/hjats_agent.py start-live    # 启动实盘引擎（后台）
  python3 scripts/hjats_agent.py stop-live     # 停止实盘引擎
  python3 scripts/hjats_agent.py list-data     # 列出可用数据
  python3 scripts/hjats_agent.py list-reports  # 列出回测报告
  python3 scripts/hjats_agent.py backtest <data> --balance 100
  python3 scripts/hjats_agent.py fetch ETHUSDT 5m 1
"""
import argparse
import json
import os
import sys
import subprocess
from datetime import datetime

HJATS_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HJATS_PATH)


def cmd_status():
    """查看实盘状态"""
    status_file = "/tmp/live_status.json"
    if not os.path.exists(status_file):
        print(json.dumps({"error": "No live status. Engine not running."}, indent=2))
        return 1
    with open(status_file) as f:
        data = json.load(f)
    out = {
        "timestamp": data.get("timestamp"),
        "running": data.get("engine_running", False),
        "paused": data.get("engine_paused", False),
        "account": {
            "balance": data["account"]["balance"],
            "equity": data["account"]["equity"],
            "daily_pnl": data["account"]["daily_pnl"],
        },
        "position": data["position"],
        "signal": {"value": data["signal"]["value"]},
        "engine": {
            "strategy_ok": data["engine"]["strategy_ok"],
            "monitor_ok": data["engine"]["monitor_ok"],
            "strategy_last": data["engine"]["strategy_last_run"],
            "monitor_last": data["engine"]["monitor_last_run"],
            "errors": data["engine"]["errors"][-3:],
        },
        "daily": data["daily"],
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def cmd_start_live():
    """后台启动实盘引擎"""
    logfile = "/tmp/live_engine.log"
    proc = subprocess.Popen(
        [sys.executable, "-m", "src.engine.live_engine"],
        cwd=HJATS_PATH,
        stdout=open(logfile, 'w'),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    print(json.dumps({
        "action": "start_live", "pid": proc.pid, "log": logfile,
        "status_cmd": "python3 scripts/hjats_agent.py status",
    }, indent=2))
    return 0


def cmd_stop_live():
    """停止实盘引擎"""
    import signal
    result = subprocess.run(["pgrep", "-f", "src.engine.live_engine"],
                          capture_output=True, text=True)
    pids = result.stdout.strip().split('\n')
    killed = 0
    for pid in pids:
        if pid:
            try:
                os.kill(int(pid), signal.SIGTERM)
                killed += 1
            except ProcessLookupError:
                pass
    print(json.dumps({"action": "stop_live", "killed": killed}, indent=2))
    return 0


def cmd_list_data():
    """列出可用历史数据"""
    data_dir = os.path.join(HJATS_PATH, "data")
    files = []
    if os.path.exists(data_dir):
        for f in sorted(os.listdir(data_dir)):
            if f.endswith('.csv'):
                path = os.path.join(data_dir, f)
                files.append({"file": f, "size_kb": round(os.path.getsize(path)/1024, 1)})
    print(json.dumps({"data_files": files}, indent=2))
    return 0


def cmd_list_reports():
    """列出回测报告"""
    reports_dir = os.path.join(HJATS_PATH, "reports")
    dirs = []
    if os.path.exists(reports_dir):
        for d in sorted(os.listdir(reports_dir)):
            path = os.path.join(reports_dir, d)
            if os.path.isdir(path) and d.startswith('bt_'):
                report_html = os.path.join(path, "report.html")
                dirs.append({"session": d, "has_report": os.path.exists(report_html)})
    print(json.dumps({"reports": dirs}, indent=2))
    return 0


def cmd_backtest(data_file, balance):
    """运行回测"""
    if not os.path.exists(data_file):
        alt = os.path.join(HJATS_PATH, "data", data_file)
        if os.path.exists(alt):
            data_file = alt
        else:
            print(json.dumps({"error": f"Data not found: {data_file}"}))
            return 1
    result = subprocess.run(
        [sys.executable, "run_backtest.py", "--data", data_file,
         "--balance", str(balance)],
        cwd=HJATS_PATH, capture_output=True, text=True)
    report_files = [f for f in os.listdir(HJATS_PATH)
                    if f.startswith("backtest_report_") and f.endswith(".json")]
    latest = max(report_files, key=lambda f: os.path.getmtime(
        os.path.join(HJATS_PATH, f))) if report_files else None
    out = {"exit_code": result.returncode, "report_file": latest,
           "stdout": result.stdout.strip().split('\n')[-15:]}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return result.returncode


def cmd_fetch(symbol, interval, days):
    """下载数据"""
    result = subprocess.run(
        [sys.executable, "scripts/fetch_data.py",
         "--symbol", symbol, "--interval", interval, "--days", str(days)],
        cwd=HJATS_PATH, capture_output=True, text=True)
    print(json.dumps({"exit_code": result.returncode,
        "stdout": result.stdout.strip().split('\n')}, indent=2))
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="HJATS AI Agent 协同接口")
    parser.add_argument("command", choices=[
        "status", "start-live", "stop-live",
        "list-data", "list-reports", "backtest", "fetch"])
    parser.add_argument("args", nargs="*")
    a = parser.parse_args()
    if a.command == "status": sys.exit(cmd_status())
    elif a.command == "start-live": sys.exit(cmd_start_live())
    elif a.command == "stop-live": sys.exit(cmd_stop_live())
    elif a.command == "list-data": sys.exit(cmd_list_data())
    elif a.command == "list-reports": sys.exit(cmd_list_reports())
    elif a.command == "backtest":
        if len(a.args) < 1:
            print("Usage: hjats_agent.py backtest <data> [--balance N]"); sys.exit(1)
        bal = 100
        if len(a.args) >= 3 and a.args[1] == '--balance':
            bal = float(a.args[2])
        sys.exit(cmd_backtest(a.args[0], bal))
    elif a.command == "fetch":
        if len(a.args) < 3:
            print("Usage: hjats_agent.py fetch <sym> <interval> <days>"); sys.exit(1)
        sys.exit(cmd_fetch(a.args[0], a.args[1], int(a.args[2])))


if __name__ == "__main__":
    main()