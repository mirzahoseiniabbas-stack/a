"""میز بازیگران: جمع‌کردن یا توزیع در پنجرهٔ ۳، ۵ و ۷ روزه.

خالص خرید حقوقی نمایندهٔ تجمیعی اشخاص حقوقی است، نه نام یک بازیگر خاص.
"""

from __future__ import annotations

from dataclasses import dataclass

from heyat.models import FlowDay, Quote


@dataclass(slots=True)
class PlayerRead:
    score: float | None
    stance: str
    reasons: list[str]
    net_legal_3: float | None = None
    net_legal_5: float | None = None
    net_legal_7: float | None = None
    net_legal_value_7: float | None = None
    buyer_power_5: float | None = None
    streak: int = 0


def _net(day: FlowDay) -> float:
    return day.buy_n_volume - day.sell_n_volume


def _value_net(day: FlowDay, fallback_price: float) -> float:
    if day.buy_n_value or day.sell_n_value:
        return day.buy_n_value - day.sell_n_value
    return _net(day) * fallback_price


def _window(flows: list[FlowDay], n: int) -> list[FlowDay]:
    if len(flows) < n:
        return []
    return flows[-n:]


def _power(days: list[FlowDay]) -> float | None:
    buy_vol = sum(d.buy_i_volume for d in days)
    sell_vol = sum(d.sell_i_volume for d in days)
    buy_count = sum(d.buy_i_count for d in days)
    sell_count = sum(d.sell_i_count for d in days)
    if buy_count <= 0 or sell_count <= 0 or buy_vol <= 0 or sell_vol <= 0:
        return None
    return (buy_vol / buy_count) / (sell_vol / sell_count)


def _streak(flows: list[FlowDay]) -> int:
    streak = 0
    for day in reversed(flows):
        net = _net(day)
        if net > 0:
            streak += 1
        else:
            break
    return streak


def read_players(quote: Quote) -> PlayerRead:
    flows = quote.flows
    if len(flows) < 3:
        return PlayerRead(
            score=None,
            stance="unknown",
            reasons=["سابقهٔ حقیقی/حقوقی برای خواندن روند چندروزه کافی نیست."],
        )

    price = quote.last or quote.close or 0
    last3 = _window(flows, 3)
    last5 = _window(flows, 5)
    last7 = _window(flows, 7)
    net3 = sum(_net(d) for d in last3) if last3 else None
    net5 = sum(_net(d) for d in last5) if last5 else None
    net7 = sum(_net(d) for d in last7) if last7 else None
    value7 = sum(_value_net(d, price) for d in last7) if last7 else None
    power5 = _power(last5 or last3)
    streak = _streak(flows)

    ret5 = None
    if len(quote.bars) >= 6 and quote.bars[-6].close:
        end = quote.last or quote.bars[-1].close
        ret5 = (end / quote.bars[-6].close - 1) * 100
    ret3 = None
    if len(quote.bars) >= 4 and quote.bars[-4].close:
        end = quote.last or quote.bars[-1].close
        ret3 = (end / quote.bars[-4].close - 1) * 100

    score = 50.0
    reasons: list[str] = []
    if net7 is not None and net7 > 0:
        score += 12
        reasons.append("در هفت جلسهٔ اخیر خالص خرید حقوقی مثبت است.")
    elif net7 is not None and net7 < 0:
        score -= 10
        reasons.append("در هفت جلسهٔ اخیر حقوقی خالص فروشنده بوده.")

    if net3 is not None and net5 is not None and net3 > 0 and net5 > 0:
        score += 8
        reasons.append("جمع‌کردن حقوقی در هر دو پنجرهٔ ۳ و ۵ روزه ادامه دارد.")
    elif net3 is not None and net3 < 0 and net7 is not None and net7 > 0:
        score -= 6
        reasons.append("روند هفت‌روزهٔ حقوقی مثبت بوده ولی سه روز اخیر برگشته.")

    if streak >= 3:
        score += 7
        reasons.append(f"حقوقی {streak} روز پیاپی خالص خریدار بوده.")

    if power5 is not None:
        if power5 >= 1.3:
            score += 8
            reasons.append(f"میانگین قدرت خریدار حقیقی پنج روز اخیر {power5:.2f} است.")
        elif power5 <= 0.75:
            score -= 8
            reasons.append(f"سرانهٔ فروش حقیقی در پنج روز اخیر غالب است ({power5:.2f}).")

    # جمع کردن در ضعف قیمت، یا توزیع بعد از رشد.
    if net5 is not None and ret5 is not None:
        if net5 > 0 and ret5 <= 1.5:
            score += 12
            reasons.append("قیمت در پنج روز اخیر جان نگرفته ولی حقوقی جمع کرده؛ الگوی انباشت است.")
        elif net5 < 0 and ret5 >= 4:
            score -= 14
            reasons.append("قیمت بالا آمده و حقوقی در حال عرضه است؛ الگوی توزیع است.")

    if net3 is not None and ret3 is not None and net3 > 0 and ret3 < 0:
        score += 6
        reasons.append("سه روز اخیر سهم منفی بوده و حقوقی همچنان خریدار است.")

    score = max(0.0, min(100.0, score))
    stance = "buy" if score >= 62 else "sell" if score <= 40 else "watch"
    return PlayerRead(
        score=score,
        stance=stance,
        reasons=reasons[:5] or ["جریان چندروزهٔ حقوقی جهت روشنی ندارد."],
        net_legal_3=net3,
        net_legal_5=net5,
        net_legal_7=net7,
        net_legal_value_7=value7,
        buyer_power_5=power5,
        streak=streak,
    )
