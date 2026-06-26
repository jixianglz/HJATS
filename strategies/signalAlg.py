"""
信号算法 - 双均线交叉策略 (MA Crossover)

逻辑:
  - 计算 ma10(快线) 和 ma30(慢线)
  - 金叉: ma10 上穿 ma30 → signal=1 (看多)
  - 死叉: ma10 下穿 ma30 → signal=-1 (看空)
  - 其他: signal=0 (持仓不动)

接口:
    run(parapoll) -> (signal, indicators_dict, indicators_w2_dict)
"""
import logging
from src.utils.helpers import print_colored

logger = logging.getLogger(__name__)


def run(parapoll):
    """
    双均线交叉策略

    Args:
        parapoll['dataset']: DataFrame, 最新N根K线 (head=最新, 倒序)
        parapoll['indicatorsdic']: 主窗口指标历史

    Returns:
        signal: 1=金叉开多, -1=死叉开空, 0=无操作
    """
    dataset = parapoll['dataset']
    cur_indicators = {}
    w2_indicators = {}

    signal = 0

    series_close = dataset['close'].sort_index()

    # 计算均线
    ma10 = series_close.rolling(window=10).mean()
    ma30 = series_close.rolling(window=30).mean()

    # 输出指标
    cur_indicators['ind1'] = round(ma10.iloc[-1], 2)
    cur_indicators['ind2'] = round(ma30.iloc[-1], 2)

    # 需要至少 31 根K线才能计算 ma30
    if len(series_close) < 31:
        return 0, cur_indicators, w2_indicators

    # 当前值和前一期值
    ma10_curr = ma10.iloc[-1]
    ma10_prev = ma10.iloc[-2]
    ma30_curr = ma30.iloc[-1]
    ma30_prev = ma30.iloc[-2]

    # 金叉: 之前 ma10 <= ma30, 现在 ma10 > ma30
    if ma10_prev <= ma30_prev and ma10_curr > ma30_curr:
        signal = 1
        print_colored(f'[sAlg] 🟢 GOLDEN CROSS! ma10={ma10_curr:.2f} ↑ ma30={ma30_curr:.2f}',
                      bg_color='green', bold=True)

    # 死叉: 之前 ma10 >= ma30, 现在 ma10 < ma30
    elif ma10_prev >= ma30_prev and ma10_curr < ma30_curr:
        signal = -1
        print_colored(f'[sAlg] 🔴 DEATH CROSS! ma10={ma10_curr:.2f} ↓ ma30={ma30_curr:.2f}',
                      bg_color='red', bold=True)

    else:
        print_colored(f'[sAlg] No crossover. ma10={ma10_curr:.2f}, ma30={ma30_curr:.2f}',
                      bg_color='green')

    return signal, cur_indicators, w2_indicators