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
   - `data/discovery_rejected.json` → known dead-ends (closed / 403 / SSL / DNS /
     off-scope / JS-only-no-deal / non-consumer-deal). **Skip any candidate whose
     name or url is listed here**, and **append new dead-ends** you hit this run
     (the unattended weekly task and you share this memory to avoid re-treading).
2. **Pick a batch** of candidate venues not already covered. Local + the weekly
   cron converge on the same famous Waikiki HH spots, so **bias toward coverage
   gaps**: run a quick `neighborhood × category/subcategory` tally of `deals.json`
   and target the thin cells — **service** (salon·barber / spa·massage / fitness /
   auto / pet grooming) and **non-Waikiki** (Kaimuki, Chinatown, Kapahulu, Mānoa,
   Kailua, Hawaii Kai, Aiea/Pearl City…) and **non-HH food** (cafe/bakery/poke/
   plate lunch). **But keep a slice (~1/3) for genuinely NEW Waikiki happy-hour
   venues** — it stays a first-class target; the daily Tier-2 cron only refreshes
   EXISTING venues, it doesn't find new ones. Independent / Squarespace sites
   convert best; large WordPress chains often hide deals in PDFs and won't verify.
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
6. **Geocode new venues**, then **rebuild and review**:
   ```
   python3 -m pipeline.core.build      # regenerates data/deals.json (validated)
   python3 -m pipeline.geocode_fill    # LOCAL Nominatim fill for deals missing lat/lng (rate-limited)
   python3 -m pipeline.core.build      # re-run: attaches the new coords from cache
   python3 -m pipeline.stats           # active/unverified/expired counts
   python3 -m pipeline.preview && open data/preview.html
   ```
   Geocoding is deterministic and event-driven — it runs here (after discovery adds
   venues), never in the cron. It writes `data/geocode_cache.json`; unresolved
   venues (no address, name not in OSM) just stay pin-less until an address is found.
7. **Commit & publish.**
   - **Interactive (default):** present the diff of `data/sources.json` (+ active /
     coords change) for the human, then commit `data/sources.json` + `data/deals.json`
     + `data/geocode_cache.json`. Push if the human approves.
   - **Unattended / auto-push (when the user asks, or a scheduled run):** the
     pre-publish guardrails are the safety net, so commit **and push** automatically.
     New sources publish as `unverified` for 7 days (probation), so an auto-push can
     never immediately surface a wrong/closed venue as a confident `active` deal.

### Unattended run (full chain, conflict-safe)
```
python3 -m pipeline.core.build      # GUARDRAILS run here. If it exits non-zero
                                    # (count-delta / invalid), STOP — push nothing.
python3 -m pipeline.geocode_fill
python3 -m pipeline.core.build
git add data/sources.json data/deals.json data/geocode_cache.json
git commit -m "data: discovery batch $(date -u +%F)"
git pull --no-edit                  # absorb the daily cron commit (pull.rebase=false)
# If pull reports a conflict in data/deals.json (generated artifact):
#   python3 -m pipeline.core.build && git add data/deals.json && git commit --no-edit
git push
curl "https://purge.jsdelivr.net/gh/tanabe11/makanapo@main/data/deals.json"
```
Guardrails that make unattended publish safe (all deterministic, in the pipeline):
denylist (`guards.denied_domain`), off-Oahu drop (`guards.out_of_area`), spam drop
(`guards.looks_spammy`), discount cap (`guards.clean_discount`), count-delta guard
(build fails on >40% drop), and 7-day probation (`_added`).

## Notes
- `discover_add` does no LLM work — it just fetches + extracts + writes config.
  The intelligence (which URL, which category) is yours (Claude + WebSearch).
- New aggregator/mall *offers pages* with their own structure need a new thin
  parser module under `pipeline/sources/` (see `ala_moana.py`, `waikiki_beach_walk.py`),
  not a `sources.json` entry.
- Keep cadence loose (e.g., weekly). Daily freshness/expiry is the cron's job.
