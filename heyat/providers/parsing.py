"""خواندن فیلدهای ناهمگون تی‌اس‌ئی‌ام‌سی و BrsApi بدون حدسِ خطرناک روی حروف بزرگ و کوچک."""

from __future__ import annotations

from heyat.models import Level, norm_fa


def pick(row: dict, names: tuple[str, ...], default=None):
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return default


def num(row: dict, names: tuple[str, ...]) -> float | None:
    raw = pick(row, names)
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        if isinstance(raw, float) and raw != raw:
            return None
        return float(raw)
    text = str(raw).strip().replace(",", "").replace("٬", "").replace("٫", ".")
    if not text or text in {"-", "None", "nan"}:
        return None
    negative = text.endswith("-") and text[:-1].replace(".", "", 1).isdigit()
    if negative:
        text = "-" + text[:-1]
    try:
        return float(text)
    except ValueError:
        return None


def text(row: dict, names: tuple[str, ...], default: str = "") -> str:
    raw = pick(row, names, default)
    return norm_fa(str(raw)) if raw is not None else default


def levels_from_flat(row: dict) -> tuple[list[Level], list[Level]]:
    bids: list[Level] = []
    asks: list[Level] = []
    for i in range(1, 6):
        suffix = str(i)
        bid_price = num(row, (f"pd{suffix}", f"pMeDem{suffix}", f"bidPrice{suffix}"))
        bid_vol = num(row, (f"qd{suffix}", f"qTitMeDem{suffix}", f"bidVolume{suffix}"))
        bid_count = num(row, (f"zd{suffix}", f"zOrdMeDem{suffix}", f"bidCount{suffix}"))
        ask_price = num(row, (f"po{suffix}", f"pMeOf{suffix}", f"askPrice{suffix}"))
        ask_vol = num(row, (f"qo{suffix}", f"qTitMeOf{suffix}", f"askVolume{suffix}"))
        ask_count = num(row, (f"zo{suffix}", f"zOrdMeOf{suffix}", f"askCount{suffix}"))
        if any(v not in (None, 0) for v in (bid_price, bid_vol, bid_count)):
            bids.append(Level(bid_price or 0, bid_vol or 0, bid_count or 0))
        if any(v not in (None, 0) for v in (ask_price, ask_vol, ask_count)):
            asks.append(Level(ask_price or 0, ask_vol or 0, ask_count or 0))
    return bids, asks


def levels_from_rows(rows) -> tuple[list[Level], list[Level]]:
    bids: list[Level] = []
    asks: list[Level] = []
    if not isinstance(rows, list):
        return bids, asks
    ordered = sorted(rows, key=lambda item: num(item, ("number", "n", "level")) or 0)
    for item in ordered:
        if not isinstance(item, dict):
            continue
        bid_price = num(item, ("pMeDem", "pd", "pmd", "bid_price"))
        bid_vol = num(item, ("qTitMeDem", "qd", "qmd", "bid_volume"))
        bid_count = num(item, ("zOrdMeDem", "zd", "zmd", "bid_count"))
        ask_price = num(item, ("pMeOf", "po", "pmo", "ask_price"))
        ask_vol = num(item, ("qTitMeOf", "qo", "qmo", "ask_volume"))
        ask_count = num(item, ("zOrdMeOf", "zo", "zmo", "ask_count"))
        if any(v not in (None, 0) for v in (bid_price, bid_vol)):
            bids.append(Level(bid_price or 0, bid_vol or 0, bid_count or 0))
        if any(v not in (None, 0) for v in (ask_price, ask_vol)):
            asks.append(Level(ask_price or 0, ask_vol or 0, ask_count or 0))
    return bids, asks


def instrument_kind(symbol: str, yval: str | None, name: str = "") -> str:
    """سهام و صندوق می‌مانند. حق تقدم، اختیار و اوراق از فهرست پیشنهاد کنار می‌روند."""

    y = (yval or "").strip()
    if symbol.endswith("ح") or y in {"303", "304"}:
        return "right"
    if symbol.startswith(("ض", "ط")) or y in {"311", "312", "320", "321", "322", "600"}:
        return "other"
    if y in {"306", "307", "208", "706", "803"}:
        return "other"
    if y in {"305", "380", "309", "701"} or "صندوق" in name:
        return "etf"
    return "stock"


def unwrap_rows(payload) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    for key in (
        "marketwatch",
        "data",
        "items",
        "Items",
        "clientType",
        "clientTypeAllDto",
        "closingPriceDaily",
        "preparedData",
        "msg",
        "indexB1",
    ):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    # A single-key envelope.
    lists = [value for value in payload.values() if isinstance(value, list)]
    if len(lists) == 1:
        return [row for row in lists[0] if isinstance(row, dict)]
    return []
