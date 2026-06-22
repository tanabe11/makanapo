---
title: makanapo — キックオフ手順（スキーマ × 検証スプリント ハイブリッド）
project: makanapo
status: 着手中 / Claude Code 引き継ぎ
created: 2026-06-21
tags: [project/makanapo, kickoff, handoff, claude-code]
---

# makanapo — キックオフ手順（ハイブリッド案）

> このファイルは **Claude Code への引き継ぎ指示** を兼ねる。
> 背景・全体仕様は [[SPEC]]、開発規約は [[CLAUDE]] を参照。
> 方針: 机上で完璧なスキーマを作らず、**最小スキーマ v0 → 手動で実データ2〜3件 → 確定** の順で、実データに当てて固める。

---

## ゴール（このキックオフの完了条件）

1. `schema/deal.schema.json` の **確定版**（実データ2〜3件で検証済み）。
2. `data/seed/` に **手動収集の実データ**（まず2〜3件 → 最終的に50件）。
3. **Go/No-Go 判定**: 「今も有効 ＆ フィールドが埋まる」飲食・サービスの割引が **50件** 集まれば Go。

> ⚠️ スコープ厳守: オアフ/ホノルル × 飲食・サービスのみ。v1は閲覧専用・ログインなし・州ID画像を持たない。詳細は [[CLAUDE]]。

---

## フェーズ 0 — リポジトリ足場（Claude Code）

- [ ] `po/` を git 初期化（未なら）。
- [ ] ディレクトリ作成: `schema/`, `data/seed/`, `pipeline/`, `app/`
- [ ] `.gitignore`（macOS `.DS_Store`、Python `__pycache__/`、Swift build 産物）
- [ ] `SPEC.md` / `CLAUDE.md` / 本ファイルが `po/` 直下にあることを確認。

目標レイアウトは [[CLAUDE]] の "Repo layout" に従う。

---

## フェーズ 1 — 最小スキーマ v0（Claude Code）

[[CLAUDE]] のデータモデルを JSON Schema (draft-07) に落とす。**v0 は緩めに**（まず実データを通すのが目的。厳格化は v1 で）。

- [ ] `schema/deal.schema.json` を作成。
- [ ] 必須キー: `id`, `name`, `category`, `discount`, `source_url`, `last_verified`, `status`。
- [ ] 列挙: `category` = `food | service`、`status` = `active | expired | unverified`、`redemption` = `show_id | code | online`。
- [ ] 任意キー: `subcategory`, `conditions`, `code`, `address`, `lat`, `lng`, `neighborhood`, `hours`。
- [ ] バリデータを用意（`pipeline/validate.py` か `ajv` などの軽量手段）。`data/seed/*.json` を検証できるようにする。

