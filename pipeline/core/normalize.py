"""Record normalization: slug/id generation, defaults, dedupe."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone

# Hawaii has no DST -> a fixed UTC-10 offset. Use this everywhere for the
# "today" of last_verified so CI (UTC runners) and local (HST) agree on the date
# and don't produce spurious daily diffs / branch divergence.
_HST = timezone(timedelta(hours=-10))


def today() -> str:
    return datetime.now(_HST).date().isoformat()


def slugify(name: str) -> str:
    s = (name or "").lower()
    for ch in "'‘’`ʻ":
        s = s.replace(ch, "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "deal"


def make_id(name: str, source_url: str) -> str:
    h = hashlib.sha1((slugify(name) + source_url).encode()).hexdigest()[:6]
    return f"{slugify(name)}-{h}"


def finalize(rec: dict, today_str: str | None = None) -> dict:
    rec.setdefault("last_verified", today_str or today())
    rec.setdefault("status", "unverified")
    return rec


_STATUS_PRIO = {"active": 0, "unverified": 1, "expired": 2}


def _identity(r: dict) -> tuple[str, str]:
    """Cross-source identity: normalized name + neighborhood.

    Drops parenthetical location suffixes ("(Ala Moana Center)") and macrons/punct
    so the same venue from different sources collapses to one record.
    """
    name = re.sub(r"\(.*?\)", "", r.get("name") or "")
    hood = (r.get("neighborhood") or "").strip()
    if hood:  # drop a trailing neighborhood qualifier, e.g. "Yard House Waikiki"
        name = re.sub(re.escape(hood) + r"\s*$", "", name, flags=re.I)
    n = re.sub(r"[^a-z0-9]+", "", name.lower())
    return (n, hood.lower())


def dedupe(records: list[dict]) -> list[dict]:
    """Dedupe by (name, neighborhood). Prefer better status, then richer record."""
    best: dict[tuple[str, str], dict] = {}
    for r in records:
        k = _identity(r)
        cur = best.get(k)
        if cur is None:
            best[k] = r
            continue
        rank_r = (_STATUS_PRIO.get(r.get("status"), 9), -len(r))
        rank_cur = (_STATUS_PRIO.get(cur.get("status"), 9), -len(cur))
        if rank_r < rank_cur:
            best[k] = r
    return list(best.values())
