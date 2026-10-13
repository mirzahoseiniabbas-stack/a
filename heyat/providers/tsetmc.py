"""دیده‌بان عمومی تی‌اس‌ئی‌ام‌سی. از بیرون ایران اغلب بسته است و آن‌وقت خوراک بعدی امتحان می‌شود."""

from __future__ import annotations

import asyncio

import httpx

from heyat.market_time import market_phase, tehran_now
from heyat.models import Bar, FlowDay, Headline, IndexQuote, MarketSnapshot, Quote
from heyat.providers.http import blocked, client
from heyat.providers.parsing import instrument_kind, levels_from_flat, levels_from_rows, num, pick, text, unwrap_rows

CDN = "https://cdn.tsetmc.com/api"
OLD = "https://old.tsetmc.com/tsev2/data"
WATCH = (
    "/ClosingPrice/GetMarketWatch?market=0&industrialGroup="
    "&paperTypes%5B0%5D=1&paperTypes%5B1%5D=2&paperTypes%5B2%5D=3"
    "&paperTypes%5B3%5D=4&paperTypes%5B4%5D=5&paperTypes%5B5%5D=6"
    "&paperTypes%5B6%5D=7&paperTypes%5B7%5D=8&paperTypes%5B8%5D=9"
    "&showTraded=false&withBestLimits=true&hEven=0&RefID=0"
)


async def tsetmc_reachable() -> bool:
    try:
        async with client() as http:
            response = await http.get(f"{CDN}/StaticData/GetTime", timeout=4)
            body = response.text
            return response.status_code == 200 and not blocked(body) and body.strip().startswith("{")
    except (httpx.HTTPError, OSError):
        return False


def _quote_from_row(row: dict) -> Quote | None:
    symbol = text(row, ("lVal18AFC", "lva", "l18", "symbol"))
    if not symbol:
        return None
    name = text(row, ("lVal30", "lvc", "l30", "name"))
    yval = text(row, ("yVal", "yval"))
    kind = instrument_kind(symbol, yval, name)
    last = num(row, ("pl", "pDrCotVal", "last")) or 0
    close = num(row, ("pc", "pClosing", "close")) or last
    yesterday = num(row, ("py", "priceYesterday", "yesterday")) or 0
    high = num(row, ("pmx", "priceMax")) or num(row, ("pmax",)) or last
    low = num(row, ("pmn", "priceMin")) or num(row, ("pmin",)) or last
    # اگر tmin/tmax جدا آمده باشند، pmin/pmax سقف دامنه نیستند.
    tmax = num(row, ("tmax", "psGelStaMax")) or num(row, ("pMax",)) or 0
    tmin = num(row, ("tmin", "psGelStaMin")) or num(row, ("pMin",)) or 0
    if tmax and high and abs(high - tmax) < 0.01 and num(row, ("pmx", "priceMax")) is None:
        high = last or high
    bids, asks = levels_from_flat(row)
    if not bids and not asks:
        nested = pick(row, ("bestLimits", "blDs", "bestLimit"))
        bids, asks = levels_from_rows(nested)
    return Quote(
        symbol=symbol,
        name=name,
        ins_code=str(pick(row, ("insCode", "InsCode", "ins_code", "id"), "") or ""),
        isin=text(row, ("cIsin", "isin")),
        market=text(row, ("flowTitle", "m", "market")),
        industry=text(row, ("cs", "csv", "lSecVal")),
        kind=kind,
        state=text(row, ("cEtavalTitle", "state", "cEtaval")),
        last=last,
        close=close,
        yesterday=yesterday,
        first=num(row, ("pf", "priceFirst")) or last,
        low=low or last,
        high=high or last,
        tmin=tmin or 0,
        tmax=tmax or 0,
        volume=num(row, ("tvol", "qTotTran5J")) or 0,
        value=num(row, ("tval", "qTotCap")) or 0,
        trades=num(row, ("tno", "zTotTran")) or 0,
        base_volume=num(row, ("bvol", "baseVol")) or 0,
        eps=num(row, ("eps", "estimatedEPS")),
        pe=num(row, ("pe",)),
        group_pe=num(row, ("g_pe", "groupPE")),
        ps=num(row, ("ps",)),
        pb=num(row, ("pb", "pbr")),
        float_percent=num(row, ("ff", "floatPercent")),
        shares=num(row, ("z", "zTitad")),
        market_cap=num(row, ("mv",)),
        bids=bids,
        asks=asks,
    )


