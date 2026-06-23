"""Build orchestrator.

Two outputs, two purposes:
  * data/deals.json  — PUBLISHED. Curated/verified records (hand-collected seed +
                       primary-source modules). Schema-validated. Served via CDN.
  * data/leads.json  — INTERNAL (gitignored). Aggregator leads (e.g. Honolulu
                       Magazine) used as a worklist to verify at primary sources.
                       NOT republished — avoids copying a third-party compilation.

Run from repo root:  python3 -m pipeline.core.build
Fails (exit 1) without writing if any record violates the schema (CI gate).
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

import jsonschema

from pipeline.core import geocode, guards, normalize
from pipeline.sources import ala_moana, honolulu_magazine, oahu_official, waikiki_beach_walk

ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA = json.loads((ROOT / "schema" / "deal.schema.json").read_text())
DEALS_OUT = ROOT / "data" / "deals.json"
LEADS_OUT = ROOT / "data" / "leads.json"
CURATED_DIR = ROOT / "data" / "seed"

# Primary/verified -> published deals.json
PUBLISH_SOURCES = [oahu_official, ala_moana, waikiki_beach_walk]
# Aggregator leads -> internal leads.json (verify at primary before publishing)
LEAD_SOURCES = [honolulu_magazine]


def _read_curated() -> list[dict]:
    recs: list[dict] = []
    for f in sorted(CURATED_DIR.glob("*.json")):
        try:
            recs.append(json.loads(f.read_text()))
        except json.JSONDecodeError as e:
            print(f"  SKIP {f.name}: JSON parse error: {e}", file=sys.stderr)
    return recs


def _run(sources) -> tuple[list[dict], list[tuple[str, int]]]:
    out: list[dict] = []
    per: list[tuple[str, int]] = []
    for src in sources:
        name = src.__name__.split(".")[-1]
        try:
            recs = src.collect()
        except Exception as e:  # noqa: BLE001 - isolate source breakage
            print(f"  SOURCE FAIL {name}: {type(e).__name__}: {e}", file=sys.stderr)
            recs = []
        if not recs:
            print(f"  WARN {name}: 0 records (possible breakage)", file=sys.stderr)
        per.append((name, len(recs)))
        out.extend(recs)
    return out, per


def _validate(records: list[dict], label: str) -> int:
    errors = 0
    for r in records:
        try:
            jsonschema.validate(instance=r, schema=SCHEMA)
        except jsonschema.ValidationError as e:
            errors += 1
            print(f"  INVALID [{label}] {r.get('id')}: {e.message}", file=sys.stderr)
    return errors


def main() -> int:
    today = normalize.today()

    published = _read_curated()
    src_recs, pub_per = _run(PUBLISH_SOURCES)
    published += src_recs
    for r in published:
        normalize.finalize(r, today)
    published = normalize.dedupe(published)

    # Attach cached coordinates (cache-only; live geocoding is the local Tier-1 step).
    geo_cache = geocode.load_cache()
    geo_attached = 0
    for r in published:
        if r.get("lat") is None or r.get("lng") is None:
            q = geocode.query_for(r)
            if q and q in geo_cache:
                r["lat"], r["lng"] = geo_cache[q][0], geo_cache[q][1]
                geo_attached += 1

    # Guardrails: drop non-primary (aggregator) / spammy records, clean discounts.
    kept: list[dict] = []
    for r in published:
        bad = guards.denied_domain(r.get("source_url", ""))
        if bad:
            print(f"  GUARD drop (non-primary domain {bad}): {r.get('name')}", file=sys.stderr)
            continue
        if guards.looks_spammy(r):
            print(f"  GUARD drop (spam markers): {r.get('name')}", file=sys.stderr)
            continue
        if r.get("discount"):
            r["discount"] = guards.clean_discount(r["discount"])
        kept.append(r)
    published = kept

    leads, lead_per = _run(LEAD_SOURCES)
    for r in leads:
        normalize.finalize(r, today)
    leads = normalize.dedupe(leads)

    if _validate(published, "deals") or _validate(leads, "leads"):
        print("FAILED: invalid record(s) — nothing written", file=sys.stderr)
        return 1

    # Count-delta guard: refuse a sudden mass shrink (source breakage / poisoning).
    if DEALS_OUT.exists() and os.environ.get("MAKANAPO_ALLOW_SHRINK") != "1":
        try:
            prev = json.loads(DEALS_OUT.read_text())
        except Exception:
            prev = []
        prev_total = len(prev)
        prev_active = sum(1 for r in prev if r.get("status") == "active")
        new_total = len(published)
        new_active = sum(1 for r in published if r.get("status") == "active")
        if prev_total and (new_total < prev_total * 0.6 or new_active < prev_active * 0.6):
            print(
                f"FAILED: count-delta guard — total {prev_total}->{new_total}, "
                f"active {prev_active}->{new_active} (>40% drop). Nothing written. "
                f"Set MAKANAPO_ALLOW_SHRINK=1 to override if intentional.",
                file=sys.stderr,
            )
            return 1

    DEALS_OUT.write_text(json.dumps(published, indent=2, ensure_ascii=False) + "\n")
    LEADS_OUT.write_text(json.dumps(leads, indent=2, ensure_ascii=False) + "\n")

    pub_status = Counter(r["status"] for r in published)
    print("=== build summary ===")
    print(f"  curated seed: {len(_read_curated())}")
    for name, n in pub_per:
        print(f"  publish source {name:20s}: {n}")
    geo_have = sum(1 for r in published if r.get("lat") and r.get("lng"))
    print(f"  PUBLISHED deals.json: {len(published)}  by_status: {dict(pub_status)}")
    print(f"  coords: {geo_have}/{len(published)} (attached from cache this run: {geo_attached})")
    for name, n in lead_per:
        print(f"  lead source {name:20s}: {n}")
    print(f"  INTERNAL leads.json:  {len(leads)}  (not published)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
