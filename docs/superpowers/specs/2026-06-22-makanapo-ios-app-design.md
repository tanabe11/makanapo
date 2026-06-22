# makanapo iOS app (v1 MVP) — design

- Date: 2026-06-22
- Status: approved (brainstorming) → ready for implementation plan
- Context: [SPEC.md](../../../SPEC.md) §6 (app features), [CLAUDE.md](../../../CLAUDE.md) (scope/architecture). Data pipeline is built & live (deals.json on GitHub, served via jsDelivr).

## Goal
A native iPhone app that combines **makana.fm radio** (AzuraCast live stream) with the **makanapo deal directory** (Honolulu kama'aina + happy-hour deals). Radio is the company's main product, so it must be front-and-center; regulars must still get an easy view of the deal list.

## MVP scope
**In:**
- Single main screen: a **collapsing radio hero** (top) + a **deals list** below.
- **Radio**: play/pause, background playback (plays while screen locked), lock-screen / Control Center controls, now-playing metadata (track/show) from AzuraCast.
- **Deals list**: rows showing name, discount, neighborhood, and freshness (`last_verified` ✓ date, or "未確認" for `unverified`). Sort: `active` first, then by neighborhood, then name.
- **Deal detail**: name, discount, conditions, redemption, hours, address, neighborhood, `last_verified` + `status`, **"公式で確認 ↗" link (`source_url`)**, **"Open in Maps"** (Apple Maps via lat/lng or address).
- Data fetched from the **jsDelivr CDN** at launch, cached locally for offline.

**Out (future):** in-app map / "nearby", search, filters (category/neighborhood/"HH now"), the "report expired" write button, accounts/notifications/favorites.

## Key decisions (locked)
| Topic | Decision |
|---|---|
| Layout | **Collapsing hero**: radio is a large hero at scroll-top (radio-forward / option C); collapses to a slim pinned bar as the user scrolls the deals list (list-forward / option A). One screen, auto-switch on scroll, no manual toggle. |
| Radio playback | Background audio + lock-screen/Control Center controls + now-playing (AzuraCast). `UIBackgroundModes: audio`. |
| Data source | **CDN-only** (`https://cdn.jsdelivr.net/gh/tanabe11/makanapo@main/data/deals.json`). Fetch on launch & foreground; cache to disk for offline. **No bundled deals.json** (user does not want stale data shipped). |
| First-launch offline | No cache + no network → friendly empty state with retry. After first successful fetch, cache serves offline. |
| Report button | **Not in MVP.** Detail's "公式で確認 ↗" (`source_url`) is the verification affordance. |
| Project scaffolding | **XcodeGen** (`project.yml` in repo → `.xcodeproj`). Free/MIT. |
| Distribution | Dev: Xcode → Simulator/device. Beta: TestFlight. Public: App Store. Requires Apple Developer Program ($99/yr). Bundle id `fm.makana.makanapo`. |
| Min iOS | iOS 16.0+ (broad reach; no in-app map in MVP so no need for iOS 17 Map APIs). |

## Screens
1. **Main** (`ContentView`): vertical `ScrollView`.
   - **RadioHeader**: at scroll offset 0 it renders the hero (station label, large play/pause disc, now-playing line). As the scroll offset increases it interpolates/collapses into a slim sticky bar (play + one-line now-playing) pinned at top. Implementation: track scroll offset via `GeometryReader` + a `PreferenceKey` (iOS 16-safe; avoid iOS 17-only scroll APIs) and drive hero height/opacity; slim bar stays visible.
   - **DealsList**: `LazyVStack` of `DealRow`. Section/sort: active first.
2. **Deal detail** (`DealDetailView`): pushed via `NavigationStack`. Fields + `source_url` link (opens in Safari/`SFSafariViewController` or `openURL`) + "Open in Maps" (`http://maps.apple.com/?q=` or `?ll=`).

## Architecture (SwiftUI, MVVM-lite)
- **`Deal`** (struct, `Codable`): mirrors `schema/deal.schema.json`. Required: `id, name, category, source_url, last_verified, status`. Optional: `subcategory, discount, conditions, redemption, code, address, lat, lng, neighborhood, hours, valid_until`. Unknown keys ignored. `status` decoded into an enum (`active|expired|unverified`).
- **`DealsStore`** (`@MainActor ObservableObject`): `@Published deals: [Deal]`, `state: idle|loading|loaded|error`. `refresh()` fetches the CDN URL (URLSession), decodes, writes JSON to Caches dir, publishes. On network error: load cache; if no cache: error/empty. Sort helper here.
- **`RadioPlayer`** (`@MainActor ObservableObject`): wraps `AVPlayer(url: streamURL)`. `@Published isPlaying`, `nowPlaying: NowPlaying?`. Configures `AVAudioSession` `.playback` on first play; registers `MPRemoteCommandCenter` (play/pause/toggle) and updates `MPNowPlayingInfoCenter`. `togglePlay()`.
- **`AzuraCastNowPlaying`**: polls `<azuracast-base>/api/nowplaying/<shortcode>` (~every 20–30s while visible/playing), decodes `now_playing.song.{title,artist}` + live flag, publishes to `RadioPlayer`. Pure JSON→model parse is unit-tested.
- **Views**: `MakanapoApp`, `ContentView`, `RadioHeader`, `DealsListView`, `DealRow`, `DealDetailView`.

## Data flow / offline
```
launch / foreground → DealsStore.refresh()
  ├─ success → decode → cache(Caches/deals.json) → publish deals
  └─ failure → load cache → publish (offline) ; no cache → empty+retry
RadioPlayer.togglePlay() → AVPlayer ; AzuraCast poll → nowPlaying → lock screen
```

## Error handling
- Network/decoding failure surfaced as `DealsStore.state = .error(message)` with a retry button; falls back to cache when present.
- Radio stream failure → show inline "再生できません・再試行" on the player; keep app usable.
- AzuraCast now-playing failure → silently keep last known / show station name only (non-fatal).

## Project setup (XcodeGen)
- `app/project.yml` defines target `Makanapo` (iOS app), bundle id `fm.makana.makanapo`, deployment target 16.0, `UIBackgroundModes: [audio]`, `NSLocationWhenInUseUsageDescription` (only if/when location is added — not MVP), app display name `Makanapo`.
- Sources under `app/Makanapo/` (`App/`, `Models/`, `Services/`, `Views/`). Generate with `xcodegen generate` (run in `app/`).
- `.gitignore`: ignore generated `*.xcodeproj`, `DerivedData/` (xcodeproj already ignored partially; add `app/*.xcodeproj`).

## Inputs needed from owner (for implementation)
- **AzuraCast stream URL** for `radio3` (e.g. `https://<host>/listen/<shortcode>/radio.mp3`).
- **AzuraCast now-playing API base + station shortcode** (`https://<host>/api/nowplaying/<shortcode>`).

## Testing
- Unit: `Deal` decoding against the real `data/deals.json` (all current records decode; required fields enforced; optional absent OK). `DealsStore` sort + cache read/write (inject a temp dir). `AzuraCastNowPlaying` JSON parse (sample payload).
- Manual (device/sim): background playback while locked, lock-screen controls, offline cache display, CDN refresh.

## Out of scope / future (tracked, not built now)
- In-app MapKit map + "nearby" (core to makanapo long-term; deferred from MVP).
- Search, filters (category / neighborhood / "happy hour now").
- "Still valid? / report expired" write path (Google Form or serverless), per CLAUDE.md "later".
