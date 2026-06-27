"""Tests for orderAlg"""
import pytest
from strategies import orderAlg

def make_order_instance(uid, side, size, price):
    from src.engine.order_instance import OrderInstance
    f = ["test", "id", uid, "OPEN", "MARKET", "processing",
         "2026-01-01", "ETH-USD", side, str(size),
         str(price), str(price), str(price)]
    oi = OrderInstance(f)
    oi.inc_position(f)  # 需要先 inc_position 来建立持仓
    return oi

class TestOrderAlg:

    def test_signal1_open_long(self, sample_klines_50, empty_pool, account_100):
        """signal=1, no position -> open LONG"""
        data = {"dataset": sample_klines_50, "c_signal": 1, "orderpool": empty_pool, "orderaccount": account_100}
        orders = orderAlg.run(data)
        assert len(orders) == 1
        assert orders[0]["oaction"] == "OPEN"
        assert orders[0]["oside"] == "LONG"

    def test_signal1_already_long(self, sample_klines_50, account_100):
        """signal=1, already LONG -> hold"""
        oi = make_order_instance("long_1", "LONG", 0.01, 2000)
        orders = orderAlg.run({"dataset": sample_klines_50, "c_signal": 1, "orderpool": {"long_1": oi}, "orderaccount": account_100})
        assert orders == []

    def test_signal1_close_short_open_long(self, sample_klines_50, account_100):
        """signal=1, has SHORT -> close SHORT + open LONG"""
        oi = make_order_instance("short_1", "SHORT", 0.01, 2000)
        orders = orderAlg.run({"dataset": sample_klines_50, "c_signal": 1, "orderpool": {"short_1": oi}, "orderaccount": account_100})
        assert len(orders) == 2
        assert orders[0]["oaction"] == "CLOSE"; assert orders[0]["oside"] == "SHORT"
        assert orders[1]["oaction"] == "OPEN"; assert orders[1]["oside"] == "LONG"

    def test_signal_neg1_open_short(self, sample_klines_50, empty_pool, account_100):
        orders = orderAlg.run({"dataset": sample_klines_50, "c_signal": -1, "orderpool": empty_pool, "orderaccount": account_100})
        assert len(orders) == 1
        assert orders[0]["oaction"] == "OPEN"; assert orders[0]["oside"] == "SHORT"

    def test_signal_neg1_already_short(self, sample_klines_50, account_100):
        oi = make_order_instance("short_1", "SHORT", 0.01, 2000)
        orders = orderAlg.run({"dataset": sample_klines_50, "c_signal": -1, "orderpool": {"short_1": oi}, "orderaccount": account_100})
        assert orders == []

    def test_signal_0_hold(self, sample_klines_50, empty_pool, account_100):
        orders = orderAlg.run({"dataset": sample_klines_50, "c_signal": 0, "orderpool": empty_pool, "orderaccount": account_100})
        assert orders == []

    def test_insufficient_balance(self, sample_klines_50, empty_pool, account_0):
        orders = orderAlg.run({"dataset": sample_klines_50, "c_signal": 1, "orderpool": empty_pool, "orderaccount": account_0})
        assert orders == []
