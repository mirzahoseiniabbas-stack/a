"""نمادهای نرمال‌شده‌ای که هر سه خوراک (تی‌اس‌ئی‌ام‌سی، BrsApi، نمونه) به آن می‌رسند."""

from __future__ import annotations

from dataclasses import dataclass, field


def norm_fa(text: str | None) -> str:
    if not text:
        return ""
    return (
        str(text)
        .replace("ي", "ی")
        .replace("ك", "ک")
        .replace("\u200c", "")
        .strip()
    )


@dataclass(slots=True)
class Level:
    price: float = 0
    volume: float = 0
    count: float = 0


@dataclass(slots=True)
class Bar:
    """کندل روزانه. ترتیب نگهداری: قدیمی به جدید."""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(slots=True)
class FlowDay:
    """یک روز حقیقی/حقوقی. ترتیب: قدیمی به جدید."""

    date: str
    buy_i_volume: float = 0
    buy_n_volume: float = 0
    sell_i_volume: float = 0
    sell_n_volume: float = 0
    buy_i_count: float = 0
    buy_n_count: float = 0
    sell_i_count: float = 0
    sell_n_count: float = 0
    buy_i_value: float = 0
    buy_n_value: float = 0
    sell_i_value: float = 0
    sell_n_value: float = 0


@dataclass(slots=True)
class Headline:
    title: str
    symbol: str = ""
    source: str = ""
    published: str = ""


@dataclass(slots=True)
class Quote:
    symbol: str
    name: str = ""
    ins_code: str = ""
    isin: str = ""
    market: str = ""
    industry: str = ""
    kind: str = "stock"  # stock | etf | right | other
    state: str = ""
    last: float = 0
    close: float = 0
    yesterday: float = 0
    first: float = 0
    low: float = 0
    high: float = 0
    tmin: float = 0
    tmax: float = 0
    volume: float = 0
    value: float = 0
    trades: float = 0
    base_volume: float = 0
    eps: float | None = None
    pe: float | None = None
    group_pe: float | None = None
    ps: float | None = None
    pb: float | None = None
    float_percent: float | None = None
    shares: float | None = None
    market_cap: float | None = None
    bids: list[Level] = field(default_factory=list)
    asks: list[Level] = field(default_factory=list)
    buy_i_volume: float = 0
    buy_n_volume: float = 0
    sell_i_volume: float = 0
    sell_n_volume: float = 0
    buy_i_count: float = 0
    buy_n_count: float = 0
    sell_i_count: float = 0
    sell_n_count: float = 0
    buy_i_value: float = 0
    buy_n_value: float = 0
    sell_i_value: float = 0
    sell_n_value: float = 0
    bars: list[Bar] = field(default_factory=list)
    flows: list[FlowDay] = field(default_factory=list)
    headlines: list[Headline] = field(default_factory=list)
    limit_inferred: bool = False

    def pct_from(self, price: float) -> float | None:
        if not self.yesterday or not price:
            return None
        return (price - self.yesterday) / self.yesterday * 100

    @property
    def pct_last(self) -> float | None:
        return self.pct_from(self.last)

    @property
    def pct_close(self) -> float | None:
        return self.pct_from(self.close or self.last)


@dataclass(slots=True)
class IndexQuote:
    name: str
    value: float | None = None
    change: float | None = None
    change_percent: float | None = None


@dataclass(slots=True)
class MarketSnapshot:
    quotes: list[Quote]
    headlines: list[Headline] = field(default_factory=list)
    indices: list[IndexQuote] = field(default_factory=list)
    source: str = "unknown"
    live: bool = False
    source_note: str = ""
    fetched_at: str = ""
    market_phase: str = "unknown"
