"""OSM Nominatim geocoding with an on-disk cache (data/geocode_cache.json).

Two-tier split: live Nominatim lookups happen LOCALLY only, via
`python3 -m pipeline.geocode_fill` (Tier-1). `build.py` (Tier-2/cron) only
READS the cache to attach lat/lng — it never calls Nominatim, keeping the daily
pipeline network-light and within Nominatim's usage policy.

Nominatim policy compliance: descriptive User-Agent + >= 1 request/second.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CACHE = ROOT / "data" / "geocode_cache.json"

_UA = "makanapo-geocoder/0.1 (+https://po.makana.fm; tanabe11@gmail.com)"
_MIN_INTERVAL = 1.1  # seconds between Nominatim requests (policy: max ~1/sec)
_last = 0.0


def query_for(rec: dict) -> str | None:
    """The geocoding query for a deal: its address, else name + neighborhood + city."""
    addr = rec.get("address")
    if addr:
        return addr
    name = rec.get("name")
    if not name:
        return None
    return name_query(rec)


def name_query(rec: dict) -> str | None:
    """Fallback query from name (+ neighborhood) — used when an address lookup fails."""
    name = rec.get("name")
    if not name:
        return None
    parts = [name]
    if rec.get("neighborhood"):
        parts.append(rec["neighborhood"])
    parts += ["Honolulu", "HI"]
    return ", ".join(parts)


def _clean_for_api(q: str) -> str:
    """Strip ʻokina/macrons and suite/unit tokens so Nominatim matches more reliably."""
    q = q.replace("‘", "").replace("’", "").replace("ʻ", "").replace("ʼ", "")
    q = "".join(c for c in unicodedata.normalize("NFKD", q) if not unicodedata.combining(c))
    q = re.sub(r",?\s*(?:suite|ste\.?|unit|bldg|building|#)\s*[\w-]+", "", q, flags=re.I)
    return re.sub(r"\s+", " ", q).strip()


def load_cache() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text())
        except Exception:
            return {}
    return {}


def save_cache(cache: dict) -> None:
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def lookup(query: str) -> list[float] | None:
    """Live Nominatim lookup (rate-limited). Returns [lat, lng] or None. Local use only."""
    global _last
    wait = _MIN_INTERVAL - (time.time() - _last)
    if wait > 0:
        time.sleep(wait)
    _last = time.time()
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": _clean_for_api(query), "format": "json", "limit": 1, "countrycodes": "us"}
    )
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
        return [float(data[0]["lat"]), float(data[0]["lon"])] if data else None
    except Exception:
        return None
