"""
订单算法 - 用户自定义订单生成逻辑

接口:
    run(parapoll) -> orderlist

参数:
    parapoll['dataset']: DataFrame, 最新N根K线
    parapoll['c_signal']: int, 当前信号值
    parapoll['orderpool']: dict, 当前订单池
    parapoll['orderaccount']: dict, 当前账户状态
    parapoll['order_statistic']: dict, 当前订单统计

返回:
    orderlist: list[dict], 订单列表，每单格式:
        {'uid': str, 'code': str, 'oaction': str, 'oside': str,
         'otype': str, 'osize': str, 'oprice': str}
"""
import logging
from src.utils.helpers import print_colored

logger = logging.getLogger(__name__)

# 订单计数器（策略运行期间保持状态）
_order_counters = {'long': 1, 'short': 1}
_order_num_limit = 5


def run(parapoll):
    """
    订单算法入口

    示例策略: 收到信号后开仓，每次开0.1个ETH
    signal=1: 开LONG
    signal=-1: 开SHORT (或平多)
    """
    global _order_counters, _order_num_limit

    dataset = parapoll['dataset']
    signal = parapoll['c_signal']
    orderpool = parapoll['orderpool']
    account = parapoll['orderaccount']
    order_statistic = parapoll['order_statistic']

    tick_last_close = str(dataset.iloc[0]['close'])
    orderlist = []

    print_colored('[oAlg] Order algorithm started', bg_color='blue')

    # 检查账户余额
    asset = account.get('asset', 0)
    if asset <= 0:
        print_colored('[oAlg] Insufficient balance', bg_color='blue')
        return orderlist

    # 处理信号
    if signal == 1 and _order_num_limit > 0:
        # 开多
        order = {
            'uid': f"long{_order_counters['long']}",
            'code': 'ETH-USD',
            'oaction': 'OPEN',
            'oside': 'LONG',
            'otype': 'MARKET',
            'osize': '0.1',
            'oprice': str(float(tick_last_close) + 20),  # 略高于市价确保成交
        }
        orderlist.append(order)
        _order_counters['long'] += 1
        _order_num_limit -= 1
        print_colored(f'[oAlg] OPEN LONG: {order["uid"]}', bg_color='blue')

    elif signal == -1 and _order_num_limit > 0:
        # 开空
        order = {
            'uid': f"short{_order_counters['short']}",
            'code': 'ETH-USD',
            'oaction': 'OPEN',
            'oside': 'SHORT',
            'otype': 'MARKET',
            'osize': '0.1',
            'oprice': str(float(tick_last_close) - 20),  # 略低于市价确保成交
        }
        orderlist.append(order)
        _order_counters['short'] += 1
        _order_num_limit -= 1
        print_colored(f'[oAlg] OPEN SHORT: {order["uid"]}', bg_color='blue')

    print_colored(f'[oAlg] Orders generated: {len(orderlist)}', bg_color='blue')
    print_colored('[oAlg] Order algorithm ended', bg_color='blue')

    return orderlist