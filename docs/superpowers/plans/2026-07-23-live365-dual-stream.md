# Live365 Dual-Stream (Regional Editions) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve makana.fm as a single radio player that auto-selects a Live365 "Hawaiʻi" edition in North America and the existing AzuraCast "Talk" edition everywhere else, driven by a CDN config file with a launch switch, across the WordPress site and the makanapo iOS app.

**Architecture:** A new `data/radio.json` (served via jsDelivr like `deals.json`) defines both channels, the North-America country list, a `hawaii.enabled` launch switch, and an optional Hawaiʻi program schedule. Both platforms run the same three-step logic — resolve region by IP (`speed.cloudflare.com/meta`, fail-open to INTL), read `radio.json`, then `pick(region, config)` to choose the channel. Until `hawaii.enabled` flips to `true`, every viewer sees today's exact behavior (Talk only).

**Tech Stack:** Python 3.11 + `jsonschema` (pipeline/CI), Swift + SwiftUI + AVFoundation (iOS, iOS 16+), vanilla HTML/CSS/JS (WordPress paste-in block, no plugins/deps), GitHub Actions + jsDelivr CDN.

## Global Constraints

- **Repo / pipeline / Bundle ID name stays `makanapo`** — do NOT rename the repo (CDN path `cdn.jsdelivr.net/gh/tanabe11/makanapo@main/...` depends on it).
- **No new services or runtime dependencies** without clear need — pipeline's only dependency is `jsonschema`; the web block adds no plugins; iOS adds no packages.
- **No LLM anywhere in the pipeline** — `radio.json` is hand-maintained config plus deterministic validation.
- **Fail-open geo (UX goal, not license enforcement)** — any geo failure, timeout, or offline state resolves to `INTL` → Talk (legal worldwide). License enforcement is Live365's own geo-block.
- **Never switch audio mid-playback** — a changed region/config applies only on the next `play`. The only in-playback change allowed is the Hawaiʻi→Talk failover.
- **Approved UI copy (verbatim):**
  - Hawaiʻi (North America): `🌺 HAWAIʻI` label; note "You're hearing our full Hawaiʻi program — music, talk & live shows."
  - Talk (elsewhere): `🎙 TALK` label; note (JA) 「こちらの地域ではトーク編成をお届けしています。音楽・生放送を含む全編成はハワイを含む北米エリア限定です。」
- **North America = `["US", "CA", "MX"]`** (Live365 default license region). UK is a future 1-line add (`"GB"`).
- **iOS ships before Web** (App Store review lead time). With `hawaii.enabled: false`, the shipped app is behavior-identical to today.
- **iOS 16+ minimum**; MapKit list/map is iOS 17+, scroll-collapse is iOS 18+ (existing graceful fallbacks — do not regress).
- **The pipeline must never crash the shipped experience:** a missing/broken `radio.json` falls back to today's hardcoded AzuraCast Talk settings on both platforms.
- **Simulator name:** test commands use `iPhone 17`. If that device is absent, pick any available one from `xcrun simctl list devices available` and substitute the `name=` value.

---

## File Structure

**Phase 1 — data + CI (this repo):**
- Create `schema/radio.schema.json` — JSON Schema (draft-07) for `radio.json`.
- Create `data/radio.json` — the published config, `hawaii.enabled: false` at launch.
- Create `pipeline/validate_radio.py` — standalone validator (schema + cross-field rules), CLI entry.
- Create `pipeline/tests/test_validate_radio.py` — stdlib `unittest` for the validator.
- Create `.github/workflows/validate-radio.yml` — CI gate on push/PR touching radio files.

**Phase 2 — iOS app (`app/Makanapo/`):**
- Create `Models/RadioConfig.swift` — `RadioConfig`, `Channel`, `ScheduleEntry` models + `RadioConfigParser`.
- Create `Services/RadioConfigStore.swift` — loads/caches `radio.json` (mirrors `DealsStore`).
- Create `Services/RegionResolver.swift` — IP geo lookup + region persistence + offline TZ fallback.
- Create `Services/ChannelDirector.swift` — pure `pick(region:config:)`.
- Create `Services/ScheduleNowPlaying.swift` — `NowPlayingProviding` backed by the Hawaiʻi schedule.
- Modify `Services/RadioPlayer.swift` — channel-driven URL + metadata source + Hawaiʻi→Talk failover.
- Modify `Views/RadioHeader.swift` — channel label chip + region note + Hawaiʻi sunset theme.
- Modify `App/Localization.swift` — add radio note / label / link strings.
- Modify `App/MakanapoApp.swift` — construct the new stores, wire launch-time channel selection.
- Create `MakanapoTests/RadioConfigDecodingTests.swift`, `ChannelDirectorTests.swift`, `ScheduleNowPlayingTests.swift`, `RegionResolverTests.swift`; extend `RadioPlayerTests.swift`, `LocalizationTests.swift`.

**Phase 3–5 — Web + cutover (this repo, paste-in artifacts):**
- Create `web/radio-player-block.html` — self-contained WordPress paste-in player.
- Create `web/radio-player.test.html` — in-browser assertion harness for the pure JS logic.
- Create `web/channel-about.html` — bilingual "About our stations" page content.
- Create `web/README.md` — where each artifact goes in WP admin, and the cutover checklist.

---

## Task 1: `radio.json` config, schema, validator, and CI gate

**Files:**
- Create: `schema/radio.schema.json`
- Create: `data/radio.json`
- Create: `pipeline/validate_radio.py`
- Test: `pipeline/tests/test_validate_radio.py`
- Create: `.github/workflows/validate-radio.yml`

**Interfaces:**
- Produces: `validate_radio.validate(config: dict) -> list[str]` (returns human-readable error strings; empty list = valid). `validate_radio.main()` reads `data/radio.json`, prints errors, exits 1 if any.
- Produces: the canonical `data/radio.json` shape consumed verbatim by Tasks 2 (iOS) and 8 (web).

- [ ] **Step 1: Write the failing validator test**

Create `pipeline/tests/test_validate_radio.py`:

```python
import json
import unittest
from pathlib import Path

from pipeline import validate_radio

ROOT = Path(__file__).resolve().parent.parent.parent


def _base() -> dict:
    return {
        "version": 1,
        "na_countries": ["US", "CA", "MX"],
        "channels": {
            "hawaii": {
                "enabled": False,
                "label": "HAWAIʻI",
                "name": "makana.fm Hawaiʻi",
                "stream_url": None,
                "regions": ["NA"],
                "theme": "sunset",
            },
            "talk": {
                "enabled": True,
                "label": "TALK",
                "name": "makana.fm Talk",
                "stream_url": "https://radio.makana.fm/hls/makana.fm/live.m3u8",
                "nowplaying_url": "https://radio.makana.fm/api/nowplaying/makana.fm",
                "regions": ["*"],
                "theme": "gold-teal",
            },
        },
        "schedule": {"hawaii": []},
    }


class ValidateRadioTests(unittest.TestCase):
    def test_valid_config_has_no_errors(self):
        self.assertEqual(validate_radio.validate(_base()), [])

    def test_shipped_data_file_is_valid(self):
        cfg = json.loads((ROOT / "data" / "radio.json").read_text())
        self.assertEqual(validate_radio.validate(cfg), [])

    def test_enabled_hawaii_without_stream_url_is_error(self):
        cfg = _base()
        cfg["channels"]["hawaii"]["enabled"] = True
        cfg["channels"]["hawaii"]["stream_url"] = None
        errs = validate_radio.validate(cfg)
        self.assertTrue(any("stream_url" in e for e in errs), errs)

    def test_talk_must_always_be_enabled(self):
        cfg = _base()
        cfg["channels"]["talk"]["enabled"] = False
        errs = validate_radio.validate(cfg)
        self.assertTrue(any("talk" in e for e in errs), errs)

    def test_na_countries_must_be_two_letter_uppercase(self):
        cfg = _base()
        cfg["na_countries"] = ["USA"]
        errs = validate_radio.validate(cfg)
        self.assertTrue(any("na_countries" in e for e in errs), errs)

    def test_schema_rejects_unknown_top_level_key(self):
        cfg = _base()
        cfg["surprise"] = 1
        errs = validate_radio.validate(cfg)
        self.assertTrue(errs)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/junichi/jt/projects/po && python3 -m pytest pipeline/tests/test_validate_radio.py -q` (or `python3 -m unittest pipeline.tests.test_validate_radio`)
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.validate_radio'` (and no `data/radio.json`).

- [ ] **Step 3: Create the JSON Schema**

