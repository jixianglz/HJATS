"""
订单算法 - 双均线策略订单管理

逻辑:
  - signal=1 (金叉): 平空 → 开多
  - signal=-1 (死叉): 平多 → 开空
  - signal=0: 持仓不动

注意事项:
  - 交易对固定为 ETH-USD
  - 每次开仓 0.01 ETH（适配小资金 $100 级别）
  - 通过 orderpool 判断当前持仓方向

接口:
    run(parapoll) -> orderlist
"""
import logging
from src.utils.helpers import print_colored

logger = logging.getLogger(__name__)


def run(parapoll):
    """
    订单算法入口

    Args:
        parapoll['c_signal']: 当前信号 (1/0/-1)
        parapoll['orderpool']: 当前订单池 {uid: OrderInstance}
        parapoll['orderaccount']: 账户状态 {'asset': float}

    Returns:
        orderlist: list[dict], 订单列表
    """
    dataset = parapoll['dataset']
    signal = parapoll['c_signal']
    orderpool = parapoll['orderpool']
    account = parapoll['orderaccount']

    tick_last_close = float(dataset.iloc[0]['close'])
    orderlist = []

    # === 判断当前持仓方向 ===
    has_long = False
    has_short = False
    open_long_uid = None
    open_short_uid = None

    for uid, order in orderpool.items():
        if order.side == 'LONG' and order.size > 0:
            has_long = True
            open_long_uid = uid
        if order.side == 'SHORT' and order.size > 0:
            has_short = True
            open_short_uid = uid

    # === 资金检查 ===
    asset = account.get('asset', 0)
    if asset <= 0:
        print_colored('[oAlg] Insufficient balance', bg_color='blue')
        return orderlist

    print_colored(f'[oAlg] Signal={signal}, LONG={has_long}, SHORT={has_short}, '
                  f'close={tick_last_close:.2f}, balance=${asset:.2f}',
                  bg_color='blue')

    # === 金叉信号: signal=1 → 开多(或平空换多) ===
    if signal == 1:
        # 如果持有多单，不动
        if has_long:
            print_colored('[oAlg] Already LONG, hold', bg_color='blue')
            return orderlist

        # 如果持有空单，先平空
        if has_short:
            close_order = {
                'uid': open_short_uid,
                'code': 'ETH-USD',
                'oaction': 'CLOSE',
                'oside': 'SHORT',
                'otype': 'MARKET',
                'osize': str(orderpool[open_short_uid].size),
                'oprice': str(tick_last_close),
            }
            orderlist.append(close_order)
            print_colored(f'[oAlg] CLOSE SHORT: {open_short_uid}', bg_color='blue')

        # 开多（固定 0.01 ETH，适配 100U 本金）
        size = 0.01
        open_order = {
            'uid': 'ma_long_1',
            'code': 'ETH-USD',
            'oaction': 'OPEN',
            'oside': 'LONG',
            'otype': 'MARKET',
            'osize': str(size),
            'oprice': str(tick_last_close + 5),  # +5 确保市价成交
        }
        orderlist.append(open_order)
        print_colored(f'[oAlg] 🟢 OPEN LONG: 0.01 ETH @ ~${tick_last_close:.2f}',
                      bg_color='blue', bold=True)

    # === 死叉信号: signal=-1 → 开空(或平多换空) ===
    elif signal == -1:
        # 如果持有空单，不动
        if has_short:
            print_colored('[oAlg] Already SHORT, hold', bg_color='blue')
            return orderlist

        # 如果持有多单，先平多
        if has_long:
            close_order = {
                'uid': open_long_uid,
                'code': 'ETH-USD',
                'oaction': 'CLOSE',
                'oside': 'LONG',
                'otype': 'MARKET',
                'osize': str(orderpool[open_long_uid].size),
                'oprice': str(tick_last_close),
            }
            orderlist.append(close_order)
            print_colored(f'[oAlg] CLOSE LONG: {open_long_uid}', bg_color='blue')

        # 开空
        size = 0.01
        open_order = {
            'uid': 'ma_short_1',
            'code': 'ETH-USD',
            'oaction': 'OPEN',
            'oside': 'SHORT',
            'otype': 'MARKET',
            'osize': str(size),
            'oprice': str(tick_last_close - 5),  # -5 确保市价成交
        }
        orderlist.append(open_order)
        print_colored(f'[oAlg] 🔴 OPEN SHORT: 0.01 ETH @ ~${tick_last_close:.2f}',
                      bg_color='blue', bold=True)

    # === 无信号 ===
    else:
        print_colored(f'[oAlg] No signal, hold current position', bg_color='blue')

    print_colored(f'[oAlg] Orders generated: {len(orderlist)}', bg_color='blue')
    return orderlist