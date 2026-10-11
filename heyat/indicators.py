"""اندیکاتورهای تکنیکال روی کندل روزانه. بدون وابستگی به TA-Lib."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from heyat.models import Bar, Quote


@dataclass(slots=True)
class Indicators:
    rsi: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    macd_cross: str | None = None  # up | down | none
    stoch_k: float | None = None
    stoch_d: float | None = None
    bb_pct_b: float | None = None
    bb_width: float | None = None
    sma20: float | None = None
    sma50: float | None = None
    sma200: float | None = None
    ema9: float | None = None
    ema21: float | None = None
    above_sma20: bool | None = None
    above_sma50: bool | None = None
    sma20_gt_sma50: bool | None = None
    adx: float | None = None
    plus_di: float | None = None
    minus_di: float | None = None
    atr_pct: float | None = None
    cci: float | None = None
    mfi: float | None = None
    obv_slope: float | None = None
    williams_r: float | None = None
    roc3: float | None = None
    roc5: float | None = None
    roc7: float | None = None
    volume_ratio: float | None = None
    ichimoku: str | None = None  # above | inside | below
    ret3: float | None = None
    ret5: float | None = None
    ret7: float | None = None
    bars_used: int = 0


def _last(values: np.ndarray) -> float | None:
    if values.size == 0 or np.isnan(values[-1]):
        return None
    return float(values[-1])


def ema(values: np.ndarray, period: int) -> np.ndarray:
    out = np.full(values.shape, np.nan)
    if values.size < period:
        return out
    seed = float(np.mean(values[:period]))
    out[period - 1] = seed
    alpha = 2 / (period + 1)
    for i in range(period, values.size):
        out[i] = alpha * values[i] + (1 - alpha) * out[i - 1]
    return out


def sma(values: np.ndarray, period: int) -> np.ndarray:
    out = np.full(values.shape, np.nan)
    if values.size < period:
        return out
    window = np.cumsum(values)
    out[period - 1 :] = (window[period - 1 :] - np.concatenate(([0.0], window[:-period]))) / period
    return out


def wilder(values: np.ndarray, period: int) -> np.ndarray:
    out = np.full(values.shape, np.nan)
    if values.size < period:
        return out
    seed = float(np.sum(values[:period]) / period)
    out[period - 1] = seed
    for i in range(period, values.size):
        out[i] = (out[i - 1] * (period - 1) + values[i]) / period
    return out


def rsi(close: np.ndarray, period: int = 14) -> float | None:
    if close.size <= period:
        return None
    delta = np.diff(close)
    gain = np.clip(delta, 0, None)
    loss = np.clip(-delta, 0, None)
    avg_gain = wilder(gain, period)
    avg_loss = wilder(loss, period)
    # wilder arrays align with delta, which is one shorter than close.
    g = avg_gain[-1]
    l = avg_loss[-1]
    if np.isnan(g) or np.isnan(l):
        return None
    if l == 0:
        return 100.0 if g > 0 else 50.0
    rs = g / l
    return float(100 - (100 / (1 + rs)))


def macd_parts(close: np.ndarray) -> tuple[float | None, float | None, float | None, str | None]:
    if close.size < 35:
        return None, None, None, None
    line = ema(close, 12) - ema(close, 26)
    # Signal is EMA of the MACD line. Seed it once the line itself is valid.
    valid = ~np.isnan(line)
    if valid.sum() < 9:
        return None, None, None, None
    signal = np.full(line.shape, np.nan)
    idx = np.flatnonzero(valid)
    start = idx[0]
    series = line[start:]
    signal[start:] = ema(series, 9)
    hist = line - signal
    if np.isnan(hist[-1]):
        return None, None, None, None
    cross = "none"
    if hist.size >= 2 and not np.isnan(hist[-2]):
        if hist[-2] <= 0 < hist[-1]:
            cross = "up"
        elif hist[-2] >= 0 > hist[-1]:
            cross = "down"
    return float(line[-1]), float(signal[-1]), float(hist[-1]), cross


def stochastic(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> tuple[float | None, float | None]:
    if close.size < period + 3:
        return None, None
    k = np.full(close.shape, np.nan)
    for i in range(period - 1, close.size):
        lo = np.min(low[i - period + 1 : i + 1])
        hi = np.max(high[i - period + 1 : i + 1])
        if hi == lo:
            k[i] = 50.0
        else:
            k[i] = (close[i] - lo) / (hi - lo) * 100
    d = sma(k, 3)
    return _last(k), _last(d)


def bollinger(close: np.ndarray, period: int = 20) -> tuple[float | None, float | None]:
    if close.size < period:
        return None, None
    window = close[-period:]
    mid = float(np.mean(window))
    std = float(np.std(window, ddof=0))
    if mid == 0:
        return None, None
    upper = mid + 2 * std
    lower = mid - 2 * std
    width = (upper - lower) / mid * 100
    if upper == lower:
        return 0.5, width
    pct_b = (float(close[-1]) - lower) / (upper - lower)
    return pct_b, width


def atr_pct(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> float | None:
    if close.size <= period:
        return None
    prev = close[:-1]
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - prev), np.abs(low[1:] - prev)))
    smoothed = wilder(tr, period)
    last = smoothed[-1]
    if np.isnan(last) or close[-1] == 0:
        return None
    return float(last / close[-1] * 100)


def adx_parts(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> tuple[float | None, float | None, float | None]:
    if close.size < period * 2 + 2:
        return None, None, None
    up = high[1:] - high[:-1]
    down = low[:-1] - low[1:]
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    prev = close[:-1]
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - prev), np.abs(low[1:] - prev)))
    atr = wilder(tr, period)
    plus_s = wilder(plus_dm, period)
    minus_s = wilder(minus_dm, period)
    with np.errstate(divide="ignore", invalid="ignore"):
        plus_di = 100 * plus_s / atr
        minus_di = 100 * minus_s / atr
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    dx = np.where(np.isfinite(dx), dx, np.nan)
    # Wilder of DX. Drop the leading NaNs so the seed is a real window.
    finite = dx[np.isfinite(dx)]
    if finite.size < period:
        return None, None, None
    adx_line = wilder(finite, period)
    if np.isnan(adx_line[-1]):
        return None, None, None
    pdi = plus_di[-1]
    mdi = minus_di[-1]
    if not np.isfinite(pdi) or not np.isfinite(mdi):
        return float(adx_line[-1]), None, None
    return float(adx_line[-1]), float(pdi), float(mdi)


def cci(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 20) -> float | None:
    if close.size < period:
        return None
    tp = (high + low + close) / 3
    window = tp[-period:]
    mean = float(np.mean(window))
    mad = float(np.mean(np.abs(window - mean)))
    if mad == 0:
        return 0.0
    return float((tp[-1] - mean) / (0.015 * mad))


def mfi(high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, period: int = 14) -> float | None:
    if close.size <= period:
        return None
    tp = (high + low + close) / 3
    raw = tp * volume
    delta = np.diff(tp)
    pos = np.where(delta > 0, raw[1:], 0.0)
    neg = np.where(delta < 0, raw[1:], 0.0)
    pos_sum = np.sum(pos[-period:])
    neg_sum = np.sum(neg[-period:])
    if neg_sum == 0:
        return 100.0 if pos_sum > 0 else 50.0
    ratio = pos_sum / neg_sum
    return float(100 - (100 / (1 + ratio)))


def obv_slope(close: np.ndarray, volume: np.ndarray, lookback: int = 10) -> float | None:
    if close.size < lookback + 1:
        return None
    direction = np.sign(np.diff(close))
    obv = np.cumsum(direction * volume[1:])
    window = obv[-lookback:]
    if np.allclose(window, window[0]):
        return 0.0
    x = np.arange(lookback, dtype=float)
    slope = float(np.polyfit(x, window, 1)[0])
    scale = float(np.mean(volume[-lookback:])) or 1.0
    return slope / scale


def williams_r(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> float | None:
    if close.size < period:
        return None
    hi = float(np.max(high[-period:]))
    lo = float(np.min(low[-period:]))
    if hi == lo:
        return -50.0
    return float((hi - close[-1]) / (hi - lo) * -100)


def roc(close: np.ndarray, period: int) -> float | None:
    if close.size <= period or close[-period - 1] == 0:
        return None
    return float((close[-1] / close[-period - 1] - 1) * 100)


def ichimoku_state(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> str | None:
    # Cloud that applies to *today* was computed 26 sessions ago.
    if close.size < 78:
        return None
    def midpoint(h, l, i, period):
        return (np.max(h[i - period + 1 : i + 1]) + np.min(l[i - period + 1 : i + 1])) / 2

    i = close.size - 1 - 26
    if i < 51:
        return None
    tenkan = midpoint(high, low, i, 9)
    kijun = midpoint(high, low, i, 26)
    span_a = (tenkan + kijun) / 2
    span_b = midpoint(high, low, i, 52)
    top = max(span_a, span_b)
    bottom = min(span_a, span_b)
    price = float(close[-1])
    if price > top:
        return "above"
    if price < bottom:
        return "below"
    return "inside"


def live_bars(quote: Quote) -> list[Bar]:
    bars = list(quote.bars)
    if not quote.last:
        return bars
    today = Bar(
        date="live",
        open=quote.first or quote.last,
        high=quote.high or max(quote.last, quote.first or quote.last),
        low=quote.low or min(quote.last, quote.first or quote.last),
        close=quote.last,
        volume=quote.volume or 0,
    )
    if bars and bars[-1].date == "live":
        bars[-1] = today
        return bars
    previous = bars[-1].close if bars else 0
    if previous and abs(previous - quote.last) / quote.last < 0.0008:
        bars[-1] = today
    else:
        bars.append(today)
    return bars


def compute_indicators(quote: Quote) -> Indicators:
    bars = live_bars(quote)
    ind = Indicators(bars_used=len(bars))
    if len(bars) < 16:
        return ind
    close = np.array([b.close for b in bars], dtype=float)
    high = np.array([b.high for b in bars], dtype=float)
    low = np.array([b.low for b in bars], dtype=float)
    volume = np.array([b.volume for b in bars], dtype=float)
    ind.rsi = rsi(close)
    ind.macd, ind.macd_signal, ind.macd_hist, ind.macd_cross = macd_parts(close)
    ind.stoch_k, ind.stoch_d = stochastic(high, low, close)
    ind.bb_pct_b, ind.bb_width = bollinger(close)
    ind.sma20 = _last(sma(close, 20))
    ind.sma50 = _last(sma(close, 50))
    ind.sma200 = _last(sma(close, 200))
    ind.ema9 = _last(ema(close, 9))
    ind.ema21 = _last(ema(close, 21))
    price = float(close[-1])
    if ind.sma20:
        ind.above_sma20 = price >= ind.sma20
    if ind.sma50:
        ind.above_sma50 = price >= ind.sma50
    if ind.sma20 and ind.sma50:
        ind.sma20_gt_sma50 = ind.sma20 >= ind.sma50
    ind.adx, ind.plus_di, ind.minus_di = adx_parts(high, low, close)
    ind.atr_pct = atr_pct(high, low, close)
    ind.cci = cci(high, low, close)
    ind.mfi = mfi(high, low, close, volume)
    ind.obv_slope = obv_slope(close, volume)
    ind.williams_r = williams_r(high, low, close)
    ind.roc3 = roc(close, 3)
    ind.roc5 = roc(close, 5)
    ind.roc7 = roc(close, 7)
    vol_avg = _last(sma(volume, 20))
    if vol_avg:
        ind.volume_ratio = float(volume[-1] / vol_avg) if vol_avg else None
    ind.ichimoku = ichimoku_state(high, low, close)
    ind.ret3 = roc(close, 3)
    ind.ret5 = roc(close, 5)
    ind.ret7 = roc(close, 7)
    return ind
