# 美股短線第 42 輪：Form 4 admission feasibility schema 修訂 v1.1

FrozenAt：`2026-08-09T23:39:35Z`

狀態：**在 root SEC 真實擷取 0、真實樣本選擇 0、候選選擇 0、策略運行 0、績效結果 0
時，按三個固定季度完整八表 schema diff 追加凍結。** v1.0 協議與收據永久保留；只有下列
metadata-to-physical header 規則與 v1.0「精確相同」有衝突時，以 v1.1 為準。

## 1. 唯一合法 metadata-to-physical 轉換

先按 v1.0 找出唯一可解析 W3C Table Group metadata JSON，並由 `tables[].url` 一對一解析八個
required TSV role。對每個 role，按 metadata `tableSchema.columns[].name` 建立 column list；
不得按未證實檔名找 metadata，也不得略過 v1.0 的 required anchors。

physical TSV header 只可由 metadata list 套用以下固定轉換後得到：

1. `SUBMISSION.tsv`：metadata 中
   `ISSUERTRADINGSYMBOL, CONTACT_NAME, CONTACT_PHONE_NUMBER, CONTACT_EMAIL_ADDRESS,
   NOTIFICATION_EMAIL_ADDRESS, REMARKS` 必須是連續且各出現一次。physical 只可省略精確四個
   contact 欄，成為 `ISSUERTRADINGSYMBOL, REMARKS`；其他欄名稱及相對次序完全相同。
   `2006Q1`、`2016Q3` 是 metadata 17／physical 13 欄；`2026Q2` 是 18／14 欄，且
   `AFF10B5ONE` 在共同序列中原位保留。
2. `NONDERIV_TRANS.tsv`：metadata 第 12 欄（1-based）必須精確為
   `EQUITY_SWAP_INVOLVED_FN`，physical 同一位置只可一對一命名為
   `EQUITY_SWAP_TRANS_CD_FN`；兩邊均為 28 欄，其他欄完全相同。
3. `DERIV_TRANS.tsv`：metadata 第 14 欄（1-based）必須精確為
   `EQUITY_SWAP_INVOLVED_FN`，physical 同一位置只可一對一命名為
   `EQUITY_SWAP_TRANS_CD_FN`；兩邊均為 42 欄，其他欄完全相同。
4. `REPORTINGOWNER.tsv`（13）、`NONDERIV_HOLDING.tsv`（14）、`DERIV_HOLDING.tsv`（26）、
   `FOOTNOTES.tsv`（3）及 `OWNER_SIGNATURE.tsv`（3）：括號是 metadata 與 physical 的精確
   欄數；名稱與次序必須逐欄相同。

這不是一般 alias、subset 或 fuzzy schema policy。四個 contact 欄只可在 `SUBMISSION.tsv`
以同一連續位置 metadata-only；swap footnote 只可在兩個 TRANS table 的指定位置作上述單一
名稱映射。任何其他 metadata-only、physical-only、rename、重排、重複、大小寫或欄數差異
一律 fail closed。

## 2. 固定 physical header profiles

header profile SHA-256 的 canonical bytes 固定由實體 TSV header column names 以單一 tab
連接、UTF-8 encode，無 BOM、無尾端 tab、無 CR/LF。三季只可接受：

| role | physical columns | header SHA-256 |
|---|---:|---|
| `DERIV_HOLDING.tsv` | 26 | `180196c439a7a44ae2247e8b2d08dc06b95db6f6792d1c1c0ad367675b182912` |
| `DERIV_TRANS.tsv` | 42 | `64ef5f035ba21fb584ae90cf546a2afc8a991b14b96656ac66e610a1f4bd4b47` |
| `FOOTNOTES.tsv` | 3 | `4c358cdc3d7456a66e132cdd8740cdcd1c19f97d3b90889ad6bff2ce9a97dd59` |
| `NONDERIV_HOLDING.tsv` | 14 | `691699ed184faed63867f73cba35d61db8f2dd21f6779097033ca26f5ee4f0e6` |
| `NONDERIV_TRANS.tsv` | 28 | `f5f4cfa029702a8ff657882a49eb38b57f6433d2719c2526b92537ca22b16699` |
| `OWNER_SIGNATURE.tsv` | 3 | `d236922d787c52488d3a3830828b78080cfb0e284f16237b2be22d87f79ce4ed` |
| `REPORTINGOWNER.tsv` | 13 | `51771f82d1594503ad7c77e775f617a331bfadf32a0852989aba3f59b4867e31` |
| `SUBMISSION.tsv`（2006Q1／2016Q3） | 13 | `a7c83d3cb724ad0e9e11511039782ae5fc4398abc876ba5572eda171dff26399` |
| `SUBMISSION.tsv`（2026Q2） | 14 | `5e9bc2a969fe9a9b4100a4740e49f241faad5d3342d03c670d17eb7a7c979ca3` |

轉換後 list、physical list、column count、required anchors 及相應 profile SHA 必須同時通過；
profile hash 不可取代逐欄 diff，也不可用其中一季的 profile 接受另一季。

## 3. 固定攻擊、停止與狀態邊界

新增 stable errors：`form4_feasibility_contact_omission_mismatch`、
`form4_feasibility_swap_footnote_alias_mismatch`、
`form4_feasibility_physical_header_profile_mismatch` 及
`form4_feasibility_unexpected_metadata_physical_drift`。任一錯誤即
`stopped_no_admission_claim`；不得刪欄至通過、用 metadata header 取代 physical header、允許
任意 alias、換季度或重選 accession。

本修訂只令 schema 驗收忠於官方 bytes，不代表任何 Form 4 gate 已通過。freeze 時仍為
Form 4 admission `0/16`、global trials 下限 `6,287` 且本輪 increment `0`、authorized real
rows 0、root real fetch 0、real sample selection 0、candidate selection 0、strategy run 0、
performance false；Paper 未授權且全現金、real money 未授權且 US$0。**今天不下單。**
