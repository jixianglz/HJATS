"""Tests for technical indicators"""
import pytest
import numpy as np
from strategies.indicators import sma, break_out

class TestIndicators:

    def test_sma_basic(self):
        assert sma([1,2,3,4,5], 3) == pytest.approx(2.0)
        assert sma([1,2,3,4,5], 5) == pytest.approx(3.0)

    def test_break_out_at_low(self):
        """last=min -> bull=0, bear=1"""
        ticks = [10, 20, 30, 40, 50]
        bull, bear = break_out(ticks, 3)
        assert bull == pytest.approx(0.0)
        assert bear == pytest.approx(1.0)

    def test_break_out_at_high(self):
        """last=max -> bull=1, bear=0"""
        ticks = [50, 40, 30, 20, 10]
        bull, bear = break_out(ticks, 3)
        assert bull == pytest.approx(1.0)
        assert bear == pytest.approx(0.0)
