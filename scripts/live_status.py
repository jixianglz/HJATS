#!/usr/bin/env python3
"""
实盘状态查看工具

用法:
    python scripts/live_status.py          # 查看完整状态
    python scripts/live_status.py --json   # 输出 JSON 格式
    python scripts/live_status.py --watch  # 持续监控（每5秒刷新）
"""
import argparse
import json
import os
import sys
import time

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine.live_status import LiveStatus


def main():
    parser = argparse.ArgumentParser(description="查看实盘运行状态")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--watch", action="store_true", help="持续监控（每5秒刷新）")
    parser.add_argument("--interval", type=int, default=5, help="监控刷新间隔（秒，默认5）")
    args = parser.parse_args()

    if args.watch:
        try:
            while True:
                os.system("clear" if os.name == "posix" else "cls")
                status = LiveStatus()
                summary = status.get_summary()
                print(summary)
                print(f"\n  每 {args.interval} 秒刷新一次 | Ctrl+C 退出")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n  已退出")
    else:
        status = LiveStatus()
        if args.json:
            print(json.dumps(status.get(), indent=2, ensure_ascii=False))
        else:
            print(status.get_summary())


if __name__ == "__main__":
    main()
