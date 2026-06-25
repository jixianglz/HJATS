"""
账户管理 - 加载交易所API配置
使用 .env 文件存储敏感信息，不再硬编码
"""
import os
import configparser
import logging

logger = logging.getLogger(__name__)


class AccountClient:
    """
    账户客户端

    从以下位置加载配置（优先级从高到低）:
    1. 环境变量 (BINANCE_API_KEY, BINANCE_API_SECRET)
    2. .env 文件
    3. strategies/config.ini (兼容旧配置，但不推荐)
    """

    def __init__(self, account_dic: dict = None):
        self.dex_name = 'binance'
        self.api_key = ''
        self.api_secret = ''

        if account_dic:
            # 从传入字典初始化
            self._init_from_dict(account_dic)
        else:
            # 自动加载配置
            self._auto_load_config()

        logger.info(f"AccountClient initialized: dex={self.dex_name}")

    def _init_from_dict(self, account_dic: dict):
        """从字典初始化"""
        self.dex_name = account_dic.get('dex', 'binance')
        self.api_key = account_dic.get('api_key', '')
        self.api_secret = account_dic.get('api_secret', '')

    def _auto_load_config(self):
        """自动加载配置"""
        # 1. 先检查环境变量
        self.api_key = os.environ.get('BINANCE_API_KEY', '')
        self.api_secret = os.environ.get('BINANCE_API_SECRET', '')

        if self.api_key and self.api_secret:
            logger.info("API keys loaded from environment variables")
            return

        # 2. 检查 .env 文件
        env_path = os.path.join(os.getcwd(), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('BINANCE_API_KEY='):
                        self.api_key = line.split('=', 1)[1].strip().strip("'\"")
                    elif line.startswith('BINANCE_API_SECRET='):
                        self.api_secret = line.split('=', 1)[1].strip().strip("'\"")

            if self.api_key and self.api_secret:
                logger.info("API keys loaded from .env file")
                return

        # 3. 回退到 config.ini
        config_path = os.path.join(os.getcwd(), 'strategies', 'config.ini')
        if os.path.exists(config_path):
            conf = configparser.ConfigParser()
            conf.read(config_path)
            try:
                self.api_key = conf.get('Dexinfo', 'binance_api_key', fallback='')
                self.api_secret = conf.get('Dexinfo', 'binance_api_secret', fallback='')
                if self.api_key and self.api_secret:
                    logger.warning("API keys loaded from config.ini (consider using .env instead)")
            except Exception:
                pass

    def to_dict(self) -> dict:
        """返回账户配置字典"""
        return {
            'dex': self.dex_name,
            'api_key': self.api_key,
            'api_secret': self.api_secret,
        }