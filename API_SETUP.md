# Yahoo!ショッピングの公式APIとの連携

[商品検索API v3](https://developer.yahoo.co.jp/webapi/shopping/v3/itemsearch.html) のClient IDが必要です。

1. Yahoo!デベロッパーネットワークで利用条件を確認して Client ID を取得
2. GitHub の `Settings → Secrets and variables → Actions → New repository secret` を開く
3. Name: `YAHOO_SHOPPING_APP_ID`、Secret: Client ID を入力（チャットには貼らない）
4. Actions → Weekly Yahoo Shopping candidate collection → Run workflow でテスト
5. 毎週月曜9:35 JSTに候補を収集（API障害などの場合は失敗し得る）

重要：取得する価格は「Yahoo!ショッピングの出品価格」であり「メルカリ・ヤフオクの成約価格」ではありません。`data/review_candidates.json` は確認待ちの一覧です。型番が一致しても、サイズ・状態・商品同一性・税区分は人間の確認が必要です。確認前にサイトの価格ランキングへ自動公開しません。

必要なAPIキーを設定するまで、自動収集は行われません。無許可のスクレイピングは使用しません。
