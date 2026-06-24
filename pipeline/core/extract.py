"""Deterministic fact extraction: HTML stripping + regex helpers.

No LLM. Pulls discount / requires_id / source-stated expiry from short text.
"""

from __future__ import annotations

import html as _html
import re
from datetime import date

_TAG = re.compile(r"<[^>]+>")


def strip_html(s: str | None) -> str:
    return _html.unescape(_TAG.sub("", s or "")).strip()


# Stop the capture at sentence/clause boundaries and exclamation spam.
_STOP = r"[^.<|()!\n\r]*"
_DISCOUNT_RE = re.compile(
    r"(\d+%\s*off" + _STOP
    + r"|BOGO"
    + r"|buy one get one" + _STOP
    + r"|\$\d+\s*off" + _STOP
    + r"|(?:1/2|half)[- ]?(?:price|off)" + _STOP
    + r"|complimentary " + _STOP
    + r"|kama['‘`ʻ]?aina (?:rate|price|discount))",
    re.I,
)


def find_discount(text: str | None) -> str | None:
    m = _DISCOUNT_RE.search(text or "")
    return m.group(0).strip().rstrip(".") if m else None


# Require ID cues to sit close together (avoid false hits like "Hawaiian Airlines").
_ID_RE = re.compile(
    r"kama['‘`ʻ]?aina"
    r"|hawai['‘`ʻ]?i\s*(?:state\s*)?id\b"
    r"|(?:show|present)\s+(?:your\s+|a\s+)?(?:valid\s+)?(?:hawai\S*\s+)?(?:state\s+)?id\b",
    re.I,
)


def requires_id(text: str | None) -> bool:
    return bool(_ID_RE.search(text or ""))


_HH_RE = re.compile(r"happy hour|pau hana|aloha hour", re.I)


def has_happy_hour(text: str | None) -> bool:
    return bool(_HH_RE.search(text or ""))


# am/pm with dots only as a paired abbreviation ("pm" or "p.m."), never a stray
# trailing sentence period (so "5 pm." yields "5 pm", not "5 pm.").
_AMPM = r"(?:[ap]m|[ap]\.m\.)"
# A clock time: "3", "3:30", "3pm", "3:30 p.m." — am/pm optional.
_TIME = r"\d{1,2}(?::\d{2})?\s*" + _AMPM + r"?"
# A time range whose END carries am/pm (so we don't grab bare number ranges like a street range).
_RANGE_RE = re.compile(
    _TIME + r"\s*(?:-|–|—|to|until|till|til)\s*"
    + r"\d{1,2}(?::\d{2})?\s*" + _AMPM,
    re.I,
)
# Day / frequency phrase: "Mon", "Mon-Fri", "Monday through Friday", "daily", "weekdays".
_DAYS_RE = re.compile(
    r"(?:mon|tue|tues|wed|weds|thu|thur|thurs|fri|sat|sun)[a-z]*"
    r"(?:\s*(?:-|–|—|through|thru|to|&|/|,|and)\s*"
    r"(?:mon|tue|tues|wed|weds|thu|thur|thurs|fri|sat|sun)[a-z]*)?"
    r"|daily|every\s*day|weekdays?",
    re.I,
)
# Only trust a time range that sits close to the happy-hour mention.
_HH_NEAR = 100


def find_happy_hour_window(text: str | None) -> str | None:
    """The happy-hour time window stated near a HH mention, e.g. 'Mon-Fri 3-6pm'.

    Fact-only: returns the time range (plus an immediately-leading day/frequency
    phrase when present). Returns None if no explicit range sits near the keyword
    — recall is intentionally limited rather than guessing.
    """
    t = text or ""
    kw = _HH_RE.search(t)
    if not kw:
        return None
    window = t[kw.start() : kw.end() + _HH_NEAR]
    rng = _RANGE_RE.search(window)
    if not rng:
        return None
    time_str = re.sub(r"\s+", " ", rng.group(0)).strip()
    before = window[: rng.start()]
    last_day = None
    for m in _DAYS_RE.finditer(before):
        last_day = m
    if last_day and rng.start() - last_day.end() <= 3:  # directly precedes the range
        day_str = re.sub(r"\s+", " ", last_day.group(0)).strip()
        return f"{day_str} {time_str}"
    return time_str


_MONTHS = {
    m: i
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1
    )
}
_EXPIRY_RE = re.compile(r"through\s+([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})", re.I)


_ADDR_RE = re.compile(
    r"\d{2,5}[\w .,'#&/‘’ʻ-]{3,60}?Honolulu,?\s*(?:HI|Hawai)[\w .]*?9\d{4}",
    re.I,
)


def find_address(text: str | None) -> str | None:
    """Best-effort US street address ending in 'Honolulu, HI 96xxx' from page text."""
    m = _ADDR_RE.search(text or "")
    if not m:
        return None
    a = re.sub(r"\s+", " ", m.group(0)).strip()
    # ensure a separator before "Honolulu" (pages often run them together)
    a = re.sub(r"\s*,?\s*Honolulu", ", Honolulu", a, count=1)
    return a


def find_source_expiry(text: str | None) -> str | None:
    """Return YYYY-MM-DD from phrases like 'through Aug. 31, 2025', else None."""
    m = _EXPIRY_RE.search(text or "")
    if not m:
        return None
    mon = _MONTHS.get(m.group(1)[:3].lower())
    if not mon:
        return None
    try:
        return date(int(m.group(3)), mon, int(m.group(2))).isoformat()
    except ValueError:
        return None
