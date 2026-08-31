# 美股短線第 49 輪：Form 4 歷史事件可行性診斷協議

FrozenAt：`2026-08-10T11:17:30Z`

狀態：**result-blind、historical-diagnostic-only。** 本協議在讀取三個已封存 SEC
季度檔的事件數、cluster 數或任何股票回報前固定。它只判斷固定 Form 4 多內部人買入規則
是否有足夠事件，值得日後另立正式、point-in-time 歷史回測；不計回報、不選股、不建立
Paper Trading（模擬交易）或實金落盤。任何結果只寫入研究 log，不顯示於公開決策頁。

## 1. 與既有研究的邊界

Round 46 是獨立的 prospective first-seen family，必須由有效 monitor start 後逐日累積，
季度 ZIP、歷史 filing date 或今天重新取得的檔案不能成為它的 known-at 證據。Round 49
不得修改、救援或縮短 Round 46 的 504 sessions／100 round trips／50 issuers 門檻，亦不得
用本輪事件數、人物、股票或歷史結果調整 Round 46 參數。

本輪亦不是 alpha trial：沒有市場價格、benchmark return、績效估計量或參數比較，因此
不增加現有 global trial lower bound `6,295`。若事件率足夠，正式歷史回測必須在第一次讀取
point-in-time 行情前另行凍結、另行登記 comparison family；本輪結果不得直接升格。

## 2. 固定資料及來源限制

唯一可讀 real-data input 是先前已收集、現在只作離線 replay 的三個 SEC Insider
Transactions quarterly ZIP：

| quarter | filename | bytes | SHA-256 |
|---|---|---:|---|
| 2006Q1 | `2006q1_form345.zip` | 17,306,804 | `62becdadbe5eaff68f03edefe2ba2357c8bb498a1f825b697003e087cf98e6ce` |
| 2016Q3 | `2016q3_form345.zip` | 8,704,557 | `5a25d3c6cb874875904b2be0059bb4784e4da28b315af30b15568fd250bd0dde` |
| 2026Q2 | `2026q2_form345.zip` | 11,498,860 | `11f1b2bbbdcbe6347a34437c02d04202fda0eca1dbb023726e4b56504b802e27` |

三季是事前固定的 early／middle／recent schema anchors，不是連續 20 年樣本，不能外推年化
交易數或盈利。不得換季度、補抽季度或按事件多少重選。這一輪不發出任何 SEC request，
不讀原始姓名、地址作因子，亦不持久化 ticker、CIK、accession 或 reporting-owner identity。

SEC 季度檔是 as-filed flattened data，可能有申報錯誤、重複、不一致及後續修訂，亦缺少
部分 EDGAR metadata。`FILING_DATE` 只有日期精度，不是盤中 public timestamp。故本輪最多
能證明資料解析及事件率可行，不能證明 contemporaneous known-at、可成交 universe 或 alpha。

## 3. 固定 ZIP 及 schema 驗證

每檔必須先通過：

1. input bytes 與上表長度、SHA-256 精確一致；
2. quarter ID 精確符合檔名及 `SUBMISSION.FILING_DATE` 的季度；
3. ZIP member 不可重複、絕對路徑、`..`、反斜線或 percent-encoded alias；
4. CRC、總解壓上限、單檔上限及 compression-ratio 上限通過；
5. 精確一份 W3C Table Group metadata，八個官方 table role 齊全；
6. 沿用 Round 42 v1.1 已凍結的 physical-header projection 及 header SHA；
7. `SUBMISSION.tsv`、`REPORTINGOWNER.tsv`、`NONDERIV_TRANS.tsv` 每列欄數一致、key 唯一，
   所有 child accession 必須存在於 submission denominator。

任一失敗整個季度停止；不得跳列、猜欄名、接受 fuzzy alias 或用 pandas 自動型別修補。

## 4. 固定合資格買入列

一個 purchase transaction 必須同時符合：

- `SUBMISSION.DOCUMENT_TYPE == "4"`；`4/A` 只計入 excluded amendment 數，不加入事件；
- `NONDERIV_TRANS.TRANS_FORM_TYPE == "4"`；
- `TRANS_CODE == "P"`，只稱 `open_or_private_purchase`；
- `TRANS_ACQUIRED_DISP_CD == "A"`；
- `EQUITY_SWAP_INVOLVED` case-insensitive 精確為 `0` 或 `false`；空白視為未知並排除；
- `TRANS_SHARES`、`TRANS_PRICEPERSHARE` 是 finite、正 base-10 Decimal；
- reporting-owner relationship 以逗號切開後，至少有一個 exact token 為
  `Director`、`Officer` 或 `TenPercentOwner`；`Other` 或
  `TenPercentOwnerOther` 不作 substring 命中。

