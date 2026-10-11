"""دبیر کمیته. فقط پیشنهادی به لیست خرید یا فروش می‌رود که همین حالا قابل اجرا باشد."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from statistics import pstdev

from heyat.engines.fundamental import read_fundamental
from heyat.engines.news import read_news
from heyat.engines.players import read_players
from heyat.engines.tape import read_tape
from heyat.engines.technical import read_technical
from heyat.indicators import Indicators
from heyat.models import Headline, Quote

LISTS = (
    "buy_now",
    "buy_in_red",
    "pre_queue",
    "sell_now",
    "distribution",
    "locked_buy",
    "locked_sell",
    "halted",
)

LIST_COPY = {
    "buy_now": {
        "title": "خرید قابل اجرا",
        "blurb": "امتیاز کمیته بالاست، قیمت به سقف نچسبیده و در سرخط هنوز فروشنده هست.",
    },
    "buy_in_red": {
        "title": "خرید در منفی",
        "blurb": "سهم منفی است، صف فروش قفل نیست، و جریان چندروزهٔ حقوقی هنوز جمع می‌کند.",
    },
    "pre_queue": {
        "title": "مستعد صف، هنوز قفل نشده",
        "blurb": "تابلو داغ است ولی سقف دامنه پر نشده. اگر حجم بماند ممکن است صف شود؛ تا وقتی فروشنده هست خرید ممکن است.",
    },
    "sell_now": {
        "title": "فروش قابل اجرا",
        "blurb": "روند و جریان پول ضعیف شده و هنوز خریدار برای اجرای فروش هست.",
    },
    "distribution": {
        "title": "خروج بازیگر",
        "blurb": "حقوقی بعد از بالا آمدن قیمت در حال عرضه است. الزاماً فرمان فروش فوری نیست.",
    },
    "locked_buy": {
        "title": "حذف از خرید: صف خرید",
        "blurb": "این نمادها در سقف قفل‌اند. کمیته حتی اگر امتیازشان بالا باشد خریدشان را پیشنهاد نمی‌کند.",
    },
    "locked_sell": {
        "title": "حذف از فروش فوری: صف فروش",
        "blurb": "فروش تازه در این صف به‌سختی اجرا می‌شود. خرید وسط این فشار هم پیشنهاد نمی‌شود.",
    },
    "halted": {
        "title": "متوقف یا ممنوع",
        "blurb": "تا رفع توقف، نه خرید و نه فروش اجرایی است.",
    },
}


@dataclass(slots=True)
class Decision:
    quote: Quote
    tape_score: float | None
    technical_score: float | None
    fundamental_score: float | None
    player_score: float | None
    news_score: float | None
    consensus: float | None
    agreement: float | None
    bucket: str | None
    thesis: str
    execution_note: str
    teams: dict
    indicators: Indicators
    tape: object
    players: object
    fundamentals: object
    news: object
    tags: list[str] = field(default_factory=list)


def _round(value: float | None, digits: int = 1) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def _consensus(parts: dict[str, float | None]) -> tuple[float | None, float | None]:
    weights = {
        "tape": 0.32,
        "technical": 0.26,
        "players": 0.24,
        "fundamental": 0.18,
    }
    if parts.get("news") is not None:
        weights = {key: value * 0.94 for key, value in weights.items()}
        weights["news"] = 0.06
    active = {key: parts[key] for key in weights if parts.get(key) is not None}
    if not active:
        return None, None
    total = sum(weights[key] for key in active)
    score = sum(parts[key] * weights[key] for key in active) / total
    spread = pstdev(active.values()) if len(active) > 1 else 0.0
    agreement = max(0.0, 100 - spread * 2.2)
    return score, agreement


def _buy_now(tape, tech, players, consensus, quote: Quote) -> bool:
    pct = quote.pct_last
    rsi = tech.indicators.rsi
    if not tape.executable_buy or tape.buy_locked or tape.halted:
        return False
    if pct is None or pct > 1.15:
        return False
    if tape.range_position is not None and tape.range_position >= 0.78:
        return False
    if tech.score is None or tech.score < 58:
        return False
    if tape.score is None or tape.score < 58:
        return False
    if consensus is None or consensus < 62:
        return False
    if rsi is not None and rsi >= 72:
        return False
    if players.score is not None and players.score < 45:
        return False
    if tape.buyer_power is not None and tape.buyer_power < 0.95 and (players.score or 0) < 60:
        return False
    return True


def _buy_red(tape, tech, players, consensus, quote: Quote) -> bool:
    pct = quote.pct_last
    rsi = tech.indicators.rsi
    if not tape.executable_buy or tape.sell_locked or tape.halted:
        return False
    if pct is None or pct > -0.45:
        return False
    if tape.range_position is not None and not (0.08 < tape.range_position < 0.62):
        return False
    if players.score is None or players.score < 64:
        return False
    if tech.score is None or tech.score < 48:
        return False
    if tape.score is None or tape.score < 52:
        return False
    if consensus is None or consensus < 58:
        return False
    if rsi is not None and rsi < 30:
        return False
    return True


def _pre_queue(tape, tech, consensus, quote: Quote) -> bool:
    pct = quote.pct_last or 0
    hot_price = pct >= 1.15 or (tape.range_position is not None and tape.range_position >= 0.72)
    if not hot_price:
        return False
    if not tape.executable_buy or tape.buy_locked or tape.at_ceiling or tape.halted:
        return False
    if tape.range_position is not None and tape.range_position >= 0.96:
        return False
    if tape.score is None or tape.score < 66:
        return False
    if tape.buyer_power is None or tape.buyer_power < 1.35:
        return False
    if tape.volume_to_base is not None and tape.volume_to_base < 1.1:
        return False
    if tech.score is None or tech.score < 52:
        return False
    rsi = tech.indicators.rsi
    if rsi is not None and rsi >= 78:
        return False
    if consensus is None or consensus < 60:
        return False
    return True


def _sell_now(tape, tech, players, consensus, quote: Quote) -> bool:
    pct = quote.pct_last
    if not tape.executable_sell or tape.sell_locked or tape.halted:
        return False
    if tape.range_position is not None and tape.range_position <= 0.12:
        return False
    if pct is not None and pct <= -2.5:
        return False
    if consensus is None or consensus > 42:
        return False
    if tech.score is None or tech.score > 42:
        return False
    weak_flow = (players.score is not None and players.score <= 45) or (tape.score is not None and tape.score <= 42)
    return weak_flow


def _distribution(players, tech, quote: Quote) -> bool:
    if players.score is None or players.score > 42:
        return False
    if players.net_legal_5 is None or players.net_legal_5 >= 0:
        return False
    if tech.score is None or not (38 <= tech.score <= 64):
        return False
    ret = tech.indicators.ret5
    if ret is None or ret < 2.5:
        return False
    if quote.pct_last is not None and quote.pct_last <= -2.5:
        return False
    return True


def decide(quote: Quote, group_pe: float | None = None, headlines: list[Headline] | None = None) -> Decision:
    tape = read_tape(quote)
    tech = read_technical(quote)
    players = read_players(quote)
    fundamentals = read_fundamental(quote, group_pe)
    news = read_news(quote, headlines)
    consensus, agreement = _consensus(
        {
            "tape": tape.score,
            "technical": tech.score,
            "players": players.score,
            "fundamental": fundamentals.score,
            "news": news.score,
        }
    )

    bucket = None
    if tape.halted:
        bucket = "halted"
    elif tape.buy_locked:
        bucket = "locked_buy"
    elif tape.sell_locked:
        bucket = "locked_sell"
    elif _pre_queue(tape, tech, consensus, quote):
        bucket = "pre_queue"
    elif _buy_red(tape, tech, players, consensus, quote):
        bucket = "buy_in_red"
    elif _buy_now(tape, tech, players, consensus, quote):
        bucket = "buy_now"
    elif _sell_now(tape, tech, players, consensus, quote):
        bucket = "sell_now"
    elif _distribution(players, tech, quote):
        bucket = "distribution"

    tags: list[str] = []
    if tape.executable_buy and bucket in {"buy_now", "buy_in_red", "pre_queue"}:
        tags.append("قابل خرید")
    if tape.executable_sell and bucket == "sell_now":
        tags.append("قابل فروش")
    if bucket == "locked_buy":
        tags.append("صف سنگین خرید" if tape.buy_queue_heavy else "صف خرید")
    if bucket == "locked_sell":
        tags.append("صف سنگین فروش" if tape.sell_queue_heavy else "صف فروش")
    if quote.pct_last is not None and quote.pct_last < 0 and bucket == "buy_in_red":
        tags.append("در منفی")
    if bucket == "pre_queue":
        tags.append("هنوز صف نشده")

    thesis = _thesis(bucket, tape, tech, players, fundamentals)
    teams = {
        "technical": {"title": "تکنیکال", "score": _round(tech.score), "stance": tech.stance, "reasons": tech.reasons},
        "fundamental": {
            "title": "بنیادی",
            "score": _round(fundamentals.score),
            "stance": fundamentals.stance,
            "reasons": fundamentals.reasons,
        },
        "tape": {"title": "تابلو", "score": _round(tape.score), "stance": tape.stance, "reasons": tape.reasons},
        "players": {"title": "بازیگران", "score": _round(players.score), "stance": players.stance, "reasons": players.reasons},
        "news": {"title": "اخبار", "score": _round(news.score), "stance": news.stance, "reasons": news.reasons},
    }
    return Decision(
        quote=quote,
        tape_score=tape.score,
        technical_score=tech.score,
        fundamental_score=fundamentals.score,
        player_score=players.score,
        news_score=news.score,
        consensus=consensus,
        agreement=agreement,
        bucket=bucket,
        thesis=thesis,
        execution_note=tape.execution_note,
        teams=teams,
        indicators=tech.indicators,
        tape=tape,
        players=players,
        fundamentals=fundamentals,
        news=news,
        tags=tags,
    )


def _thesis(bucket, tape, tech, players, fundamentals) -> str:
    if bucket == "buy_now":
        return "کمیته خرید را فقط به این دلیل می‌گذارد که هم روند و هم تابلو همراه‌اند و سهم هنوز به سقف نرسیده."
    if bucket == "buy_in_red":
        return "قیمت منفی است ولی حقوقی چند روز است جمع می‌کند و صف فروش قفل نشده."
    if bucket == "pre_queue":
        return "تابلو مستعد قفل شدن در سقف است، ولی هنوز فروشنده دارد و صف سنگین تشکیل نشده."
    if bucket == "sell_now":
        return "مومنتوم و جریان پول ضعیف شده و هنوز می‌شود بدون صف فروش خارج شد."
    if bucket == "distribution":
        return "بعد از رشد قیمت، خالص حقوقی منفی است؛ بازیگر حقوقی در حال عرضه است."
    if bucket == "locked_buy":
        return "امتیاز هرچه باشد، خرید در این صف اجرا نمی‌شود."
    if bucket == "locked_sell":
        return "برای فروش باید خریدار باشد؛ این صف خریدار کافی ندارد."
    if bucket == "halted":
        return "نماد متوقف است."
    lead = ""
    if tech.reasons:
        lead = tech.reasons[0]
    elif tape.reasons:
        lead = tape.reasons[0]
    return lead or "در هیچ‌کدام از فهرست‌های اجرایی کمیته جا نگرفت."


def industry_medians(quotes: list[Quote]) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for quote in quotes:
        if quote.industry and quote.pe is not None and quote.pe > 0:
            buckets.setdefault(quote.industry, []).append(quote.pe)
    medians: dict[str, float] = {}
    for industry, values in buckets.items():
        values.sort()
        medians[industry] = values[len(values) // 2]
    return medians


def shortlist(quotes: list[Quote], limit: int = 24) -> list[Quote]:
    """نمادهایی که تاریخچه‌شان را برای میز تکنیکال و بازیگر می‌گیریم."""

    ranked: list[tuple[float, Quote]] = []
    for quote in quotes:
        tape = read_tape(quote)
        if tape.halted or tape.buy_locked or tape.sell_locked:
            continue
        pct = quote.pct_last or 0
        interest = tape.score or 0
        if -4 <= pct <= 1.2:
            interest += 10
        if pct <= -0.4:
            interest += 8
        if tape.range_position is not None and 0.7 <= tape.range_position < 0.95:
            interest += 12
        if tape.buyer_power is not None and tape.buyer_power < 0.85:
            interest += 6
        ranked.append((interest, quote))
    ranked.sort(key=lambda item: item[0], reverse=True)
    chosen: list[Quote] = []
    seen: set[str] = set()
    for _score, quote in ranked:
        if quote.symbol in seen:
            continue
        seen.add(quote.symbol)
        chosen.append(quote)
        if len(chosen) >= limit:
            break
    weak = []
    for quote in quotes:
        tape = read_tape(quote)
        if tape.executable_sell and not tape.sell_locked and not tape.halted:
            weak.append((tape.score or 50, quote))
    weak.sort(key=lambda item: item[0])
    for _score, quote in weak[:6]:
        if quote.symbol not in seen:
            chosen.append(quote)
            seen.add(quote.symbol)
    return chosen


def _indicator_dict(ind: Indicators) -> dict:
    raw = asdict(ind)
    out = {}
    for key, value in raw.items():
        if isinstance(value, float):
            out[key] = round(value, 2)
        else:
            out[key] = value
    return out


def _million_toman(volume: float | None, price: float) -> float | None:
    """سرانه به میلیون تومان. قیمت تی‌اس‌ئی‌ام‌سی ریال است."""

    if volume is None or not price:
        return None
    return volume * price / 10_000_000


def card(decision: Decision) -> dict:
    quote = decision.quote
    tape = decision.tape
    players = decision.players
    ind = decision.indicators
    return {
        "symbol": quote.symbol,
        "name": quote.name,
        "industry": quote.industry,
        "market": quote.market,
        "kind": quote.kind,
        "state": quote.state,
        "bucket": decision.bucket,
        "last": _round(quote.last, 0),
        "close": _round(quote.close, 0),
        "pct_last": _round(quote.pct_last, 2),
        "pct_close": _round(quote.pct_close, 2),
        "tmin": _round(quote.tmin, 0),
        "tmax": _round(quote.tmax, 0),
        "range_position": _round(None if tape.range_position is None else tape.range_position * 100, 1),
        "consensus": _round(decision.consensus),
        "agreement": _round(decision.agreement),
        "scores": {
            "technical": _round(decision.technical_score),
            "fundamental": _round(decision.fundamental_score),
            "tape": _round(decision.tape_score),
            "players": _round(decision.player_score),
            "news": _round(decision.news_score),
        },
        "thesis": decision.thesis,
        "execution_note": decision.execution_note,
        "tags": decision.tags,
        "teams": decision.teams,
        "queue": {
            "buy_locked": tape.buy_locked,
            "sell_locked": tape.sell_locked,
            "buy_heavy": tape.buy_queue_heavy,
            "sell_heavy": tape.sell_queue_heavy,
            "bid_volume": tape.bid_volume,
            "ask_volume": tape.ask_volume,
            "executable_buy": tape.executable_buy,
            "executable_sell": tape.executable_sell,
        },
        "flow": {
            "buyer_power": _round(tape.buyer_power, 2),
            "buy_per_capita_mt": _round(_million_toman(tape.buy_per_capita, quote.last), 1),
            "sell_per_capita_mt": _round(_million_toman(tape.sell_per_capita, quote.last), 1),
            "real_net_volume": tape.real_net_volume,
            "legal_net_today": tape.legal_net_volume,
            "volume_to_base": _round(tape.volume_to_base, 2),
            "net_legal_3": players.net_legal_3,
            "net_legal_5": players.net_legal_5,
            "net_legal_7": players.net_legal_7,
            "buyer_power_5": _round(players.buyer_power_5, 2),
            "legal_buy_streak": players.streak,
        },
        "fundamentals": {
            "pe": _round(quote.pe, 2),
            "group_pe": _round(decision.fundamentals.group_pe, 2),
            "ps": _round(quote.ps, 2),
            "pb": _round(quote.pb, 2),
            "eps": _round(quote.eps, 1),
            "float_percent": _round(quote.float_percent, 1),
        },
        "indicators": _indicator_dict(ind),
        "headlines": decision.news.headlines,
        "limit_inferred": quote.limit_inferred,
    }


def build_board(quotes: list[Quote], headlines: list[Headline] | None = None, per_list: int = 12) -> dict:
    medians = industry_medians(quotes)
    decisions = [
        decide(quote, medians.get(quote.industry), headlines)
        for quote in quotes
        if quote.kind in {"stock", "etf"}
    ]
    buckets: dict[str, list[Decision]] = {name: [] for name in LISTS}
    for decision in decisions:
        if decision.bucket:
            buckets[decision.bucket].append(decision)

    def sort_key(item: Decision, reverse_score: bool) -> float:
        score = item.consensus if item.consensus is not None else 0
        return -score if reverse_score else score

    cards = {}
    for name, rows in buckets.items():
        descending = name in {"buy_now", "buy_in_red", "pre_queue"}
        rows.sort(key=lambda item: sort_key(item, descending))
        cards[name] = [card(item) for item in rows[:per_list]]

    return {
        "lists": cards,
        "list_copy": LIST_COPY,
        "counts": {name: len(rows) for name, rows in buckets.items()},
        "scanned": len(decisions),
    }
