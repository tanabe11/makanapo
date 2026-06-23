# makanapo — STATUS / 引き継ぎ（handoff）

> 別マシン（Mac Mini）でローカル作業（特に Tier-1 発見スキル）を続けるための引き継ぎ文書。
> **状態が変わるたびに更新する。** 背景は [SPEC.md] / 規約は [CLAUDE.md] / 経緯は [KICKOFF.md]。
> Last updated: 2026-06-22 (rebrand: app=makana.fm / deals=Makanapō; +menu/About/ad banner; map+geocoding; coords 29/31)

## 現在地（TL;DR）
- リポジトリ: https://github.com/tanabe11/makanapo （public, main）
- 公開 `data/deals.json`: **43件**（active 27 / unverified 15 / expired 1）一次情報・公式のみ。coords 38/43。
- `data/sources.json` の official_sites: **25件**（発見スキルが追記していく）
- CDN: `https://cdn.jsdelivr.net/gh/tanabe11/makanapo@main/data/deals.json`
- Tier-2 cron（GitHub Actions `build-deals`）: **手動runで緑を確認済み**（毎日 15:17 UTC ≒ HST 05:17 自動実行）
- Tier-1 発見（`makanapo-discover` スキル）: ローカル運用（要 WebSearch = Claude Code）
- **Go 基準: active 50件。現在 27件**（あと23）。未push のローカルコミットあり → `git push` 必要。

## アーキテクチャ（二層）
```
週1・ローカル : makanapo-discover (Claude + WebSearch) → data/sources.json を更新 → 人がレビュー → push
毎日・クラウド: GitHub Actions → build.py が sources.json + パーサ群を巡回 → data/deals.json 更新 → コミット → jsDelivr 反映
```
- 「No LLM in the pipeline」: LLMは cron の外（ローカル発見スキル）にだけ存在。
- アグリゲータ（Honolulu Magazine 等）は **leads-only・非公開**（著作権）。公開は一次情報/公式のみ。

## iOS アプリ（`app/` 配下）
**ブランド（決定 2026-06-22, 詳細 SPEC.md §9）**：アプリ名＝**makana.fm**（社名 makana.fm LLC＝傘ブランド）／ディール機能＝**Makanapō** section（`last_verified` 鮮度が主役）。内部名（repo/パイプライン/Bundle ID `fm.makana.makanapo`）は **makanapo** のまま（CDN URL 維持のため改名しない）。UI：ナビ中央＝`makana.fm`、ラジオ下の見出し＝`Makanapō`＋「ハッピーアワー & カマアイナ」。左上メニュー＝再読込/言語/About。下部＝ハウス広告バナー。残務：USPTO 連邦検索（区分9/38/41/35、特に音楽の "Makana"）＋ App Store 表示名予約。

**実装済み機能（ユーザー確認済み）**：
| 機能 | 実装 |
|---|---|
| ラジオ再生 | AVPlayer + AVAudioSession(.playback) + UIBackgroundModes:audio |
| ロック画面操作 | MPNowPlayingInfoCenter / MPRemoteCommandCenter |
| Now-Playing 取得 | AzuraCast REST 25秒ポーリング |
| 折り畳みヒーロー | `onScrollGeometryChange`（iOS18+）。iOS16-17はヒーロー固定 |
| 割引一覧 + 詳細 | CDN `deals.json` 取得・オフラインキャッシュ |
| セグメント絞り込み | All / Happy Hour / Kama'aina（`Deal.isHappyHour`/`isKamaaina`） |
| EN/JA 切替 | `LocalizationManager` + `L10n` テーブル、左上メニュー内で即時切替、端末言語初期値 |
| 地図ビュー | `DealMapView`（iOS17+ MapKit）。見出し右トグルでリスト⇄地図。ピン→詳細。絞り込み連動 |
| 左上メニュー | `Menu`（☰）：再読込 / 言語切替 / このアプリについて（`AboutView` シート） |
| 広告 | 下部固定のハウス広告バナー `AdBannerView`（現状 makana.fm 宣伝。後でAdMob等に差替え可能な独立枠） |
| アプリアイコン | `img/makana_fm.jpg`→PNG化 → `Assets.xcassets/AppIcon.appiconset/` |

