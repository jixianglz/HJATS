"""
回测模拟交易所 - 模拟订单执行（立即按最新价成交）
"""
import logging
from src.broker.base import BrokerBase
from src.utils.constants import ORDER_STATUS_SUCCESS

logger = logging.getLogger(__name__)


class BacktestBroker(BrokerBase):
    """
    回测 Broker
    - 所有订单立即成交
    - 成交价 = 当前价格（由 OrderManager 传入）
    """

    def __init__(self):
        self.balance = 0.0

    def check_balance(self) -> float:
        return self.balance

    def order_open(self, code: str, oside: str, otype: str,
                   osize: float, oprice: float = None) -> dict:
        """
        模拟开仓 - 立即成交

        Returns:
            dict: {success: True, order_id: None, deal_price: None (由调用方填充), status: 'SUCCESS'}
        """
        return {
            'success': True,
            'order_id': None,
            'deal_price': None,  # 由 OrderManager 用当前价格填充
            'status': ORDER_STATUS_SUCCESS,
        }

    def order_close(self, code: str, oside: str, otype: str,
                    osize: float, oprice: float = None) -> dict:
        """模拟平仓 - 立即成交"""
        return {
            'success': True,
            'order_id': None,
            'deal_price': None,
            'profit': 0.0,
            'status': ORDER_STATUS_SUCCESS,
        }