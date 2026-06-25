#!/usr/bin/env python3
"""
回测报告生成器 - 生成带图表的交互式 HTML 报告

使用:
    python scripts/report_generator.py \\
        --data data/xxx.csv \\
        --report reports/bt_20260625_xxx \\
        --balance 100 \\
        --trades trades.csv \\
        --equity equity.csv

输出到 reports/bt_20260625_xxx/ 目录:
    ├── report.html       # 可交互的网页报告（手机友好）
    ├── chart_kline.html  # K线图（含买卖点、指标）
    ├── chart_equity.html # 收益曲线图
    └── data.json         # 回测数据摘要
"""
import argparse
import json
import os
import sys
from datetime import datetime

import pandas as pd
import numpy as np

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.helpers import print_colored


def generate_charts(kline_df, trades_df, equity_df, indicators, output_dir):
    """生成 Plotly 图表并保存为 HTML"""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        print_colored("请先安装 plotly: pip3 install plotly", bg_color='red')
        sys.exit(1)

    # ==============================================================
    # 图1: K线 + 买卖点 + 指标
    # ==============================================================
    num_rows = 2
    row_heights = [0.6, 0.4]
    if indicators and any(indicators.get(k, []) for k in indicators):
        num_rows = 3
        row_heights = [0.5, 0.25, 0.25]

    fig = make_subplots(
        rows=num_rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=row_heights,
        subplot_titles=("K线 & 买卖点", "收益曲线", "指标") if num_rows > 2
                       else ("K线 & 买卖点", "收益曲线"),
    )

    # -- K线（使用 OHLC） --
    fig.add_trace(go.Candlestick(
        x=kline_df.index,
        open=kline_df['open'],
        high=kline_df['high'],
        low=kline_df['low'],
        close=kline_df['close'],
        name='K线',
        showlegend=False,
    ), row=1, col=1)

    # -- 买卖点 --
    if trades_df is not None and len(trades_df) > 0:
        for _, t in trades_df.iterrows():
            if t['action'] == 'OPEN':
                color = 'green' if t['side'] == 'LONG' else 'red'
                symbol = 'triangle-up' if t['side'] == 'LONG' else 'triangle-down'
                label = f"{'买入' if t['side'] == 'LONG' else '卖空'} ${t['price']:.2f}"
                fig.add_trace(go.Scatter(
                    x=[t['time']], y=[t['price']],
                    mode='markers+text',
                    marker=dict(size=12, color=color, symbol=symbol),
                    name=label,
                    text=[label],
                    textposition="top center",
                    textfont=dict(size=10, color=color),
                    showlegend=False,
                ), row=1, col=1)

    # -- 均线指标 --
    if indicators:
        for i, (ind_name, ind_values) in enumerate(indicators.items()):
            if ind_values and len(ind_values) == len(kline_df):
                series = pd.Series(ind_values, index=kline_df.index)
                fig.add_trace(go.Scatter(
                    x=series.index, y=series.values,
                    mode='lines',
                    name=ind_name,
                    line=dict(width=1),
                ), row=1, col=1)

    # -- 收益曲线 --
    if equity_df is not None and len(equity_df) > 0:
        eq_times = pd.to_datetime(equity_df['time']) if 'time' in equity_df.columns else equity_df.index
        eq_values = equity_df['equity'].values if 'equity' in equity_df.columns else equity_df.iloc[:, 1].values

        fig.add_trace(go.Scatter(
            x=eq_times, y=eq_values,
            mode='lines',
            name='权益',
            line=dict(color='#4CAF50', width=2),
            fill='tozeroy',
            fillcolor='rgba(76, 175, 80, 0.1)',
        ), row=2, col=1)

        # 基准线（初始资金）
        init_balance = eq_values[0] if len(eq_values) > 0 else 100
        fig.add_hline(y=init_balance, line_dash="dash", line_color="gray",
                      annotation_text=f"初始 ${init_balance:.2f}", row=2, col=1)

    # -- 指标面板（第三行） --
    if num_rows > 2 and indicators:
        row_idx = 3
        for ind_name, ind_values in indicators.items():
            if ind_values and len(ind_values) > 0:
                series = pd.Series(ind_values, index=kline_df.index if len(ind_values) == len(kline_df) else range(len(ind_values)))
                fig.add_trace(go.Scatter(
                    x=series.index, y=series.values,
                    mode='lines',
                    name=ind_name,
                    line=dict(width=1.5),
                ), row=row_idx, col=1)
                break  # 只显示第一个指标

    # 布局
    fig.update_layout(
        title=dict(text="回测详情", x=0.5),
        xaxis=dict(rangeslider=dict(visible=False)),
        xaxis2=dict(rangeslider=dict(visible=False)),
        template="plotly_dark",
        hovermode='x unified',
        height=1000 if num_rows <= 2 else 1200,
        margin=dict(l=60, r=30, t=60, b=30),
    )
    fig.update_xaxes(title_text="时间", row=num_rows, col=1)
    fig.update_yaxes(title_text="价格", row=1, col=1)
    fig.update_yaxes(title_text="权益 ($)", row=2, col=1)

    kline_path = os.path.join(output_dir, "chart_kline.html")
    fig.write_html(kline_path, include_plotlyjs='cdn', full_html=False)
    print_colored(f"  K线图: {kline_path}", bg_color='green')

    # ==============================================================
    # 图2: 收益曲线（独立大图）
    # ==============================================================
    fig2 = go.Figure()
    if equity_df is not None and len(equity_df) > 0:
        eq_times = pd.to_datetime(equity_df['time']) if 'time' in equity_df.columns else equity_df.index
        eq_values = equity_df['equity'].values if 'equity' in equity_df.columns else equity_df.iloc[:, 1].values

        fig2.add_trace(go.Scatter(
            x=eq_times, y=eq_values,
            mode='lines',
            name='权益',
            line=dict(color='#4CAF50', width=3),
            fill='tozeroy',
            fillcolor='rgba(76, 175, 80, 0.15)',
        ))
        fig2.add_hline(y=eq_values[0], line_dash="dash", line_color="gray",
                       annotation_text=f"初始 ${eq_values[0]:.2f}")

    fig2.update_layout(
        title=dict(text="收益曲线", x=0.5),
        xaxis_title="时间",
        yaxis_title="权益 ($)",
        template="plotly_dark",
        hovermode='x',
        height=500,
        margin=dict(l=60, r=30, t=60, b=30),
    )
    equity_path = os.path.join(output_dir, "chart_equity.html")
    fig2.write_html(equity_path, include_plotlyjs='cdn', full_html=False)
    print_colored(f"  收益图: {equity_path}", bg_color='green')

    return kline_path, equity_path


