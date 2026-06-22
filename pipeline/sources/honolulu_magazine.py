"""Source: Honolulu Magazine — Kama'aina Deals: Restaurants and Eateries.

A Tier-2 LEAD source (editorial listicle): records are emitted as
`status: unverified` with a link back to the article so the user can confirm
at the primary source. Pulled via the WordPress REST API (clean JSON, no JS).

Article HTML structure (one deal per block):
    <h2>Business Name</h2>
    <p>10% off food (excludes alcohol).</p>
Region headers are <h2> followed by an empty <p>: <h2>WAIKIKI</h2><p>&nbsp;</p>
"""

from __future__ import annotations

import re

from pipeline.core import extract, fetch, normalize

API = "https://www.honolulumagazine.com/wp-json/wp/v2/posts?slug=kamaaina-deals-restaurants"
ARTICLE = "https://www.honolulumagazine.com/kamaaina-deals-restaurants/"

# Region markers that are <h2> headings, not deals.
_SECTIONS = {"waikiki", "waikīkī", "outside waikiki", "outside waikīkī"}

# Each <h2> and the immediately following <p> (the deal's one-line description).
_BLOCK = re.compile(r"<h2[^>]*>(.*?)</h2>\s*(?:<p[^>]*>(.*?)</p>)?", re.I | re.S)


def _section_label(low: str, name: str) -> str:
    if "outside" in low:
        return "Outside Waikiki"
    if "waik" in low:
        return "Waikiki"
    return name.title()


def collect() -> list[dict]:
    today = normalize.today()
    posts = fetch.get_json(API)
    if not posts:
        return []
    html = posts[0]["content"]["rendered"]

    records: list[dict] = []
    section: str | None = None

    for m in _BLOCK.finditer(html):
        name = extract.strip_html(m.group(1))
        body = extract.strip_html(m.group(2) or "")
        if not name:
            continue

        low = name.lower()
        if low in _SECTIONS or (name.isupper() and not body):
            section = _section_label(low, name)
            continue
        if not body:
            continue  # SEE ALSO / nav blocks etc.

        discount = extract.find_discount(body)
        has_id = extract.requires_id(body) or extract.requires_id(name)
        # Skip headings that are clearly not deals (long prose, no discount, no ID cue).
        if not discount and not has_id and len(body) > 120:
            continue

        rec: dict = {
            # include section so chain locations (e.g. Alo Café in two areas) stay distinct
            "id": normalize.make_id(f"{name} {section or ''}", ARTICLE),
            "name": name,
            "category": "food",
            "source_url": ARTICLE,
            "last_verified": today,
        }
        if discount:
            rec["discount"] = discount
        elif len(body) <= 120:
            rec["discount"] = body.rstrip(".")  # short factual line e.g. "Complimentary appetizer"
        if has_id:
            rec["requires_id"] = True
            rec["redemption"] = "show_id"
        if section:
            rec["neighborhood"] = section
        cond = re.search(r"\(([^)]+)\)", body)
        if cond:
            rec["conditions"] = cond.group(1).strip()

        # Honolulu Magazine is a lead -> unverified; flag expired if its stated date has passed.
        expiry = extract.find_source_expiry(body)
        if expiry:
            rec["valid_until"] = expiry
            rec["status"] = "expired" if expiry < today else "unverified"
        else:
            rec["status"] = "unverified"

        records.append(rec)

    return records
