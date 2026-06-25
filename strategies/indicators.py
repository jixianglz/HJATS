"""
技术指标工具函数库

提供各种常用技术指标的计算函数
"""
import pandas as pd
import numpy as np


def sma(ticks, n: int) -> float:
    """简单移动平均"""
    return sum(ticks[:n]) / n


def rate_of_change(ticks, n: int, full_cal=True) -> pd.Series:
    """
    变化率指标 (ROC)

    Args:
        ticks: 价格序列
        n: 周期
        full_cal: 是否全量计算

    Returns:
        pd.Series
    """
    roc = pd.Series(dtype=float)
    na = np.nan
    ticks_cal = ticks[-n:] if not full_cal else ticks

    for sers in ticks_cal.rolling(n):
        if len(sers) < n:
            tmp = pd.Series({sers.tail(1).index[0]: na})
        else:
            tmp_roc = 100 * (sers[-1] - sers[-n]) / sers[-n]
            tmp = pd.Series({sers.tail(1).index[0]: tmp_roc})
        roc = pd.concat([roc, tmp])

    return roc


def kst(ticks):
    """
    KST (Know Sure Thing) 指标

    Returns:
        DataFrame with columns: KST, Signal, KSTSignal
    """
    roc10 = rate_of_change(ticks, 10)
    roc15 = rate_of_change(ticks, 15)
    roc20 = rate_of_change(ticks, 20)
    roc30 = rate_of_change(ticks, 30)

    roc10_ma = roc10.rolling(10).mean()
    roc15_ma = roc15.rolling(10).mean()
    roc20_ma = roc20.rolling(10).mean()
    roc30_ma = roc30.rolling(15).mean()

    kst_val = roc10_ma + 2 * roc15_ma + 3 * roc20_ma + 4 * roc30_ma
    kst_signal = kst_val.rolling(9).mean()
    kst_diff = kst_val.copy()
    kst_diff.name = "KSTSignal"

    result = pd.concat([kst_diff, kst_val, kst_signal], axis=1)
    result.columns = ['KSTSignal', 'KST', 'Signal']

    # 计算交叉信号
    for i in range(1, len(result)):
        if pd.isna(result['Signal'].iloc[i - 1]):
            result['KSTSignal'].iloc[i] = 0
            continue
        result['KSTSignal'].iloc[i] = 2 * result['KST'].iloc[i] - result['Signal'].iloc[i]

    return result


def break_out(ticks, win: int) -> tuple:
    """
    突破指标

    Args:
        ticks: 价格序列
        win: 窗口大小

    Returns:
        (bull_line, bear_line)
    """
    if len(ticks) >= win:
        high = max(ticks[:win + 1])
        low = min(ticks[:win + 1])
        last = ticks[0]
        bull = 1 - abs(last - high) / abs(high - low) if (high - low) != 0 else 0
        bear = 1 - abs(last - low) / abs(high - low) if (high - low) != 0 else 0
        return bull, bear
    return 0, 0