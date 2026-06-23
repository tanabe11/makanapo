"""Tier-1 (local) step: fill data/geocode_cache.json for deals missing lat/lng.

Reads data/deals.json, geocodes each record lacking coordinates via Nominatim
(rate-limited), and caches successes. Then re-run `python3 -m pipeline.core.build`
so the coordinates are attached and published. Network/Nominatim happens here,
never in the cron.

Run:  python3 -m pipeline.geocode_fill
"""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.core import geocode

ROOT = Path(__file__).resolve().parent.parent
DEALS = ROOT / "data" / "deals.json"


def main() -> int:
    deals = json.loads(DEALS.read_text())
    cache = geocode.load_cache()

    missing = [r for r in deals if r.get("lat") is None or r.get("lng") is None]
    todo = []
    for r in missing:
        q = geocode.query_for(r)
        if q and q not in cache:
            todo.append((r, q))

    print(f"missing coords: {len(missing)} | new queries to geocode: {len(todo)}")
    found = 0
    for r, q in todo:
        coords = geocode.lookup(q)
        if not coords:
            nq = geocode.name_query(r)
            if nq and nq != q:
                coords = geocode.lookup(nq)  # address failed -> try name
        if coords:
            cache[q] = coords  # store under the key build.py will look up (query_for)
            found += 1
            print(f"  OK  {r['name']} -> {coords}")
        else:
            print(f"  --  {r['name']} -> not found  ({q})")

    geocode.save_cache(cache)
    print(f"geocoded {found}/{len(todo)} new; cache size {len(cache)}.")
    print("Next: python3 -m pipeline.core.build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
