"""درخواست‌های خواندنی به خوراک بازار. بدون هیچ مسیر نوشتنی."""

from __future__ import annotations

import httpx

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,text/csv,*/*",
    "Referer": "https://www.tsetmc.com/",
    "Origin": "https://www.tsetmc.com",
}


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers=BROWSER_HEADERS, follow_redirects=True, timeout=20)


def blocked(text: str) -> bool:
    sample = text[:500]
    return "مسدود" in sample or "دسترسی شما" in sample or "General Error Detected" in sample
