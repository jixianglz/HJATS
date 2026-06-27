"""HJATS test fixtures"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd
import numpy as np
import pytest

@pytest.fixture
def empty_pool():
    return {}

@pytest.fixture
def account_100():
    return {"asset": 100.0}

@pytest.fixture
def account_0():
    return {"asset": 0.0}

# === Sample Kline Data ===

def _make_klines(periods, close_values):
    import pandas as pd
    import numpy as np
    np.random.seed(42)
    dates = pd.date_range("2026-01-01", periods=len(close_values), freq="5min")
    df = pd.DataFrame({
        "open": [c-2 for c in close_values],        "high": [c+3 for c in close_values],
        "low": [c-3 for c in close_values],
        "close": close_values,
        "volume": np.random.uniform(100, 500, len(close_values)),
    }, index=dates)
    df.index.name = "time"
    return df

@pytest.fixture
def sample_klines_50():
    import numpy as np
    close = np.concatenate([np.linspace(2000,1950,20), np.linspace(1950,2050,30)])
    return _make_klines(50, close)

@pytest.fixture
def short_klines_20():
    import numpy as np
    close = np.linspace(2000, 2050, 20)
    return _make_klines(20, close)
