"""خوراک BrsApi وقتی کلید کاربر در BRSAPI_KEY باشد.

کلید مثالِ سایت معتبر نیست. کلید را از brsapi.ir بگیرید و در محیط بگذارید.
"""

from __future__ import annotations

import asyncio

import httpx

from heyat.market_time import market_phase, tehran_now
from heyat.models import Bar, FlowDay, MarketSnapshot, Quote
from heyat.providers.http import client
from heyat.providers.parsing import instrument_kind, levels_from_flat, num, unwrap_rows
from heyat.providers.tsetmc import _quote_from_row

BASE = "https://Api.BrsApi.ir/Tsetmc"


class BrsApiProvider:
    name = "brsapi"
    live = True

    def __init__(self, key: str):
        self.key = key

    async def load(self) -> MarketSnapshot:
        async with client() as http:
            response = await http.get(
                f"{BASE}/AllSymbols.php",
                params={"key": self.key, "type": "1"},
                timeout=40,
            )
            response.raise_for_status()
            payload = response.json()
        if isinstance(payload, dict) and payload.get("successful") is False:
            message = payload.get("message_error") or "کلید BrsApi پذیرفته نشد"
            raise RuntimeError(str(message))
        rows = unwrap_rows(payload)
        if isinstance(payload, list):
            rows = payload
        quotes: list[Quote] = []
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            quote = _quote_from_row(row)
            if quote is None or quote.symbol in seen:
                continue
            quote.kind = instrument_kind(quote.symbol, "", quote.name)
            if quote.kind not in {"stock", "etf"}:
                continue
            if not quote.last or not quote.yesterday:
                continue
            _apply_brs_flow(quote, row)
            if not quote.bids and not quote.asks:
                bids, asks = levels_from_flat(row)
                quote.bids, quote.asks = bids, asks
            seen.add(quote.symbol)
            quotes.append(quote)
        if not quotes:
            raise RuntimeError("BrsApi نمادی برنگرداند")
        clock = tehran_now()
        return MarketSnapshot(
            quotes=quotes,
            source="brsapi",
            live=True,
            source_note="دیده‌بان از Api.BrsApi.ir خوانده شده است.",
            fetched_at=clock.isoformat(timespec="seconds"),
            market_phase=market_phase(clock),
        )

    async def enrich(self, quotes: list[Quote]) -> None:
        semaphore = asyncio.Semaphore(2)

        async def one(http: httpx.AsyncClient, quote: Quote) -> None:
            async with semaphore:
                try:
                    candles = await http.get(
                        f"{BASE}/Candlestick.php",
                        params={"key": self.key, "type": "2", "l18": quote.symbol},
                        timeout=25,
                    )
                    if candles.status_code == 200:
                        quote.bars = _candles(candles.json())
                    history = await http.get(
                        f"{BASE}/History.php",
                        params={"key": self.key, "type": "1", "l18": quote.symbol},
                        timeout=25,
                    )
                    if history.status_code == 200:
                        quote.flows = _history_flows(history.json())
                except (httpx.HTTPError, ValueError, OSError):
                    return
                await asyncio.sleep(0.15)

        async with client() as http:
            await asyncio.gather(*(one(http, quote) for quote in quotes))


def _apply_brs_flow(quote: Quote, row: dict) -> None:
    quote.buy_i_volume = num(row, ("Buy_I_Volume", "buy_I_Volume")) or quote.buy_i_volume
    quote.buy_n_volume = num(row, ("Buy_N_Volume", "buy_N_Volume")) or quote.buy_n_volume
    quote.sell_i_volume = num(row, ("Sell_I_Volume", "sell_I_Volume")) or quote.sell_i_volume
    quote.sell_n_volume = num(row, ("Sell_N_Volume", "sell_N_Volume")) or quote.sell_n_volume
    quote.buy_i_count = num(row, ("Buy_CountI", "buy_CountI")) or quote.buy_i_count
    quote.buy_n_count = num(row, ("Buy_CountN", "buy_CountN")) or quote.buy_n_count
    quote.sell_i_count = num(row, ("Sell_CountI", "sell_CountI")) or quote.sell_i_count
    quote.sell_n_count = num(row, ("Sell_CountN", "sell_CountN")) or quote.sell_n_count
    if quote.group_pe is None:
        quote.group_pe = num(row, ("g_pe",))
    if quote.ps is None:
        quote.ps = num(row, ("ps",))
    if quote.float_percent is None:
        quote.float_percent = num(row, ("ff",))


def _candles(payload) -> list[Bar]:
    rows = payload if isinstance(payload, list) else unwrap_rows(payload)
    bars: list[Bar] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        close = num(row, ("close", "c", "pc"))
        if not close:
            continue
        bars.append(
            Bar(
                date=str(row.get("date") or row.get("dEven") or ""),
                open=num(row, ("open", "o", "pf")) or close,
                high=num(row, ("high", "h", "pmax")) or close,
                low=num(row, ("low", "l", "pmin")) or close,
                close=close,
                volume=num(row, ("volume", "v", "tvol")) or 0,
            )
        )
    bars.sort(key=lambda bar: bar.date)
    return bars[-180:]


def _history_flows(payload) -> list[FlowDay]:
    rows = payload if isinstance(payload, list) else unwrap_rows(payload)
    days: list[FlowDay] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        days.append(
            FlowDay(
                date=str(row.get("date") or row.get("recDate") or ""),
                buy_i_volume=num(row, ("Buy_I_Volume", "buy_I_Volume")) or 0,
                buy_n_volume=num(row, ("Buy_N_Volume", "buy_N_Volume")) or 0,
                sell_i_volume=num(row, ("Sell_I_Volume", "sell_I_Volume")) or 0,
                sell_n_volume=num(row, ("Sell_N_Volume", "sell_N_Volume")) or 0,
                buy_i_count=num(row, ("Buy_CountI", "buy_CountI")) or 0,
                buy_n_count=num(row, ("Buy_CountN", "buy_CountN")) or 0,
                sell_i_count=num(row, ("Sell_CountI", "sell_CountI")) or 0,
                sell_n_count=num(row, ("Sell_CountN", "sell_CountN")) or 0,
                buy_i_value=num(row, ("Buy_I_Value",)) or 0,
                buy_n_value=num(row, ("Buy_N_Value",)) or 0,
                sell_i_value=num(row, ("Sell_I_Value",)) or 0,
                sell_n_value=num(row, ("Sell_N_Value",)) or 0,
            )
        )
    days.sort(key=lambda day: day.date)
    return days[-40:]
