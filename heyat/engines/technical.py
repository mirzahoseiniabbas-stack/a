"""میز تکنیکال: روند، مومنتوم، نوسان و حجم."""

from __future__ import annotations

from dataclasses import dataclass

from heyat.indicators import Indicators, compute_indicators
from heyat.models import Quote


@dataclass(slots=True)
class TechnicalRead:
    score: float | None
    stance: str
    reasons: list[str]
    indicators: Indicators


def _fmt(value: float | None, digits: int = 0) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}f}"


def read_technical(quote: Quote, indicators: Indicators | None = None) -> TechnicalRead:
    ind = indicators if indicators is not None else compute_indicators(quote)
    if ind.rsi is None:
        return TechnicalRead(
            score=None,
            stance="unknown",
            reasons=["کندل روزانه برای RSI و مکدی کافی نیست."],
            indicators=ind,
        )

    score = 50.0
    reasons: list[str] = []
    rsi = ind.rsi
    if 45 <= rsi <= 64:
        score += 10
        reasons.append(f"RSI در ناحیهٔ متعادلِ رو به بالا است ({_fmt(rsi)}).")
    elif 32 <= rsi < 45:
        score += 6
        reasons.append(f"RSI از اشباع فروش برگشته ({_fmt(rsi)}) و هنوز گران نیست.")
    elif rsi < 30:
        score -= 4
        reasons.append(f"RSI اشباع فروش است ({_fmt(rsi)})؛ تا برگشت حجم، چاقوی در حال سقوط است.")
    elif rsi > 74:
        score -= 16
        reasons.append(f"RSI اشباع خرید است ({_fmt(rsi)}) و تعقیب قیمت دیر است.")
    elif rsi > 68:
        score -= 7
        reasons.append(f"RSI بالاست ({_fmt(rsi)}).")

    if ind.macd_cross == "up":
        score += 12
        reasons.append("هیستوگرام مکدی تازه بالای خط سیگنال آمده.")
    elif ind.macd_hist is not None and ind.macd_hist > 0:
        score += 6
        reasons.append("مکدی بالای سیگنال است.")
    elif ind.macd_cross == "down":
        score -= 12
        reasons.append("مکدی تازه به زیر سیگنال برگشته.")
    elif ind.macd_hist is not None and ind.macd_hist < 0:
        score -= 4

    if ind.above_sma20:
        score += 6
    elif ind.above_sma20 is False:
        score -= 5
        reasons.append("قیمت زیر میانگین ۲۰روزه است.")
    if ind.above_sma50:
        score += 4
    if ind.sma20_gt_sma50:
        score += 4
        reasons.append("میانگین ۲۰روزه بالای میانگین ۵۰روزه است.")
    elif ind.sma20_gt_sma50 is False:
        score -= 3

    if ind.adx is not None and ind.plus_di is not None and ind.minus_di is not None:
        if ind.adx >= 20 and ind.plus_di > ind.minus_di:
            score += 8
            reasons.append(f"ADX {_fmt(ind.adx)} و جهت مثبت؛ روند صعودی ساختار دارد.")
        elif ind.adx >= 20 and ind.minus_di > ind.plus_di:
            score -= 8
            reasons.append(f"ADX {_fmt(ind.adx)} و جهت منفی؛ روند نزولی غالب است.")

    if ind.bb_pct_b is not None:
        if ind.bb_pct_b > 1.05:
            score -= 8
            reasons.append("قیمت از باند بالای بولینگر بیرون زده.")
        elif 0.15 <= ind.bb_pct_b <= 0.75:
            score += 3

    if ind.stoch_k is not None and ind.stoch_k > 85:
        score -= 5
        reasons.append(f"استوکاستیک در اشباع خرید است ({_fmt(ind.stoch_k)}).")
    elif ind.stoch_k is not None and ind.stoch_k < 20:
        score += 2

    if ind.mfi is not None and ind.mfi > 82:
        score -= 5
    elif ind.mfi is not None and 45 <= ind.mfi <= 70:
        score += 3

    if ind.williams_r is not None and ind.williams_r > -15:
        score -= 3
    if ind.cci is not None and ind.cci > 180:
        score -= 4
    elif ind.cci is not None and -50 <= ind.cci <= 100:
        score += 2

    if ind.ichimoku == "above":
        score += 6
        reasons.append("قیمت بالای ابر ایچیموکو است.")
    elif ind.ichimoku == "below":
        score -= 6
        reasons.append("قیمت زیر ابر ایچیموکو است.")

    if ind.roc7 is not None:
        if ind.roc7 > 12:
            score -= 6
            reasons.append(f"رشد هفت‌روزه زیاد است ({ind.roc7:.1f}٪) و بخشی از حرکت خرج شده.")
        elif 0 < ind.roc7 <= 7:
            score += 4
            reasons.append(f"بازده هفت‌روزه ملایم و مثبت است ({ind.roc7:.1f}٪).")
        elif ind.roc7 < -8:
            score -= 3

    if ind.volume_ratio is not None and ind.volume_ratio >= 1.3 and (quote.pct_last or 0) > 0:
        score += 4
        reasons.append("حجم امروز بالاتر از میانگین ۲۰روزه و هم‌جهت با رشد قیمت است.")
    if ind.obv_slope is not None and ind.obv_slope > 0.15:
        score += 3
    elif ind.obv_slope is not None and ind.obv_slope < -0.15:
        score -= 3

    score = max(0.0, min(100.0, score))
    stance = "buy" if score >= 60 else "sell" if score <= 40 else "watch"
    return TechnicalRead(score=score, stance=stance, reasons=reasons[:6], indicators=ind)
