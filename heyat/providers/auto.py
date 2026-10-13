"""انتخاب خوراک: اول تی‌اس‌ئی‌ام‌سی، بعد BrsApi اگر کلید باشد، وگرنه نمونهٔ آموزشی."""

from __future__ import annotations

import os

from heyat.models import MarketSnapshot, Quote
from heyat.providers.brsapi import BrsApiProvider
from heyat.providers.fixture import FixtureProvider
from heyat.providers.tsetmc import TsetmcProvider, tsetmc_reachable


class AutoProvider:
    name = "auto"
    live = False

    def __init__(self) -> None:
        self.inner: TsetmcProvider | BrsApiProvider | FixtureProvider = FixtureProvider()

    async def resolve(self) -> None:
        forced = os.environ.get("HEYAT_PROVIDER", "auto").strip().lower()
        if forced == "fixture":
            self.inner = FixtureProvider()
        elif forced == "tsetmc":
            self.inner = TsetmcProvider()
        elif forced == "brsapi":
            key = os.environ.get("BRSAPI_KEY", "").strip()
            if not key:
                raise RuntimeError("BRSAPI_KEY خالی است")
            self.inner = BrsApiProvider(key)
        else:
            if await tsetmc_reachable():
                self.inner = TsetmcProvider()
            else:
                key = os.environ.get("BRSAPI_KEY", "").strip()
                self.inner = BrsApiProvider(key) if key else FixtureProvider()
        self.live = self.inner.live
        self.name = self.inner.name

    async def load(self) -> MarketSnapshot:
        try:
            return await self.inner.load()
        except Exception:
            if isinstance(self.inner, FixtureProvider):
                raise
            # خوراک زنده قطع شد؛ تابلو آموزشی را با توضیح خطا نشان بده، نه فهرست خالی.
            self.inner = FixtureProvider()
            self.live = False
            self.name = "fixture"
            snapshot = await self.inner.load()
            snapshot.source_note = (
                "اتصال به دیده‌بان زنده برقرار نشد و تابلو به حالت آموزشی برگشت. " + snapshot.source_note
            )
            return snapshot

    async def enrich(self, quotes: list[Quote]) -> None:
        enrich = getattr(self.inner, "enrich", None)
        if enrich is not None:
            await enrich(quotes)
