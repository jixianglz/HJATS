"""Tests for LiveEngine components"""
import pytest
from unittest.mock import Mock, patch, PropertyMock
import threading
from datetime import datetime

# Test strategy_tick order_pool tracking


class TestLiveEngineOrderFlow:
    """Test OPEN->CLOSE order_pool lifecycle"""

    def test_order_pool_record_on_open(self):
        """OPEN should record position in order_pool"""
        pool = {}
        order = {"uid": "ma_long_1"}
        oside = "LONG"
        osize = 0.01
        current_price = 2100.0
        # Simulate what LiveEngine does on OPEN success
        pool[order["uid"]] = {
            "uid": order["uid"],
            "side": oside,
            "size": osize,
            "entry_price": current_price,
            "open_time": datetime.now().strftime("%H:%M:%S"),
        }
        assert order["uid"] in pool
        assert pool[order["uid"]]["side"] == "LONG"
        assert pool[order["uid"]]["entry_price"] == 2100.0
        assert pool[order["uid"]]["size"] == 0.01

    def test_order_pool_read_on_close(self):
        """CLOSE should read entry_price from order_pool"""
        pool = {"ma_long_1": {"uid": "ma_long_1", "side": "LONG",
                              "size": 0.01, "entry_price": 2000.0}}
        order = {"uid": "ma_long_1"}
        current_price = 2100.0
        oside = "LONG"
        # Simulate CLOSE logic
        pos = pool.get(order["uid"], {})
        entry = pos.get("entry_price", current_price)
        pos_size = pos.get("size", 0.01)
        profit = (current_price - entry) * pos_size if oside == "LONG" else (entry - current_price) * pos_size
        assert profit == pytest.approx(1.0)  # (2100-2000)*0.01 = 1.0

    def test_order_pool_clean_on_close(self):
        """CLOSE should remove position from order_pool"""
        pool = {"ma_long_1": {"uid": "ma_long_1", "side": "LONG",
                              "size": 0.01, "entry_price": 2000.0}}
        order = {"uid": "ma_long_1"}
        if order["uid"] in pool:
            del pool[order["uid"]]
        assert order["uid"] not in pool

    def test_short_close_profit(self):
        """SHORT position close profit calculation"""
        pool = {"ma_short_1": {"uid": "ma_short_1", "side": "SHORT",
                               "size": 0.01, "entry_price": 2100.0}}
        order = {"uid": "ma_short_1"}
        current_price = 2000.0
        oside = "SHORT"
        pos = pool.get(order["uid"], {})
        entry = pos.get("entry_price", current_price)
        pos_size = pos.get("size", 0.01)
        profit = (current_price - entry) * pos_size if oside == "LONG" else (entry - current_price) * pos_size
        assert profit == pytest.approx(1.0)  # (2100-2000)*0.01 = 1.0


class TestLiveEnginePositionUpdate:
    """Test position status from order_pool"""

    def test_no_positions(self):
        """Empty order_pool -> side=None, size=0"""
        pool = {}
        pos_side = None
        pos_size = 0.0
        pos_entry = 0.0
        for uid, pdata in pool.items():
            pos_side = pdata["side"]
            pos_size += pdata["size"]
            pos_entry = pdata["entry_price"] if pos_entry == 0 else (pos_entry + pdata["entry_price"]) / 2
        assert pos_side is None
        assert pos_size == 0.0

    def test_one_position(self):
        """One position -> correct side/size/entry"""
        pool = {"l1": {"side": "LONG", "size": 0.01, "entry_price": 2000.0}}
        pos_side = None
        pos_size = 0.0
        pos_entry = 0.0
        for uid, pdata in pool.items():
            pos_side = pdata["side"]
            pos_size += pdata["size"]
            pos_entry = pdata["entry_price"] if pos_entry == 0 else (pos_entry + pdata["entry_price"]) / 2
        assert pos_side == "LONG"
        assert pos_size == 0.01
        assert pos_entry == 2000.0
