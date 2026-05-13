# 3D Box Packing Optimizer

複数の段ボール箱をラップで一体化して発送する前提で、  
配置を最適化して「最終サイズ」を最小化するアプリです。

現在は `佐川モード` のみ実装しています。

- 制約1: 最長辺 `<= 90cm (900mm)`
- 制約2: サイズ区分 `<= 160`
- 目的: 上記制約の中でサイズ区分を最小化
- 160サイズを超える場合は、自動で複数便に分割

## 1. セットアップ (Windows / VS Code)

```powershell
cd <project-root>
pip install -r src\box_packing\requirements.txt
```

## 2. GUI 実行

```powershell
python src\box_packing\gui.py
```

箱種類ごとに数量を入力し、`最適化して可視化` を押してください。  
出力HTMLには、箱の境界線と色分け、最終サイズが表示されます。  
複数便になった場合は `..._parcel01.html`, `..._parcel02.html` のように分割保存されます。
`カスタム箱（任意）` は最大4種類まで追加できます。

## 3. CLI 実行

```powershell
python src\box_packing\app.py --counts "50=2,60=1,100=1" --output outputs\box_packing_result.html
```

`--counts` は次の2形式に対応しています。

- `50=2,60=1,100=1`
- `{"50":2,"60":1,"100":1}`
  
CLIでは固定箱の個数入力のみ対応しています。  
カスタム箱（最大4種類）の入力は GUI / Webアプリ で利用してください。

## 4. Webアプリ（Streamlit）

```powershell
streamlit run src\box_packing\web_app.py
```

ブラウザで表示されたURLを開くと、固定箱・カスタム箱を入力して最適化できます。  
スマホで使う場合は、PCと同じWi-Fiに接続して、表示されたローカルIPのURLへアクセスしてください。
Webアプリでもカスタム箱は最大4種類まで入力できます。
終了する場合は、実行したターミナルで `Ctrl + C` を押してください。

## 5. 入力箱サイズ（mm）

- 50: `(180, 210, 112)`
- 60: `(185, 240, 150)`
- 70: `(220, 310, 145)`
- 80: `(310, 220, 230)`
- 80_medium: `(310, 220, 190)`
- 80_small: `(310, 220, 100)`
- 100: `(290, 380, 300)`
- 100_medium: `(290, 380, 200)`
- 100_small: `(290, 380, 100)`
- 120: `(400, 540, 250)`

## 6. テスト

```powershell
pytest -q -p no:cacheprovider src\box_packing\test_optimizer.py
```
