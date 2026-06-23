# Mac Mini セットアップ / 引き継ぎ手順

makanapo のローカル作業（特に **Tier-1 discovery**＝LLM+WebSearch）を Mac Mini で
続けるための手順。ブランド/設計は `SPEC.md` §9、開発規約は `CLAUDE.md`、生きた状態は
`STATUS.md` を参照。

---

## 0. 先に「いまの開発機」で push（最重要）
Mac Mini で clone する前に、**現在の開発機の未push コミットを origin に上げる**こと。
さもないと Mac Mini の clone が古いコードになる。
```
git push
```
- rejected されたら → 下の「8. push 衝突時」を実行してから再 push。

---

## 1. 前提ソフト（Mac Mini に入れる）
- **git**
- **Python 3.9+**（GitHub CI は 3.11）
- **`gh` CLI**（GitHub 認証 & push 用）
- **Claude Code**（discovery スキルは WebSearch が必要）
- （アプリをビルドするなら）**Xcode** ＋ `brew install xcodegen`

---

## 2. clone
```
git clone https://github.com/tanabe11/makanapo
cd makanapo
```

---

## 3. git push できるようにする（認証セットアップ）
HTTPS + `gh` の credential helper が一番簡単（SSH 鍵不要）。
```
gh auth login                                # GitHub.com → HTTPS → ブラウザ認証
gh auth refresh -h github.com -s workflow    # .github/workflows も push 可にする
git config user.name  "Junichi Tanabe"
git config user.email "tanabe11@gmail.com"
git config pull.rebase false                 # cron と衝突した時にマージ方式（divergent 回避）
```
確認:
```
git push            # 変更が無ければ "Everything up-to-date" と出れば成功
```

---

## 4. 依存と gitignore 再生成
```
pip install jsonschema            # 唯一の必須依存
python3 -m pipeline.core.build    # data/deals.json と data/leads.json を生成
```
gitignore されていて clone 後にローカル再生成が要るもの:
- `data/leads.json` / `data/leads/`（discovery の候補名ワークリスト。build で再生成）
- `data/preview.html`（`python3 -m pipeline.preview` で生成、`open` で閲覧）
- `.claude/settings.local.json`（ローカル設定）
- `app/*.xcodeproj`（`xcodegen generate` で生成）

---

## 5. 日次ジョブ（GitHub 側）= Mac Mini では何もしない
`.github/workflows/build.yml`（`build-deals`）が **毎日 15:17 UTC ≒ ハワイ 05:17** に
`deals.json` を更新して push。決定論のみ・LLM なし。手動実行は:
```
gh workflow run build-deals
gh run list --workflow=build-deals
```

---

## 6. 週1の discovery（ローカル LLM ジョブ）
**毎日は不要**（日次の鮮度は上の GitHub ジョブが担当）。新店追加は週1〜随時で十分。
1. リポジトリ内で **Claude Code を開く**
2. 「**makanapo discovery を回して**」と言う（`makanapo-discover` スキル起動）
3. スキルが: 候補選定 → WebSearch で公式URL → `discover_add` で決定論検証 →
   `data/sources.json` 追記 → `build` → `geocode_fill` → `build`
4. **差分を人がレビュー**: `git diff data/sources.json` と active 件数
5. 問題なければ:
   ```
   git add data/sources.json data/deals.json data/geocode_cache.json
   git commit -m "data: discovery batch ..."
   git push
   ```
6. jsDelivr 反映（下記 7）
- 頻度目安: active 50 到達まで週2〜3回、到達後は月1程度。

---

## 7. jsDelivr 反映（push 後すぐ見たい時）
```
curl "https://purge.jsdelivr.net/gh/tanabe11/makanapo@main/data/deals.json"
```
確認（43件等になっているか）:
```
https://cdn.jsdelivr.net/gh/tanabe11/makanapo@main/data/deals.json
```
パージしなくても最大〜12h で自動反映。アプリ側は再起動 or メニュー「再読み込み」で取得。

---

## 8. push 衝突時（"fetch first" / divergent branches）
日次 cron が先に `data/deals.json` を commit しているのが原因。`deals.json` は生成物なので
**マージ → sources.json から再生成 → 確定** で解決:
```
git fetch origin
git merge origin/main --no-edit
python3 -m pipeline.core.build          # deals.json を再生成して衝突解決
git add data/deals.json && git commit --no-edit
git push
```
（`git config pull.rebase false` 済みなら `git pull` でもマージされる。）

---

## 9. アプリのビルド（任意）
```
cd app && xcodegen generate
# Xcode で開き、iOS Simulator（iPhone 17 等）を選んで ⌘R
# 実機: Signing & Capabilities で自分の Apple ID(Personal Team) を選び実機を選択して ⌘R
# テスト: ⌘U（Deal/Store/NowPlaying/Filter/Localization/Smoke）
```

---

## クイックリファレンス（よく使う）
```
python3 -m pipeline.core.build     # deals.json 再生成（検証込み）
python3 -m pipeline.geocode_fill   # 座標補完（Nominatim, ローカルのみ）
python3 -m pipeline.stats          # active/unverified/expired 集計
python3 -m pipeline.preview        # data/preview.html 生成
gh workflow run build-deals        # 日次ジョブ手動実行
```
