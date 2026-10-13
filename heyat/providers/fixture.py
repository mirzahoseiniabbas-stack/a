"""دادهٔ آزمایشی برای وقتی دیده‌بان بورس از این شبکه در دسترس نیست.

نمادها ساختگی‌اند. این فهرست پیشنهاد معاملاتی بازار واقعی نیست.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from heyat.market_time import market_phase, tehran_now
from heyat.models import Bar, FlowDay, Headline, IndexQuote, Level, MarketSnapshot, Quote


def _closes(start: float, days: int, drift: float, shock: float = 0.008, seed: int = 1) -> list[float]:
    """مسیر پرنوسان حول یک رانش ملایم تا RSI به سقف یا کف نچسبد."""

    rng = random.Random(seed)
    price = start
    closes: list[float] = []
    for i in range(days):
        anchor = start * ((1 + drift) ** i)
        gap = (anchor - price) / price
        ret = drift * 0.25 + gap * 0.35 + rng.uniform(-shock, shock)
        price = max(1.0, price * (1 + ret))
        closes.append(price)
    return closes


def _rewrite_tail(closes: list[float], days: int, end_ratio: float) -> list[float]:
    """انتهای سری را طوری خم می‌کند که قیمت آخر نسبت به days روز قبل برابر end_ratio شود."""

    out = list(closes)
    if days <= 1 or len(out) <= days:
        return out
    anchor = out[-days - 1]
    target = anchor * end_ratio
    for step in range(1, days + 1):
        weight = step / days
        out[-days - 1 + step] = anchor + (target - anchor) * weight
    return out


def _bars(closes: list[float], volume: float) -> list[Bar]:
    bars: list[Bar] = []
    previous = closes[0]
    start = datetime(2026, 6, 1)
    for index, close in enumerate(closes):
        day = start + timedelta(days=index)
        high = max(previous, close) * 1.004
        low = min(previous, close) * 0.996
        bars.append(
            Bar(
                date=day.strftime("%Y%m%d"),
                open=previous,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
        previous = close
    return bars


def _flows(
    dates: list[str],
    *,
    legal_buy: float,
    legal_sell: float,
    retail_buy: float,
    retail_sell: float,
    retail_buy_count: float,
    retail_sell_count: float,
) -> list[FlowDay]:
    return [
        FlowDay(
            date=date,
            buy_i_volume=retail_buy,
            buy_n_volume=legal_buy,
            sell_i_volume=retail_sell,
            sell_n_volume=legal_sell,
            buy_i_count=retail_buy_count,
            sell_i_count=retail_sell_count,
            buy_n_count=4,
            sell_n_count=4,
        )
        for date in dates
    ]


def _quote(
    symbol: str,
    name: str,
    closes: list[float],
    *,
    last_ratio: float,
    industry: str,
    pe: float,
    group_pe: float,
    ps: float,
    eps: float,
    flows: list[FlowDay],
    buy_i: float,
    sell_i: float,
    buy_n: float,
    sell_n: float,
    buy_i_count: float,
    sell_i_count: float,
    bid: tuple[float, float, float],
    ask: tuple[float, float, float],
    volume_ratio: float = 1.4,
    base_volume: float = 1_000_000,
    state: str = "مجاز",
    headlines: list[Headline] | None = None,
    pb: float | None = 1.4,
) -> Quote:
    yesterday = closes[-1]
    last = yesterday * last_ratio
    band = 0.03
    tmin = yesterday * (1 - band)
    tmax = yesterday * (1 + band)
    # اگر سناریو خودش را به سقف یا کف چسبانده، همان را حفظ کن.
    if last_ratio >= 1 + band:
        last = tmax
    if last_ratio <= 1 - band:
        last = tmin
    volume = base_volume * volume_ratio
    return Quote(
        symbol=symbol,
        name=name,
        ins_code=f"fixture-{symbol}",
        market="نمونه",
        industry=industry,
        kind="stock",
        state=state,
        last=last,
        close=yesterday * (1 + (last_ratio - 1) * 0.65),
        yesterday=yesterday,
        first=yesterday * (1 + (last_ratio - 1) * 0.25),
        low=min(last, yesterday),
        high=max(last, yesterday),
        tmin=tmin,
        tmax=tmax,
        volume=volume,
        value=volume * last,
        trades=1800,
        base_volume=base_volume,
        eps=eps,
        pe=pe,
        group_pe=group_pe,
        ps=ps,
        pb=pb,
        float_percent=28,
        shares=2_000_000_000,
        bids=[Level(*bid)],
        asks=[Level(*ask)] if ask[1] else [],
        buy_i_volume=buy_i,
        sell_i_volume=sell_i,
        buy_n_volume=buy_n,
        sell_n_volume=sell_n,
        buy_i_count=buy_i_count,
        sell_i_count=sell_i_count,
        buy_n_count=6,
        sell_n_count=5,
        bars=_bars(closes, base_volume),
        flows=flows,
        headlines=headlines or [],
    )


def build_snapshot(now: datetime | None = None) -> MarketSnapshot:
    clock = tehran_now(now)
    up = _closes(800, 110, drift=0.0018, shock=0.008, seed=2)
    red_path = list(up)
    hot = _closes(700, 110, drift=0.0015, shock=0.008, seed=4)
    down = _closes(1500, 110, drift=-0.0016, shock=0.008, seed=1)
    distributed = _rewrite_tail(_closes(1100, 110, drift=0.0003, shock=0.007, seed=4), 5, 1.032)
    locked = _closes(640, 110, drift=0.0012, shock=0.008, seed=3)
    floor = _closes(480, 110, drift=-0.0012, shock=0.008, seed=8)
    halted = _closes(1000, 110, drift=0.0, shock=0.004, seed=9)

    dates = [bar.date for bar in _bars(up, 1)[-12:]]
    accumulate = _flows(
        dates,
        legal_buy=800_000,
        legal_sell=150_000,
        retail_buy=500_000,
        retail_sell=280_000,
        retail_buy_count=400,
        retail_sell_count=900,
    )
    distribute = _flows(
        dates,
        legal_buy=120_000,
        legal_sell=700_000,
        retail_buy=200_000,
        retail_sell=450_000,
        retail_buy_count=800,
        retail_sell_count=350,
    )
    quiet = _flows(
        dates,
        legal_buy=200_000,
        legal_sell=200_000,
        retail_buy=200_000,
        retail_sell=200_000,
        retail_buy_count=400,
        retail_sell_count=400,
    )

    quotes = [
        _quote(
            "آرام",
            "آزمایشی آرام",
            up,
            last_ratio=1.004,
            industry="فلزات نمونه",
            pe=6.2,
            group_pe=9.4,
            ps=0.72,
            eps=180,
            flows=accumulate,
            buy_i=900_000,
            sell_i=320_000,
            buy_n=400_000,
            sell_n=80_000,
            buy_i_count=280,
            sell_i_count=640,
            bid=(2480, 420_000, 18),
            ask=(2505, 160_000, 11),
            volume_ratio=1.8,
            headlines=[Headline("قرارداد فروش جدید به تأیید هیئت‌مدیره رسید", "آرام", "کدال", "امروز")],
        ),
        _quote(
            "سپید",
            "آزمایشی سپید",
            red_path,
            last_ratio=0.988,
            industry="فلزات نمونه",
            pe=5.4,
            group_pe=9.4,
            ps=0.6,
            eps=210,
            flows=accumulate,
            buy_i=700_000,
            sell_i=300_000,
            buy_n=500_000,
            sell_n=90_000,
            buy_i_count=260,
            sell_i_count=700,
            bid=(2100, 300_000, 14),
            ask=(2140, 220_000, 16),
            volume_ratio=1.5,
        ),
        _quote(
            "موج",
            "آزمایشی موج",
            hot,
            last_ratio=1.021,
            industry="فلزات نمونه",
            pe=7.1,
            group_pe=9.4,
            ps=0.9,
            eps=140,
            flows=accumulate,
            buy_i=1_400_000,
            sell_i=360_000,
            buy_n=600_000,
            sell_n=70_000,
            buy_i_count=300,
            sell_i_count=820,
            bid=(3100, 900_000, 40),
            ask=(3180, 140_000, 9),
            volume_ratio=2.4,
        ),
        _quote(
            "کهنه",
            "آزمایشی کهنه",
            down,
            last_ratio=0.992,
            industry="شیمیایی نمونه",
            pe=24,
            group_pe=8,
            ps=4.8,
            eps=-20,
            flows=distribute,
            buy_i=180_000,
            sell_i=640_000,
            buy_n=40_000,
            sell_n=420_000,
            buy_i_count=700,
            sell_i_count=260,
            bid=(900, 120_000, 8),
            ask=(940, 480_000, 22),
            volume_ratio=1.3,
            pb=6.5,
        ),
        _quote(
            "عرضه",
            "آزمایشی عرضه",
            distributed,
            last_ratio=1.004,
            industry="شیمیایی نمونه",
            pe=11,
            group_pe=8,
            ps=1.4,
            eps=90,
            flows=distribute,
            buy_i=260_000,
            sell_i=300_000,
            buy_n=50_000,
            sell_n=380_000,
            buy_i_count=500,
            sell_i_count=420,
            bid=(1400, 180_000, 10),
            ask=(1460, 200_000, 12),
            volume_ratio=1.2,
        ),
        _quote(
            "قفلخ",
            "آزمایشی صف خرید",
            locked,
            last_ratio=1.03,
            industry="فلزات نمونه",
            pe=5,
            group_pe=9.4,
            ps=0.5,
            eps=200,
            flows=accumulate,
            buy_i=2_000_000,
            sell_i=200_000,
            buy_n=900_000,
            sell_n=10_000,
            buy_i_count=200,
            sell_i_count=900,
            bid=(tmax_price(locked), 5_000_000, 400),
            ask=(0, 0, 0),
            volume_ratio=3,
        ),
        _quote(
            "قفلف",
            "آزمایشی صف فروش",
            floor,
            last_ratio=0.97,
            industry="شیمیایی نمونه",
            pe=30,
            group_pe=8,
            ps=5,
            eps=-40,
            flows=distribute,
            buy_i=80_000,
            sell_i=900_000,
            buy_n=10_000,
            sell_n=700_000,
            buy_i_count=400,
            sell_i_count=200,
            bid=(0, 0, 0),
            ask=(floor_price(floor), 4_000_000, 300),
            volume_ratio=2.2,
        ),
        _quote(
            "توقف",
            "آزمایشی متوقف",
            halted,
            last_ratio=1.0,
            industry="فلزات نمونه",
            pe=8,
            group_pe=9.4,
            ps=1,
            eps=100,
            flows=quiet,
            buy_i=0,
            sell_i=0,
            buy_n=0,
            sell_n=0,
            buy_i_count=0,
            sell_i_count=0,
            bid=(1000, 10_000, 1),
            ask=(1010, 10_000, 1),
            volume_ratio=0.1,
            state="ممنوع-متوقف",
        ),
    ]
    # قیمت سرخط صف‌ها را با آستانهٔ همان سهم یکی کن.
    for quote in quotes:
        if quote.symbol == "قفلخ" and quote.bids:
            quote.bids[0].price = quote.tmax
            quote.last = quote.tmax
            quote.high = quote.tmax
        if quote.symbol == "قفلف" and quote.asks:
            quote.asks[0].price = quote.tmin
            quote.last = quote.tmin
            quote.low = quote.tmin
            quote.bids = []

    return MarketSnapshot(
        quotes=quotes,
        headlines=[
            Headline("قرارداد فروش جدید به تأیید هیئت‌مدیره رسید", "آرام", "کدال", "امروز"),
            Headline("توقف نماد به‌دلیل افشای اطلاعات بااهمیت", "توقف", "ناظر", "امروز"),
        ],
        indices=[
            IndexQuote("شاخص کل نمونه", 2_150_000, 4200, 0.2),
            IndexQuote("شاخص هم‌وزن نمونه", 720_000, -800, -0.11),
        ],
        source="fixture",
        live=False,
        source_note=(
            "این تابلو نمونهٔ آموزشی است، نه بازار واقعی. "
            "سرور فعلی به تی‌اس‌ئی‌ام‌سی وصل نشده. با اجرای برنامه داخل ایران، "
            "یا با متغیر BRSAPI_KEY، همین میز روی دیده‌بان زنده پر می‌شود."
        ),
        fetched_at=clock.isoformat(timespec="seconds"),
        market_phase=market_phase(clock),
    )


def tmax_price(closes: list[float]) -> float:
    return closes[-1] * 1.03


def floor_price(closes: list[float]) -> float:
    return closes[-1] * 0.97


class FixtureProvider:
    name = "fixture"
    live = False

    async def load(self) -> MarketSnapshot:
        return build_snapshot()

    async def enrich(self, quotes: list[Quote]) -> None:
        return None
