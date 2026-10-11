import os

os.environ["HEYAT_PROVIDER"] = "fixture"

from fastapi.testclient import TestClient

from heyat.api import create_app


def test_desk_and_board_render_the_sample_committee():
    app = create_app(start_poller=False)
    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "هیئت" in page.text
        assert "خروجی میزها" in page.text

        board = client.get("/api/board").json()
        assert board["ok"] is True
        assert board["source"]["live"] is False
        assert board["lists"]["buy_now"][0]["symbol"] == "آرام"
        assert board["lists"]["sell_now"][0]["symbol"] == "کهنه"
        assert board["disclaimer"]

        health = client.get("/api/health").json()
        assert health["ok"] is True