### v0 雛形（叩き台・このまま `deal.schema.json` の出発点に）
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "makanapo deal",
  "type": "object",
  "required": ["id", "name", "category", "discount", "source_url", "last_verified", "status"],
  "additionalProperties": false,
  "properties": {
    "id": { "type": "string" },
    "name": { "type": "string" },
    "category": { "enum": ["food", "service"] },
    "subcategory": { "type": "string" },
    "discount": { "type": "string" },
    "conditions": { "type": "string" },
    "redemption": { "enum": ["show_id", "code", "online"] },
    "code": { "type": ["string", "null"] },
    "address": { "type": "string" },
    "lat": { "type": "number" },
    "lng": { "type": "number" },
    "neighborhood": { "type": "string" },
    "hours": { "type": "string" },
    "source_url": { "type": "string", "format": "uri" },
    "last_verified": { "type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$" },
    "status": { "enum": ["active", "expired", "unverified"] }
  }
}
```

---

## フェーズ 2 — 手動で実データ 2〜3件（人間 + Claude Code 補助）

スキーマを「実物」に当てる。**一次情報優先**（店の公式ページ/公式IG/HVCB/モール公式）。編集記事はリードとして使い、説明文は自作。詳細ルールは [[CLAUDE]] の "Data collection rules"。

- [ ] まず **異なる3パターン** を1件ずつ作る:
  1. 飲食 / ハッピーアワー（例: Kakaako のレストラン、時間帯ありの `hours`）
  2. 飲食 / カマアイナ割引（`redemption: show_id`、`conditions` に「ハワイID提示」）
  3. サービス（サロン or スパ、`redemption: code` か `show_id`）
- [ ] 各件を `data/seed/<id>.json` で作成し、v0スキーマで検証 → **通す**。
- [ ] 検証で見つかった不足/不整合を記録（下の「スキーマ改訂メモ」へ）。

### サンプルレコード（形式の手本・実在データではない）
```json
{
  "id": "example-hh-0001",
  "name": "(店名)",
  "category": "food",
  "subcategory": "happy_hour",
  "discount": "appetizers 50% off",
  "conditions": "dine-in only; bar area",
  "redemption": "show_id",
  "code": null,
  "address": "(住所), Honolulu, HI",
  "lat": 21.29,
  "lng": -157.85,
  "neighborhood": "Kakaako",
  "hours": "Mon-Fri 15:00-17:00",
  "source_url": "https://(一次情報URL)",
  "last_verified": "2026-06-21",
  "status": "active"
}
```

---

## フェーズ 3 — スキーマ確定（Claude Code）

- [ ] フェーズ2の気づきを反映し `deal.schema.json` を **確定版**へ。
- [ ] 想定される改訂候補（実データ次第で採否を判断）:
  - `discount_type`（`percent | bogo | fixed_price | freebie`）を別フィールド化するか？
  - `conditions` を文字列のままか、`requires_id: bool` などフラグ化するか？
  - `hours` を構造化（曜日×時間帯の配列）するか、MVPは文字列で十分か？
  - `island` / `city` を持たせるか（当面オアフ/ホノルル固定なら省略可）。
- [ ] 確定後、全 `data/seed/*.json` を再検証して緑にする。

---

## フェーズ 4 — 検証スプリント本番（人間主導 + Claude Code 補助）

- [ ] 名指しソースから **合計50件** を `data/seed/` に収集（飲食・サービス）。
- [ ] 各件に `last_verified` と `status` を必ず付与。期限切れは `expired`、未確認は `unverified`。
- [ ] 集計スクリプト（`pipeline/stats.py`）: `active` 件数、カテゴリ別件数、地区別件数を出力。
- [ ] **Go/No-Go**: `active` の飲食・サービスが **50件** → Go。30件程度なら範囲/カテゴリを再検討（[[SPEC]] の判定基準）。

### 収集元（要約。詳細は [[SPEC]] の §4）
- Tier 1（公式・準公式）: HVCBオアフ `kamaainaspecialoffers.com/oahu`、アラモアナセンター カマアイナ割引、各店公式ページ。
- Tier 2（リードとして）: Honolulu Magazine、HAWAII Magazine、onolicioushawaii.com、nateeatshawaii.com、hawaiihappyhours.com。
- Tier 3（発見）: Yelp/Google、Instagram #kamaaina #pauhana、Reddit r/Hawaii。

---

## スキーマ改訂メモ（フェーズ2〜3で追記していく）

- （例）conditions が長文化しやすい → `requires_id` フラグ＋自由記述に分離を検討
- **実データ3件（2026-06-21, v0で全件PASS）からの気づき:**
  - `redemption` に「不要」がない。ハッピーアワー（VEIN）は時間帯のみで ID/コード不要 → 任意キーなので省略で対応できたが、`redemption: none` を足すか「省略=不要」を規約化するか要決定。
  - `hours` が過負荷。VEIN では「HHの時間帯」と「営業時間」を1フィールドに詰め込んだ → 読みにくい。`happy_hour` 窓を別キー化 or MVPは文字列のまま割り切りか要決定。
  - `discount` が全件パーセント表記（18%/20%/10%）。フィルタ/表示用に `discount_type`（percent|bogo|fixed_price|freebie）の別フィールド化が有効そう。
  - カマアイナ系は条件に必ず「Hawaii ID 提示」が入る。`requires_id: bool` を立てるとアプリで重要属性を前面に出しやすい（makanapo の差別化点）。
  - **出典の期限を鵜呑みにしない実例:** Hawaii Massage Clinic はサイト掲載のキャンペーン期間が「Until April 30, 2025」=既に期限切れ → サービス枠から除外し現行有効な Hawaii Natural Therapy に差し替え。`status`/`last_verified` の価値を実地で確認。掲載側の期限を持つ `valid_until`（任意）を足すか検討。
  - `island`/`city` は全件オアフ/ホノルルのため省略で問題なし（当面据え置き）。
  - `lat`/`lng` は手作業では近似値どまり。本番パイプラインでジオコーディング必須（スキーマ問題ではない）。
- **Phase 3 確定結果（2026-06-21 適用済み）:** 任意フィールド2つを `deal.schema.json` に追加 → `requires_id`(bool) と `valid_until`(YYYY-MM-DD)。既存3件に `requires_id` を補完し再検証 3/3 PASS。`discount_type` の別フィールド化と `hours` の構造化は **50件収集後に再判断**（現時点は据え置き）。`lat`/`lng` は近似のため本番でジオコーディング。

---

## フェーズ4 結果（2026-06-21 暫定）

- **収集件数: 56件**（`data/seed/`）。内訳 — status: `active` 9 / `unverified` 42 / `expired` 5。category: food 48 / service 8。
- **active（一次確認済み）9件**: VEIN(HH), The Buffet at Hyatt(20% show_id), Hawaii Natural Therapy(10% massage), Texas de Brazil, Island Crepes(以上 Ala Moana 公式), Body Balance(fitness), Mani Pedi Spa(salon), Moku Kitchen(HH), Doraku(HH)。一次情報＝各店公式 or モール公式（Ala Moana）。
- **unverified 42件**: Honolulu Magazine 等の信頼リード。多くは「10% off kamaaina（期限なし）」の常設系で、一次確認すれば active 化が濃厚。`status:unverified` で正直に保持し、`build.py` 段階で確認→昇格する運用。
- **expired 5件**: 出典掲載の期限が既に経過（Basalt 〜2025-08-31, Ruth's Chris/Solera/Ramen Bario 〜2025-12-31, Hawaii Massage Clinic 〜2025-04-30）。**「リストは陳腐化する」= makanapo の中核仮説を実地で確認**。`last_verified`/`status` の価値が実証された。
- **Go/No-Go 判定（暫定）: 入手可能性ベースでは GO 寄り。** 候補プールは50を優に超え、飲食カマアイナ＋HHは潤沢。律速は「件数」ではなく**一次確認のスループット**（モール/店舗公式サイトが JS 重め・タイムアウト多発）。
- **発見した偏り**: 飲食(48)に対し**サービス系の住民割引は薄い(8)**。spa/massageは見つかるが、barber/auto/pet groomingの「kamaaina」明示は少ない → サービス枠は直接問い合わせ or 別ソース開拓が必要。
- **次の一手**: ①unverified を一次確認して active 50件化（モール公式: Royal Hawaiian Center / International Market Place のカマアイナ頁が有力、要レンダリング対応）。②サービス枠の補強。③`build.py` で active のみ `data/deals.json` へ。

---

## パイプライン方針（2026-06-21 決定）

> 自動化バッチ（GitHub Actions）の前提。詳細規約は [[CLAUDE]] の "Extraction policy" を参照。

- **手動ゼロ・LLMゼロ**：収集〜抽出は決定論コードのみ。日次の手入力もLLM API呼び出しもしない。
- **抽出スタック（レバレッジ順）**：①隠れJSON API/公式API（WordPress `/wp-json/` 等）→ ②JSON-LD(schema.org) 共通パーサ → ③OG/メタ → ④正規表現（`\d+%\s*off`, `Hawaii ID` 等）→ ⑤ジオコーディングは無料の OSM Nominatim。
- **説明文は保存しない**（事実のみ）→ LLM要約が不要になる。
- **取れた事実だけ／捏造しない**：
  - `discount` まで取れた → `status: active`
  - 店は特定できたが詳細を取り切れない → `status: unverified` ＋ `source_url` 必須。アプリは取れた事実＋「公式で確認」リンクを出し、**ユーザーに確認を委ねる**。
  - 何も取れない → レコードを作らない（スキップ）。
- **スキーマ修正済み**：`discount` を必須→任意に変更（`source_url`/`status` は必須のまま）。これで「未確認＋リンクだけ」のレコードが検証を通る。
- **Go/No-Go は `active` のみで数える**。`unverified`＋リンクは補助的な発見導線。
- ソース別コードは「URL/APIエンドポイント＋使う抽出器＋割引の正規表現ヒント」だけの薄いモジュールに（共通基盤が9割）。JS重めのサイトは Actions 上の Playwright で対応（常時サーバ不要、まず公式JSON APIを優先）。
- **アグリゲータは leads-only・転載しない（[[CLAUDE]] 準拠, 2026-06-21）**：Honolulu Magazine 等の編集リストは**選択・配列に薄い著作権**があるため丸ごと公開しない。`build.py` を二分割し、**公開 `data/deals.json` ＝一次情報/公式のみ**、**アグリゲータ由来は内部 `data/leads.json`（gitignore・非公開）** に出して一次確認の作業リストにする。各リードは公式サイトで裏取りできたものだけ `active` として公開。
- **二層アーキテクチャ（発見＝LLM/ローカル ＋ 更新＝決定論/クラウド, 2026-06-21）**：発見に不可避なLLM/検索を cron から分離。
  - **Tier1 発見（ローカル・週1/随時）**：スキル `makanapo-discover`（`.claude/skills/`）が WebSearch で新店の公式頁を探し、`pipeline/discover_add.py` で決定論検証 → **`data/sources.json`（設定＝データ）** に追記。人がレビュー。`deals.json` は書かない。
  - **Tier2 更新（GitHub Actions・毎日）**：`.github/workflows/build.yml` が `build.py` 実行 → `sources.json`＋パーサ群を巡回 → 期限/`last_verified` 再判定 → `deals.json` をコミット。LLM・秘密情報なし（依存は jsonschema のみ）。
  - **設定のデータ化**：巡回先は `data/sources.json` の `official_sites`（コード直書きをやめた）。Tier1が書き、Tier2が読む。独自HTMLのモール/オファー頁は従来どおり薄いパーサ（`ala_moana.py` / `waikiki_beach_walk.py`）。
  - これで「No LLM in the pipeline」を守りつつ発見も自動化（鍵はCIに置かない）。
  - 運用残：①GitHubへpush（Actions前提）②公開＋jsDelivr配信 ③発見スキルを随時実行。

---

## このキックオフ完了後の次ステップ（参考）

- GitHub Actions ＋ jsDelivr 静的配信の最小構成（`pipeline/build.py` → `data/deals.json` → CDN）。
- SwiftUI + MapKit でアプリ v1（閲覧専用・近くの割引・最終確認日表示・報告ボタン）。
- 詳細は [[SPEC]] §10 / [[CLAUDE]] "Immediate next actions"。

---

## Claude Code への一言サマリ

> 最小スキーマ v0 を作り、実データを2〜3件手で作って通し、その学びでスキーマを確定する。
> その後 50件まで収集して Go/No-Go を出す。スコープ（オアフ/ホノルル × 飲食・サービス、閲覧専用、PII非保持）と
> 収集の法務ルール（一次情報優先・転載しない・ログアウト・robots尊重）を厳守。判断に迷ったら [[SPEC]] / [[CLAUDE]]。