**ラジオ URL（`Config.swift`）**：
- stream: `https://radio.makana.fm/listen/makana.fm/radio.mp3`
- now-playing: `https://radio.makana.fm/api/nowplaying/makana.fm`（shortcode = `makana.fm`）

**ビルド手順（Mac）**：
```
brew install xcodegen
cd app && xcodegen generate
# Xcode で開き iOS Simulator（iPhone 17 等）を選択 → ⌘R
# テスト: ⌘U（DealDecoding / DealsStore / NowPlaying / DealFilter / Localization / Smoke）
```
`*.xcodeproj` は gitignore — 毎回 `xcodegen generate` が必要。

**ジオコーディング（地図ピン）**：
- 31件中 **29件に座標あり**（coords 13→29）。
- 未解決2件（JSページで住所取得不可）：**My Hawaii Spa** / **Royal Kaila Spa** → seed に住所を追記すればジオコーダが解決。
- 座標追加手順：`python3 -m pipeline.geocode_fill` → `python3 -m pipeline.core.build` → `deals.json`＋`geocode_cache.json` をコミット＆push → jsDelivr 反映でピン増（必要なら purge）。`makanapo-discover` スキルにこの手順を内蔵済み。

**未確認（実機推奨）**：ロック画面バックグラウンド継続（シミュレータは擬似的）。

**次の候補**：現在地/近く（`CLLocationWhenInUse`、同意設計必要）、検索、「期限切れ報告」ボタン、App Store 配布（Apple Developer Program $99/年）。

## 別マシン（Mac Mini）でのセットアップ
> **完全な手順書: [docs/MACMINI_SETUP.md](docs/MACMINI_SETUP.md)**（clone前のpush・gh認証・push衝突回復・discovery運用・jsDelivrパージまで網羅）。以下は要約。
### 前提
- git / Python 3.9+（CIは3.11）/ `pip install jsonschema`（唯一の依存）
- `gh` CLI を認証し **workflow スコープ付き**にする（ワークフローファイルを push するため）:
  ```
  gh auth login
  gh auth refresh -h github.com -s workflow
  ```
- Claude Code（Tier-1 発見スキルは WebSearch が必要）
### クローン
```
git clone https://github.com/tanabe11/makanapo && cd makanapo
```
### 注意: gitignore されているもの（クローン後ローカルで再生成）
- `data/leads.json` / `data/leads/`（内部リード）・`data/preview.html`（閲覧用）・`.claude/settings.local.json`
- 再生成: `python3 -m pipeline.core.build`（deals.json と leads.json を生成） → `python3 -m pipeline.preview`

## よく使うコマンド
```
python3 -m pipeline.core.build     # Tier-2 をローカル実行 → data/deals.json 生成（検証込み）
python3 -m pipeline.stats          # active/unverified/expired・カテゴリ・地区の集計
python3 pipeline/validate.py       # data/seed/*.json をスキーマ検証
python3 -m pipeline.preview        # data/preview.html 生成（open data/preview.html で閲覧）
# 候補URLの検証＆設定追記（発見スキルが使う）:
python3 -m pipeline.discover_add "<url>" --category food --subcategory happy_hour \
    --neighborhood Waikiki --name "Foo Bar"          # ドライラン（検証のみ）
python3 -m pipeline.discover_add "<url>" --category food ... --add   # data/sources.json に追記
gh workflow run build-deals        # Actions を手動実行（要 gh 認証）
gh run list --workflow=build-deals # 実行履歴
```

## Tier-1 発見スキルの回し方（Mac Mini）
1. リポジトリ内で Claude Code を開き、`makanapo-discover` スキルを起動（「makanapo discovery を回して」）。
2. スキルが leads/既存を見て候補を選び、WebSearch で公式URLを探し、`discover_add` で決定論検証 → 取れたものを `data/sources.json` に追記（unverified は公式リンク付きで保持）。
3. `python3 -m pipeline.core.build` で再生成し、差分（`git diff data/sources.json` と active 件数）を確認。
4. 問題なければ `git add data/sources.json data/deals.json && git commit && git push`。
5. 次の cron（または `gh workflow run build-deals`）で公開反映。

