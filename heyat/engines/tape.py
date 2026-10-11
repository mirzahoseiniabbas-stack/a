"""میز تابلو: صف، سرانه، قدرت خریدار، حجم مبنا و فاصله تا آستانه."""

from __future__ import annotations

from dataclasses import dataclass

from heyat.models import Quote


HALT_WORDS = ("متوقف", "ممنوع", "معلق", "تعلیق")
CONTINUOUS_STATES = {"", "A", "مجاز"}


@dataclass(slots=True)
class TapeRead:
    halted: bool
    at_ceiling: bool
    at_floor: bool
    buy_locked: bool
    sell_locked: bool
    buy_queue_heavy: bool
    sell_queue_heavy: bool
    executable_buy: bool
    executable_sell: bool
    range_position: float | None
    buyer_power: float | None
    buy_per_capita: float | None
    sell_per_capita: float | None
    real_net_volume: float
    legal_net_volume: float
    bid_volume: float
    ask_volume: float
    volume_to_base: float | None
    last_vs_close: float | None
    score: float | None
    stance: str
    reasons: list[str]
    execution_note: str


def _best(levels) -> tuple[float, float]:
    if not levels:
        return 0.0, 0.0
    return levels[0].volume or 0.0, levels[0].price or 0.0


def _per_capita(volume: float, count: float) -> float | None:
    if count <= 0 or volume <= 0:
        return None
    return volume / count


def _state_halted(state: str) -> bool:
    raw = (state or "").strip()
    if raw in CONTINUOUS_STATES or raw in {"AR", "مجاز-محفوظ"}:
        return False
    if raw in {"I", "IS", "IG", "IR"}:
        return True
    return any(word in raw for word in HALT_WORDS)


