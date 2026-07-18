# Live365 二本立て配信 + 地域別エディション設計

日付: 2026-07-18
状態: 承認済み(ブレインストーミング完了)
対象: makana.fm Webサイト(WordPress)+ makanapo iOSアプリ + データ配信(このリポジトリ)

## 1. 背景と決定事項

Live365 を新規契約し、既存 AzuraCast と二本立てにする。

| | Live365 | AzuraCast(既存) |
|---|---|---|
| 内容 | **全編成**(音楽+トーク+生放送) | 全編成から音楽入り番組を除いた**トーク編成**(+著作権フリー音楽) |
| 対象地域 | 北米(US/CA/MX = Live365ライセンス範囲) | 全世界(日本が主対象) |
| ライセンス | Live365込み(ASCAP/BMI/SESAC/SoundExchange等)+Live365側ジオブロック | 著作権フリーのみなので制約なし |
| 生放送 | こちらのみ | なし |

### UI方針(D案・承認済み)

- **プレイヤーは常に1本**。IPジオ判定した地域のチャンネルだけを表示し、もう一方は出さない(disabled表示もしない)。
- 枠組みは「別の局が2つ」ではなく「**同じ makana.fm の地域別エディション**」。
  - 北米: `🌺 HAWAIʻI` — "You're hearing our full Hawaiʻi program — music, talk & live shows."
  - その他: `🎙 TALK` — 「こちらの地域ではトーク編成をお届けしています。音楽・生放送を含む全編成はハワイを含む北米エリア限定です。」
  - 注記から「チャンネルについて」ページ(WP固定ページ、日英)へリンク。
- 検討済み代替案: A=2段ピル、B=タブ+1プレイヤー、C=カード2枚(いずれも「常にどちらかが死んだUI」になるため不採用)。モックは `.superpowers/brainstorm/6261-1784409782/content/`(gitignored)。
- 名称「World」は多言語放送に見えるため不採用。「Talk only for Japan」も英語として不自然なため不採用。ラベルは `TALK`。

### ジオ判定(方式A・承認済み)

- 目的は**UXの自然さ**(fail-open)。ライセンス執行はLive365側のジオブロックが担う。
- `GET https://speed.cloudflare.com/meta`(キー不要・CORS可)、タイムアウト1.5秒 → `country`。
- `country ∈ na_countries` → `NA`、それ以外・失敗・オフライン → `INTL`(Talk=全世界で合法な安全側)。
- Web: sessionStorageにセッション内キャッシュ。アプリ: UserDefaultsに最終判明地域を保存、初回オフライン時のみ米国・カナダ・メキシコの `America/*` タイムゾーンでNA推定。
- 不採用案: B=AzuraCast VPSに自前 `/geo`(GeoIP2)はサーバー構成管理が増える。C=タイムゾーンのみは精度不足。

## 2. データ契約 — `data/radio.json`(新設)

deals.json と同様に jsDelivr(`cdn.jsdelivr.net/gh/tanabe11/makanapo@main/data/radio.json`)で配信。
**`hawaii.enabled` が公開スイッチ**: Live365 開通日に `stream_url` を入れて `true` にする1コミットで Web/アプリ両方が切り替わる。それまで両者は現状と同一挙動。

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
    "hawaii": [
      { "days": ["fri"], "start": "17:00", "end": "19:00", "tz": "Pacific/Honolulu", "title": "Sunset Mele Hour", "live": true }
    ]
  }
}
```

- `schema/radio.schema.json` を新設し、CI(build.yml)で deals.json 同様にバリデーション。
- `schedule` は Hawaiʻi の番組名表示用(Live365にnow-playing公式APIがないため)。空配列でも動作。
- 将来 UK ライセンスアドオン購入時は `na_countries` に `"GB"` を追加するだけ。

### チャンネル選択(共有ロジック・純関数)

```
pick(region, channels):
  region == NA かつ hawaii.enabled → hawaii
  それ以外 → talk