def generate_html_report(report_data, kline_chart_path, equity_chart_path, output_dir):
    """生成完整的 HTML 回测报告"""
    r = report_data

    # 读取图表 HTML（嵌入到报告中）
    kline_html = ""
    if kline_chart_path and os.path.exists(kline_chart_path):
        with open(kline_chart_path) as f:
            kline_html = f.read()

    equity_html = ""
    if equity_chart_path and os.path.exists(equity_chart_path):
        with open(equity_chart_path) as f:
            equity_html = f.read()

    # 状态颜色
    color = "#4CAF50" if r['total_return'] >= 0 else "#f44336"
    arrow = "▲" if r['total_return'] >= 0 else "▼"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>回测报告 - {r.get('data_file', 'N/A')}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: #0d1117; color: #c9d1d9; padding: 0; margin: 0;
    -webkit-font-smoothing: antialiased;
}}
.header {{
    background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
    padding: 24px 16px; border-bottom: 1px solid #30363d; text-align: center;
}}
.header h1 {{ font-size: 22px; font-weight: 600; color: #f0f6fc; }}
.header .subtitle {{ font-size: 13px; color: #8b949e; margin-top: 4px; }}
.summary {{
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 10px; padding: 16px; max-width: 600px; margin: 0 auto;
}}
.card {{
    background: #161b22; border: 1px solid #30363d; border-radius: 12px;
    padding: 14px; text-align: center;
}}
.card .label {{ font-size: 11px; text-transform: uppercase; color: #8b949e; letter-spacing: 0.5px; }}
.card .value {{ font-size: 20px; font-weight: 700; margin-top: 4px; }}
.card .value.positive {{ color: #4CAF50; }}
.card .value.negative {{ color: #f44336; }}
.chart-container {{ padding: 0; margin: 0; }}
.chart-container > div {{ width: 100% !important; }}
.details {{ padding: 16px; max-width: 600px; margin: 0 auto; }}
.details h2 {{ font-size: 16px; color: #f0f6fc; margin-bottom: 12px; }}
.detail-table {{ width: 100%; border-collapse: collapse; }}
.detail-table tr {{ border-bottom: 1px solid #21262d; }}
.detail-table td {{ padding: 10px 8px; font-size: 14px; }}
.detail-table td:first-child {{ color: #8b949e; }}
.detail-table td:last-child {{ text-align: right; font-weight: 500; }}
.footer {{ text-align: center; padding: 20px; color: #484f58; font-size: 12px; }}
@media (max-width: 480px) {{
    .summary {{ grid-template-columns: 1fr 1fr; gap: 8px; padding: 12px; }}
    .card .value {{ font-size: 18px; }}
    .header h1 {{ font-size: 18px; }}
}}
</style>
</head>
<body>

<div class="header">
    <h1>{arrow} 回测报告</h1>
    <div class="subtitle">{r.get('data_file', 'N/A')} | {r.get('candles', 0)} 根K线 | {r.get('elapsed_seconds', 0):.2f}秒</div>
</div>

<div class="summary">
    <div class="card">
        <div class="label">初始资金</div>
        <div class="value">${r['initial_balance']:.2f}</div>
    </div>
    <div class="card">
        <div class="label">最终权益</div>
        <div class="value {'positive' if r['total_return'] >= 0 else 'negative'}">${r['final_equity']:.2f}</div>
    </div>
    <div class="card">
        <div class="label">总盈亏</div>
        <div class="value {'positive' if r['total_return'] >= 0 else 'negative'}">{r['return_pct']:+.2f}%</div>
    </div>
    <div class="card">
        <div class="label">最大回撤</div>
        <div class="value negative">{r['max_drawdown_pct']:.2f}%</div>
    </div>
</div>

<div class="chart-container">
    {kline_html}
</div>

<div class="chart-container">
    {equity_html}
</div>

<div class="details">
    <h2>📊 详细数据</h2>
    <table class="detail-table">
        <tr><td>交易次数</td><td>{r['total_trades']}</td></tr>
        <tr><td>胜率</td><td>{r['win_rate_pct']:.1f}% ({r['win_trades']}/{r['total_trades']})</td></tr>
        <tr><td>盈亏比</td><td>{r['profit_factor']:.2f}</td></tr>
        <tr><td>夏普比率</td><td>{r['sharpe_ratio']}</td></tr>
        <tr><td>最大回撤</td><td>${r['max_drawdown']:.2f}</td></tr>
        <tr><td>平均盈利</td><td>${r['avg_win']:.2f}</td></tr>
        <tr><td>平均亏损</td><td>${r['avg_loss']:.2f}</td></tr>
    </table>
</div>

<div class="footer">
    HJATS Backtest Engine | {datetime.now().strftime('%Y-%m-%d %H:%M')}
</div>

</body>
</html>"""

    report_path = os.path.join(output_dir, "report.html")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print_colored(f"  网页报告: {report_path}", bg_color='green')
    return report_path


def run(args):
    """主入口"""
    # 创建回测会话目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data_basename = os.path.splitext(os.path.basename(args.data_file))[0]
    session_name = f"bt_{timestamp}_{data_basename}"
    output_dir = os.path.join(args.output_dir, session_name)
    os.makedirs(output_dir, exist_ok=True)

    print_colored(f"生成回测报告: {output_dir}", bg_color='blue')

    # 1. 加载 JSON 报告
    with open(args.report_json) as f:
        report_data = json.load(f)

    # 2. 保存数据摘要
    data_summary = {k: report_data[k] for k in [
        'data_file', 'candles', 'elapsed_seconds', 'initial_balance',
        'final_equity', 'total_return', 'return_pct', 'max_drawdown',
        'max_drawdown_pct', 'sharpe_ratio', 'total_trades', 'win_trades',
        'loss_trades', 'win_rate_pct', 'avg_win', 'avg_loss', 'profit_factor',
    ]}
    with open(os.path.join(output_dir, "data.json"), 'w') as f:
        json.dump(data_summary, f, indent=2)

    # 3. 复制交易日志和权益曲线
    kline_df = pd.read_csv(args.data_file)
    if 'time' in kline_df.columns:
        kline_df.set_index('time', inplace=True)
    kline_df.index = pd.to_datetime(kline_df.index)
    kline_df = kline_df.sort_index()

    trades_df = None
    if args.trades_csv and os.path.exists(args.trades_csv):
        trades_df = pd.read_csv(args.trades_csv)
        trades_df.to_csv(os.path.join(output_dir, "trades.csv"), index=False)

    equity_df = None
    if args.equity_csv and os.path.exists(args.equity_csv):
        equity_df = pd.read_csv(args.equity_csv)
        equity_df.to_csv(os.path.join(output_dir, "equity.csv"), index=False)

    # 4. 读取指标数据（从 signalAlg 输出中）
    indicators = report_data.get('indicators', {})

    # 5. 生成图表
    kline_path, equity_path = generate_charts(
        kline_df, trades_df, equity_df, indicators, output_dir
    )

    # 6. 生成 HTML 报告
    report_path = generate_html_report(
        report_data, kline_path, equity_path, output_dir
    )

    # 7. 移动 JSON 报告到目录中
    import shutil
    json_dest = os.path.join(output_dir, "backtest_report.json")
    shutil.copy2(args.report_json, json_dest)

    print_colored(f"\n✅ 报告生成完成!", bg_color='green')
    print_colored(f"   打开: {report_path}", bg_color='green')
    print(f"   目录: {output_dir}/")
    print(f"   ├── report.html          ← 手机网页报告")
    print(f"   ├── chart_kline.html     ← K线图（含买卖点）")
    print(f"   ├── chart_equity.html    ← 收益曲线")
    print(f"   ├── backtest_report.json ← 回测数据")
    print(f"   ├── trades.csv           ← 交易记录")
    print(f"   └── equity.csv           ← 权益曲线")
    print()

    return output_dir


def main():
    parser = argparse.ArgumentParser(description="生成回测图表和HTML报告")
    parser.add_argument("--data-file", required=True, help="原始K线CSV")
    parser.add_argument("--report-json", required=True, help="回测报告JSON")
    parser.add_argument("--trades-csv", help="交易日志CSV")
    parser.add_argument("--equity-csv", help="权益曲线CSV")
    parser.add_argument("--output-dir", default="reports", help="输出根目录")

    args = parser.parse_args()

    for f in [args.data_file, args.report_json]:
        if not os.path.exists(f):
            print_colored(f"文件不存在: {f}", bg_color='red')
            sys.exit(1)

    run(args)


if __name__ == "__main__":
    main()