"""Source: Waikiki Beach Walk official Kama'aina & Military page (PRIMARY / mall).

Static .htm page listing merchant kamaaina offers. Category comes from the
merchant link path (/Restaurants -> food, /Services -> service, /Shops -> skip),
which is a deterministic signal — no keyword guessing. Food & service only.
"""

from __future__ import annotations

import re
from datetime import date

from pipeline.core import extract, fetch, normalize

URL = "https://www.waikikibeachwalk.com/Events-And-News/Kamaaina-Military.htm"
ADDRESS = "226 Lewers Street, Waikiki Beach Walk, Honolulu, HI 96815"
NEIGHBORHOOD = "Waikiki"
LAT, LNG = 21.2826, -157.8290

# Each merchant: <a href="/Restaurants|Shops|Services/.../Name.htm">...Name:...</a>
_MERCHANT = re.compile(r'href="(/(?:Restaurants|Shops|Services)/[^"]+\.htm)"[^>]*>(.*?)</a>', re.I | re.S)
# The kamaaina line: "Kamaʻāina: 10% off" (also "Kamaʻāina and Military: 15% off")
_KAMA = re.compile(r"kama\S*?ina[^:]*:\s*(.+?)(?:\bmilitary\b|$)", re.I | re.S)
_COND = re.compile(r"((?:discount not valid|valid only|not valid|excludes?|excl)\b[^\n]*)", re.I)


def _category(path: str) -> str | None:
    if path.startswith("/Restaurants"):
        return "food"
    if path.startswith("/Services"):
        return "service"
    return None  # /Shops -> retail, out of scope


def collect() -> list[dict]:
    today = normalize.today()
    html = fetch.get_text(URL, timeout=30)
    matches = list(_MERCHANT.finditer(html))
    out: list[dict] = []

    for idx, m in enumerate(matches):
        category = _category(m.group(1))
        if category is None:
            continue
        name = extract.strip_html(m.group(2)).rstrip(":").strip()
        if not name:
            continue
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(html)
        block = extract.strip_html(html[m.end() : end])

        km = _KAMA.search(block)
        if not km:
            continue  # no kamaaina-specific deal here -> skip
        segment = km.group(1).strip()
        discount = extract.find_discount(segment) or segment.split("  ")[0].strip()[:80]
        if not discount:
            continue

        rec: dict = {
            "id": normalize.make_id(f"{name} {NEIGHBORHOOD}", URL),
            "name": name,
            "category": category,
            "discount": discount,
            "redemption": "show_id",
            "requires_id": True,
            "address": ADDRESS,
            "lat": LAT,
            "lng": LNG,
            "neighborhood": NEIGHBORHOOD,
            "source_url": URL,
            "last_verified": today,
            "status": "active",
        }
        cond = _COND.search(block)
        rec["conditions"] = (
            "show valid Hawaii ID; " + cond.group(1).strip() if cond else "show valid Hawaii ID"
        )
        out.append(rec)

    return out
