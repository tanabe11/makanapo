# CLAUDE.md — makanapo

This file is read automatically by Claude Code. Keep instructions concise and imperative.
Human-facing rationale lives in `SPEC.md`.

## What this project is
- **App = `makana.fm`** (the umbrella brand; matches `makana.fm LLC`): Hawaii internet radio + local info.
- **`Makanapō`** = the deals **feature/section inside the app**: aggregates **Honolulu** kama'aina discounts
  and happy-hour deals. makana (gift) + pō (night) = "evening gift".
- Differentiator (the defensible asset): every deal shows a **`last_verified` date**. Freshness + trust
  beat stale lists. Keep this front-and-center; don't let the radio shell bury it.
- **Internal name** (this repo, the Python pipeline, Bundle ID `fm.makana.makanapo`) stays **`makanapo`** —
  the CDN URL `cdn.jsdelivr.net/gh/tanabe11/makanapo@main/...` depends on it; do NOT rename the repo.
- Domain / data host base: `po.makana.fm`. Brand decision recorded in SPEC.md §9.

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
     - **Local-only**: `python3 -m pipeline.geocode_fill` (Tier-1). Results cached in `data/geocode_cache.json`.
     - `build.py` (Tier-2/cron) reads the cache only — never calls Nominatim.
     - Geocoder normalizes ʻokina/macrons, Suite, Floor tokens; falls back from address query to name query.
     - Run `geocode_fill` after discovery adds new venues; commit `geocode_cache.json` alongside `deals.json`.
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

## Naming / branding (revised 2026-06-22)
- **App display name**: `makana.fm` (umbrella brand = company `makana.fm LLC`).
- **Deals feature/section**: `Makanapō` (distinctive sub-brand; carries the `last_verified` differentiator).
- **Repo / pipeline / Bundle ID**: `makanapo` (internal; do NOT rename — CDN path depends on it).
- Do NOT use bare `makana` as a brand: generic Hawaiian word + collides with the slack-key artist "Makana"
  (same music/radio space) → ASO-weak and trademark-risky.
- Pending (SPEC.md §9): USPTO federal search (classes 9/38/41/35, esp. "Makana" in music/broadcast),
  App Store Connect display-name reservation. Hawaii DCCA name + state TM + domain: DONE.

## iOS app — implemented (2026-06-22)
- **SwiftUI / iOS 16+**, XcodeGen (`app/project.yml` → `.xcodeproj` gitignored). Bundle ID `fm.makana.makanapo`.
- Features shipped: radio (AVPlayer over **HLS** `live.m3u8`; background + lock-screen via `AVAudioSession(.playback)` + `UIBackgroundModes:audio` — the key lives in a partial `app/Makanapo/Info.plist` via `INFOPLIST_FILE`, NOT `INFOPLIST_KEY_*` which Xcode silently drops; stop tears down the item and play installs a fresh `AVPlayerItem` for live-edge, via the testable `RadioEngine`; MPNowPlayingInfoCenter/MPRemoteCommandCenter, AzuraCast now-playing poll) · collapsing hero (`onScrollGeometryChange`, iOS18+ only) · deals list/detail (CDN JSON, offline cache) · **shows verified (`status==active`) deals only** (`DealsStore.visible`; unverified/expired stay in the feed but are hidden) · segmented filter (All/Happy Hour/Kama'aina) · EN/JA toggle (device-language default) · **map view** (`DealMapView`, iOS17+ MapKit, list↔map toggle, pins for geocoded deals, tap→detail).
- App icon: `img/makana_fm.jpg` → PNG → `app/Makanapo/Assets.xcassets/AppIcon.appiconset/`.
- Build: `brew install xcodegen && cd app && xcodegen generate` → Xcode, pick iOS Simulator, ⌘R.
- Data: CDN `https://cdn.jsdelivr.net/gh/tanabe11/makanapo@main/data/deals.json`. No bundled data.

## Repo layout (actual)
```
po/
  SPEC.md                       # human spec (Obsidian)
  CLAUDE.md                     # this file
  STATUS.md                     # living handoff doc (update each session)
  schema/deal.schema.json       # canonical data contract
  pipeline/
    core/                       # fetch / extract / jsonld / venue / classify / normalize / geocode / build
    sources/                    # one module per source (oahu_official / ala_moana / waikiki_beach_walk / honolulu_magazine)
    geocode_fill.py             # Tier-1 local Nominatim fill → data/geocode_cache.json
    discover_add.py             # Tier-1 CLI helper (verify + append to sources.json)
    preview.py                  # local HTML viewer (gitignored output)
    tests/                      # stdlib unittest (HH window extraction, venue wiring)
  data/
    sources.json                # crawl targets (Tier-1 writes, Tier-2 reads)
    deals.json                  # published artifact (CI commits)
    geocode_cache.json          # Nominatim cache (local writes, CI reads)
    seed/*.json                 # hand-curated records
    leads.json / leads/         # aggregator leads (gitignored)
    preview.html                # local viewer (gitignored)
  img/makana_fm.jpg             # app icon source
  app/                          # SwiftUI iOS app
    project.yml                 # XcodeGen spec
    Makanapo/                   # app source + Assets.xcassets
    MakanapoTests/              # XCTest unit tests
  .claude/skills/makanapo-discover/  # Tier-1 discovery skill
  .github/workflows/build.yml   # Tier-2 daily cron
```

## Current status / next actions
- **data**: 49 deals (active 27 / unverified 21 / expired 1). Goal: active 50 → Go/No-Go. App shows active only (27 visible).
- **coords**: 41/49 geocoded. Missing (need address / cleaner extraction): My Hawaii Spa, Royal Kaila Spa, Maui Brewing Waikiki, Restaurant Suntory, Arancino on Beachwalk, Plumeria Beach House, Wicked Maine Lobster, 206 BCE.
- **happy-hour windows**: `hours` now carries the extracted HH time window (deterministic, recall 10/21). Misses are JS-rendered pages (window not in static text) → needs Playwright, NOT an LLM. HH deals never show general opening hours.
- **app**: MVP shipped (radio HLS + lock-screen audio verified on device; verified-only list). Pending: user-location/nearby, report-expired button, App Store.
- **priority**: `git push` this session's commits (not yet pushed); then run `makanapo-discover` to push active 27 → 50.
