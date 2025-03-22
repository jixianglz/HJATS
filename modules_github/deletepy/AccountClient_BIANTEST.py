# -*- coding: utf-8 -*-
"""
Created on Sun Aug 13 16:31:47 2023

@author: Administrator
"""




binance_api_key='gV197J8sk98FJPIg9GPeJ8ioaOwD776YMD52CaLKYPOVE1FiPt0lXA1MrD1RGz83'
binance_api_secret='boWu8BthROkTQq9Ul9eGUevehmRlX9U0UIJx45xdFK9ePB044hY6kztVnsXLwSo6'


import logging
from binance.um_futures import UMFutures
from binance.lib.utils import config_logging
from binance.error import ClientError

#config_logging(logging, logging.DEBUG)
#config_logging(logging, logging.ERROR)

key = binance_api_key
secret = binance_api_secret

um_futures_client = UMFutures(key=key, secret=secret)

try:
    response = um_futures_client.balance(recvWindow=5000)
    logging.info(response)
except ClientError as error:
    logging.error(
        "Found error. status: {}, error code: {}, error message: {}".format(
            error.status_code, error.error_code, error.error_message
        )
    )