def _apply_client(quote: Quote, row: dict, *, legacy: bool) -> None:
    if legacy:
        quote.buy_i_volume = num(row, ("n_buy_volume",)) or 0
        quote.buy_n_volume = num(row, ("l_buy_volume",)) or 0
        quote.sell_i_volume = num(row, ("n_sell_volume",)) or 0
        quote.sell_n_volume = num(row, ("l_sell_volume",)) or 0
        quote.buy_i_count = num(row, ("n_buy_count",)) or 0
        quote.buy_n_count = num(row, ("l_buy_count",)) or 0
        quote.sell_i_count = num(row, ("n_sell_count",)) or 0
        quote.sell_n_count = num(row, ("l_sell_count",)) or 0
        return
    quote.buy_i_volume = num(row, ("buy_I_Volume", "Buy_I_Volume")) or 0
    quote.buy_n_volume = num(row, ("buy_N_Volume", "Buy_N_Volume")) or 0
    quote.sell_i_volume = num(row, ("sell_I_Volume", "Sell_I_Volume")) or 0
    quote.sell_n_volume = num(row, ("sell_N_Volume", "Sell_N_Volume")) or 0
    quote.buy_i_count = num(row, ("buy_CountI", "Buy_CountI")) or 0
    quote.buy_n_count = num(row, ("buy_CountN", "Buy_CountN")) or 0
    quote.sell_i_count = num(row, ("sell_CountI", "Sell_CountI")) or 0
    quote.sell_n_count = num(row, ("sell_CountN", "Sell_CountN")) or 0
    quote.buy_i_value = num(row, ("buy_I_Value",)) or 0
    quote.buy_n_value = num(row, ("buy_N_Value",)) or 0
    quote.sell_i_value = num(row, ("sell_I_Value",)) or 0
    quote.sell_n_value = num(row, ("sell_N_Value",)) or 0


def _bars(rows: list[dict]) -> list[Bar]:
    parsed: list[Bar] = []
    for row in rows:
        date = str(pick(row, ("dEven", "date"), "") or "")
        close = num(row, ("pClosing", "pc", "close"))
        last = num(row, ("pDrCotVal", "pl", "last")) or close
        if not last:
            continue
        parsed.append(
            Bar(
                date=date,
                open=num(row, ("priceFirst", "pf", "open")) or last,
                high=num(row, ("priceMax", "pmax", "high")) or last,
                low=num(row, ("priceMin", "pmin", "low")) or last,
                close=close or last,
                volume=num(row, ("qTotTran5J", "tvol", "volume")) or 0,
            )
        )
    parsed.sort(key=lambda bar: bar.date)
    return parsed[-180:]


def _flows(rows: list[dict], *, legacy: bool) -> list[FlowDay]:
    parsed: list[FlowDay] = []
    for row in rows:
        date = str(pick(row, ("recDate", "dEven", "date"), "") or "")
        if legacy:
            parsed.append(
                FlowDay(
                    date=date,
                    buy_i_volume=num(row, ("n_buy_volume",)) or 0,
                    buy_n_volume=num(row, ("l_buy_volume",)) or 0,
                    sell_i_volume=num(row, ("n_sell_volume",)) or 0,
                    sell_n_volume=num(row, ("l_sell_volume",)) or 0,
                    buy_i_count=num(row, ("n_buy_count",)) or 0,
                    buy_n_count=num(row, ("l_buy_count",)) or 0,
                    sell_i_count=num(row, ("n_sell_count",)) or 0,
                    sell_n_count=num(row, ("l_sell_count",)) or 0,
                    buy_i_value=num(row, ("n_buy_value",)) or 0,
                    buy_n_value=num(row, ("l_buy_value",)) or 0,
                    sell_i_value=num(row, ("n_sell_value",)) or 0,
                    sell_n_value=num(row, ("l_sell_value",)) or 0,
                )
            )
        else:
            parsed.append(
                FlowDay(
                    date=date,
                    buy_i_volume=num(row, ("buy_I_Volume",)) or 0,
                    buy_n_volume=num(row, ("buy_N_Volume",)) or 0,
                    sell_i_volume=num(row, ("sell_I_Volume",)) or 0,
                    sell_n_volume=num(row, ("sell_N_Volume",)) or 0,
                    buy_i_count=num(row, ("buy_I_Count", "buy_CountI")) or 0,
                    buy_n_count=num(row, ("buy_N_Count", "buy_CountN")) or 0,
                    sell_i_count=num(row, ("sell_I_Count", "sell_CountI")) or 0,
                    sell_n_count=num(row, ("sell_N_Count", "sell_CountN")) or 0,
                    buy_i_value=num(row, ("buy_I_Value",)) or 0,
                    buy_n_value=num(row, ("buy_N_Value",)) or 0,
                    sell_i_value=num(row, ("sell_I_Value",)) or 0,
                    sell_n_value=num(row, ("sell_N_Value",)) or 0,
                )
            )
    parsed.sort(key=lambda day: day.date)
    return parsed[-40:]


