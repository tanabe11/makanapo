"""Build a deal record from a business's OWN official page (primary source).

Combines schema.org JSON-LD (name / address / geo / hours) with regex fact
extraction (discount / requires_id / expiry). If a discount is confidently
extracted from a primary source, the record is `status: active`.
"""

from __future__ import annotations

import re

from pipeline.core import extract, fetch, jsonld, normalize

_BIZ_TYPES = (
    "Restaurant",
    "FoodEstablishment",
    "CafeOrCoffeeShop",
    "BarOrPub",
    "LocalBusiness",
    "HealthAndBeautyBusiness",
    "DaySpa",
    "HairSalon",
)


def _flatten_address(addr) -> str | None:
    if isinstance(addr, str):
        parts = [p.strip() for p in re.split(r"[\n,]", addr) if p.strip()]
        parts = [p for p in parts if p.lower() != "united states"]
        return ", ".join(parts) or None
    if isinstance(addr, dict):
        keys = ["streetAddress", "addressLocality", "addressRegion", "postalCode"]
        parts = [str(addr[k]).strip() for k in keys if addr.get(k)]
        return ", ".join(parts) or None
    return None


def _hours(node: dict) -> str | None:
    h = node.get("openingHours")
    if isinstance(h, list):
        return "; ".join(str(x) for x in h)
    if isinstance(h, str):
        return h
    return None


def _pick_business(ld: list[dict]) -> dict | None:
    for d in ld:
        t = d.get("@type")
        types = t if isinstance(t, list) else [t]
        if any(any(b in str(x) for b in _BIZ_TYPES) for x in types) and (
            d.get("address") or d.get("geo") or d.get("openingHours")
        ):
            return d
    for d in ld:  # fallback: anything carrying an address
        if d.get("address"):
            return d
    return None


def from_official(
    url: str,
    category: str,
    subcategory: str | None = None,
    neighborhood: str | None = None,
    name: str | None = None,
    address: str | None = None,
) -> dict | None:
    html = fetch.get_text(url)
    biz = _pick_business(jsonld.extract_jsonld(html)) or {}
    text = extract.strip_html(html)
    today = normalize.today()

    resolved_name = name or biz.get("name") or ""
    if not resolved_name:
        return None

    rec: dict = {
        "id": normalize.make_id(f"{resolved_name} {neighborhood or ''}", url),
        "name": resolved_name,
        "category": category,
        "source_url": url,
        "last_verified": today,
    }
    if subcategory:
        rec["subcategory"] = subcategory
    if neighborhood:
        rec["neighborhood"] = neighborhood

    addr = _flatten_address(biz.get("address")) or extract.find_address(text) or address
    if addr:
        rec["address"] = addr
    geo = biz.get("geo")
    if isinstance(geo, dict) and geo.get("latitude") and geo.get("longitude"):
        try:
            lat = float(geo["latitude"])
            lng = float(geo["longitude"])
            # Some Hawaii sites publish a sign-flipped longitude in JSON-LD (e.g.
            # +157.83 instead of -157.83), which lands the venue in the western
            # Pacific and trips the off-Oahu guard. Hawaii is at negative longitude,
            # so flip a positive Pacific longitude paired with a Hawaii latitude.
            if 18.0 <= lat <= 23.0 and 154.0 <= lng <= 161.0:
                lng = -lng
            rec["lat"] = lat
            rec["lng"] = lng
        except (TypeError, ValueError):
            pass
    # On a happy-hour deal, `hours` means the HH window only — general opening
    # hours would misleadingly read as "happy hour all day". So for HH deals use
    # the extracted window if found, else leave hours unset; other deals keep
    # the venue's stated opening hours.
    if subcategory == "happy_hour":
        window = extract.find_happy_hour_window(text)
        if window:
            rec["hours"] = window
    else:
        hrs = _hours(biz)
        if hrs:
            rec["hours"] = hrs

    discount = extract.find_discount(text)
    # Happy-hour fallback: the official page advertises a happy hour but no % is
    # machine-readable -> still a verified deal at the primary source.
    if not discount and subcategory == "happy_hour" and extract.has_happy_hour(text):
        discount = "happy hour specials"
    if discount:
        rec["discount"] = discount
    if extract.requires_id(text):
        rec["requires_id"] = True
        rec["redemption"] = "show_id"
    expiry = extract.find_source_expiry(text)
    if expiry:
        rec["valid_until"] = expiry

    # Primary source: extracted discount -> active (unless its stated date has passed).
    if expiry and expiry < today:
        rec["status"] = "expired"
    elif discount:
        rec["status"] = "active"
    else:
        rec["status"] = "unverified"  # venue found but no deal detail -> link for user to confirm

    return rec
