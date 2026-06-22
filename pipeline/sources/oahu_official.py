"""Source: Oahu businesses' OWN official pages (PRIMARY source).

Config-as-data: the list of official URLs lives in data/sources.json
("official_sites"), which the Tier-1 discovery skill appends to and this
Tier-2 deterministic module reads. The shared core.venue.from_official does
the work (JSON-LD venue facts + regex discount). A confidently extracted
discount from a primary source -> status: active.
"""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.core import venue

SOURCES = Path(__file__).resolve().parent.parent.parent / "data" / "sources.json"


def _load_sites() -> list[dict]:
    if not SOURCES.exists():
        return []
    cfg = json.loads(SOURCES.read_text())
    return cfg.get("official_sites", [])


def collect() -> list[dict]:
    out: list[dict] = []
    for site in _load_sites():
        site = {k: v for k, v in site.items() if not k.startswith("_")}
        try:
            rec = venue.from_official(**site)
        except PermissionError as e:
            print(f"  SKIP (robots) {site.get('url')}: {e}")
            continue
        except Exception as e:  # noqa: BLE001 - isolate per-site breakage
            print(f"  SKIP {site.get('url')}: {type(e).__name__}: {e}")
            continue
        if rec:
            out.append(rec)
    return out