Create `schema/radio.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "makana.fm radio config",
  "type": "object",
  "required": ["version", "na_countries", "channels"],
  "additionalProperties": false,
  "properties": {
    "version": { "type": "integer", "minimum": 1 },
    "na_countries": {
      "type": "array",
      "minItems": 1,
      "items": { "type": "string", "pattern": "^[A-Z]{2}$" }
    },
    "channels": {
      "type": "object",
      "required": ["hawaii", "talk"],
      "additionalProperties": false,
      "properties": {
        "hawaii": { "$ref": "#/definitions/channel" },
        "talk": { "$ref": "#/definitions/channel" }
      }
    },
    "schedule": {
      "type": "object",
      "additionalProperties": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["days", "start", "end", "tz", "title"],
          "additionalProperties": false,
          "properties": {
            "days": {
              "type": "array",
              "items": { "enum": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] }
            },
            "start": { "type": "string", "pattern": "^[0-2][0-9]:[0-5][0-9]$" },
            "end": { "type": "string", "pattern": "^[0-2][0-9]:[0-5][0-9]$" },
            "tz": { "type": "string" },
            "title": { "type": "string" },
            "live": { "type": "boolean" }
          }
        }
      }
    }
  },
  "definitions": {
    "channel": {
      "type": "object",
      "required": ["enabled", "label", "name", "regions", "theme"],
      "additionalProperties": false,
      "properties": {
        "enabled": { "type": "boolean" },
        "label": { "type": "string" },
        "name": { "type": "string" },
        "stream_url": { "type": ["string", "null"], "format": "uri" },
        "nowplaying_url": { "type": "string", "format": "uri" },
        "regions": { "type": "array", "items": { "type": "string" } },
        "theme": { "type": "string" }
      }
    }
  }
}
```

- [ ] **Step 4: Create the published config file**

Create `data/radio.json`:

```json
{
  "version": 1,
  "na_countries": ["US", "CA", "MX"],
  "channels": {
    "hawaii": {
      "enabled": false,
      "label": "HAWAIʻI",
      "name": "makana.fm Hawaiʻi",
      "stream_url": null,
      "regions": ["NA"],
      "theme": "sunset"
    },
    "talk": {
      "enabled": true,
      "label": "TALK",
      "name": "makana.fm Talk",
      "stream_url": "https://radio.makana.fm/hls/makana.fm/live.m3u8",
      "nowplaying_url": "https://radio.makana.fm/api/nowplaying/makana.fm",
      "regions": ["*"],
      "theme": "gold-teal"
    }
  },
  "schedule": {
    "hawaii": []
  }
}
```

- [ ] **Step 5: Implement the validator**

Create `pipeline/validate_radio.py`:

```python
"""Validate data/radio.json against schema + cross-field launch-safety rules.

Standalone (not part of the deals build). CI runs this on any change to
data/radio.json or schema/radio.schema.json. Deterministic, no LLM.
"""
import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "radio.schema.json").read_text())
CONFIG = ROOT / "data" / "radio.json"


def validate(config: dict) -> list[str]:
    """Return a list of error strings; empty means valid."""
    errors: list[str] = []
    try:
        jsonschema.validate(instance=config, schema=SCHEMA)
    except jsonschema.ValidationError as e:
        return [f"schema: {e.message} (at {'/'.join(str(p) for p in e.path)})"]

    channels = config.get("channels", {})
    talk = channels.get("talk", {})
    hawaii = channels.get("hawaii", {})

    if not talk.get("enabled", False):
        errors.append("talk channel must always be enabled (worldwide fallback)")
    if not talk.get("stream_url"):
        errors.append("talk channel requires a stream_url")
    if hawaii.get("enabled") and not hawaii.get("stream_url"):
        errors.append("hawaii channel is enabled but has no stream_url (cannot go live)")
    return errors


def main() -> int:
    config = json.loads(CONFIG.read_text())
    errors = validate(config)
    if errors:
        for e in errors:
            print(f"  INVALID radio.json: {e}", file=sys.stderr)
        return 1
    print("radio.json OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd /Users/junichi/jt/projects/po && python3 -m unittest pipeline.tests.test_validate_radio -v`
Expected: PASS (6 tests). Also run `python3 -m pipeline.validate_radio` → prints `radio.json OK`, exit 0.

- [ ] **Step 7: Create the CI workflow**

Create `.github/workflows/validate-radio.yml`:

```yaml
name: validate-radio

# Gate: radio.json must stay schema-valid and launch-safe. Runs on any change
# to the config or its schema/validator. No secrets, only jsonschema.
on:
  push:
    paths:
      - "data/radio.json"
      - "schema/radio.schema.json"
      - "pipeline/validate_radio.py"
      - "pipeline/tests/test_validate_radio.py"
  pull_request:
    paths:
      - "data/radio.json"
      - "schema/radio.schema.json"
      - "pipeline/validate_radio.py"
  workflow_dispatch: {}

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install jsonschema
      - name: Unit tests
        run: python3 -m unittest pipeline.tests.test_validate_radio -v
      - name: Validate data/radio.json
        run: python3 -m pipeline.validate_radio
```

- [ ] **Step 8: Commit**

```bash
git add schema/radio.schema.json data/radio.json pipeline/validate_radio.py pipeline/tests/test_validate_radio.py .github/workflows/validate-radio.yml
git commit -m "feat(radio): radio.json config + schema + validator + CI gate"
```

---

## Task 2: iOS `RadioConfig` models + parser

**Files:**
- Create: `app/Makanapo/Models/RadioConfig.swift`
- Test: `app/MakanapoTests/RadioConfigDecodingTests.swift`

**Interfaces:**
- Produces: `struct RadioConfig: Decodable, Equatable { let version: Int; let naCountries: [String]; let channels: Channels; let schedule: [String: [ScheduleEntry]] }`
- Produces: `struct Channels: Decodable, Equatable { let hawaii: Channel; let talk: Channel }`
- Produces: `struct Channel: Decodable, Equatable { let enabled: Bool; let label: String; let name: String; let streamURL: URL?; let nowPlayingURL: URL?; let regions: [String]; let theme: String }`
- Produces: `struct ScheduleEntry: Decodable, Equatable { let days: [String]; let start: String; let end: String; let tz: String; let title: String; let live: Bool? }`
- Produces: `enum RadioConfigParser { static func parse(_ data: Data) throws -> RadioConfig }`

- [ ] **Step 1: Write the failing decoding test**

Create `app/MakanapoTests/RadioConfigDecodingTests.swift`:

```swift
import XCTest
@testable import Makanapo

final class RadioConfigDecodingTests: XCTestCase {
    private let json = """
    {
      "version": 1,
      "na_countries": ["US", "CA", "MX"],
      "channels": {
        "hawaii": { "enabled": false, "label": "HAWAIʻI", "name": "makana.fm Hawaiʻi",
                    "stream_url": null, "regions": ["NA"], "theme": "sunset" },
        "talk": { "enabled": true, "label": "TALK", "name": "makana.fm Talk",
                  "stream_url": "https://radio.makana.fm/hls/makana.fm/live.m3u8",
                  "nowplaying_url": "https://radio.makana.fm/api/nowplaying/makana.fm",
                  "regions": ["*"], "theme": "gold-teal" }
      },
      "schedule": {
        "hawaii": [
          { "days": ["fri"], "start": "17:00", "end": "19:00",
            "tz": "Pacific/Honolulu", "title": "Sunset Mele Hour", "live": true }
        ]
      }
    }
    """.data(using: .utf8)!

    func test_parse_decodesChannelsAndSchedule() throws {
        let cfg = try RadioConfigParser.parse(json)
        XCTAssertEqual(cfg.naCountries, ["US", "CA", "MX"])
        XCTAssertFalse(cfg.channels.hawaii.enabled)
        XCTAssertNil(cfg.channels.hawaii.streamURL)
        XCTAssertEqual(cfg.channels.talk.label, "TALK")
        XCTAssertEqual(cfg.channels.talk.streamURL?.absoluteString,
                       "https://radio.makana.fm/hls/makana.fm/live.m3u8")
        XCTAssertEqual(cfg.schedule["hawaii"]?.first?.title, "Sunset Mele Hour")
    }
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/junichi/jt/projects/po/app && xcodegen generate && xcodebuild test -scheme Makanapo -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:MakanapoTests/RadioConfigDecodingTests`
Expected: FAIL to compile — `RadioConfigParser` undefined.

- [ ] **Step 3: Implement the models + parser**

Create `app/Makanapo/Models/RadioConfig.swift`:

```swift
import Foundation

struct RadioConfig: Decodable, Equatable {
    let version: Int
    let naCountries: [String]
    let channels: Channels
    let schedule: [String: [ScheduleEntry]]

    enum CodingKeys: String, CodingKey {
        case version
        case naCountries = "na_countries"
        case channels
        case schedule
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        version = try c.decode(Int.self, forKey: .version)
        naCountries = try c.decode([String].self, forKey: .naCountries)
        channels = try c.decode(Channels.self, forKey: .channels)
        schedule = try c.decodeIfPresent([String: [ScheduleEntry]].self, forKey: .schedule) ?? [:]
    }
}

struct Channels: Decodable, Equatable {
    let hawaii: Channel
    let talk: Channel
}

struct Channel: Decodable, Equatable {
    let enabled: Bool
    let label: String
    let name: String
    let streamURL: URL?
    let nowPlayingURL: URL?
    let regions: [String]
    let theme: String

    enum CodingKeys: String, CodingKey {
        case enabled, label, name, regions, theme
        case streamURL = "stream_url"
        case nowPlayingURL = "nowplaying_url"
    }
}

struct ScheduleEntry: Decodable, Equatable {
    let days: [String]
    let start: String
    let end: String
    let tz: String
    let title: String
    let live: Bool?
}

enum RadioConfigParser {
    static func parse(_ data: Data) throws -> RadioConfig {
        try JSONDecoder().decode(RadioConfig.self, from: data)
    }
}
```