同一 `(ACCESSION_NUMBER, NONDERIV_TRANS_SK)` 必須唯一。每個 accession 的
`reported_purchase_dollars` 是其合資格 transaction 的 `shares × filed price` 精確總和；
不能因一份 filing 有多位 reporting owners 而重複計算 notional。owner 只用 distinct
`RPTOWNERCIK` 計數，不假稱已驗證資本集團獨立性。

## 5. 固定 cluster 狀態機

每個 issuer 在單季內按 `(filing_date, accession)` 排序；同一 filing date 的 accession
必須一次加入，避免 accession 排序改變成案結果。維持未 consumed 的 20 calendar-day
inclusive window `[D-19, D]`。只有在 D 加入完所有 filing 後，cluster 才可第一次跨門檻：

1. 至少兩份 distinct accessions；
2. 至少兩個 distinct reporting-owner CIK；
3. 每份 accession `reported_purchase_dollars >= US$10,000`；
4. cluster 去重總額 `>= US$100,000`。

成案後 window members 全部 consumed，issuer 進入至 `D + 20 calendar days`（inclusive）的
診斷 cooldown。cooldown 內新事件保留；首次在 cooldown 後有 filing 時，先移除超出新
20-day window 的事件，再評估。這只是無行情的 event-rate proxy；Round 46 的 XNYS-session
cooldown、量價確認及成交時鐘不由本輪替代。

由於每季獨立，quarter start 後首 19 calendar days 是 left-truncated；其成案候選一律不計入
primary cluster count，只記 `left_boundary_excluded`。quarter-end cluster 可計入，因其成案
只依 D 之前資料；但不得跨季延續 cooldown 或 window。

## 6. 固定輸出及成功條件

公開／versioned validation receipt 只可包含：

- 每季 ZIP hash 驗證、row counts、Form 4 submission denominator；
- 4/A、非 P、非 A、swap unknown/true、非正／缺價量、角色不合格等 aggregate exclusions；
- 合資格 purchase accessions、raw gate crossings、left-boundary exclusions、primary clusters；
- distinct owner count、accession count、notional 的 bucketed distribution，不含 exact values；
- parser/schema／determinism／privacy attacks 的 pass/fail；
- `performance_present=false`、`promotion_authorized=false`、`paper_authorized=false`、
  `real_money_action_usd=0`、`today_action="今天不下單"`。

不得輸出或 hash 低熵 identifier set、ticker、issuer、姓名、CIK、accession、精確 filing date、
逐筆 notional、候選名單或任何可逆映射。完整解析列只存於 process memory，結束後丟棄。

本輪唯一診斷成功條件：三個固定 ZIP 全部可決定性解析、所有攻擊拒收、privacy scan 通過，
且三季合計至少 `30` 個 primary clusters。門檻是資料量 feasibility，不是盈利門檻；即使通過，
輸出仍只能是 `historical_backtest_preregistration_warranted`，不能稱策略成功。低於 30 則
`insufficient_event_rate_no_historical_backtest`，不得放寬 window／owner／US$ 門檻。

## 7. 若日後另立正式歷史回測

只有本輪成功才可另立新協議；正式協議至少必須固定：

- 全部 2006Q1 至最新完整季度、相鄰季度連續狀態及原始申報抽樣覆核；
- point-in-time security master、退市、公司行動、raw open／close／volume 及 XNYS calendar；
- filing date 只能保守映射為其後第一個完整 XNYS decision close，再於下一 session raw open
  成交；沒有同日成交；
- D 日正回報、成交額高於 prior-20 median、price > US$5、prior-20 ADV >= US$20m、
  252 sessions、最流通股份類別等 Round 46 gates；
- D+10 close 退出、十個 10% slots、空槽 QQQ、D+20 XNYS cooldown；
- 10／25／50 bps per actual leg，QQQ→股票→QQQ 四腿全收；
- QQQ、SPY、PIT equal-weight、single-owner、price-volume matched、non-signal-code 及
  issuer-month permutation controls；
- global trial lower bound 至少 6,295、moving-block bootstrap、Holm／max-t、DSR、分段及
  成本壓力；current-survivor universe 或 adjusted-close-only 結果永久不可升格。

## 8. 必須拒收的攻擊

Tests 至少覆蓋：wrong hash／quarter、bad ZIP／CRC、path traversal、duplicate member、缺 metadata、
缺／多 table、header drift、row-width drift、duplicate／unknown accession、duplicate transaction key、
錯 form／code／A-D、blank／true swap、NaN／Infinity／零／負 shares 或 price、substring role、
同 accession 假兩人、同 owner 假兩 accession、notional 重複、同日輸入順序漂移、20-day 邊界、
cooldown 邊界、left truncation、identifier 出現在 receipt、任何 performance／Paper／實金欄位解鎖。

任一失敗只產生 stable `form4_history_*` error 或 fail-closed aggregate receipt；不得局部續跑。
