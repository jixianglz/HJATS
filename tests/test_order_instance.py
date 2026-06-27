"""Tests for OrderInstance"""
import pytest
from src.engine.order_instance import OrderInstance

def make_forder(uid, side, osize, oprice, tickprice):
    """Helper: create forder list"""
    return ["test", "id1", uid, "OPEN", "MARKET", "processing",
            "2026-01-01", "ETH-USD", side, str(osize),
            str(oprice), str(oprice), str(tickprice)]

class TestOrderInstance:

    def test_init_long(self):
        f = make_forder("uid1", "LONG", 0.01, 2000, 2000)
        oi = OrderInstance(f)
        oi.inc_position(f)
        assert oi.side == "LONG"
        assert oi.osize == 0.01
        assert oi.status == "processing"

    def test_inc_position(self):
        f = make_forder("uid1", "LONG", 0.01, 2000, 2000)
        oi = OrderInstance(f)
        oi.inc_position(f)
        f2 = make_forder("uid1", "LONG", 0.01, 2100, 2100)
        oi.inc_position(f2)
        assert oi.size == 0.02
        assert oi.aveprice == 2050.0

    def test_dec_position_long_profit(self):
        f = make_forder("uid1", "LONG", 0.01, 2000, 2000)
        oi = OrderInstance(f)
        oi.inc_position(f)
        close_f = make_forder("uid1", "LONG", 0.01, 2100, 2100)
        profit, err = oi.dec_position(close_f)
        assert profit == pytest.approx(1.0)
        assert err == 0

    def test_dec_position_long_loss(self):
        f = make_forder("uid1", "LONG", 0.01, 2000, 2000)
        oi = OrderInstance(f)
        oi.inc_position(f)
        close_f = make_forder("uid1", "LONG", 0.01, 1900, 1900)
        profit, err = oi.dec_position(close_f)
        assert profit == pytest.approx(-1.0)