- [ ] **Step 4: Add both new files to the Xcode target**

`app/project.yml` uses XcodeGen with directory globbing (`Makanapo/` and `MakanapoTests/`), so no manual edit is needed — the files are picked up on `xcodegen generate`. (If `project.yml` lists sources explicitly, add the two paths there.)

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd /Users/junichi/jt/projects/po/app && xcodegen generate && xcodebuild test -scheme Makanapo -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:MakanapoTests/RadioConfigDecodingTests`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/Makanapo/Models/RadioConfig.swift app/MakanapoTests/RadioConfigDecodingTests.swift
git commit -m "feat(ios): RadioConfig models + parser"
```

---

## Task 3: iOS `ChannelDirector` (pure selection)

**Files:**
- Create: `app/Makanapo/Services/ChannelDirector.swift`
- Test: `app/MakanapoTests/ChannelDirectorTests.swift`

**Interfaces:**
- Consumes: `RadioConfig`, `Channel` (Task 2).
- Produces: `enum Region { case na, intl }`
- Produces: `enum ChannelDirector { static func pick(region: Region, config: RadioConfig) -> Channel }`
- Rule: `region == .na && config.channels.hawaii.enabled` → hawaii; otherwise talk.

- [ ] **Step 1: Write the failing test**

Create `app/MakanapoTests/ChannelDirectorTests.swift`:

```swift
import XCTest
@testable import Makanapo

final class ChannelDirectorTests: XCTestCase {
    private func config(hawaiiEnabled: Bool) -> RadioConfig {
        let json = """
        {
          "version": 1, "na_countries": ["US","CA","MX"],
          "channels": {
            "hawaii": { "enabled": \(hawaiiEnabled), "label": "HAWAIʻI", "name": "H",
                        "stream_url": "https://example.com/hi.aac", "regions": ["NA"], "theme": "sunset" },
            "talk": { "enabled": true, "label": "TALK", "name": "T",
                      "stream_url": "https://example.com/talk.m3u8", "regions": ["*"], "theme": "gold-teal" }
          }
        }
        """.data(using: .utf8)!
        return try! RadioConfigParser.parse(json)
    }

    func test_na_withHawaiiEnabled_picksHawaii() {
        let ch = ChannelDirector.pick(region: .na, config: config(hawaiiEnabled: true))
        XCTAssertEqual(ch.label, "HAWAIʻI")
    }

    func test_na_withHawaiiDisabled_picksTalk() {
        let ch = ChannelDirector.pick(region: .na, config: config(hawaiiEnabled: false))
        XCTAssertEqual(ch.label, "TALK")
    }

    func test_intl_alwaysPicksTalk() {
        XCTAssertEqual(ChannelDirector.pick(region: .intl, config: config(hawaiiEnabled: true)).label, "TALK")
        XCTAssertEqual(ChannelDirector.pick(region: .intl, config: config(hawaiiEnabled: false)).label, "TALK")
    }
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/junichi/jt/projects/po/app && xcodebuild test -scheme Makanapo -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:MakanapoTests/ChannelDirectorTests`
Expected: FAIL to compile — `ChannelDirector`/`Region` undefined.

- [ ] **Step 3: Implement**

Create `app/Makanapo/Services/ChannelDirector.swift`:

```swift
import Foundation

enum Region { case na, intl }

enum ChannelDirector {
    static func pick(region: Region, config: RadioConfig) -> Channel {
        if region == .na, config.channels.hawaii.enabled {
            return config.channels.hawaii
        }
        return config.channels.talk
    }
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /Users/junichi/jt/projects/po/app && xcodegen generate && xcodebuild test -scheme Makanapo -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:MakanapoTests/ChannelDirectorTests`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add app/Makanapo/Services/ChannelDirector.swift app/MakanapoTests/ChannelDirectorTests.swift
git commit -m "feat(ios): ChannelDirector pure channel selection"
```

---

## Task 4: iOS `RegionResolver` (IP geo + offline fallback)

**Files:**
- Create: `app/Makanapo/Services/RegionResolver.swift`
- Test: `app/MakanapoTests/RegionResolverTests.swift`

**Interfaces:**
- Consumes: `Region` (Task 3).
- Produces: `protocol CountryLookup { func country() async throws -> String }` (seam for tests).
- Produces: `struct CloudflareCountryLookup: CountryLookup` (GET `https://speed.cloudflare.com/meta`, 1.5s timeout, reads `country`).
- Produces: `@MainActor final class RegionResolver` with `func resolve(naCountries: [String]) async -> Region` — persists last known region to `UserDefaults` (key `radio_last_region`); on lookup failure returns the persisted region if present, else `offlineFallback(naCountries:)` (NA only if `TimeZone.current.identifier` maps to a US/CA/MX zone, else `.intl`).
- Produces: `static func region(forCountry country: String, naCountries: [String]) -> Region` (pure; used by both live path and tests).

- [ ] **Step 1: Write the failing test**

Create `app/MakanapoTests/RegionResolverTests.swift`:

```swift
import XCTest
@testable import Makanapo

private struct StubLookup: CountryLookup {
    let result: Result<String, Error>
    func country() async throws -> String { try result.get() }
}

private struct AnyError: Error {}

@MainActor
final class RegionResolverTests: XCTestCase {
    private let na = ["US", "CA", "MX"]
    private let defaultsKey = "radio_last_region"

    override func setUp() { UserDefaults.standard.removeObject(forKey: defaultsKey) }

    func test_pureRegion_naCountryIsNA() {
        XCTAssertEqual(RegionResolver.region(forCountry: "US", naCountries: na), .na)
        XCTAssertEqual(RegionResolver.region(forCountry: "MX", naCountries: na), .na)
    }

    func test_pureRegion_otherCountryIsINTL() {
        XCTAssertEqual(RegionResolver.region(forCountry: "JP", naCountries: na), .intl)
    }

    func test_resolve_usesLookupCountry() async {
        let r = RegionResolver(lookup: StubLookup(result: .success("CA")))
        let region = await r.resolve(naCountries: na)
        XCTAssertEqual(region, .na)
    }

    func test_resolve_failure_fallsBackToPersistedRegion() async {
        UserDefaults.standard.set("na", forKey: defaultsKey)
        let r = RegionResolver(lookup: StubLookup(result: .failure(AnyError())))
        let region = await r.resolve(naCountries: na)
        XCTAssertEqual(region, .na)  // persisted, not recomputed
    }

    func test_resolve_persistsResult() async {
        let r = RegionResolver(lookup: StubLookup(result: .success("JP")))
        _ = await r.resolve(naCountries: na)
        XCTAssertEqual(UserDefaults.standard.string(forKey: defaultsKey), "intl")
    }
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/junichi/jt/projects/po/app && xcodebuild test -scheme Makanapo -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:MakanapoTests/RegionResolverTests`
Expected: FAIL to compile — `RegionResolver`/`CountryLookup` undefined.

- [ ] **Step 3: Implement**

Create `app/Makanapo/Services/RegionResolver.swift`:

