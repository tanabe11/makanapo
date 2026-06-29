"""Pre-publish guardrails (run before deals.json is written/committed).

These encode, as deterministic code, the checks a human used to do when reviewing
a discovery diff — so the pipeline can run unattended without publishing junk:

  * denied_domain(url) — aggregators / review sites / social must never be a
    published source (copyright + non-primary). Real sources = a business's OWN page.
  * looks_spammy(rec)  — parked/hijacked domain markers (casino/pharma/...).
  * clean_discount(s)  — collapse whitespace and trim run-on regex captures.
  * count-delta guard lives in build.py (needs the previous deals.json).
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

# Non-primary hosts: aggregators, review sites, social, listicles. Publishing these
# would republish a third-party compilation (copyright) or non-official data.
DENY_DOMAINS = {
    "honolulumagazine.com", "hawaiimagazine.com",
    "yelp.com", "opentable.com", "tripadvisor.com", "foursquare.com",
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "google.com", "maps.google.com", "goo.gl", "groupon.com",
    "hawaiihappyhours.com", "ultimatehappyhours.com", "totalhappyhour.com",
    "onolicioushawaii.com", "localicioushawaii.org",
    "restaurantji.com", "wheree.com", "hungryfoody.com", "gohawaii.com",
}

# Obvious parked-domain / hijack spam — should never appear in a real venue deal.
_SPAM = re.compile(
    r"\b(casino|viagra|cialis|porn|sex\s*cam|crypto|airdrop|payday|forex|"
    r"escort|replica\s+watch|betting|gambling)\b",
    re.I,
)

_MAX_DISCOUNT = 70


def domain_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def denied_domain(url: str) -> str | None:
    """Return the matched denied domain (or None) for a source URL."""
    host = domain_of(url)
    for d in DENY_DOMAINS:
        if host == d or host.endswith("." + d):
            return d
    return None


# Oahu bounding box (rough) for sanity-checking geocoded coordinates.
_OAHU = (21.20, 21.75, -158.32, -157.60)  # lat_min, lat_max, lng_min, lng_max


def out_of_area(rec: dict) -> bool:
    """True only with POSITIVE evidence the venue is NOT on Oahu — geocoded coords
    off-island, or a non-Hawaii ZIP (HI = 967xx/968xx) in the address. Catches a
    same-name store in another state or a chain's national page. Ambiguous (no
    coords/zip) returns False (let probation/human catch it)."""
    lat, lng = rec.get("lat"), rec.get("lng")
    if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
        if not (_OAHU[0] <= lat <= _OAHU[1] and _OAHU[2] <= lng <= _OAHU[3]):
            return True
    # A genuine Oahu address carries a 967xx/968xx ZIP. Only flag out-of-area when
    # ZIP-like tokens exist and NONE is a Hawaii ZIP. Scanning all 5-digit groups
    # (not just the first) tolerates a mis-extracted leading number, e.g.
    # "22301 Kalakaua Ave, Honolulu, HI 96815", which would otherwise read "22301"
    # as the ZIP and wrongly drop a real Waikiki venue.
    zips = re.findall(r"\b(\d{5})\b", rec.get("address") or "")
    if zips and not any(z[:3] in ("967", "968") for z in zips):
        return True
    return False


def looks_spammy(rec: dict) -> bool:
    blob = " ".join(str(rec.get(k, "")) for k in ("name", "discount", "conditions"))
    return bool(_SPAM.search(blob))


def clean_discount(s: str | None) -> str | None:
    """Collapse whitespace; trim run-on regex captures to the lead offer."""
    if not s:
        return s
    s = re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()
    if len(s) <= _MAX_DISCOUNT:
        return s
    return s[:_MAX_DISCOUNT].rsplit(" ", 1)[0] + "…"