class TsetmcProvider:
    name = "tsetmc"
    live = True

    async def load(self) -> MarketSnapshot:
        async with client() as http:
            watch_rows, legacy_limits = await self._watch(http)
            if not watch_rows and not legacy_limits:
                raise RuntimeError("دیده‌بان تی‌اس‌ئی‌ام‌سی خالی برگشت")
            clients = await self._clients(http)
            headlines = await self._headlines(http)
            indices = await self._indices(http)
        quotes: list[Quote] = []
        seen: set[str] = set()
        for row in watch_rows:
            quote = _quote_from_row(row)
            if quote is None or quote.kind not in {"stock", "etf"} or quote.symbol in seen:
                continue
            if not quote.last or not quote.yesterday:
                continue
            client_row = clients.get(quote.ins_code) or clients.get(quote.symbol)
            if client_row:
                _apply_client(quote, client_row, legacy=client_row.get("_legacy") is True)
            seen.add(quote.symbol)
            quotes.append(quote)
        clock = tehran_now()
        return MarketSnapshot(
            quotes=quotes,
            headlines=headlines,
            indices=indices,
            source="tsetmc",
            live=True,
            source_note="دیده‌بان از cdn.tsetmc.com خوانده شده است.",
            fetched_at=clock.isoformat(timespec="seconds"),
            market_phase=market_phase(clock),
        )

    async def enrich(self, quotes: list[Quote]) -> None:
        semaphore = asyncio.Semaphore(3)

        async def one(http: httpx.AsyncClient, quote: Quote) -> None:
            if not quote.ins_code or quote.ins_code.startswith("fixture"):
                return
            async with semaphore:
                try:
                    daily = await http.get(
                        f"{CDN}/ClosingPrice/GetClosingPriceDailyList/{quote.ins_code}/160",
                        timeout=20,
                    )
                    if daily.status_code == 200 and not blocked(daily.text):
                        quote.bars = _bars(unwrap_rows(daily.json()))
                    flow = await http.get(
                        f"{CDN}/ClientType/GetClientTypeHistory/{quote.ins_code}",
                        timeout=20,
                    )
                    if flow.status_code == 200 and not blocked(flow.text):
                        quote.flows = _flows(unwrap_rows(flow.json()), legacy=False)
                    elif not quote.flows:
                        old = await http.get(f"{OLD}/clienttype.aspx?i={quote.ins_code}", timeout=20)
                        if old.status_code == 200 and ";" in old.text:
                            quote.flows = _flows(_legacy_csv(old.text), legacy=True)
                except (httpx.HTTPError, ValueError, OSError):
                    return
                await asyncio.sleep(0.12)

        async with client() as http:
            await asyncio.gather(*(one(http, quote) for quote in quotes))

    async def _watch(self, http: httpx.AsyncClient) -> tuple[list[dict], list[dict]]:
        try:
            response = await http.get(f"{CDN}{WATCH}", timeout=25)
            if response.status_code == 200 and not blocked(response.text):
                rows = unwrap_rows(response.json())
                if rows:
                    return rows, []
        except (httpx.HTTPError, ValueError, OSError):
            pass
        try:
            response = await http.get(f"{OLD}/MarketWatchInit.aspx?h=0&r=0", timeout=25)
            if response.status_code != 200 or blocked(response.text) or "@" not in response.text:
                return [], []
            parts = response.text.split("@")
            if len(parts) < 5:
                return [], []
            prices = _legacy_price_rows(parts[2])
            limits = _legacy_limit_rows(parts[3])
            by_id: dict[str, list[dict]] = {}
            for level in limits:
                by_id.setdefault(str(level.get("ins_code")), []).append(level)
            for row in prices:
                nested = by_id.get(row["ins_code"], [])
                for level in nested:
                    number = str(level.get("number") or "")
                    if not number:
                        continue
                    row[f"zo{number}"] = level.get("zo")
                    row[f"zd{number}"] = level.get("zd")
                    row[f"pd{number}"] = level.get("pd")
                    row[f"po{number}"] = level.get("po")
                    row[f"qd{number}"] = level.get("qd")
                    row[f"qo{number}"] = level.get("qo")
            return prices, limits
        except (httpx.HTTPError, ValueError, OSError):
            return [], []

    async def _clients(self, http: httpx.AsyncClient) -> dict[str, dict]:
        found: dict[str, dict] = {}
        try:
            response = await http.get(f"{CDN}/ClientType/GetClientTypeAll", timeout=25)
            if response.status_code == 200 and not blocked(response.text):
                for row in unwrap_rows(response.json()):
                    key = str(pick(row, ("insCode", "InsCode", "ins_code"), "") or "")
                    if key:
                        found[key] = row
                if found:
                    return found
        except (httpx.HTTPError, ValueError, OSError):
            pass
        try:
            response = await http.get(f"{OLD}/ClientTypeAll.aspx", timeout=25)
            if response.status_code != 200:
                return found
            for row in _legacy_csv(response.text):
                row["_legacy"] = True
                key = str(row.get("ins_code") or "")
                if key:
                    found[key] = row
        except (httpx.HTTPError, OSError):
            return found
        return found

    async def _headlines(self, http: httpx.AsyncClient) -> list[Headline]:
        items: list[Headline] = []
        try:
            codal = await http.get(f"{CDN}/Codal/GetPreparedData/25", timeout=15)
            if codal.status_code == 200 and not blocked(codal.text):
                for row in unwrap_rows(codal.json()):
                    items.append(
                        Headline(
                            title=text(row, ("title", "tseTitle")),
                            symbol=text(row, ("symbol", "lVal18AFC")),
                            source="کدال",
                            published=text(row, ("publishDateTime_Gregorian", "sentDateTime_Gregorian")),
                        )
                    )
        except (httpx.HTTPError, ValueError, OSError):
            pass
        try:
            msg = await http.get(f"{CDN}/Msg/GetMsgByFlow/0/25", timeout=15)
            if msg.status_code == 200 and not blocked(msg.text):
                for row in unwrap_rows(msg.json()):
                    items.append(
                        Headline(
                            title=text(row, ("tseTitle", "title")),
                            symbol=text(row, ("symbol", "lVal18AFC")),
                            source="ناظر",
                            published=str(pick(row, ("dEven",), "") or ""),
                        )
                    )
        except (httpx.HTTPError, ValueError, OSError):
            pass
        return [item for item in items if item.title]

    async def _indices(self, http: httpx.AsyncClient) -> list[IndexQuote]:
        try:
            response = await http.get(f"{CDN}/Index/GetIndexB1LastAll/SelectedIndexes/1", timeout=15)
            if response.status_code != 200 or blocked(response.text):
                return []
            payload = response.json()
            rows = payload.get("indexB1") if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                rows = unwrap_rows(payload)
            indices: list[IndexQuote] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                indices.append(
                    IndexQuote(
                        name=text(row, ("lVal30", "name")) or "شاخص",
                        value=num(row, ("xDrNivJIdx004", "value")),
                        change=num(row, ("indexChange", "change")),
                        change_percent=num(row, ("xVarIdxJRfV", "changePercent")),
                    )
                )
            return indices[:6]
        except (httpx.HTTPError, ValueError, OSError):
            return []


