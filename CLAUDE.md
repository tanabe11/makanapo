# CLAUDE.md — makanapo

This file is read automatically by Claude Code. Keep instructions concise and imperative.
Human-facing rationale lives in `SPEC.md`.

## What this project is
- **makanapo**: an iOS app that aggregates **Honolulu** kama'aina discounts and happy-hour deals.
- Differentiator: every deal shows a **`last_verified` date**. Freshness + trust beat existing stale lists.
- Brand: house-brand `makana` (makana.fm) + `pō` (night) = "evening gift".
- Domain / data host base: `po.makana.fm`.

## MVP scope (do NOT widen without being asked)
- **Island**: Oahu only (Honolulu first).
- **Categories**: food & service only.
  - food: restaurants → **happy hour** → cafes/bakeries → poke/plate lunch
  - service: salon/barber → spa/massage → fitness/yoga → auto → pet grooming
- **Launch bar**: 50 currently-valid food/service deals with populated fields.
- v1 is **read-only, no login, no accounts**. Do NOT add auth, accounts, push, favorites,
  reminders, merchant self-serve, or monetization unless explicitly requested.
- **Never collect or store state-ID images or other sensitive PII.**

## Architecture (pre-built, effectively serverless)
- Do **NOT** do live or on-device scraping. One central scheduled crawler only.
- Pipeline: collect → extract → normalize → dedupe → expiry-flag → set `last_verified`
  → write `data/deals.json` → commit to GitHub → serve via **jsDelivr CDN**.
- App reads `deals.json` once/day, caches locally, does all search/filter/map **on-device**.
- Scheduler: GitHub Actions cron (Mac cron acceptable for very first MVP). No always-on server.
- Writes (the "still valid? / report expired" button) go through a SEPARATE small endpoint:
  Google Form OR serverless function OR Supabase. Never through the GitHub read path.
- Serve via `cdn.jsdelivr.net/gh/<user>/<repo>@main/data/deals.json` — NOT raw.githubusercontent.com.

## Tech stack
- **iOS app**: Swift + SwiftUI, **MapKit** for maps (no paid map API). Native, solo-maintainable.
- **Pipeline**: Python (matches existing news→summary cron pipeline structure).
- **Data**: static JSON in Git, validated against `schema/deal.schema.json`.
- **Hosting**: GitHub + jsDelivr (or GitHub Pages). No VPS/EC2.
- **Reports endpoint (later)**: start with a form; Supabase/Firebase only if accounts arrive.
- **Browser storage in any web artifact**: NOT supported — use in-memory only.

## Data model — one record in `deals.json`
```json
{
  "id": "string (slug + short hash)",
  "name": "string",
  "category": "food | service",
  "subcategory": "string",
  "discount": "string e.g. '10% off', 'kamaaina price', 'BOGO'",
  "conditions": "string e.g. 'show HI ID, dine-in only, excludes alcohol'",
  "redemption": "show_id | code | online",
  "code": "string | null",
  "address": "string",
  "lat": 0.0,
  "lng": 0.0,
  "neighborhood": "Kaimuki | Kakaako | Ala Moana | Waikiki | ...",
  "hours": "string (happy-hour window if applicable)",
  "source_url": "string (primary source)",
  "last_verified": "YYYY-MM-DD",
  "status": "active | expired | unverified"
}
```
- REQUIRED keys: `id`, `name`, `category`, `source_url`, `last_verified`, `status`. All others optional.
- `last_verified` and `status` must surface in the UI.
- **`discount` is OPTIONAL** (relaxed 2026-06-21). A record may exist with only name + `source_url` + `status`
  when the scraper could not extract the deal details — see the extract-only-facts policy below.

## Data collection rules (legal-safe)
- Prefer **primary sources** (business site / official IG / HVCB / mall pages).
- Use blogs/listicles (Honolulu Magazine, HAWAII Magazine, onolicious, nateeatshawaii,
  hawaiihappyhours) only as **leads** — then verify at the primary source.
- **Do NOT copy** descriptions, photos, logos, or article text. Re-write descriptions in our own words.
- Facts (price/discount/address) are not copyrightable — those are fine.
- Logged-out only; respect robots.txt; rate-limit. No login-walled scraping.
- Federal gov data (NWS etc.) is public domain; state/county (HVCB) — check terms.
- Never trust source expiry blindly: re-flag with `status` + `last_verified`.

