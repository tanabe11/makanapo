#!/usr/bin/env python3
"""Summarize data/seed/*.json: counts by status, category, neighborhood.

Used for the validation-sprint Go/No-Go: target is 50 active food/service deals.
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent
SEED_DIR = ROOT / "data" / "seed"

GO_TARGET = 50


def main() -> int:
    files = sorted(SEED_DIR.glob("*.json"))
    records = []
    for path in files:
        try:
            records.append(json.loads(path.read_text()))
        except json.JSONDecodeError as e:
            print(f"  SKIP {path.name}: JSON parse error: {e}", file=sys.stderr)

    total = len(records)
    by_status = Counter(r.get("status", "?") for r in records)
    by_category = Counter(r.get("category", "?") for r in records)
    by_subcategory = Counter(r.get("subcategory", "?") for r in records)
    by_neighborhood = Counter(r.get("neighborhood", "?") for r in records)

    active = by_status.get("active", 0)
    active_food = sum(
        1 for r in records if r.get("status") == "active" and r.get("category") == "food"
    )
    active_service = sum(
        1 for r in records if r.get("status") == "active" and r.get("category") == "service"
    )

    def show(title, counter):
        print(f"\n{title}")
        for key, n in counter.most_common():
            print(f"  {n:3d}  {key}")

    print("=" * 40)
    print("makanapo seed stats")
    print("=" * 40)
    print(f"\nTotal records: {total}")
    show("By status", by_status)
    show("By category", by_category)
    show("By subcategory", by_subcategory)
    show("By neighborhood", by_neighborhood)

    print("\n" + "-" * 40)
    print(f"ACTIVE deals: {active}  (food {active_food}, service {active_service})")
    remaining = max(0, GO_TARGET - active)
    verdict = "GO ✅" if active >= GO_TARGET else f"NOT YET — need {remaining} more active"
    print(f"Go/No-Go (target {GO_TARGET} active): {verdict}")
    print("-" * 40)
    return 0


if __name__ == "__main__":
    sys.exit(main())
