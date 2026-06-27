"""Tests for signalAlg"""
import pytest, numpy as np, pandas as pd
from strategies import signalAlg

class TestSignalAlg:
    def test_flat_no_signal(self):
        np.random.seed(42)
        dates = pd.date_range('2026-01-01', periods=50, freq='5min')
        df = pd.DataFrame({'open':[2000]*50,'high':[2000]*50,'low':[2000]*50,'close':[2000]*50,'volume':[100]*50}, index=dates)
        r = signalAlg.run({'dataset': df})
        assert r[0] == 0

    def test_insufficient_data(self):
        dates = pd.date_range('2026-01-01', periods=20, freq='5min')
        df = pd.DataFrame({'open':range(20),'high':range(20),'low':range(20),'close':range(20),'volume':range(20)}, index=dates)
        r = signalAlg.run({'dataset': df})
        assert r[0] == 0