## ファイル地図
| パス | 役割 | git |
|---|---|---|
| `data/sources.json` | 巡回設定（Tier-1書く / Tier-2読む） | 追跡 |
| `data/deals.json` | 公開成果物（CIが更新） | 追跡 |
| `data/seed/*.json` | 一次確認済みのキュレーション記録 | 追跡 |
| `data/leads.json` `data/leads/` | 内部リード（アグリゲータ由来・非公開） | **ignore** |
| `data/preview.html` | ローカル閲覧ビューア | **ignore** |
| `data/geocode_cache.json` | Nominatim ジオコーディングキャッシュ（`geocode_fill` が書く / `build.py` が読む） | 追跡 |
| `img/makana_fm.jpg` | アプリアイコン原画（1024²・PNG化してアセットカタログへ） | 追跡 |
| `pipeline/core/*` | 決定論エンジン（fetch/extract/jsonld/venue/classify/normalize/geocode/build） | 追跡 |
| `pipeline/geocode_fill.py` | ローカル専用 Nominatim ジオコーダ（Tier-1。cronから呼ばない） | 追跡 |
| `pipeline/sources/*` | ソース別パーサ（ala_moana / waikiki_beach_walk / oahu_official / honolulu_magazine） | 追跡 |
| `app/` | SwiftUI iOS アプリ（XcodeGen。`*.xcodeproj` は gitignore） | 追跡（xcodeproj除く） |
| `app/Makanapo/Assets.xcassets/` | アプリアイコン等アセット | 追跡 |
| `.claude/skills/makanapo-discover/` | Tier-1 発見スキル | 追跡 |
| `.github/workflows/build.yml` | Tier-2 cron | 追跡 |

## スコープ / 方針（厳守。詳細は CLAUDE.md）
- オアフ/ホノルル × 飲食・サービスのみ。v1 は閲覧専用・ログインなし・州ID画像/PII 非保持。
- 公開は一次情報/公式のみ。アグリゲータは leads-only。
- スキーマ: 必須 `id,name,category,source_url,last_verified,status`（`discount` は任意）。

## 既知の注意点（gotchas）
- `gh` での workflow ファイル push には **workflow スコープ**が必要。
- CI は GitHub のデータセンターIPから取得。サイトによっては弾かれ得る（現状は全到達OK）。あるソースがCIで0件だと deals.json が一時的に縮みコミットされ得る → 将来「件数大幅減なら commit しない」セーフガード検討。
- Python 3.9 互換のため各モジュール先頭に `from __future__ import annotations`（実装済み）。
- IMP（International Market Place）= 接続レベルでブロック（Playwright不可）→ 対象外。RHC = テナント割引一覧頁が存在せず深追い不要。
- `last_verified` の日付は `normalize.today()`（Honolulu時刻・UTC-10固定）で統一済み（CI/ローカルの日付ズレ対策）。

## push が rejected されたら（毎日の cron が先にコミットしている）
日次 Actions が `data/deals.json` を自動更新するため、ローカルに未push作業があると衝突する。`deals.json` は生成物なので**取り込んで再生成**するだけ：
```
git fetch origin
git merge origin/main --no-edit       # deals.json は自動マージされるが信用しない
python3 -m pipeline.core.build         # sources.json から再生成（整合保証）
git add data/deals.json && git commit --amend --no-edit   # マージコミットに反映
git push
```
（対応済み 2026-06-22: `last_verified` は `normalize.today()` が **Honolulu時刻(UTC-10)固定**で付与＝CI(UTC)とローカルで日付一致。ランナーTZに非依存。）

## 次にやること（候補）
- [ ] 発見スキルを回して active を 18 → 50 に近づける（Go/No-Go 最優先。HHある独立系=active化しやすい / カマアイナのみ=unverified+リンク）
- [ ] 残り2件の座標補完：My Hawaii Spa / Royal Kaila Spa の住所を調べて seed に追記 → `geocode_fill` → `build` → push
- [ ] アプリ：現在地/近く（`CLLocationWhenInUse`・同意設計）
- [ ] アプリ：「期限切れ報告」ボタン（Google Form 等の別エンドポイント）
- [ ] CI セーフガード（件数大幅減で commit 抑止）
- [ ] App Store 配布（Apple Developer Program $99/年、TestFlight → 審査）
- [ ] README 追加
