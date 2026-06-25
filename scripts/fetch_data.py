#!/usr/bin/env python3
"""
数据获取工具 - 从 Binance 下载历史 K 线数据并保存为 CSV

用法:
    # 下载昨日的 ETH 5分钟K线
    python scripts/fetch_data.py --symbol ETHUSDT --interval 5m --days 1

    # 下载指定日期范围的 BTC 15分钟K线
    python scripts/fetch_data.py --symbol BTCUSDT --interval 15m --start 2026-06-01 --end 2026-06-24

    # 下载最近 7 天的数据
    python scripts/fetch_data.py --symbol ETHUSDT --interval 5m --days 7
"""
import argparse
import os
import sys

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timedelta, timezone

from src.data.market import MarketClient
from src.utils.helpers import print_colored


def download_data(symbol: str, interval: str, days: int = None,
                  start_date: str = None, end_date: str = None,
                  output_dir: str = "data") -> str:
    """
    下载历史 K 线数据并保存为 CSV（自动分批下载，不限数量）

    Args:
        symbol: 交易对，如 "ETHUSDT", "BTCUSDT"
        interval: K线周期，如 "1m", "5m", "15m", "1h", "4h", "1d"
        days: 下载最近 N 天数据
        start_date: 开始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"（默认今天）
        output_dir: 输出目录

    Returns:
        保存的文件路径
    """
    client = MarketClient(dex_name='binance')

    # ---- 计算时间范围（统一用 UTC 时区） ----
    if days:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
    elif start_date:
        start = pd.Timestamp(start_date).tz_localize('UTC')
        end = pd.Timestamp(end_date).tz_localize('UTC') if end_date else pd.Timestamp.now(tz='UTC')
    else:
        # 默认昨天全天
        end = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        start = end - timedelta(days=1)

    start_str = start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end.strftime("%Y-%m-%d %H:%M:%S")

    print_colored(f"下载数据: {symbol} @ {interval}", bg_color='blue')
    print_colored(f"  时间范围: {start_str} -> {end_str}", bg_color='blue')

    # ---- 分批下载（Binance API 每次最多 1000 根K线） ----
    all_data = []

    # 统一使用 offset-naive UTC 时间戳做比较
    start_naive = pd.Timestamp(start).tz_localize(None)
    current_end_naive = pd.Timestamp(end).tz_localize(None)

    while current_end_naive > start_naive:
        stop_str = current_end_naive.strftime("%Y-%m-%d %H:%M:%S")
        res = client.get_price_v1(
            code=symbol,
            count=1000,
            frequency=interval,
            stop=stop_str,
        )
        if res is None or len(res) == 0:
            break

        all_data.append(res)
        # 用本次返回的最早K线时间作为下次拉取的结束点
        current_end_naive = res.index[0]

        if len(all_data) > 100:  # 防无限循环（最多10万根K线）
            print("已达最大下载量限制")
            break

    if not all_data:
        print_colored("未获取到数据!", bg_color='red')
        return ""

    df = pd.concat(all_data).sort_index().drop_duplicates()

    # ---- 保存 CSV ----
    os.makedirs(output_dir, exist_ok=True)
    filename = (
        f"{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}"
        f"_{symbol}_{interval}.csv"
    )
    filepath = os.path.join(output_dir, filename)

    df.to_csv(filepath)
    print_colored(f"成功保存: {filepath}", bg_color='green')
    print_colored(f"  共 {len(df)} 根K线", bg_color='green')
    print_colored(f"  时间: {df.index[0]} ~ {df.index[-1]}", bg_color='green')

    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="下载 Binance 历史K线数据（自动分批）"
    )
    parser.add_argument(
        "--symbol", default="ETHUSDT",
        help="交易对 (默认: ETHUSDT)"
    )
    parser.add_argument(
        "--interval", default="5m",
        help="K线周期 (默认: 5m)"
    )
    parser.add_argument(
        "--days", type=int, default=1,
        help="下载最近 N 天数据"
    )
    parser.add_argument(
        "--start", help="开始日期 YYYY-MM-DD"
    )
    parser.add_argument(
        "--end", help="结束日期 YYYY-MM-DD"
    )
    parser.add_argument(
        "--output", default="data",
        help="输出目录 (默认: data/)"
    )

    args = parser.parse_args()

    if args.start and args.days:
        print_colored("错误: --days 和 --start/--end 不能同时使用", bg_color='red')
        sys.exit(1)

    filepath = download_data(
        symbol=args.symbol,
        interval=args.interval,
        days=args.days if not args.start else None,
        start_date=args.start,
        end_date=args.end,
        output_dir=args.output,
    )

    if filepath:
        print(f"\n回测时使用该数据:")
        print(f"  python run.py --data {filepath}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()