_LEGACY_PRICE = (
    "ins_code",
    "isin",
    "l18",
    "l30",
    "heven",
    "pf",
    "pc",
    "pl",
    "tno",
    "tvol",
    "tval",
    "pmin",
    "pmax",
    "py",
    "eps",
    "bvol",
    "visitcount",
    "flow",
    "cs",
    "tmax",
    "tmin",
    "z",
    "yval",
    "predtran",
    "buyop",
    "cgrvalcot",
)


def _legacy_price_rows(blob: str) -> list[dict]:
    rows: list[dict] = []
    for raw in blob.split(";"):
        if not raw.strip():
            continue
        cells = raw.split(",")
        if len(cells) < 14:
            continue
        row = {name: cells[i] if i < len(cells) else "" for i, name in enumerate(_LEGACY_PRICE)}
        rows.append(row)
    return rows


def _legacy_limit_rows(blob: str) -> list[dict]:
    names = ("ins_code", "number", "zo", "zd", "pd", "po", "qd", "qo")
    rows: list[dict] = []
    for raw in blob.split(";"):
        cells = raw.split(",")
        if len(cells) < 8:
            continue
        rows.append({name: cells[i] for i, name in enumerate(names)})
    return rows


def _legacy_csv(blob: str) -> list[dict]:
    names = (
        "ins_code",
        "n_buy_count",
        "l_buy_count",
        "n_buy_volume",
        "l_buy_volume",
        "n_sell_count",
        "l_sell_count",
        "n_sell_volume",
        "l_sell_volume",
    )
    # تاریخچهٔ قدیمی ستون‌های بیشتری دارد و ins_code ندارد.
    history_names = (
        "date",
        "n_buy_count",
        "l_buy_count",
        "n_sell_count",
        "l_sell_count",
        "n_buy_volume",
        "l_buy_volume",
        "n_sell_volume",
        "l_sell_volume",
        "n_buy_value",
        "l_buy_value",
        "n_sell_value",
        "l_sell_value",
    )
    rows: list[dict] = []
    for raw in blob.split(";"):
        cells = [cell for cell in raw.split(",") if cell != ""]
        if len(cells) >= 13:
            rows.append({name: cells[i] for i, name in enumerate(history_names) if i < len(cells)})
        elif len(cells) >= 9:
            rows.append({name: cells[i] for i, name in enumerate(names)})
    return rows