```swift
import Foundation

protocol CountryLookup {
    /// ISO 3166-1 alpha-2 country of the caller's IP.
    func country() async throws -> String
}

struct CloudflareCountryLookup: CountryLookup {
    var session: URLSession = .shared
    let url = URL(string: "https://speed.cloudflare.com/meta")!

    private struct Meta: Decodable { let country: String }

    func country() async throws -> String {
        var req = URLRequest(url: url, timeoutInterval: 1.5)
        req.cachePolicy = .reloadIgnoringLocalCacheData
        let (data, _) = try await session.data(for: req)
        return try JSONDecoder().decode(Meta.self, from: data).country
    }
}

@MainActor
final class RegionResolver {
    private let lookup: CountryLookup
    private let defaults: UserDefaults
    private let key = "radio_last_region"

    init(lookup: CountryLookup = CloudflareCountryLookup(),
         defaults: UserDefaults = .standard) {
        self.lookup = lookup
        self.defaults = defaults
    }

    static func region(forCountry country: String, naCountries: [String]) -> Region {
        naCountries.contains(country.uppercased()) ? .na : .intl
    }

    func resolve(naCountries: [String]) async -> Region {
        do {
            let country = try await lookup.country()
            let region = Self.region(forCountry: country, naCountries: naCountries)
            defaults.set(region == .na ? "na" : "intl", forKey: key)
            return region
        } catch {
            if let saved = defaults.string(forKey: key) {
                return saved == "na" ? .na : .intl
            }
            return Self.offlineFallback()
        }
    }

    /// First-ever launch while offline: guess from the device time zone.
    /// Only continental US/CA/MX zones count as NA; anything else is INTL.
    private static func offlineFallback() -> Region {
        let id = TimeZone.current.identifier
        let naPrefixes = ["America/", "Pacific/Honolulu", "Pacific/Anchorage"]
        let nonNAAmerica = ["America/Sao_Paulo", "America/Argentina", "America/Bogota",
                            "America/Lima", "America/Santiago", "America/Caracas"]
        guard naPrefixes.contains(where: { id.hasPrefix($0) }) else { return .intl }
        return nonNAAmerica.contains(where: { id.hasPrefix($0) }) ? .intl : .na
    }
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /Users/junichi/jt/projects/po/app && xcodegen generate && xcodebuild test -scheme Makanapo -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:MakanapoTests/RegionResolverTests`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add app/Makanapo/Services/RegionResolver.swift app/MakanapoTests/RegionResolverTests.swift
git commit -m "feat(ios): RegionResolver (IP geo + offline TZ fallback)"
```

---

## Task 5: iOS `RadioConfigStore` (load + cache radio.json)

**Files:**
- Create: `app/Makanapo/Services/RadioConfigStore.swift`
- Modify: `app/Makanapo/App/Config.swift` (add `radioConfigURL`)
- Test: (covered by decoding in Task 2; store wiring is smoke-tested in Task 9)

**Interfaces:**
- Consumes: `RadioConfig`, `RadioConfigParser` (Task 2); `DealsLoading`/`URLSessionDealsLoader` (existing, reused as the generic loader).
- Produces: `@MainActor final class RadioConfigStore: ObservableObject { @Published private(set) var config: RadioConfig?; func refresh() async }` — loads from URL, caches to `radio.json` in caches dir, falls back to cache then to `RadioConfigStore.fallback` (hardcoded Talk-only config identical to today).
- Produces: `static var fallback: RadioConfig` — the never-crash default.

- [ ] **Step 1: Add the config URL**

Modify `app/Makanapo/App/Config.swift` — add after `dealsURL`:

```swift
    /// Radio channel config (jsDelivr CDN, same repo as deals). Launch switch lives here.
    static let radioConfigURL = URL(string: "https://cdn.jsdelivr.net/gh/tanabe11/makanapo@main/data/radio.json")!
```

- [ ] **Step 2: Write the failing fallback test**

Add to `app/MakanapoTests/RadioConfigDecodingTests.swift`:

```swift
    @MainActor
    func test_fallback_isTalkOnlyAndValid() {
        let cfg = RadioConfigStore.fallback
        XCTAssertTrue(cfg.channels.talk.enabled)
        XCTAssertFalse(cfg.channels.hawaii.enabled)
        XCTAssertNotNil(cfg.channels.talk.streamURL)
        XCTAssertEqual(ChannelDirector.pick(region: .intl, config: cfg).label,
                       cfg.channels.talk.label)
    }
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd /Users/junichi/jt/projects/po/app && xcodebuild test -scheme Makanapo -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:MakanapoTests/RadioConfigDecodingTests/test_fallback_isTalkOnlyAndValid`
Expected: FAIL to compile — `RadioConfigStore` undefined.

- [ ] **Step 4: Implement the store**

Create `app/Makanapo/Services/RadioConfigStore.swift`:

```swift
import Foundation

@MainActor
final class RadioConfigStore: ObservableObject {
    @Published private(set) var config: RadioConfig?

    private let loader: DealsLoading
    private let cacheURL: URL

    init(loader: DealsLoading = URLSessionDealsLoader(url: Config.radioConfigURL),
         cacheURL: URL = FileManager.default
            .urls(for: .cachesDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("radio.json")) {
        self.loader = loader
        self.cacheURL = cacheURL
    }

    func refresh() async {
        do {
            let data = try await loader.load()
            let decoded = try RadioConfigParser.parse(data)
            try? data.write(to: cacheURL, options: .atomic)
            config = decoded
        } catch {
            if let cached = try? Data(contentsOf: cacheURL),
               let decoded = try? RadioConfigParser.parse(cached) {
                config = decoded
            } else {
                config = Self.fallback
            }
        }
    }

    /// Never-crash default: today's Talk-only behavior, hardcoded so a missing or
    /// broken radio.json can never take radio off the air.
    static let fallback: RadioConfig = {
        let json = """
        {
          "version": 1, "na_countries": ["US","CA","MX"],
          "channels": {
            "hawaii": { "enabled": false, "label": "HAWAIʻI", "name": "makana.fm Hawaiʻi",
                        "stream_url": null, "regions": ["NA"], "theme": "sunset" },
            "talk": { "enabled": true, "label": "TALK", "name": "makana.fm Talk",
                      "stream_url": "https://radio.makana.fm/hls/makana.fm/live.m3u8",
                      "nowplaying_url": "https://radio.makana.fm/api/nowplaying/makana.fm",
                      "regions": ["*"], "theme": "gold-teal" }
          },
          "schedule": { "hawaii": [] }
        }
        """.data(using: .utf8)!
        return try! RadioConfigParser.parse(json)
    }()
}
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd /Users/junichi/jt/projects/po/app && xcodegen generate && xcodebuild test -scheme Makanapo -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:MakanapoTests/RadioConfigDecodingTests`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/Makanapo/App/Config.swift app/Makanapo/Services/RadioConfigStore.swift app/MakanapoTests/RadioConfigDecodingTests.swift
git commit -m "feat(ios): RadioConfigStore with never-crash Talk fallback"
```

---

## Task 6: iOS `ScheduleNowPlaying` (Hawaiʻi program name)

**Files:**
- Create: `app/Makanapo/Services/ScheduleNowPlaying.swift`
- Test: `app/MakanapoTests/ScheduleNowPlayingTests.swift`

**Interfaces:**
- Consumes: `ScheduleEntry` (Task 2), `NowPlaying`/`NowPlayingProviding` (existing).
- Produces: `enum ScheduleResolver { static func current(_ entries: [ScheduleEntry], now: Date, stationName: String) -> NowPlaying }` — returns the matching entry's title (as a live `NowPlaying` when `live == true`), else a default `NowPlaying(stationName:...)` with title `nil` (UI shows station name / "Live from Honolulu").
- Produces: `struct ScheduleNowPlaying: NowPlayingProviding { let entries: [ScheduleEntry]; let stationName: String; func fetch() async throws -> NowPlaying }` (wraps the resolver with `Date()`).

- [ ] **Step 1: Write the failing test**

Create `app/MakanapoTests/ScheduleNowPlayingTests.swift`:

```swift
import XCTest
@testable import Makanapo

final class ScheduleNowPlayingTests: XCTestCase {
    private func entry() -> ScheduleEntry {
        ScheduleEntry(days: ["fri"], start: "17:00", end: "19:00",
                      tz: "Pacific/Honolulu", title: "Sunset Mele Hour", live: true)
    }

    /// A Friday 18:00 in Honolulu.
    private func honoluluFriday1800() -> Date {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "Pacific/Honolulu")!
        // 2026-07-24 is a Friday.
        return cal.date(from: DateComponents(year: 2026, month: 7, day: 24, hour: 18, minute: 0))!
    }

    private func honoluluFriday1200() -> Date {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "Pacific/Honolulu")!
        return cal.date(from: DateComponents(year: 2026, month: 7, day: 24, hour: 12, minute: 0))!
    }

    func test_insideWindow_returnsProgramTitle() {
        let np = ScheduleResolver.current([entry()], now: honoluluFriday1800(), stationName: "makana.fm Hawaiʻi")
        XCTAssertEqual(np.title, "Sunset Mele Hour")
        XCTAssertTrue(np.isLive)
    }

    func test_outsideWindow_returnsStationOnly() {
        let np = ScheduleResolver.current([entry()], now: honoluluFriday1200(), stationName: "makana.fm Hawaiʻi")
        XCTAssertNil(np.title)
        XCTAssertEqual(np.stationName, "makana.fm Hawaiʻi")
    }

    func test_emptySchedule_returnsStationOnly() {
        let np = ScheduleResolver.current([], now: honoluluFriday1800(), stationName: "makana.fm Hawaiʻi")
        XCTAssertNil(np.title)
    }
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/junichi/jt/projects/po/app && xcodebuild test -scheme Makanapo -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:MakanapoTests/ScheduleNowPlayingTests`
Expected: FAIL to compile — `ScheduleResolver` undefined.

- [ ] **Step 3: Implement**

Create `app/Makanapo/Services/ScheduleNowPlaying.swift`:

```swift
import Foundation

enum ScheduleResolver {
    private static let dayCode: [Int: String] =
        [1: "sun", 2: "mon", 3: "tue", 4: "wed", 5: "thu", 6: "fri", 7: "sat"]

    static func current(_ entries: [ScheduleEntry], now: Date, stationName: String) -> NowPlaying {
        for e in entries {
            guard let tz = TimeZone(identifier: e.tz) else { continue }
            var cal = Calendar(identifier: .gregorian)
            cal.timeZone = tz
            let comps = cal.dateComponents([.weekday, .hour, .minute], from: now)
            guard let wd = comps.weekday, let code = dayCode[wd], e.days.contains(code) else { continue }
            let mins = (comps.hour ?? 0) * 60 + (comps.minute ?? 0)
            guard let s = minutes(e.start), let en = minutes(e.end), (s..<en).contains(mins) else { continue }
            return NowPlaying(stationName: stationName, title: e.title, artist: nil,
                              isLive: e.live ?? false, streamerName: (e.live ?? false) ? e.title : nil)
        }
        return NowPlaying(stationName: stationName, title: nil, artist: nil,
                          isLive: false, streamerName: nil)
    }

    private static func minutes(_ hhmm: String) -> Int? {
        let parts = hhmm.split(separator: ":")
        guard parts.count == 2, let h = Int(parts[0]), let m = Int(parts[1]) else { return nil }
        return h * 60 + m
    }
}

struct ScheduleNowPlaying: NowPlayingProviding {
    let entries: [ScheduleEntry]
    let stationName: String

    func fetch() async throws -> NowPlaying {
        ScheduleResolver.current(entries, now: Date(), stationName: stationName)
    }
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /Users/junichi/jt/projects/po/app && xcodegen generate && xcodebuild test -scheme Makanapo -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:MakanapoTests/ScheduleNowPlayingTests`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add app/Makanapo/Services/ScheduleNowPlaying.swift app/MakanapoTests/ScheduleNowPlayingTests.swift
git commit -m "feat(ios): ScheduleNowPlaying for Hawaii program names"
```

---

## Task 7: iOS `RadioPlayer` — channel-driven playback + failover

**Files:**
- Modify: `app/Makanapo/Services/RadioPlayer.swift`
- Test: `app/MakanapoTests/RadioPlayerTests.swift`

**Interfaces:**
- Consumes: `Channel` (Task 2), `ChannelDirector` (Task 3), `ScheduleNowPlaying` (Task 6), `AzuraCastClient` (existing).
- Produces: `RadioEngine` gains `var onFailedToPlay: (() -> Void)? { get set }`.
- Produces: `RadioPlayer` gains `@Published private(set) var channel: Channel`, `func configure(channel: Channel, schedule: [ScheduleEntry])` (sets next-play channel + metadata source; **does not touch live audio**), and internal `handlePlaybackFailure()` (if current channel is Hawaiʻi, switch to the Talk channel and replay + set a `@Published var failedOver` flag for the UI note).
- Produces: `RadioPlayer.init` accepts an optional `talkChannel: Channel` used as the failover target.

- [ ] **Step 1: Extend RadioPlayerTests with channel + failover cases**

Add to `app/MakanapoTests/RadioPlayerTests.swift` (update `FakeEngine` first):

```swift
// Add to FakeEngine:
    var onFailedToPlay: (() -> Void)?
    func triggerFailure() { onFailedToPlay?() }
```

Then add these test methods to `RadioPlayerTests`:

```swift
    private func hawaiiChannel() -> Channel {
        try! RadioConfigParser.parse("""
        { "version":1,"na_countries":["US"],"channels":{
          "hawaii":{"enabled":true,"label":"HAWAIʻI","name":"H","stream_url":"https://example.com/hi.aac","regions":["NA"],"theme":"sunset"},
          "talk":{"enabled":true,"label":"TALK","name":"T","stream_url":"https://example.com/talk.m3u8","regions":["*"],"theme":"gold-teal"}
        }}
        """.data(using: .utf8)!).channels.hawaii
    }
    private func talkChannel() -> Channel {
        try! RadioConfigParser.parse("""
        { "version":1,"na_countries":["US"],"channels":{
          "hawaii":{"enabled":true,"label":"HAWAIʻI","name":"H","stream_url":"https://example.com/hi.aac","regions":["NA"],"theme":"sunset"},
          "talk":{"enabled":true,"label":"TALK","name":"T","stream_url":"https://example.com/talk.m3u8","regions":["*"],"theme":"gold-teal"}
        }}
        """.data(using: .utf8)!).channels.talk
    }

