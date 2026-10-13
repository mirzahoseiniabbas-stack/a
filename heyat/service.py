"""یک دور پایش: دیده‌بان، تاریخچهٔ کوتاه‌فهرست، بعد رأی کمیته."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta

from heyat.engines.committee import build_board, shortlist
from heyat.market_time import phase_label, tehran_now
from heyat.providers.auto import AutoProvider

DISCLAIMER = (
    "خروجی هیئت یک جمع‌بندی الگوریتمی از داده‌های عمومی بازار است، "
    "نه توصیهٔ رسمی خرید یا فروش و نه تضمین سود. "
    "صف، سرانه و خبر در چند ثانیه عوض می‌شوند. قبل از سفارش، تابلو همان لحظه را خودتان ببینید."
)


class Scanner:
    def __init__(self, provider: AutoProvider | None = None) -> None:
        self.provider = provider or AutoProvider()
        self.payload: dict | None = None
        self.fetched_at: datetime | None = None
        self.error: str | None = None
        self._lock = asyncio.Lock()

    def _ttl(self) -> timedelta:
        phase = (self.payload or {}).get("market", {}).get("phase")
        if phase == "open":
            return timedelta(seconds=20)
        return timedelta(seconds=90)

    def _fresh(self) -> bool:
        if self.payload is None or self.fetched_at is None:
            return False
        return tehran_now() - self.fetched_at < self._ttl()

    async def board(self, force: bool = False) -> dict:
        async with self._lock:
            if not force and self._fresh():
                return self.payload
            try:
                self.payload = await self._scan()
                self.error = None
            except Exception as exc:  # خوراک قطع است؛ آخرین تابلو اگر باشد می‌ماند.
                self.error = str(exc)
                if self.payload is None:
                    self.payload = _empty_board(str(exc))
            self.fetched_at = tehran_now()
            return self.payload

    async def _scan(self) -> dict:
        forced = os.environ.get("HEYAT_PROVIDER", "auto").strip().lower()
        if forced == "auto" and not getattr(self.provider, "live", False):
            await self.provider.resolve()
        elif getattr(self.provider, "name", "") == "auto":
            await self.provider.resolve()
        snapshot = await self.provider.load()
        if snapshot.live:
            picks = shortlist(snapshot.quotes, limit=24)
            missing = [quote for quote in picks if len(quote.bars) < 40 or len(quote.flows) < 5]
            if missing:
                await self.provider.enrich(missing)
        board = build_board(snapshot.quotes, snapshot.headlines)
        clock = tehran_now()
        board.update(
            {
                "ok": True,
                "disclaimer": DISCLAIMER,
                "market": {
                    "phase": snapshot.market_phase,
                    "phase_label": phase_label(snapshot.market_phase),
                    "as_of": snapshot.fetched_at or clock.isoformat(timespec="seconds"),
                    "clock": clock.strftime("%Y-%m-%d %H:%M:%S"),
                },
                "source": {
                    "name": snapshot.source,
                    "live": snapshot.live,
                    "note": snapshot.source_note,
                },
                "indices": [
                    {
                        "name": item.name,
                        "value": item.value,
                        "change": item.change,
                        "change_percent": item.change_percent,
                    }
                    for item in snapshot.indices
                ],
                "error": None,
            }
        )
        return board


def _empty_board(message: str) -> dict:
    return {
        "ok": False,
        "disclaimer": DISCLAIMER,
        "error": message,
        "lists": {},
        "list_copy": {},
        "counts": {},
        "scanned": 0,
        "market": {"phase": "unknown", "phase_label": "نامشخص", "as_of": "", "clock": ""},
        "source": {"name": "none", "live": False, "note": message},
        "indices": [],
    }
