"""میز کار هیئت روی مرورگر. داده فقط از سمت سرور خوانده می‌شود."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from heyat import __version__
from heyat.providers.auto import AutoProvider
from heyat.service import Scanner

WEB = Path(__file__).resolve().parent.parent / "web"


def create_app(provider: AutoProvider | None = None, start_poller: bool = True) -> FastAPI:
    scanner = Scanner(provider)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = asyncio.create_task(_poll(scanner)) if start_poller else None
        yield
        if task is not None:
            task.cancel()

    app = FastAPI(title="هیئت", version=__version__, lifespan=lifespan)
    app.state.scanner = scanner

    @app.get("/")
    async def desk() -> FileResponse:
        return FileResponse(WEB / "index.html")

    @app.get("/api/board")
    async def board(force: bool = False) -> dict:
        return await scanner.board(force=force)

    @app.get("/api/health")
    async def health() -> dict:
        payload = scanner.payload or {}
        return {
            "ok": True,
            "version": __version__,
            "source": (payload.get("source") or {}).get("name"),
            "live": (payload.get("source") or {}).get("live"),
        }

    if WEB.is_dir():
        app.mount("/assets", StaticFiles(directory=WEB), name="assets")
    return app


async def _poll(scanner: Scanner) -> None:
    while True:
        try:
            await scanner.board(force=True)
        except Exception:
            pass
        phase = ((scanner.payload or {}).get("market") or {}).get("phase")
        await asyncio.sleep(20 if phase == "open" else 90)


app = create_app()