    func test_configure_doesNotChangeLiveAudio() {
        let (player, engine) = makePlayer()
        player.toggle() // playing talk (default url)
        let playedBefore = engine.playedURLs.count
        player.configure(channel: hawaiiChannel(), schedule: [])
        XCTAssertEqual(engine.playedURLs.count, playedBefore) // no new play mid-stream
    }

    func test_playAfterConfigure_usesChannelURL() {
        let (player, engine) = makePlayer()
        player.configure(channel: hawaiiChannel(), schedule: [])
        player.toggle()
        XCTAssertEqual(engine.playedURLs.last?.absoluteString, "https://example.com/hi.aac")
    }

    func test_hawaiiPlaybackFailure_failsOverToTalk() {
        let (player, engine) = makePlayerWithFailover(talk: talkChannel())
        player.configure(channel: hawaiiChannel(), schedule: [])
        player.toggle() // play hawaii
        engine.triggerFailure()
        XCTAssertEqual(engine.playedURLs.last?.absoluteString, "https://example.com/talk.m3u8")
        XCTAssertTrue(player.failedOver)
        XCTAssertTrue(player.isPlaying)
    }
```

Add a `makePlayerWithFailover` helper:

```swift
    private func makePlayerWithFailover(talk: Channel) -> (RadioPlayer, FakeEngine) {
        let engine = FakeEngine()
        let player = RadioPlayer(streamURL: url, engine: engine,
                                 metadata: StubNowPlaying(), talkChannel: talk)
        return (player, engine)
    }
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/junichi/jt/projects/po/app && xcodebuild test -scheme Makanapo -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:MakanapoTests/RadioPlayerTests`
Expected: FAIL to compile — `onFailedToPlay`, `configure`, `failedOver`, `talkChannel:` undefined.

- [ ] **Step 3: Update the RadioEngine protocol + AVRadioEngine**

In `app/Makanapo/Services/RadioPlayer.swift`, change the protocol and engine:

```swift
protocol RadioEngine: AnyObject {
    var onFailedToPlay: (() -> Void)? { get set }
    func play(url: URL)
    func stop()
}

final class AVRadioEngine: RadioEngine {
    var onFailedToPlay: (() -> Void)?
    private var statusObs: NSKeyValueObservation?

    private let player: AVPlayer = {
        let p = AVPlayer()
        p.automaticallyWaitsToMinimizeStalling = true
        return p
    }()

    func play(url: URL) {
        let item = AVPlayerItem(url: url)
        statusObs = item.observe(\.status) { [weak self] item, _ in
            if item.status == .failed { Task { @MainActor in self?.onFailedToPlay?() } }
        }
        player.replaceCurrentItem(with: item)
        player.play()
    }

    func stop() {
        statusObs = nil
        player.pause()
        player.replaceCurrentItem(with: nil)
    }
}
```

- [ ] **Step 4: Make RadioPlayer channel-driven**

Replace the stored `streamURL`/metadata wiring in `RadioPlayer` with channel state. Key changes:

```swift
@MainActor
final class RadioPlayer: ObservableObject {
    @Published private(set) var isPlaying = false
    @Published private(set) var nowPlaying: NowPlaying?
    @Published private(set) var channel: Channel
    @Published private(set) var failedOver = false

    private var streamURL: URL
    private let engine: RadioEngine
    private var metadata: NowPlayingProviding
    private let talkChannel: Channel?
    private var pollTask: Task<Void, Never>?

    init(streamURL: URL = Config.radioStreamURL,
         engine: RadioEngine = AVRadioEngine(),
         metadata: NowPlayingProviding = AzuraCastClient(url: Config.nowPlayingURL),
         talkChannel: Channel? = nil) {
        self.streamURL = streamURL
        self.engine = engine
        self.metadata = metadata
        self.talkChannel = talkChannel
        // A neutral default channel so the header has a label before config loads.
        self.channel = RadioConfigStore.fallback.channels.talk
        configureSession()
        configureRemoteCommands()
        engine.onFailedToPlay = { [weak self] in self?.handlePlaybackFailure() }
    }

    /// Set the channel to use on the NEXT play. Never interrupts live audio.
    func configure(channel: Channel, schedule: [ScheduleEntry]) {
        self.channel = channel
        if let url = channel.streamURL { self.streamURL = url }
        self.metadata = Self.metadataSource(for: channel, schedule: schedule)
        failedOver = false
    }

    private static func metadataSource(for channel: Channel, schedule: [ScheduleEntry]) -> NowPlayingProviding {
        if let np = channel.nowPlayingURL {
            return AzuraCastClient(url: np)              // Talk: live AzuraCast metadata
        }
        return ScheduleNowPlaying(entries: schedule, stationName: channel.name) // Hawaiʻi: schedule
    }

