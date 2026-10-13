import numpy as np

from heyat.indicators import rsi


def test_rsi_follows_the_direction_of_a_one_way_market():
    up = 100 * np.cumprod(np.full(40, 1.01))
    down = 100 * np.cumprod(np.full(40, 0.99))
    assert rsi(up) > 70
    assert rsi(down) < 30


def test_flat_market_rsi_is_near_fifty():
    # Wilder RSI is undefined when every change is zero; a tiny two-sided wiggle stays mid-range.
    close = np.array([100 + (1 if i % 2 == 0 else -1) * 0.2 for i in range(40)], dtype=float)
    value = rsi(close)
    assert 40 < value < 60
