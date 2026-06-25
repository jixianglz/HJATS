"""
信号算法 - 用户自定义信号生成逻辑

接口:
    run(parapoll) -> (signal, indicators_dict, indicators_w2_dict)

参数:
    parapoll['dataset']: DataFrame, 最新N根K线 (head=最新)
    parapoll['indicatorsdic']: dict, 主窗口指标历史缓存
    parapoll['indicatorsdic_w2']: dict, 次窗口指标历史缓存

返回:
    signal: int, 信号值 (0=无信号, 1=开多, -1=开空)
    cur_indicators: dict, 主窗口指标 {ind1: val, ind2: val, ...}
    w2_indicators: dict, 次窗口指标 {ind1: val, ind2: val, ...}
"""
import logging
from src.utils.helpers import print_colored
from strategies import indicators

logger = logging.getLogger(__name__)


def run(parapoll):
    """
    信号算法入口

    示例策略: 简单均线策略
    - ma10 > ma30 > ma60: 看多信号 (1)
    - ma10 < ma30 < ma60: 看空信号 (-1)
    - 其他: 无信号 (0)
    """
    dataset = parapoll['dataset']
    indicators_main = parapoll['indicatorsdic']
    indicators_w2 = parapoll['indicatorsdic_w2']

    cur_indicators = {}
    w2_indicators = {}

    print_colored('[sAlg] Algorithm started', bg_color='green')
    last_close = dataset['close'].values[0]
    print_colored(f"[sAlg] Last close: {last_close:.2f}", bg_color='green')

    signal = 0

    # 均线信号示例
    series_close = dataset['close'].sort_index()

    ma10 = series_close.rolling(window=10).mean()
    ma30 = series_close.rolling(window=30).mean()
    ma60 = series_close.rolling(window=60).mean()

    cur_indicators['ind1'] = ma10.iloc[-1]
    cur_indicators['ind2'] = ma30.iloc[-1]
    cur_indicators['ind3'] = ma60.iloc[-1]

    # 简单趋势判断
    if ma10.iloc[-1] > ma30.iloc[-1] > ma60.iloc[-1]:
        signal = 1  # 看多
    elif ma10.iloc[-1] < ma30.iloc[-1] < ma60.iloc[-1]:
        signal = -1  # 看空
    else:
        signal = 0  # 震荡

    print_colored(f'[sAlg] Signal: {signal}', bg_color='green')
    print_colored('[sAlg] Algorithm ended', bg_color='green')

    return signal, cur_indicators, w2_indicators