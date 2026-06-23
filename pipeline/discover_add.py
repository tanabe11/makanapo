"""Tier-1 discovery helper: verify a candidate official URL, optionally add it to
data/sources.json (config-as-data) for the Tier-2 deterministic pipeline.

Run LOCALLY (inside the makanapo-discover skill, where WebSearch found the URL):

  python3 -m pipeline.discover_add URL --category food \
      --subcategory happy_hour --neighborhood Waikiki --name "Foo Bar" [--add]

Prints the record core.venue.from_official would produce (status active /
unverified / none) so a human can judge, then --add appends it (deduped by url).
No LLM here — this is the deterministic verify+write step; the *judgment* of
which URL to pass in is done by the skill (Claude + WebSearch).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline.core import guards, venue

SOURCES = Path(__file__).resolve().parent.parent / "data" / "sources.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--category", required=True, choices=["food", "service"])
    ap.add_argument("--subcategory")
    ap.add_argument("--neighborhood")
    ap.add_argument("--name")
    ap.add_argument("--add", action="store_true", help="append to data/sources.json if usable")
    args = ap.parse_args()

    bad = guards.denied_domain(args.url)
    if bad:
        print(f"REFUSED: '{bad}' is a non-primary/aggregator domain. Publish only a "
              f"business's OWN official page (aggregators are leads-only).")
        return 1

    site = {"url": args.url, "category": args.category}
    for k in ("subcategory", "neighborhood", "name"):
        if getattr(args, k):
            site[k] = getattr(args, k)

    try:
        rec = venue.from_official(**site)
    except Exception as e:  # noqa: BLE001
        print(f"VERIFY FAILED: {type(e).__name__}: {e}")
        return 1
    if not rec:
        print("No record produced (no name resolved / nothing extractable). Not adding.")
        return 1

    print(json.dumps(rec, ensure_ascii=False, indent=2))
    print(f"\n-> status={rec['status']}  discount={rec.get('discount')!r}")

    if not args.add:
        print("(dry run — pass --add to write to data/sources.json)")
        return 0

    cfg = json.loads(SOURCES.read_text())
    sites = cfg.setdefault("official_sites", [])
    if any(s.get("url") == args.url for s in sites):
        print("Already present in sources.json — no change.")
        return 0
    sites.append(site)
    SOURCES.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
    print(f"ADDED to data/sources.json (now {len(sites)} official_sites). Rebuild to publish.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