```

再生失敗時(ジオ誤判定等)は talk へ自動フォールバック+小さく注記。

## 3. Web(WordPress)実装

- 成果物 = **貼り替え用の自己完結HTMLブロック1個**(現行カスタムプレイヤー `aloha-radio-player` の拡張)。プラグイン・サーバー変更なし。差し替え作業はユーザーがWP管理画面で実施。
- フロー: 地域判定(キャッシュ→API)→ radio.json取得 → `pick()` → ピル描画(ラベル+テーマグラデーション+地域注記+「チャンネルについて」リンク)→ 既存の再生/停止/スクロールはそのまま、`src` だけチャンネルの `stream_url`。
- 注記言語: NA=英語、INTL=日本語。
- 曲名: talk=現行AzuraCast APIポーリング / hawaii=radio.json `schedule` 照合(該当なしは "Live from Honolulu")。
- テーマ: talk=現行ゴールド→ティール / hawaii=サンセット系(オレンジ→ピンク→紫)グラデーション。
- 安全網: ジオAPI失敗→INTL。radio.json取得失敗→スニペット内ハードコードの現行AzuraCast設定(現状より壊れない)。hawaii再生失敗→talkへ自動切替+注記。

## 4. iOSアプリ実装

新規依存なし。`hawaii.enabled: false` の間は現行と同一挙動のため、Live365契約前にリリース可能。

| ユニット | 種別 | 内容 |
|---|---|---|
| `RadioConfig` | 新規 | radio.jsonモデル+ローダー。DealsStore方式(キャッシュ即表示→日次更新→オフラインキャッシュ) |
| `RegionResolver` | 新規 | 起動時ジオ判定+UserDefaults最終地域+初回オフライン時のタイムゾーン推定 |
| `ChannelDirector` | 新規 | `pick(region, config) -> Channel` 純関数。ユニットテスト主対象 |
| `RadioEngine` | 変更 | 固定URL → `play(url:)`。talk=HLS、hawaii=Icecast(AAC/MP3)直接再生 |
| `RadioHeader` | 変更 | チャンネルラベルチップ+地域注記1行+hawaii時サンセットグラデーション |
| 曲名/ロック画面 | 変更 | talk=現行ポーリング / hawaii=ICY timed metadata、fallback=schedule番組名 |
| `Localization` | 変更 | 注記・ラベルのEN/JA文字列追加 |

- 作法: **再生中は音を切り替えない**(設定・地域変化は次回再生時に反映)。hawaii再生失敗時のみtalkへ自動フォールバック+注記。
- テスト: ChannelDirector分岐 / configデコード / schedule照合(MakanapoTests)。

## 5. フェーズ計画

| Phase | 内容 | 担当 |
|---|---|---|
| 0 | Live365契約(Broadcast 1・月払い、7日トライアル)。局設定、ライブラリ、編成、ライブ配信テスト。Restrictionsはデフォルト(US/CA/MX)のまま | ユーザー(手順書で補助) |
| 1 | `data/radio.json` + `schema/radio.schema.json` + CI検証(hawaii.enabled=false) | 実装 |
| 2 | iOSアプリ実装→TestFlight→App Store提出(審査リードタイムのためWebより先。見た目現状同一) | 実装 |
| 3 | Web貼り替えブロック納品→ユーザーがWPで差し替え→現状同一を確認 | 実装+ユーザー |
| 4 | 「チャンネルについて」WP固定ページ(日英) | 実装+ユーザー |
| 5 | **切替日**: radio.json 1コミット(stream_url + enabled:true)→ 両面自動切替。AzuraCast編成をトーク+著作権フリーへ移行(前倒し可) | ユーザー+1コミット |

### Phase 0 トライアル中の確認事項
1. ストリームURL(Icecast)取得
2. 日本からのジオブロックの実挙動(エラーの見え方)
3. AVPlayerでの再生+ICYメタデータ取得可否
4. 広告(収益化オプション)の有無・挙動
5. 月払い→年払い切替可否をサポートに確認(ドキュメント上は「いつでもChange Package可・日割り調整」だが月/年切替の明記なし)

## 6. 検証

- ユニット: ChannelDirector等(アプリ)。WebはJS分岐を `pick()` 1関数に集約し、VPN実機確認でカバー。
- E2E: VPNで US/日本 切替 → 表示・再生・注記確認。ジオAPI遮断・オフライン → Talkフォールバック確認。
- 切替リハーサル: jsDelivrのブランチ指定URL(`@test-branch`)で本番同等の radio.json をフル動作確認してから本番コミット。
- jsDelivrキャッシュは最大〜12時間。即時反映が必要なら purge API。

## 7. 運用メモ

- TLH監視: Live365ダッシュボード月次確認。1,500 TLH ≈ 毎日1時間×50人。北米限定のため急増リスク小。超過は$0.05/時間で自動上位昇格。
- Live365料金(2026-07時点): Broadcast 1 = $59/月(年払いで2ヶ月分無料)。
- 在ハワイ日本人はTalk編成を聴けない → トーク番組のPodcast配信(サイト既存のPodcasts枠)で補完する方針。
- Live365仕様の根拠: ライセンス範囲・ジオブロック([Licensing coverage](https://help.live365.com/en/support/solutions/articles/43000573915-what-licensing-coverage-does-live365-provide-), [Stream Restrictions](https://help.live365.com/en/support/solutions/articles/43000533260-stream-restrictions))、サードパーティプレイヤー利用可([Share your Station](https://help.live365.com/en/support/solutions/articles/43000642760-live365-new-user-guide-share-your-station))、now-playing外部API無し([要望スレ](https://feedback.live365.com/suggestions/39219/enable-api-for-broadcaster-external-use))、料金([Pricing](https://live365.com/broadcaster/pricing))。

## 8. スコープ外(明示)

- ログイン・アカウント・お気に入り・通知(CLAUDE.mdのMVP方針通り)
- 手動チャンネル切替UI(要望が出たら検討。設計上は `pick()` の入力を増やすだけ)
- UKアドオン(将来 `na_countries` 1コミットで対応)
- Makanapō(ディール機能)への変更なし