    private func handlePlaybackFailure() {
        guard let talk = talkChannel, channel.streamURL != talk.streamURL else { return }
        failedOver = true
        configure(channel: talk, schedule: [])
        engine.play(url: streamURL)
        isPlaying = true
        startMetadata()
        updateNowPlayingInfo()
    }
```

Leave `toggle()`, `startMetadata()`, `configureSession()`, `configureRemoteCommands()`, `resume()`, `pause()`, `updateNowPlayingInfo()` as-is (they already read `streamURL`/`metadata`/`nowPlaying`).

- [ ] **Step 5: Update FakeEngine in the test file to satisfy the new protocol**

(Already added `onFailedToPlay`/`triggerFailure` in Step 1 — confirm `FakeEngine` now conforms.)

- [ ] **Step 6: Run to verify all RadioPlayer tests pass**

Run: `cd /Users/junichi/jt/projects/po/app && xcodegen generate && xcodebuild test -scheme Makanapo -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:MakanapoTests/RadioPlayerTests`
Expected: PASS (existing 3 + new 3).

- [ ] **Step 7: Commit**

```bash
git add app/Makanapo/Services/RadioPlayer.swift app/MakanapoTests/RadioPlayerTests.swift
git commit -m "feat(ios): channel-driven RadioPlayer with Hawaii->Talk failover"
```

---

## Task 8: iOS UI — channel label chip, region note, sunset theme, localization

**Files:**
- Modify: `app/Makanapo/App/Localization.swift`
- Modify: `app/Makanapo/Views/RadioHeader.swift`
- Test: `app/MakanapoTests/LocalizationTests.swift`

**Interfaces:**
- Consumes: `RadioPlayer.channel` (Task 7), `LocalizationManager`/`L10n` (existing).
- Produces: `L10n` cases `radioNoteHawaii`, `radioNoteTalk`, `radioAboutStations`.
- Produces: `RadioHeader` shows the channel `label` as a chip and a one-line note derived from `player.channel.theme` (`sunset` → Hawaiʻi note, else Talk note), with the play button/gradient tinted by theme.

- [ ] **Step 1: Write the failing localization test**

Add to `app/MakanapoTests/LocalizationTests.swift`:

```swift
    func test_radioNotes_haveBothLanguages() {
        XCTAssertEqual(L10n.radioNoteHawaii.value(.en),
                       "You're hearing our full Hawaiʻi program — music, talk & live shows.")
        XCTAssertTrue(L10n.radioNoteTalk.value(.ja).contains("トーク編成"))
        XCTAssertEqual(L10n.radioAboutStations.value(.en), "About our stations")
        XCTAssertEqual(L10n.radioAboutStations.value(.ja), "チャンネルについて")
    }
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/junichi/jt/projects/po/app && xcodebuild test -scheme Makanapo -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:MakanapoTests/LocalizationTests`
Expected: FAIL to compile — new `L10n` cases undefined.

- [ ] **Step 3: Add the L10n cases**

In `app/Makanapo/App/Localization.swift`, add to the `enum L10n` case list:

```swift
    case radioNoteHawaii, radioNoteTalk, radioAboutStations
```

And in the `pair` switch:

```swift
        case .radioNoteHawaii:
            return ("音楽・トーク・生放送を含む、ハワイのフル編成をお届けしています。",
                    "You're hearing our full Hawaiʻi program — music, talk & live shows.")
        case .radioNoteTalk:
            return ("こちらの地域ではトーク編成をお届けしています。音楽・生放送を含む全編成はハワイを含む北米エリア限定です。",
                    "In your region we stream our Talk edition. The full program with music & live shows is available in North America.")
        case .radioAboutStations:
            return ("チャンネルについて", "About our stations")
```

- [ ] **Step 4: Update RadioHeader to show chip + note + theme**

In `app/Makanapo/Views/RadioHeader.swift`, add a computed helper and render it in `hero` (below the marquee) and a compact chip in `slim`:

```swift
    private var isHawaii: Bool { player.channel.theme == "sunset" }
    private var accent: Color { isHawaii ? Color(red: 0.88, green: 0.34, blue: 0.44) : .orange }
    private var note: L10n { isHawaii ? .radioNoteHawaii : .radioNoteTalk }
```

In `hero`, after the `MarqueeText`, add:

```swift
            Text(player.channel.label)
                .font(.caption2).bold().tracking(1)
                .padding(.horizontal, 10).padding(.vertical, 3)
                .background(Capsule().fill(accent.opacity(0.15)))
                .foregroundStyle(accent)
            Text(loc.t(note))
                .font(.caption2).foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)
            if player.failedOver {
                Text(loc.lang == .ja ? "接続の都合でトーク編成に切り替えました。"
                                     : "Switched to the Talk edition due to a connection issue.")
                    .font(.caption2).foregroundStyle(.secondary)
            }
```

Change the play button tint from `.foregroundStyle(.orange)` to `.foregroundStyle(accent)` in `playButton`. In `slim`, change the top `Text("makana.fm")` to also show the channel label:

```swift
                Text("makana.fm · \(player.channel.label)").font(.caption).bold()
```

- [ ] **Step 5: Run to verify localization test passes + app builds**

Run: `cd /Users/junichi/jt/projects/po/app && xcodegen generate && xcodebuild test -scheme Makanapo -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:MakanapoTests/LocalizationTests`
Expected: PASS. (Full build confirms `RadioHeader` compiles.)

- [ ] **Step 6: Commit**

```bash
git add app/Makanapo/App/Localization.swift app/Makanapo/Views/RadioHeader.swift app/MakanapoTests/LocalizationTests.swift
git commit -m "feat(ios): channel chip + region note + sunset theme in RadioHeader"
```

---

## Task 9: iOS wiring — launch-time config load + channel selection

**Files:**
- Modify: `app/Makanapo/App/MakanapoApp.swift`
- Test: `app/MakanapoTests/SmokeTests.swift`

**Interfaces:**
- Consumes: `RadioConfigStore` (Task 5), `RegionResolver` (Task 4), `ChannelDirector` (Task 3), `RadioPlayer.configure` (Task 7).
- Produces: on launch, the app loads `radio.json`, resolves region, and calls `radio.configure(channel:schedule:)`. `RadioPlayer` is constructed with `talkChannel: RadioConfigStore.fallback.channels.talk` so failover always has a target.

- [ ] **Step 1: Add a smoke assertion for the selection helper**

Add to `app/MakanapoTests/SmokeTests.swift`:

```swift
    @MainActor
    func test_launchSelection_pillsToTalkWhenHawaiiDisabled() {
        let cfg = RadioConfigStore.fallback // hawaii disabled
        let ch = ChannelDirector.pick(region: .na, config: cfg)
        XCTAssertEqual(ch.label, "TALK")
    }
```

- [ ] **Step 2: Run to verify it passes (guards the invariant before wiring)**

Run: `cd /Users/junichi/jt/projects/po/app && xcodebuild test -scheme Makanapo -destination 'platform=iOS Simulator,name=iPhone 17' -only-testing:MakanapoTests/SmokeTests`
Expected: PASS.

- [ ] **Step 3: Wire the launch flow**

Replace `app/Makanapo/App/MakanapoApp.swift` with:

```swift
import SwiftUI

@main
struct MakanapoApp: App {
    @StateObject private var dealsStore = DealsStore(
        loader: URLSessionDealsLoader(url: Config.dealsURL))
    @StateObject private var radio = RadioPlayer(
        talkChannel: RadioConfigStore.fallback.channels.talk)
    @StateObject private var loc = LocalizationManager()
    @StateObject private var radioConfig = RadioConfigStore()
    private let region = RegionResolver()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(dealsStore)
                .environmentObject(radio)
                .environmentObject(loc)
                .task { await selectChannel() }
        }
    }

    @MainActor
    private func selectChannel() async {
        await radioConfig.refresh()
        let cfg = radioConfig.config ?? RadioConfigStore.fallback
        let r = await region.resolve(naCountries: cfg.naCountries)
        let channel = ChannelDirector.pick(region: r, config: cfg)
        radio.configure(channel: channel, schedule: cfg.schedule[channelKey(channel, cfg)] ?? [])
    }

    private func channelKey(_ channel: Channel, _ cfg: RadioConfig) -> String {
        channel.streamURL == cfg.channels.hawaii.streamURL ? "hawaii" : "talk"
    }
}
```

- [ ] **Step 4: Run the full test suite + build**

Run: `cd /Users/junichi/jt/projects/po/app && xcodegen generate && xcodebuild test -scheme Makanapo -destination 'platform=iOS Simulator,name=iPhone 17'`
Expected: PASS (all suites). Build succeeds.

- [ ] **Step 5: Device/simulator smoke (manual, per verification-before-completion)**

Launch in the simulator. Confirm: radio plays Talk exactly as before, header shows `TALK` chip + Japanese/English Talk note per the language toggle, no visual regression to deals/map. (Live behavior is unchanged because `hawaii.enabled: false`.)

- [ ] **Step 6: Commit**

```bash
git add app/Makanapo/App/MakanapoApp.swift app/MakanapoTests/SmokeTests.swift
git commit -m "feat(ios): launch-time radio config load + channel selection wiring"
```

---

## Task 10: Web — self-contained WordPress player block + JS test harness

**Files:**
- Create: `web/radio-player.test.html`
- Create: `web/radio-player-block.html`
- Create: `web/README.md`

**Interfaces:**
- Produces: pure JS functions on `window.MakanaRadio`: `regionFor(country, naCountries) -> "NA"|"INTL"` and `pickChannel(region, config) -> channelObject`.
- Consumes: `data/radio.json` shape (Task 1), same fields as iOS.

- [ ] **Step 1: Write the failing in-browser test harness**

Create `web/radio-player.test.html`:

```html
<!DOCTYPE html>
<meta charset="utf-8">
<title>MakanaRadio logic tests</title>
<body style="font-family:system-ui;padding:20px">
<h1>MakanaRadio logic tests</h1>
<pre id="out"></pre>
<script src="./radio-player-logic.js"></script>
<script>
  const out = document.getElementById('out');
  let pass = 0, fail = 0;
  function eq(actual, expected, name) {
    const ok = JSON.stringify(actual) === JSON.stringify(expected);
    out.textContent += (ok ? "PASS " : "FAIL ") + name +
      (ok ? "" : ` (got ${JSON.stringify(actual)}, want ${JSON.stringify(expected)})`) + "\n";
    ok ? pass++ : fail++;
  }
  const NA = ["US","CA","MX"];
  const cfg = (hawaiiEnabled) => ({
    na_countries: NA,
    channels: {
      hawaii: { enabled: hawaiiEnabled, label: "HAWAIʻI", stream_url: "https://x/hi.aac", theme: "sunset" },
      talk:   { enabled: true, label: "TALK", stream_url: "https://x/talk.m3u8",
                nowplaying_url: "https://x/np", theme: "gold-teal" }
    }
  });
  eq(MakanaRadio.regionFor("US", NA), "NA", "US is NA");
  eq(MakanaRadio.regionFor("JP", NA), "INTL", "JP is INTL");
  eq(MakanaRadio.regionFor("", NA), "INTL", "empty country is INTL");
  eq(MakanaRadio.pickChannel("NA", cfg(true)).label, "HAWAIʻI", "NA+enabled -> Hawaii");
  eq(MakanaRadio.pickChannel("NA", cfg(false)).label, "TALK", "NA+disabled -> Talk");
  eq(MakanaRadio.pickChannel("INTL", cfg(true)).label, "TALK", "INTL -> Talk");
  out.textContent += `\n${pass} passed, ${fail} failed\n`;
  document.title = fail ? `FAIL (${fail})` : "PASS";
