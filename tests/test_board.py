from heyat.engines.committee import build_board
from heyat.engines.tape import read_tape
from heyat.providers.fixture import build_snapshot
from heyat.providers.parsing import num


def _symbols(board, name):
    return [card["symbol"] for card in board["lists"][name]]


def test_committee_separates_actionable_ideas_from_locked_queues():
    snapshot = build_snapshot()
    board = build_board(snapshot.quotes, snapshot.headlines)

    assert _symbols(board, "buy_now") == ["آرام"]
    assert _symbols(board, "buy_in_red") == ["سپید"]
    assert _symbols(board, "pre_queue") == ["موج"]
    assert _symbols(board, "sell_now") == ["کهنه"]
    assert _symbols(board, "distribution") == ["عرضه"]
    assert _symbols(board, "locked_buy") == ["قفلخ"]
    assert _symbols(board, "locked_sell") == ["قفلف"]
    assert _symbols(board, "halted") == ["توقف"]

    locked = next(card for card in board["lists"]["locked_buy"] if card["symbol"] == "قفلخ")
    assert locked["queue"]["executable_buy"] is False
    assert "قفلخ" not in _symbols(board, "buy_now")
    assert "قفلخ" not in _symbols(board, "pre_queue")

    red = board["lists"]["buy_in_red"][0]
    assert red["pct_last"] < 0
    assert red["queue"]["executable_buy"] is True
    assert red["flow"]["net_legal_7"] > 0

    hot = board["lists"]["pre_queue"][0]
    assert hot["pct_last"] > 1
    assert hot["queue"]["ask_volume"] > 0


def test_heavy_buy_queue_is_not_executable():
    snapshot = build_snapshot()
    locked = next(quote for quote in snapshot.quotes if quote.symbol == "قفلخ")
    tape = read_tape(locked)
    assert tape.buy_locked
    assert tape.buy_queue_heavy
    assert not tape.executable_buy


def test_iranian_trailing_minus_is_negative():
    assert num({"eps": "784-"}, ("eps",)) == -784