## Extraction policy — no LLM, extract-only-facts (decided 2026-06-21)
- **No LLM in the pipeline.** Extraction is deterministic code only (cost/key/maintenance free).
- Extraction stack, in order of leverage:
  1. Hidden JSON endpoints / official APIs (e.g. WordPress REST `/wp-json/`, mall store-list JSON) — most robust.
  2. `JSON-LD` (schema.org `Restaurant`/`LocalBusiness`) — standardized, one shared parser for many sites
     (name / address / geo / openingHours).
  3. Open Graph / meta tags as fallback.
  4. Regex for `discount` / `conditions` / source-stated expiry (e.g. `\d+%\s*off`, `BOGO`, `Hawaii (State )?ID`).
  5. Geocoding for `lat`/`lng` via free OSM Nominatim (rate-limited, cached). No paid/keyed geocoder.
- **Do NOT write descriptions** (so no LLM "rewrite" step is needed) — store facts only; template short labels if needed.
- **Best-effort, never fabricate.** Emit only fields confidently extracted:
  - Extracted `discount` → `status: active`.
  - Place identified but deal details not extractable → `status: unverified`, always keep `source_url`.
    The app shows what we have + a prominent "公式で確認 / verify at source" link so the **user** confirms.
  - Nothing extractable → skip (no record).
- **Go/No-Go counts `active` only.** `unverified` + link records are a supplementary discovery aid, not launch deals.
- JS-heavy sites that need rendering: Playwright in the Action (no always-on server); prefer their JSON API first.

## Discovery & refresh — two-tier (decided 2026-06-21)
Splits the unavoidable LLM/search step (discovery) from the deterministic refresh, by capability + cadence:
- **Tier 1 — discovery (LOCAL, LLM + WebSearch, ~weekly/on-demand):** the `makanapo-discover` skill
  (`.claude/skills/makanapo-discover/`). Finds new Honolulu food/service venues' OWN official pages via
  WebSearch, verifies deterministically (`python3 -m pipeline.discover_add <url> ...` → `core.venue.from_official`),
  and appends usable ones to **`data/sources.json`** (config-as-data). Human reviews the diff. Writes CONFIG only,
  never `deals.json`. Keeps the LLM/API cost OFF the cron and out of CI.
- **Tier 2 — refresh (CLOUD, deterministic, daily):** `.github/workflows/build.yml` runs `pipeline/core/build.py`,
  which reads `data/sources.json` + the per-source parser modules, re-crawls, re-flags expiry/`last_verified`,
  validates, and commits `data/deals.json`. No LLM, no secrets (only `jsonschema`).
- **Config-as-data:** crawl targets live in `data/sources.json` (`official_sites`), NOT in Python. Tier 1 writes it,
  Tier 2 reads it. New aggregator/mall *offers pages* with bespoke HTML still get a thin parser module under
  `pipeline/sources/` (e.g. `ala_moana.py`, `waikiki_beach_walk.py`).
- This preserves "No LLM in the pipeline": the pipeline (cron) stays deterministic; the LLM lives in the separate,
  local, occasional discovery skill.

## Coding conventions
- Keep it solo-maintainable and small. Prefer clarity over cleverness.
- Pipeline output must validate against the JSON schema before commit; fail the Action if invalid.
- Each source gets its own parser module; isolate breakage.
- Log a daily summary (counts added/removed/expired) so count crashes are visible in Git diffs.
- Don't introduce new services/dependencies without a clear need (cost + maintenance burden).

## Naming / branding
- App/display name: `Makanapo` (also "Makana Pō"). Project + repo: `makanapo`.
- Pending (track in SPEC.md): USPTO search (classes 9/42/35), App Store Connect name, @handle.

## Repo layout (target)
```
po/
  SPEC.md                  # human spec (Obsidian)
  CLAUDE.md                # this file
  schema/deal.schema.json  # canonical data contract
  pipeline/                # Python collectors + normalizer
    sources/               # one module per source
    normalize.py
    build.py               # emits data/deals.json
  data/deals.json          # generated artifact (committed)
  .github/workflows/build.yml  # daily cron
  app/                     # SwiftUI iOS app
```

## Immediate next actions
1. Validation sprint: hand-collect 50 valid Honolulu food/service deals → Go/No-Go.
2. Finalize `schema/deal.schema.json`.
3. Stand up GitHub Actions + jsDelivr static delivery (collector stub + workflow).
