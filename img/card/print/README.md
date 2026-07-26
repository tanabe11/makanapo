# FedEx Office にアップロードするファイル

このフォルダにある **3 つの PDF がそのまま入稿ファイル**。ほかは何もない。

| ファイル | 中身 |
|---|---|
| `card_johnny_front_bleed_600dpi.pdf` | Johnny 表 |
| `card_colleen_front_bleed_600dpi.pdf` | Colleen 表 |
| `card_back_bleed_600dpi.pdf` | 裏（**2 名共通**） |

- **3.75 × 2.25 in / 600 dpi** — FedEx Office 指定の塗り足し 1/8 in 込み。仕上がりは 3.5 × 2 in。
- 注文時は **Quick Business Cards → 「自分のファイルをアップロード」**。テンプレートから作り直すと寸法が崩れる。
- **紙はマット。グロスと盛り上げ印刷（raised print）は選ばない** — どちらも QR の読み取りを妨げる。

## 刷る前に必ず確認すること

1. **QR 3 つを実物でスキャン**する。中身は目で読めないので、刷り上がるまで間違いに気づけない。
2. マーク下の小さい `makana.fm`（**1.27 mm**、印刷下限割れ）が潰れていないか。
3. 裏面の濃い青が、表の白い面に透けていないか（100 lb は薄めの紙）。

## 作り直し

`python3 tools/render_card.py` で再生成する（`segno` と `Pillow` が要る）。
文言・URL・サイズは `tools/render_card.py` の `PEOPLE` と定数にまとまっている。

過去の版・プレビュー用・未使用の素材は `backup/` に移してある。
