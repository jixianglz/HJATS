#!/usr/bin/env python3
"""
回测运行器 - 加载 CSV 数据，执行策略，输出回测报告

用法:
    python run_backtest.py --data data/2026-06-24_2026-06-25_ETHUSDT_5m.csv --balance 100
"""
import argparse
import os
import sys
import time
import json
from datetime import datetime

import pandas as pd
import numpy as np

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.helpers import print_colored
from strategies import signalAlg, orderAlg


# ============================================================
# 简化版 OrderInstance（回测专用）
# ============================================================
class OrderInstance:
    """订单实例 - 管理持仓、盈亏"""

    def __init__(self, uid, code, side, size, open_price, tick_price):
        self.uid = uid
        self.code = code
        self.side = side  # LONG / SHORT
        self.size = size
        self.open_price = open_price
        self.aveprice = open_price
        self.totalvalue = size * tick_price
        self.closeprofit = 0.0
        self.floatingPL = 0.0
        self.status = "open"

    def inc_position(self, size, tick_price):
        """加仓"""
        self.totalvalue += size * tick_price
        self.size += size
        self.aveprice = self.totalvalue / self.size
        self.open_price = tick_price

    def dec_position(self, size, tick_price):
        """减仓/平仓"""
        if self.side == "LONG":
            profit = (tick_price - self.aveprice) * size
        else:
            profit = (self.aveprice - tick_price) * size

        self.closeprofit += profit
        self.size -= size
        if self.size > 0:
            self.totalvalue -= size * tick_price
            self.aveprice = self.totalvalue / self.size
        else:
            self.totalvalue = 0
            self.aveprice = 0
            self.status = "closed"

        return profit