</script>
</body>
```

Note: the harness loads `radio-player-logic.js` — extract the pure functions there so both the test and the block share one source.

- [ ] **Step 2: Open the harness to verify it fails**

Run: `open /Users/junichi/jt/projects/po/web/radio-player.test.html`
Expected: page can't find `radio-player-logic.js` → all assertions FAIL / `MakanaRadio` undefined.

- [ ] **Step 3: Create the shared pure-logic file**

Create `web/radio-player-logic.js`:

```javascript
// Shared, dependency-free channel logic. Loaded by both the test harness and
// the paste-in block (the block also inlines a copy — keep them identical).
(function (root) {
  const MakanaRadio = {
    regionFor(country, naCountries) {
      return naCountries.includes((country || "").toUpperCase()) ? "NA" : "INTL";
    },
    pickChannel(region, config) {
      const c = config.channels;
      return (region === "NA" && c.hawaii.enabled) ? c.hawaii : c.talk;
    }
  };
  root.MakanaRadio = MakanaRadio;
})(window);
```

- [ ] **Step 4: Open the harness to verify it passes**

Run: `open /Users/junichi/jt/projects/po/web/radio-player.test.html`
Expected: tab title shows `PASS`; all 6 assertions PASS.

- [ ] **Step 5: Build the paste-in block**

Create `web/radio-player-block.html` — a single self-contained block (inline CSS/JS, no external files, so it survives pasting into a WP Custom HTML block). It must:
  1. Inline the same `regionFor`/`pickChannel` logic.
  2. On load: read cached region from `sessionStorage['makana_region']`; else `fetch("https://speed.cloudflare.com/meta")` with `AbortController` (1.5s) → `country`; on any failure use `"INTL"`; cache it.
  3. `fetch("https://cdn.jsdelivr.net/gh/tanabe11/makanapo@main/data/radio.json")`; on failure use an inlined fallback config equal to today's Talk-only settings.
  4. `pickChannel(region, config)` → render one pill: gradient by `theme` (`sunset` = orange→pink→purple; `gold-teal` = today's gold→teal), the channel `label`, a play/pause button whose `<audio>.src` = channel `stream_url`, plus the region note (EN for NA, JA for INTL) with an "About our stations / チャンネルについて" link to `/stations/` (Task 11 page).
  5. Now-playing: if `nowplaying_url` present (Talk), poll it every 25s (reuse today's AzuraCast fetch); else show the channel `name`.
  6. On `<audio>` `error` event while on Hawaiʻi: swap to the Talk channel's `stream_url` and show the failover note.

Full file:

```html
<!-- makana.fm radio player — paste into a WordPress "Custom HTML" block.
     Self-contained: no external CSS/JS. Replaces the current aloha-radio-player block. -->
<div id="makana-radio"></div>
<style>
  #makana-radio .pill{border-radius:999px;padding:12px 18px;display:flex;align-items:center;
    gap:10px;color:#fff;font-size:14px;flex-wrap:wrap;row-gap:6px}
  #makana-radio .pill.sunset{background:linear-gradient(90deg,#f2a65a,#e0567a 50%,#6b4f9e)}
  #makana-radio .pill.gold-teal{background:linear-gradient(90deg,#e8c37a,#4e8d7c 45%,#1d4e66)}
  #makana-radio .playbtn{background:rgba(255,255,255,.92);color:#2a6b66;border:none;
    border-radius:999px;padding:8px 16px;font-weight:700;cursor:pointer}
  #makana-radio .label{font-weight:800;letter-spacing:.06em;font-size:12px}
  #makana-radio .song{opacity:.85;font-size:12px}
  #makana-radio .note{font-size:11.5px;color:#8a8178;margin-top:8px;line-height:1.6}
  #makana-radio .note a{color:#2a6b66;font-weight:700}
</style>
<script>
(function(){
  var CDN="https://cdn.jsdelivr.net/gh/tanabe11/makanapo@main/data/radio.json";
  var FALLBACK={na_countries:["US","CA","MX"],channels:{
    hawaii:{enabled:false,label:"HAWAIʻI",name:"makana.fm Hawaiʻi",stream_url:null,theme:"sunset"},
    talk:{enabled:true,label:"TALK",name:"makana.fm Talk",
      stream_url:"https://radio.makana.fm/hls/makana.fm/live.m3u8",
      nowplaying_url:"https://radio.makana.fm/api/nowplaying/makana.fm",theme:"gold-teal"}}};
  function regionFor(c,na){return na.indexOf((c||"").toUpperCase())>=0?"NA":"INTL";}
  function pickChannel(r,cfg){var c=cfg.channels;return (r==="NA"&&c.hawaii.enabled)?c.hawaii:c.talk;}

  function getRegion(na){
    var cached=sessionStorage.getItem("makana_region");
    if(cached) return Promise.resolve(cached);
    var ctrl=new AbortController(); var t=setTimeout(function(){ctrl.abort();},1500);
    return fetch("https://speed.cloudflare.com/meta",{signal:ctrl.signal})
      .then(function(r){return r.json();})
      .then(function(m){clearTimeout(t);var reg=regionFor(m.country,na);
        sessionStorage.setItem("makana_region",reg);return reg;})
      .catch(function(){clearTimeout(t);return "INTL";});
  }
  function getConfig(){return fetch(CDN).then(function(r){return r.json();}).catch(function(){return FALLBACK;});}

  function render(cfg){
    getRegion(cfg.na_countries).then(function(region){
      var ch=pickChannel(region,cfg), talk=cfg.channels.talk;
      var el=document.getElementById("makana-radio");
      var isHi=ch.theme==="sunset";
      var note=isHi
        ? "You're hearing our full Hawaiʻi program — music, talk &amp; live shows."
        : "こちらの地域ではトーク編成をお届けしています。音楽・生放送を含む全編成はハワイを含む北米エリア限定です。";
      var linkLabel=isHi?"About our stations":"チャンネルについて";
      el.innerHTML=
        '<div class="pill '+ch.theme+'">'+
          '<button class="playbtn" id="mk-btn">▶ Tap to Listen</button>'+
          '<span class="label">'+ch.label+'</span>'+
          '<span class="song" id="mk-song">'+ch.name+'</span>'+
          '<audio id="mk-audio" preload="none"></audio>'+
        '</div>'+
        '<div class="note">'+note+' <a href="/stations/">'+linkLabel+'</a></div>';
      var audio=document.getElementById("mk-audio");
      var btn=document.getElementById("mk-btn");
      audio.src=ch.stream_url||talk.stream_url;
      btn.onclick=function(){
        if(audio.paused){audio.src=audio.src;audio.play();btn.textContent="⏸ Playing";}
        else{audio.pause();btn.textContent="▶ Tap to Listen";}
      };
      audio.addEventListener("error",function(){
        if(ch.stream_url && ch.stream_url!==talk.stream_url){
          audio.src=talk.stream_url; if(!audio.paused){audio.play();}
          document.getElementById("mk-song").textContent=talk.name;
        }
      });
      if(ch.nowplaying_url){pollSong(ch.nowplaying_url);}
    });
  }
  function pollSong(url){
    function tick(){
      fetch(url,{cache:"no-store"}).then(function(r){return r.json();}).then(function(j){
        try{var s=j.now_playing.song;var el=document.getElementById("mk-song");
          if(el&&s&&s.title){el.textContent=s.artist?(s.title+" — "+s.artist):s.title;}}catch(e){}
      }).catch(function(){});
    }
    tick(); setInterval(tick,25000);
  }
  getConfig().then(render);
})();
</script>
```

- [ ] **Step 6: Write the paste-in README**

Create `web/README.md`:

```markdown
# Web deliverables (paste into WordPress admin)

