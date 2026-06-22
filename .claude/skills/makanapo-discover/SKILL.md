---
name: makanapo-discover
description: Use when expanding makanapo's deal sources / running discovery — find new Honolulu food & service venues' official kamaaina or happy-hour pages via web search, verify them deterministically, and append usable ones to data/sources.json so the Tier-2 pipeline publishes them. Run locally (needs WebSearch).
---

# makanapo — discovery (Tier 1, local, LLM + WebSearch)

This is the **LLM/judgment half** of the two-tier design. It runs locally (where
WebSearch is available), updates **config-as-data** (`data/sources.json`), and
the deterministic GitHub Actions pipeline (`pipeline/core/build.py`) then
publishes from that config. **Never write `data/deals.json` here** — only config.

## Scope guards (do not violate)
- Oahu / Honolulu only; **food & service only** (no retail).
- **Aggregators are leads-only**: do NOT add Honolulu Magazine / mall editorial
  lists as `official_sites`. Only a business's OWN official page (or an official
  mall offers page that already has its own parser module) is publishable.
- Facts only; the pipeline never copies descriptions. Respect robots.txt (the
  fetch layer enforces it — a robots-blocked URL will simply not verify).

## Workflow
1. **Load state** to avoid duplicates and find targets:
   - `data/sources.json` → URLs already configured.
   - `data/deals.json` → venues already published (names).
   - `data/leads.json` → candidate venue **names** harvested from aggregators
     (Honolulu Magazine). These are the primary worklist.
2. **Pick a batch** of candidate venues (from leads, or new ideas) not already
   covered. Prefer happy-hour and kamaaina spots likely to state the deal on
   their own site (independent / Squarespace sites convert best; large WordPress
   chains often hide deals in PDFs and won't verify → that's fine).
3. For each candidate, **WebSearch** for its official site, e.g.
   `"<name>" Honolulu official website happy hour` or `... kamaaina`.
   Take the business's OWN domain (not Yelp/OpenTable/Instagram/aggregators).
4. **Verify deterministically** (dry run):
   ```
   python3 -m pipeline.discover_add "<official_url>" --category food \
       --subcategory happy_hour --neighborhood Waikiki --name "<Name>"
   ```
   Read the printed record:
   - `status: active` → great (a discount/HH was extracted from the primary source).
   - `status: unverified` → acceptable (venue found, no machine-readable deal →
     app shows an official-source link for the user to confirm).
   - `No record` / robots / fetch fail → skip.
5. **Add the usable ones**: re-run the same command with `--add` to append to
   `data/sources.json` (deduped by url).
6. After the batch, **rebuild and review**:
   ```
   python3 -m pipeline.core.build      # regenerates data/deals.json (validated)
   python3 -m pipeline.stats           # active/unverified/expired counts
   python3 -m pipeline.preview && open data/preview.html
   ```
7. **Present the diff** of `data/sources.json` (and the active-count change) for
   the human to approve, then commit. Do not auto-push.

## Notes
- `discover_add` does no LLM work — it just fetches + extracts + writes config.
  The intelligence (which URL, which category) is yours (Claude + WebSearch).
- New aggregator/mall *offers pages* with their own structure need a new thin
  parser module under `pipeline/sources/` (see `ala_moana.py`, `waikiki_beach_walk.py`),
  not a `sources.json` entry.
- Keep cadence loose (e.g., weekly). Daily freshness/expiry is the cron's job.
