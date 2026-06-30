"""
Binance 实盘交易所适配器
"""
import logging
import time
from binance.um_futures import UMFutures
from binance.error import ClientError
from src.broker.base import BrokerBase
from src.broker.account import AccountClient
from src.utils.constants import (
    ORDER_STATUS_FILLED, ORDER_STATUS_CANCELED, ORDER_STATUS_SUCCESS,
    ORDER_STATUS_FAILED, ORDER_STATUS_NA,
)

logger = logging.getLogger(__name__)


class BinanceBroker(BrokerBase):
    """
    Binance U本位合约 Broker
    """

    def __init__(self, account_dic: dict = None):
        account = AccountClient(account_dic)
        self.dex_name = account.dex_name
        self.api_key = account.api_key
        self.api_secret = account.api_secret

        if not self.api_key or not self.api_secret:
            logger.warning("Binance API keys not configured - broker will not work")

        self.client = UMFutures(key=self.api_key, secret=self.api_secret)
        logger.info("BinanceBroker initialized")

    def check_balance(self) -> float:
        """检查账户余额（USDT）"""
        try:
            resp = self.client.balance()
            for item in resp:
                if item['asset'] == 'USDT':
                    balance = float(item['balance'])
                    logger.info(f"Balance: {balance} USDT")
                    return balance
            return 0.0
        except ClientError as e:
            logger.error(f"Balance check failed: {e}")
            return 0.0

    def order_open(self, code: str, oside: str, otype: str,
                   osize: float, oprice: float = None) -> dict:
        """
        开仓

        Args:
            code: 交易对 (如 "ETHUSDT")
            oside: 方向 "LONG" / "SHORT"
            otype: "MARKET" / "LIMIT"
            osize: 数量
            oprice: 价格（市价单传None）

        Returns:
            dict: 执行结果
        """
        try:
            side = "BUY" if oside == "LONG" else "SELL"
            params = {
                'symbol': code,
                'side': side,
                'type': otype,
                'quantity': float(osize),
            }
            if otype == 'LIMIT' and oprice:
                params['price'] = float(oprice)
                params['timeInForce'] = 'GTC'

            ret = self.client.new_order(**params)
            logger.info(f"Order OPEN success: {ret.get('orderId')}")

            # 市价单立即获取成交价
            deal_price = None
            status = ORDER_STATUS_FILLED
            if 'fills' in ret and ret['fills']:
                deal_price = sum(float(f['price']) * float(f['qty'])
                                 for f in ret['fills']) / sum(
                    float(f['qty']) for f in ret['fills'])
            elif otype == 'MARKET':
                status = ORDER_STATUS_NA

            return {
                'success': True,
                'order_id': ret.get('orderId'),
                'deal_price': deal_price,
                'status': status,
            }

        except ClientError as e:
            logger.error(f"Order OPEN failed: {e}")
            return {
                'success': False,
                'order_id': None,
                'deal_price': None,
                'status': ORDER_STATUS_FAILED,
                'error': str(e),
            }

    def order_close(self, code: str, oside: str, otype: str,
                    osize: float, oprice: float = None) -> dict:
        """
        平仓
        """
        try:
            side = "SELL" if oside == "LONG" else "BUY"
            params = {
                'symbol': code,
                'side': side,
                'type': otype,
                'quantity': float(osize),
            }
            if otype == 'LIMIT' and oprice:
                params['price'] = float(oprice)
                params['timeInForce'] = 'GTC'

            ret = self.client.new_order(**params)
            logger.info(f"Order CLOSE success: {ret.get('orderId')}")

            deal_price = None
            if 'fills' in ret and ret['fills']:
                deal_price = sum(float(f['price']) * float(f['qty'])
                                 for f in ret['fills']) / sum(
                    float(f['qty']) for f in ret['fills'])

            return {
                'success': True,
                'order_id': ret.get('orderId'),
                'deal_price': deal_price,
                'profit': 0.0,  # 利润由 OrderInstance 计算
                'status': ORDER_STATUS_FILLED,
            }

        except ClientError as e:
            logger.error(f"Order CLOSE failed: {e}")
            return {
                'success': False,
                'order_id': None,
                'deal_price': None,
                'profit': 0.0,
                'status': ORDER_STATUS_FAILED,
                'error': str(e),
            }

    def get_order_status(self, order_id: str) -> str:
        """获取订单状态（简化实现）"""
        return ORDER_STATUS_FILLED

    def get_position(self, code: str) -> dict:
        """获取持仓"""
        try:
            positions = self.client.get_position_risk(symbol=code)
            if positions:
                return positions[0]
            return {}
        except ClientError as e:
            logger.error(f"Get position failed: {e}")
            return {}