These files are pasted into the WordPress admin — they are not deployed by any
pipeline. Nothing here changes the live site until you paste it.

## radio-player-block.html
Replaces the current `aloha-radio-player` block on the home page.
1. WP admin → edit the home page.
2. Find the existing radio player (Custom HTML block).
3. Replace its entire contents with `radio-player-block.html`.
4. Preview. With `hawaii.enabled: false` in radio.json, it looks/behaves exactly
   like today (Talk, gold→teal pill).

## channel-about.html  (Task 11)
New page at slug `/stations/`. Paste into a Custom HTML block on a new page.

## Testing the logic
Open `radio-player.test.html` in a browser — tab title shows PASS/FAIL.
Region behavior: use a VPN (US vs Japan) and reload; NA shows the Hawaiʻi pill
only after the launch switch flips.

## radio-player-logic.js
Source of truth for `regionFor`/`pickChannel`, shared with the test harness.
The paste-in block inlines an identical copy (WP blocks can't load local JS).
If you change one, change both.
```

- [ ] **Step 7: Commit**

```bash
git add web/radio-player.test.html web/radio-player-logic.js web/radio-player-block.html web/README.md
git commit -m "feat(web): self-contained radio player block + JS logic tests"
```

---

## Task 11: Web — "About our stations" bilingual page

**Files:**
- Create: `web/channel-about.html`
- Modify: `web/README.md` (already references it — confirm accurate)

**Interfaces:**
- Consumes: nothing (static content). Linked from the note in Task 10's block (`/stations/`) and the iOS note (future: link the chip to the same URL).

- [ ] **Step 1: Write the page content**

Create `web/channel-about.html` — a Custom HTML block for a new `/stations/` page, English then Japanese, explaining the two editions and why programming differs by region. No external assets.

```html
<!-- makana.fm — About our stations. Paste into a Custom HTML block on page /stations/. -->
<div style="max-width:720px;margin:0 auto;font-family:system-ui,-apple-system,sans-serif;line-height:1.7">
  <h2>About our stations 🌺</h2>
  <p><strong>makana.fm streams two regional editions of the same station.</strong>
     Which one you hear is chosen automatically for your location.</p>
  <h3>🌺 Hawaiʻi — full program</h3>
  <p>Our complete program: music, talk, and live shows from Honolulu. Available to
     listeners in North America (United States, Canada, and Mexico), where our music
     licensing applies.</p>
  <h3>🎙 Talk — worldwide</h3>
  <p>Everywhere else, we stream our Talk edition: the same station with talk
     programming and license-free music, so it can play anywhere in the world.
     Our talk shows are also available as podcasts.</p>
  <p style="color:#8a8178;font-size:14px">Programming differs by region because music
     licensing for the full program is limited to North America. We're working to
     bring more of makana.fm to more places over time.</p>
  <hr style="margin:28px 0;border:none;border-top:1px solid #e3ded8">
  <h2>チャンネルについて 🌺</h2>
  <p><strong>makana.fm は、同じ局を地域ごとに2つのエディションでお届けしています。</strong>
     どちらが流れるかは、お使いの地域に合わせて自動で選ばれます。</p>
  <h3>🌺 Hawaiʻi ― フル編成</h3>
  <p>音楽・トーク・ホノルルからの生放送を含む完全版です。音楽ライセンスが適用される
     北米エリア（アメリカ・カナダ・メキシコ）の皆さまがお聴きいただけます。</p>
  <h3>🎙 Talk ― 全世界</h3>
  <p>それ以外の地域では、トーク編成をお届けします。トーク番組と著作権フリーの音楽で
     構成され、世界中どこでもお聴きいただけます。トーク番組はポッドキャストでも配信予定です。</p>
  <p style="color:#8a8178;font-size:14px">全編成の音楽ライセンスが北米に限られているため、
     地域によって放送内容が異なります。より多くの地域に makana.fm をお届けできるよう取り組んでいます。</p>
</div>
```

- [ ] **Step 2: Verify it renders standalone**

Run: `open /Users/junichi/jt/projects/po/web/channel-about.html`
Expected: both language sections render cleanly with no broken layout.

- [ ] **Step 3: Commit**

```bash
git add web/channel-about.html
git commit -m "feat(web): bilingual About our stations page content"
```

---

## Task 12: Cutover runbook + rehearsal

**Files:**
- Create: `web/README.md` cutover section is present; add `docs/superpowers/plans/live365-cutover-runbook.md`

**Interfaces:**
- Consumes: everything above. This task ships no code — it documents the exact one-commit go-live and the pre-flight rehearsal on a test branch.

- [ ] **Step 1: Write the runbook**

Create `docs/superpowers/plans/live365-cutover-runbook.md`:

```markdown
# Live365 Cutover Runbook

Prereqs: Tasks 1–11 merged; iOS build with hawaii.enabled=false already on the App
Store; web block + /stations/ page pasted and live (behavior-identical to old site).

## Phase 0 — Live365 live (before touching radio.json)
- [ ] Broadcast 1 station live; music library + automation + at least one live-show test done.
- [ ] Restrictions left at default (US/CA/MX).
- [ ] Copy the Icecast/HLS stream URL from Live365 dashboard → Listen tab.
- [ ] Confirm from Japan (VPN) that Live365's own player geo-blocks (expected).

## Rehearsal (no production impact)
- [ ] Create branch `radio-cutover`. Edit `data/radio.json`:
      hawaii.enabled=true, hawaii.stream_url="<Live365 URL>", fill schedule[].
- [ ] Run `python3 -m pipeline.validate_radio` locally → must print "radio.json OK".
- [ ] Push branch. Point a scratch test page / the iOS debug build at
      `https://cdn.jsdelivr.net/gh/tanabe11/makanapo@radio-cutover/data/radio.json`.
- [ ] VPN US → Hawaiʻi pill + Live365 audio + sunset theme + schedule name.
- [ ] VPN Japan → Talk pill unchanged.
- [ ] Kill network mid-play on US → Hawaiʻi→Talk failover fires.

## Go-live (the one commit)
- [ ] Merge `radio-cutover` to `main` (or edit radio.json on main): hawaii.enabled=true + stream_url.
- [ ] CI `validate-radio` must pass.
- [ ] jsDelivr serves within ~12h; to force now, purge:
      `curl https://purge.jsdelivr.net/gh/tanabe11/makanapo@main/data/radio.json`
- [ ] Re-verify US and Japan on production web + shipped app.

## Rollback
- [ ] Set hawaii.enabled=false on main + purge jsDelivr. Both platforms revert to Talk
      within one config fetch. No app resubmission needed.

## After go-live
- [ ] Move AzuraCast programming to talk + license-free music (can precede go-live).
- [ ] Watch Live365 TLH in the dashboard (North-America listeners only).
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/plans/live365-cutover-runbook.md
git commit -m "docs: Live365 cutover runbook + rehearsal steps"
```

---

## Self-Review Notes

- **Spec §1 (data contract + pick logic):** Task 1 (radio.json/schema/validator), Task 3 (iOS pick), Task 10 (web pick). ✓
- **Spec §1 geo (fail-open):** Task 4 (iOS RegionResolver, offline fallback), Task 10 (web getRegion → INTL on failure). ✓
- **Spec §2 (web block, fallbacks, note language, now-playing):** Task 10; About page Task 11. ✓
- **Spec §3 (iOS units RadioConfig/RegionResolver/ChannelDirector/RadioEngine/RadioHeader/metadata/localization/tests):** Tasks 2–9. ✓
- **Spec §4 phases + rehearsal + verification:** Task 12 runbook; per-task device smoke in Task 9. ✓
- **Spec §5 operations (TLH, UK add-on):** documented in spec §7 and runbook; UK = 1-line `na_countries` change (schema allows any 2-letter upper). ✓
- **Never-switch-mid-play:** Task 7 `configure` test asserts no new play; failover is the sole exception, tested. ✓
- **Never-crash fallback:** Task 5 `RadioConfigStore.fallback` + Task 10 inlined `FALLBACK`. ✓
- **Type consistency:** `ChannelDirector.pick(region:config:)`, `RegionResolver.resolve(naCountries:)`/`region(forCountry:naCountries:)`, `RadioPlayer.configure(channel:schedule:)`, `RadioConfigStore.fallback`, JS `regionFor`/`pickChannel` — names match across all tasks. ✓
