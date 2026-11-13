# 楽天市場のAPI連携設定（PREMIUM PULSE）

この連携は**未接続**です。コードは実装済みですが、楽天市場の実データを取得するには利用者本人によるアプリ登録とGitHub Actionsのシークレット登録が必要です。

1. 楽天ウェブサービスでアプリを登録します: https://webservice.rakuten.co.jp/
2. 楽天市場商品検索API（2026-07-01）のアプリID（Application ID）とアクセスキー（Access key）を確認してください: https://webservice.rakuten.co.jp/documentation/ichiba-item-search
3. GitHubの `yujimyzk/premium-pulse` → **Settings** → **Secrets and variables** → **Actions** → **New repository secret** から次の2件を登録してください。
   - `RAKUTEN_APP_ID` = Application ID
   - `RAKUTEN_ACCESS_KEY` = Access key
4. **Actions** → **Daily Yahoo Shopping candidate collection** → **Run workflow** または翌日の定期実行で取り込みます。
5. `data/rakuten_candidates.json` に `status: unverified_candidates` が入り、`compare.html` に「楽天市場」の実測候補が表示されたら連携済みです。

**シークレットをチャットやGitHubのソースコードに貼らないでください。**

楽天APIはアプリIDとアクセスキーを両方必要とします。アクセスキーはHTTPヘッダーとして送信し、処理ログに値を出さない設計です。鍵が未設定の場合は楽天の収集処理をスキップし、Yahoo!の既存収集を継続します。

**重要:** 取得した楽天価格は商品の販売希望価格です。成約価格ではありません。楽天のAPI検索はサイズ・商品状態の完全一致を保証しません。画像は公式APIが返すURLのみを表示し、画像ファイルを保存しません。掲載画像およびAPIデータの利用規約を確認し、規約に従って運用してください。

## 運用・障害時の注意

- APIの利用上限やエラーがある場合、楽天の連携処理が失敗することがあります。
- 現行ワークフローは連携時のAPIエラーで失敗する設計です。失敗した場合はGitHub Actionsの実行ログを確認し、必要なら楽天のシークレット設定を外してください（古い楽天データは `compare.html` に残るため日付を必ず確認してください）。
- 仕入れ判断には商品URL・サイズ・状態・送料・真贋の確認を必須とし、サイト上の価格だけを根拠に売買を決めないでください。
