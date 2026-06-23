# makanapo — STATUS / 引き継ぎ（handoff）

> 別マシン（Mac Mini）でローカル作業（特に Tier-1 発見スキル）を続けるための引き継ぎ文書。
> **状態が変わるたびに更新する。** 背景は [SPEC.md] / 規約は [CLAUDE.md] / 経緯は [KICKOFF.md]。
> Last updated: 2026-06-22 (iOS MVP built: radio + deals + collapsing hero; data: active 18)

## 現在地（TL;DR）
- リポジトリ: https://github.com/tanabe11/makanapo （public, main）
- 公開 `data/deals.json`: **31件**（active 18 / unverified 12 / expired 1）一次情報・公式のみ
- `data/sources.json` の official_sites: **13件**（発見スキルが追記していく）
- CDN: `https://cdn.jsdelivr.net/gh/tanabe11/makanapo@main/data/deals.json`
- Tier-2 cron（GitHub Actions `build-deals`）: **手動runで緑を確認済み**（毎日 15:17 UTC ≒ HST 05:17 自動実行）
- Tier-1 発見（`makanapo-discover` スキル）: ローカル運用（要 WebSearch = Claude Code）
- **Go 基準: active 50件。現在 18件。**

## アーキテクチャ（二層）
```
週1・ローカル : makanapo-discover (Claude + WebSearch) → data/sources.json を更新 → 人がレビュー → push
毎日・クラウド: GitHub Actions → build.py が sources.json + パーサ群を巡回 → data/deals.json 更新 → コミット → jsDelivr 反映
```
- 「No LLM in the pipeline」: LLMは cron の外（ローカル発見スキル）にだけ存在。
- アグリゲータ（Honolulu Magazine 等）は **leads-only・非公開**（著作権）。公開は一次情報/公式のみ。

## iOS アプリ（MVP・`app/` 配下）
- **状態：MVP 完成（未push のコミットあり）**。ラジオ（makana.fm/AzuraCast バックグラウンド再生＋ロック画面操作＋now-playing）＋ 割引一覧＋詳細。トップは「折り畳みヒーロー」（スクロールでラジオが細バーに）。
- 技術：SwiftUI / iOS 16+（折り畳みは `onScrollGeometryChange`＝iOS18+のみ作動、16-17はヒーロー固定）。XcodeGen。Bundle ID `fm.makana.makanapo`。データは CDN直 `deals.json`。
- ラジオ実URL（`app/Makanapo/App/Config.swift`）：stream `https://radio.makana.fm/listen/makana.fm/radio.mp3`、now-playing `https://radio.makana.fm/api/nowplaying/makana.fm`（station shortcode = `makana.fm`）。
- **ビルド手順（Mac）**：`brew install xcodegen` → `cd app && xcodegen generate` → Xcode で開き **iOS Simulator（例 iPhone 17）**を選んで ⌘R。`*.xcodeproj` は gitignore（毎回 generate）。テスト：⌘U（Deal/Store/NowPlaying の単体）。
- 設計/計画：`docs/superpowers/specs/2026-06-22-makanapo-ios-app-design.md` / `docs/superpowers/plans/2026-06-22-makanapo-ios-mvp.md`。
- 未確認（実機推奨）：ロック画面でのバックグラウンド継続（シミュレータは擬似的）。
- 実装済み追加：**セグメント絞り込み**（すべて/ハッピーアワー/カマアイナ。`Deal.isHappyHour`/`isKamaaina` で分類）。
- 実装済み追加：**EN/JA ローカライズ**（`LocalizationManager`＋`L10n` 文字列テーブル、ナビバー🌐で即切替、初回は端末言語追従）。UIラベルのみ（データ＝店名/割引文は英語のまま）。
- 実装済み追加：**地図ビュー（Phase A）**（`DealMapView`、左上トグルでリスト⇄地図、座標ありの割引をピン表示＝現13件、ピン→詳細、絞り込み連動。iOS17+のMapKit）。
- 実装済み追加：**地図ピン増加（Phase B・ジオコーディング）**。`pipeline/core/geocode.py`＋`pipeline/geocode_fill.py`（ローカルでNominatim、1req/秒、`data/geocode_cache.json`にキャッシュ）。`build.py` は**キャッシュ読むだけ**でlat/lng付与（cronはネット不要）。**coords 13→20/31**。
  - 運用：座標を増やすときはローカルで `python3 -m pipeline.geocode_fill` → `python3 -m pipeline.core.build` → `data/deals.json`＋`data/geocode_cache.json` をコミット＆push。アプリは CDN 取得なので**push後にjsDelivr反映されてからピン増**（必要なら purge）。
  - 未解決11件（店名がNominatim未収録）：spa系/Piko/Hideout/Redfish/Pint+Jigger/Fat Cheeks/Yoga Room/Tommy Bahama/Hawaii Massage Clinic。**住所が取れれば解決** → discoveryで各公式から住所抽出を足すのが次の改善。
- 次：現在地/近く（位置情報許可）、検索、報告ボタン、App Store配布（Developer Program $99/年）。

## 別マシン（Mac Mini）でのセットアップ
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
| `pipeline/core/*` | 決定論エンジン（fetch/extract/jsonld/venue/classify/normalize/build） | 追跡 |
| `pipeline/sources/*` | ソース別パーサ（ala_moana / waikiki_beach_walk / oahu_official / honolulu_magazine） | 追跡 |
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
- [ ] 発見スキルを回して active を 18 → 50 に近づける（最優先。HHある独立系=active化しやすい / カマアイナのみ=unverified+リンクになりがち）
- [ ] CI セーフガード（件数大幅減で commit 抑止）
- [ ] README 追加
- [ ] アプリ（SwiftUI + MapKit, v1 閲覧専用）着手は active が十分溜まってから