# ============================================================
# 回测引擎
# ============================================================
class BacktestEngine:
    """同步回测引擎 - 逐根K线执行策略"""

    def __init__(self, csv_path: str, initial_balance: float = 100.0):
        self.csv_path = csv_path
        self.initial_balance = initial_balance

        # 账户
        self.balance = initial_balance
        self.equity_curve = []  # [(timestamp, equity)]

        # 订单
        self.order_pool = {}  # uid -> OrderInstance
        self.trade_log = []   # 每笔成交记录

        # 统计
        self.stat = {
            "total_trades": 0,
            "win_trades": 0,
            "loss_trades": 0,
            "total_profit": 0.0,
            "max_drawdown": 0.0,
            "peak_equity": initial_balance,
            "returns": [],
        }

        # 加载数据
        self._load_data()

    def _load_data(self):
        """加载CSV数据"""
        df = pd.read_csv(self.csv_path)
        if 'time' in df.columns:
            df.set_index('time', inplace=True)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        self.data = df
        print_colored(f"加载数据: {len(self.data)} 根K线", bg_color='blue')
        print_colored(f"  时间: {df.index[0]} -> {df.index[-1]}", bg_color='blue')
        print_colored(f"  价格范围: {df['low'].min():.2f} - {df['high'].max():.2f}", bg_color='blue')

    def run(self):
        """运行回测"""
        start_time = time.time()

        # 初始化指标缓存
        indicators = {f'ind{i}': [] for i in range(1, 11)}
        indicators_w2 = {f'ind{i}': [] for i in range(1, 11)}
        order_statistic = {
            "totalnumber": 0, "win_num": 0, "win_win_count": 0,
            "loss_num": 0, "loss_loss_count": 0,
            "finish_num": 0, "holding_num": 0,
        }

        # 按时间窗口构建 storj（倒序，head=最新）
        storj_maxlen = 100

        total_candles = len(self.data)
        count = 0

        for idx, row in self.data.iterrows():
            # 构建 storj (倒序)
            candle_df = pd.DataFrame([row.values], columns=self.data.columns, index=[idx])
            if 'time' not in self.data.columns and 'time' not in candle_df.columns:
                pass

            if count == 0:
                storj = candle_df
            else:
                storj = pd.concat([candle_df, storj])
                if len(storj) > storj_maxlen:
                    storj = storj.drop(storj.tail(1).index)

            # 调用信号算法
            parapoll = {
                'dataset': storj,
                'indicatorsdic': indicators,
                'indicatorsdic_w2': indicators_w2,
            }

            signal, cur_ind, w2_ind = signalAlg.run(parapoll)

            # 更新指标缓存
            for k in list(indicators.keys()):
                if len(indicators[k]) >= 100:
                    del indicators[k][0]
            for k, v in cur_ind.items():
                if k in indicators:
                    indicators[k].append(v)
            for k in list(indicators_w2.keys()):
                if len(indicators_w2[k]) >= 100:
                    del indicators_w2[k][0]
            for k, v in w2_ind.items():
                if k in indicators_w2:
                    indicators_w2[k].append(v)

            # 调用订单算法
            parapoll['c_signal'] = signal
            parapoll['orderpool'] = self.order_pool
            parapoll['orderaccount'] = {'asset': self.balance, 'profit': 0,
                                         'h_profit': 0, 'h_profit_long': 0,
                                         'h_profit_short': 0}
            parapoll['order_statistic'] = order_statistic

            orderlist = orderAlg.run(parapoll)

            # 处理订单
            for order in orderlist:
                uid = order['uid']
                oside = order['oside']
                osize = float(order['osize'])
                oprice = float(order['oprice'])
                tick_price = float(storj.iloc[0]['close'])
                oaction = order['oaction']

                if oaction == 'OPEN':
                    if uid not in self.order_pool:
                        new_order = OrderInstance(
                            uid=uid, code=order['code'],
                            side=oside, size=osize,
                            open_price=oprice, tick_price=tick_price
                        )
                        self.order_pool[uid] = new_order
                        order_statistic['totalnumber'] += 1
                        order_statistic['holding_num'] += 1
                    else:
                        # 加仓
                        self.order_pool[uid].inc_position(osize, tick_price)

                    self.trade_log.append({
                        'time': idx, 'action': 'OPEN', 'side': oside,
                        'uid': uid, 'size': osize, 'price': tick_price,
                        'profit': 0,
                    })

                elif oaction == 'CLOSE':
                    if uid in self.order_pool:
                        order_obj = self.order_pool[uid]
                        if order_obj.size >= osize:
                            profit = order_obj.dec_position(osize, tick_price)
                            self.balance += profit
                            self.stat['total_profit'] += profit
                            order_statistic['finish_num'] += 1
                            order_statistic['holding_num'] -= 1

                            if profit >= 0:
                                order_statistic['win_num'] += 1
                                order_statistic['win_win_count'] += 1
                                order_statistic['loss_loss_count'] = 0
                            else:
                                order_statistic['loss_num'] += 1
                                order_statistic['win_win_count'] = 0
                                order_statistic['loss_loss_count'] += 1

                            self.trade_log.append({
                                'time': idx, 'action': 'CLOSE', 'side': oside,
                                'uid': uid, 'size': osize, 'price': tick_price,
                                'profit': round(profit, 4),
                            })

            # 计算浮动盈亏
            floating_pl = 0.0
            for order_obj in self.order_pool.values():
                if order_obj.size > 0:
                    curr_price = float(storj.iloc[0]['close'])
                    if order_obj.side == 'LONG':
                        order_obj.floatingPL = (curr_price - order_obj.aveprice) * order_obj.size
                    else:
                        order_obj.floatingPL = (order_obj.aveprice - curr_price) * order_obj.size
                    floating_pl += order_obj.floatingPL

            # 记录权益曲线
            equity = self.balance + floating_pl
            self.equity_curve.append((idx, equity))

            # 跟踪最大回撤
            self.stat['peak_equity'] = max(self.stat['peak_equity'], equity)
            dd = self.stat['peak_equity'] - equity
            self.stat['max_drawdown'] = max(self.stat['max_drawdown'], dd)

            count += 1
            if count % 100 == 0:
                print(f"  进度: {count}/{total_candles} ({100*count//total_candles}%)")

        # 保存最终统计用于报告
        self._final_order_stats = {
            'win_num': order_statistic.get('win_num', 0),
            'loss_num': order_statistic.get('loss_num', 0),
        }

        elapsed = time.time() - start_time
        self._generate_report(elapsed)
        return self.stat

    def _generate_report(self, elapsed: float):
        """生成回测报告"""
        final_equity = self.equity_curve[-1][1] if self.equity_curve else self.balance
        total_return = final_equity - self.initial_balance
        return_pct = (final_equity / self.initial_balance - 1) * 100

        # 计算年化收益率和夏普比率
        equity_series = pd.Series([e for _, e in self.equity_curve])
        returns = equity_series.pct_change().dropna()
        sharpe = 0.0
        if len(returns) > 1 and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(365 * 24 * 60 / 5)  # 5min bars

        # 从 _final_order_stats 获取胜率数据
        win_trades = self._final_order_stats.get('win_num', 0)
        loss_trades = self._final_order_stats.get('loss_num', 0)
        total_closed = win_trades + loss_trades
        win_rate = (win_trades / total_closed * 100) if total_closed > 0 else 0

        # 盈亏比
        avg_win = self.stat['total_profit'] / win_trades if win_trades > 0 else 0
        avg_loss = abs(self.stat['total_profit']) / loss_trades if loss_trades > 0 else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss > 0 else 0

        # 输出报告
        print("\n" + "=" * 60)
        print_colored("          回 测 报 告", bg_color='green', bold=True)
        print("=" * 60)
        print(f"  数据文件:     {self.csv_path}")
        print(f"  K线数量:      {len(self.data)}")
        print(f"  运行时间:     {elapsed:.2f}秒")
        print("─" * 60)
        print_colored(f"  初始资金:     ${self.initial_balance:.2f}", bg_color='yellow')
        print_colored(f"  最终权益:     ${final_equity:.2f}", bg_color='yellow')
        print_colored(f"  总盈亏:       ${total_return:+.2f} ({return_pct:+.2f}%)", bg_color='yellow')
        print("─" * 60)
        print(f"  最大回撤:     ${self.stat['max_drawdown']:.2f}")
        if self.stat['peak_equity'] > 0:
            print(f"  最大回撤率:   {self.stat['max_drawdown']/self.stat['peak_equity']*100:.2f}%")
        print(f"  夏普比率:     {sharpe:.4f}")
        print("─" * 60)
        print_colored(f"  总交易次数:   {total_closed}", bg_color='cyan')
        print_colored(f"  胜率:         {win_trades}/{total_closed} = {win_rate:.1f}%", bg_color='cyan')
        print_colored(f"  平均盈利:     ${avg_win:.2f}", bg_color='cyan')
        print_colored(f"  平均亏损:     ${avg_loss:.2f}", bg_color='cyan')
        print_colored(f"  盈亏比:       {profit_factor:.2f}", bg_color='cyan')
        print("=" * 60)

        # 保存报告到JSON
        report = {
            "data_file": self.csv_path,
            "candles": len(self.data),
            "elapsed_seconds": round(elapsed, 2),
            "initial_balance": self.initial_balance,
            "final_equity": round(final_equity, 2),
            "total_return": round(total_return, 2),
            "return_pct": round(return_pct, 2),
            "max_drawdown": round(self.stat['max_drawdown'], 2),
            "max_drawdown_pct": round(self.stat['max_drawdown'] / max(self.stat['peak_equity'], 1) * 100, 2),
            "sharpe_ratio": round(sharpe, 4),
            "total_trades": total_closed,
            "win_trades": win_trades,
            "loss_trades": loss_trades,
            "win_rate_pct": round(win_rate, 1),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2),
        }

        import os as _os
        _os.makedirs("reports", exist_ok=True)
        report_path = f"reports/backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n报告已保存: {report_path}")

        # 保存交易日志
        if self.trade_log:
            trade_df = pd.DataFrame(self.trade_log)
            trade_path = report_path.replace('.json', '_trades.csv')
            trade_df.to_csv(trade_path, index=False)
            print(f"交易日志:   {trade_path}")

        # 保存权益曲线
        if self.equity_curve:
            equity_df = pd.DataFrame(self.equity_curve, columns=['time', 'equity'])
            equity_path = report_path.replace('.json', '_equity.csv')
            equity_df.to_csv(equity_path, index=False)
            print(f"权益曲线:   {equity_path}")


def main():
    parser = argparse.ArgumentParser(description="HJATS 回测运行器")
    parser.add_argument("--data", required=True, help="CSV数据文件路径")
    parser.add_argument("--balance", type=float, default=100.0, help="初始资金 (默认: 100)")
    args = parser.parse_args()

    if not os.path.exists(args.data):
        print_colored(f"文件不存在: {args.data}", bg_color='red')
        sys.exit(1)

    engine = BacktestEngine(csv_path=args.data, initial_balance=args.balance)
    engine.run()


if __name__ == "__main__":
    main()