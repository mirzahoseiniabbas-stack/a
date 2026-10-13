"""میز اخبار: پیام ناظر و تیتر کدال، با واژگان ساده نه مدل زبانی."""

from __future__ import annotations

from dataclasses import dataclass

from heyat.models import Headline, Quote


POSITIVE = (
    "افزایش سرمایه",
    "تعدیل مثبت",
    "سود خالص",
    "قرارداد",
    "بهره‌برداری",
    "بهره برداری",
    "مجوز",
    "تقسیم سود",
    "شفاف‌سازی مثبت",
    "برنده",
    "تقاضای خرید",
)
NEGATIVE = (
    "توقف نماد",
    "تعلیق",
    "ممنوع‌المعامله",
    "زیان",
    "تعدیل منفی",
    "ابهام",
    "ورشکست",
    "برگشت از سود",
    "عدم تأیید",
    "عدم تایید",
    "رد شدن",
    "حراج مجدد",
)


@dataclass(slots=True)
class NewsRead:
    score: float | None
    stance: str
    reasons: list[str]
    headlines: list[str]


def read_news(quote: Quote, extra: list[Headline] | None = None) -> NewsRead:
    items = list(quote.headlines)
    symbol = quote.symbol
    for headline in extra or []:
        if headline.symbol and headline.symbol == symbol:
            items.append(headline)
        elif symbol and symbol in headline.title:
            items.append(headline)
    # یکتا بر اساس تیتر
    seen: set[str] = set()
    unique: list[Headline] = []
    for item in items:
        if item.title in seen:
            continue
        seen.add(item.title)
        unique.append(item)

    if not unique:
        return NewsRead(
            score=None,
            stance="unknown",
            reasons=["خبر تازهٔ مرتبط با این نماد در پیام ناظر و کدالِ دریافت‌شده نیست."],
            headlines=[],
        )

    score = 50.0
    reasons: list[str] = []
    for item in unique[:6]:
        title = item.title
        hit_pos = [word for word in POSITIVE if word in title]
        hit_neg = [word for word in NEGATIVE if word in title]
        if hit_pos and not hit_neg:
            score += 10
            reasons.append(f"تیتر {item.source or 'خبر'}: {title}")
        elif hit_neg and not hit_pos:
            score -= 14
            reasons.append(f"هشدار {item.source or 'خبر'}: {title}")
        else:
            reasons.append(f"تیتر خنثی {item.source or 'خبر'}: {title}")

    score = max(0.0, min(100.0, score))
    stance = "buy" if score >= 62 else "sell" if score <= 40 else "watch"
    return NewsRead(
        score=score,
        stance=stance,
        reasons=reasons[:4],
        headlines=[item.title for item in unique[:4]],
    )
