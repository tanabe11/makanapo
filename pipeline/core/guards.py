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
