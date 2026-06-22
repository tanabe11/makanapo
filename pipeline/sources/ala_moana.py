"""Source: Ala Moana Center official kama'aina discounts (PRIMARY / mall-operator).

Official mall page lists current merchant kamaaina offers with the discount text
inline (statically rendered). We keep only food & service (MVP scope) and emit
them as `status: active` (operator-listed, current). Legally clean: a mall's own
offers page is a primary source, not a third-party editorial compilation.

Card structure (Brookfield/GGP markup):
  ...content-wrapper... <offer text> ... <strong>Merchant Name</strong> ... <date>
"""

from __future__ import annotations

import re
from datetime import date

from pipeline.core import classify, extract, fetch, normalize

URL = "https://www.alamoanacenter.com/en/shopping/kamaainadiscounts/"
ADDRESS = "1450 Ala Moana Boulevard, Ala Moana Center, Honolulu, HI 96814"
NEIGHBORHOOD = "Ala Moana"
LAT, LNG = 21.2911, -157.8434

_MONTHS = {
    m: i
    for i, m in enumerate(
        ["january", "february", "march", "april", "may", "june", "july", "august",
         "september", "october", "november", "december"], 1
    )
}
_DATE = re.compile(r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})")
_ICON_NOISE = re.compile(r"Icons\s*/\s*ggpcorp-malls\s*/\s*\w+", re.I)
_NAME = re.compile(r"<strong>(.*?)</strong>", re.I | re.S)


def _last_date(text: str) -> str | None:
    best = None
    for mo, d, y in _DATE.findall(text):
        m = _MONTHS.get(mo.lower())
        if not m:
            continue
        try:
            iso = date(int(y), m, int(d)).isoformat()
        except ValueError:
            continue
        if best is None or iso > best:
            best = iso
    return best


def collect() -> list[dict]:
    today = normalize.today()
    html = fetch.get_text(URL, timeout=40)
    out: list[dict] = []

    for chunk in html.split("b-mall-offer-card-list__content-wrapper")[1:]:
        # the split lands mid-attribute; drop the dangling tag tail before text
        chunk = chunk.split(">", 1)[1] if ">" in chunk else chunk
        m = _NAME.search(chunk)
        if not m:
            continue
        name = extract.strip_html(m.group(1))
        if not name:
            continue
        offer = _ICON_NOISE.sub("", extract.strip_html(chunk[: m.start()])).strip()

        category = classify.category_of(name, offer)
        if category is None:
            continue  # retail -> skip (out of MVP scope)

        discount = extract.find_discount(offer) or offer[:80].rstrip(" ,;")
        rec: dict = {
            "id": normalize.make_id(f"{name} {NEIGHBORHOOD}", URL),
            "name": name,
            "category": category,
            "discount": discount,
            "conditions": "show valid Hawaii state photo ID",
            "redemption": "show_id",
            "requires_id": True,
            "address": ADDRESS,
            "lat": LAT,
            "lng": LNG,
            "neighborhood": NEIGHBORHOOD,
            "source_url": URL,
            "last_verified": today,
        }
        expiry = _last_date(extract.strip_html(chunk))
        if expiry:
            rec["valid_until"] = expiry
        rec["status"] = "expired" if expiry and expiry < today else "active"
        out.append(rec)

    return out