def read_tape(quote: Quote) -> TapeRead:
    reasons: list[str] = []
    halted = _state_halted(quote.state)
    last = quote.last or quote.close
    at_ceiling = bool(quote.tmax and last and last >= quote.tmax * 0.999)
    at_floor = bool(quote.tmin and last and last <= quote.tmin * 1.001)
    bid_volume, bid_price = _best(quote.bids)
    ask_volume, _ask_price = _best(quote.asks)
    book = bool(quote.bids or quote.asks)

    range_position = None
    if quote.tmax and quote.tmin and quote.tmax > quote.tmin and last:
        range_position = (last - quote.tmin) / (quote.tmax - quote.tmin)

    heavy_bid = bid_volume >= max(quote.volume * 0.35, quote.base_volume * 0.8, 1)
    heavy_ask = ask_volume >= max(quote.volume * 0.35, quote.base_volume * 0.8, 1)
    buy_locked = (not halted) and at_ceiling and (not book or ask_volume <= 0 or heavy_bid)
    sell_locked = (not halted) and at_floor and (not book or bid_volume <= 0 or heavy_ask)
    buy_queue_heavy = buy_locked and (heavy_bid or ask_volume <= 0)
    sell_queue_heavy = sell_locked and (heavy_ask or bid_volume <= 0)

    if halted:
        executable_buy = False
        executable_sell = False
    elif book:
        executable_buy = (not buy_locked) and ask_volume > 0 and not at_ceiling
        executable_sell = (not sell_locked) and bid_volume > 0 and not at_floor
    else:
        executable_buy = not at_ceiling and not buy_locked
        executable_sell = not at_floor and not sell_locked

    buy_pc = _per_capita(quote.buy_i_volume, quote.buy_i_count)
    sell_pc = _per_capita(quote.sell_i_volume, quote.sell_i_count)
    buyer_power = (buy_pc / sell_pc) if buy_pc and sell_pc else None
    real_net = quote.buy_i_volume - quote.sell_i_volume
    legal_net = quote.buy_n_volume - quote.sell_n_volume
    volume_to_base = (quote.volume / quote.base_volume) if quote.base_volume else None
    last_vs_close = None
    if quote.close and last:
        last_vs_close = (last - quote.close) / quote.close * 100

    score = 50.0
    if buyer_power is not None:
        if buyer_power >= 2:
            score += 16
            reasons.append(f"قدرت خریدار حقیقی {buyer_power:.2f} است؛ سرانهٔ خرید دست‌کم دو برابر فروش.")
        elif buyer_power >= 1.25:
            score += 9
            reasons.append(f"قدرت خریدار حقیقی {buyer_power:.2f} است و سمت خرید سنگین‌تر است.")
        elif buyer_power <= 0.7:
            score -= 14
            reasons.append(f"قدرت خریدار حقیقی ضعیف است ({buyer_power:.2f}).")
        else:
            reasons.append(f"قدرت خریدار حقیقی متعادل است ({buyer_power:.2f}).")
    else:
        score -= 4
        reasons.append("سرانهٔ حقیقی این لحظه در خوراک نیست.")

    if real_net > 0:
        score += 7
        reasons.append("حجم خرید حقیقی از فروش حقیقی بیشتر است؛ ورود پول خرد مثبت است.")
    elif real_net < 0:
        score -= 7
        reasons.append("حجم فروش حقیقی بیشتر از خرید است.")

    if legal_net > 0:
        score += 6
        reasons.append("خالص امروز حقوقی مثبت است.")
    elif legal_net < 0:
        score -= 5
        reasons.append("حقوقی امروز خالص فروشنده است.")

    if last_vs_close is not None:
        if last_vs_close > 0.15:
            score += 5
            reasons.append("آخرین قیمت بالای قیمت پایانی است و فشار خرید هنوز در تابلو هست.")
        elif last_vs_close < -0.15:
            score -= 5
            reasons.append("آخرین قیمت زیر پایانی است.")

    if volume_to_base is not None:
        if volume_to_base >= 2:
            score += 7
            reasons.append(f"حجم معامله {volume_to_base:.1f} برابر حجم مبنا شده.")
        elif volume_to_base >= 1:
            score += 3
        elif volume_to_base < 0.25:
            score -= 6
            reasons.append("حجم نسبت به حجم مبنا کم است و تابلو هنوز جدی نشده.")

    if book and (bid_volume + ask_volume) > 0:
        imbalance = bid_volume / (bid_volume + ask_volume)
        if imbalance >= 0.68:
            score += 6
            reasons.append("حجم سرخط خرید از سرخط فروش بیشتر است.")
        elif imbalance <= 0.32:
            score -= 6
            reasons.append("سرخط فروش سنگین‌تر از سرخط خرید است.")

    if range_position is not None and range_position >= 0.9:
        score -= 8
        reasons.append("قیمت به سقف دامنه چسبیده؛ برای خرید دیر است.")
    if at_floor:
        score -= 8

    if halted:
        note = "نماد متوقف یا ممنوع است و سفارش تازه اجرا نمی‌شود."
        stance = "avoid"
    elif buy_queue_heavy:
        note = "صف خرید سنگین است و فروشنده‌ای برای اجرای خرید دیده نمی‌شود."
        stance = "avoid"
        score = min(score, 45)
    elif buy_locked:
        note = "قیمت در سقف دامنه قفل است و امکان خرید عملی نیست."
        stance = "avoid"
    elif sell_queue_heavy:
        note = "صف فروش سنگین است؛ فروش تازه به‌سختی اجرا می‌شود و خرید هم افتادن وسط فشار فروش است."
        stance = "avoid"
    elif not executable_buy and not executable_sell:
        note = "عمق سفارش برای اجرای مطمئن دیده نمی‌شود."
        stance = "watch"
    else:
        note = "سفارش سمت مقابل هنوز هست و معامله خارج از صف سنگین ممکن است."
        stance = "buy" if score >= 60 else "sell" if score <= 40 else "watch"

    score = max(0.0, min(100.0, score))
    return TapeRead(
        halted=halted,
        at_ceiling=at_ceiling,
        at_floor=at_floor,
        buy_locked=buy_locked,
        sell_locked=sell_locked,
        buy_queue_heavy=buy_queue_heavy,
        sell_queue_heavy=sell_queue_heavy,
        executable_buy=executable_buy,
        executable_sell=executable_sell,
        range_position=range_position,
        buyer_power=buyer_power,
        buy_per_capita=buy_pc,
        sell_per_capita=sell_pc,
        real_net_volume=real_net,
        legal_net_volume=legal_net,
        bid_volume=bid_volume,
        ask_volume=ask_volume,
        volume_to_base=volume_to_base,
        last_vs_close=last_vs_close,
        score=score,
        stance=stance,
        reasons=reasons[:5],
        execution_note=note,
    )
