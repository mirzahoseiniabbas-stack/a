"""میز بنیادی لحظه‌ای: ارزندگی نسبی، نه صورت مالی کامل کدال."""

from __future__ import annotations

from dataclasses import dataclass

from heyat.models import Quote


@dataclass(slots=True)
class FundamentalRead:
    score: float | None
    stance: str
    reasons: list[str]
    group_pe: float | None = None


def read_fundamental(quote: Quote, group_pe: float | None = None) -> FundamentalRead:
    sector = group_pe if group_pe and group_pe > 0 else None
    if quote.group_pe and quote.group_pe > 0:
        sector = quote.group_pe
    reasons: list[str] = []
    pieces = 0
    score = 50.0

    pe = quote.pe
    if pe is None:
        reasons.append("P/E در خوراک این نماد نیست.")
    elif pe <= 0:
        score -= 18
        pieces += 1
        reasons.append("سود هر سهم منفی یا صفر است و P/E ارزندگی نمی‌سازد.")
    elif sector:
        rel = pe / sector
        pieces += 1
        if 0.35 <= rel <= 0.85:
            score += 22
            reasons.append(f"P/E سهم {pe:.1f} و گروه {sector:.1f}؛ سهم از صنعت خودش ارزان‌تر است.")
        elif rel <= 1.15:
            score += 8
            reasons.append(f"P/E نزدیک میانهٔ گروه است ({pe:.1f} در برابر {sector:.1f}).")
        elif rel >= 1.7:
            score -= 16
            reasons.append(f"P/E {pe:.1f} خیلی بالاتر از گروه {sector:.1f} است.")
        else:
            score -= 6
            reasons.append(f"P/E {pe:.1f} از گروه {sector:.1f} گران‌تر است.")
    else:
        pieces += 1
        if pe <= 8:
            score += 10
            reasons.append(f"P/E {pe:.1f} در سطح پایین بازار است، ولی میانهٔ گروه برای مقایسه نیست.")
        elif pe >= 20:
            score -= 8
            reasons.append(f"P/E {pe:.1f} بالاست.")

    if quote.eps is not None and quote.eps < 0 and (pe is None or pe > 0):
        score -= 8
        reasons.append("EPS منفی است.")

    if quote.ps is not None and quote.ps > 0:
        pieces += 1
        if quote.ps < 1:
            score += 8
            reasons.append(f"P/S برابر {quote.ps:.2f} است و فروش شرکت نسبت به قیمت سنگین است.")
        elif quote.ps > 4:
            score -= 6
            reasons.append(f"P/S برابر {quote.ps:.2f} و فروش نسبت به ارزش بازار نازک است.")

    if quote.pb is not None and quote.pb > 0:
        pieces += 1
        if quote.pb < 1.6:
            score += 8
            reasons.append(f"P/B برابر {quote.pb:.2f} است.")
        elif quote.pb > 5:
            score -= 6
            reasons.append(f"P/B برابر {quote.pb:.2f} و ارزش دفتری فاصلهٔ زیادی با قیمت دارد.")
    else:
        reasons.append("P/B در خوراک لحظه‌ای نیست؛ ارزندگی با P/E نسبی و P/S سنجیده شد.")

    if quote.float_percent is not None:
        pieces += 1
        if 10 <= quote.float_percent <= 45:
            score += 4
            reasons.append(f"شناوری {quote.float_percent:.0f}٪ است و برای معاملهٔ خرد قابل‌قبول است.")
        elif quote.float_percent < 8:
            score -= 6
            reasons.append(f"شناوری فقط {quote.float_percent:.0f}٪ است و تابلو می‌تواند نازک باشد.")

    if pieces == 0:
        return FundamentalRead(
            score=None,
            stance="unknown",
            reasons=["دادهٔ بنیادی قابل‌اتکا برای این نماد نرسیده."],
            group_pe=sector,
        )

    score = max(0.0, min(100.0, score))
    stance = "buy" if score >= 60 else "sell" if score <= 42 else "watch"
    return FundamentalRead(score=score, stance=stance, reasons=reasons[:5], group_pe=sector)
