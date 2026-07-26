# backup/ — 入稿に使わないファイル

`img/card/print/` を「アップロードする 3 つの PDF だけ」にするため、それ以外をここへ移した。
消してはいない。元のパス構造をそのまま保っているので、戻すときは `backup/` を外すだけ。

| 移したもの | 理由 |
|---|---|
| `img/card/print/*_bleed_600dpi.png` | 入稿 PDF と同じ内容の PNG。FedEx には PDF を出すので不要 |
| `img/card/print/*_trim_600dpi.*` | 塗り足しなしの仕上がりサイズ。画面確認用で入稿には使えない |
| `img/card/front_v1.png` / `back_v1.png` | 初期のモックアップ。**QR がダミー柄**で、レイアウトも現行と違う |
| `img/card/logo_blue.png` | 縦並びロックアップ。表面は横並びに変わったので未使用 |
| `img/card/logo_h_white.png` | 横並びの白抜き版。裏面は縦並びを使っているので現状未使用 |
| `img/card/logo_h_native.png` | 原本の青 `#2668A5` 版。ブランドカラー未確定のため保留 |
| `img/card/qr/*` | Canva に貼る想定で作った QR。`tools/render_card.py` は自前で QR を描くので不要 |

## 移していないもの

`tools/render_card.py` が読む入力と、ブランドの原本は元の場所に残してある。

- `img/card/logo_h_blue.png` — 表面のロゴ
- `img/card/logo_white.png` — 裏面のロゴ
- `img/logo.png` — ユーザー提供の横並びロゴ原本
- `img/makana_fm.jpg` — アプリアイコンの原本（`CLAUDE.md` が参照）
