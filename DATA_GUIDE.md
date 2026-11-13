# 価格データの追加手順

`data/verified.csv` に**証拠を確認した観測データのみ**を入力します。データ取得は手動またはサービス規約に基づく正規APIに限ります。

| 列 | 入力例 | 注意 |
|---|---|---|
| id | nike-model-27-20261113 | 1行ごとに一意 |
| name / brand / sku | Nike Model / Nike / ABC123 | 商品の正式名称と品番 |
| size_cm | 27 | cm表記で統一 |
| condition | new または used | 新品／中古 |
| price_type | listing または sale | 出品希望額／成立価格 |
| tax_basis | tax_included または tax_excluded | 定価と観測価格の税込税抜を統一 |
| retail | 20000 | 定価（円、整数） |
| observed_price | 30000 | 観測された同サイズ・同状態の価格（円） |
| prior_price / prior_checked | 28000 / 2026-11-01 | 同一モデル・サイズ・状態・価格種別・税込税抜の場合のみ入力 |
| retail_source | https://... | 定価の根拠ページ |
| source | https://... | 観測価格の根拠ページ |
| checked | 2026-11-13 | 価格確認日 |
| note | 27cmの新品未使用 | 取引条件に関する補足 |

**重要**：過去価格の単純な比較は「同一条件での個別観測の差」であり、相場全体の上昇率ではありません。送料・手数料・状態・真贋・市場流動性を考慮した利益予測には使用しません。出品価格と成約価格はランキングで別々に区別し、定価比は売却益の保証ではありません。

`python update.py` を実行すると入力チェックの後 `data/latest.json` が再生成されます。空のままでも動作します。毎週のGitHub ActionsはCSVを検証して再生成するだけで、外部サイトから価格を取得しません。
