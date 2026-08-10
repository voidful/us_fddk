# 美股短線 Form 4 內部人同期買入事件診斷協議（Round 53）

凍結時間：`2026-08-10T13:08:49Z`

狀態：**事前凍結、aggregate-only event study。** 本輪只檢驗「同一 issuer、同一披露日有
多個合資格 Form 4 purchase」是否有可重測的短窗相對回報，不建立策略、Paper 或實金行動。

## 1. 資料與不可變綁定

- Form 4 來源固定沿用 Round52 的 82 季 SEC ZIP（2006Q1–2026Q2），manifest SHA-256
  `b7e1b42923cee0ef2079494f2004c56f41976899e98d1f4352b990517bb9af85`。
- Round52 aggregate validation SHA-256 固定為
  `36768ac8cd6f5b4435d9b2a90c9c2c6761bb4c3498e6eb58a6dead54977e23f0`；只可重新解析相同
  source bytes，不可改篩選條件或補回被丟棄的 row identifiers。
- 行情固定為 `snapshot_20260731_6a7ca6b8.zip`，archive SHA-256
  `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b`，panel SHA-256
  `6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66`。只承認 adjusted
  OHLCV；不得稱為 raw execution price 或完整總回報賬本。
- watchlist 固定 30 檔現時大型股，SHA-256
  `b6002e4e151bd298884f8cdd6272b5cbfde8aedca47cb58b92830d4d92028014`；它不是歷史
  point-in-time membership，整輪結果必須標示 survivorship-biased。
- SEC `company_tickers.json` 固定 bytes `795627`、SHA-256
  `6dd9c4363c5a95d43f4d8e8f8279f9ae6538d10d295bbdeebe5a433ec954bf6d`，只作 current CIK
  對照；不可用模糊名稱或人工修正歷史代號。

## 2. 固定事件定義

沿用 Round52 的 purchase row gate：`DOCUMENT_TYPE=4`、`TRANS_FORM_TYPE=4`、`TRANS_CODE=P`、
`TRANS_ACQUIRED_DISP_CD=A`、swap 明確為 false、shares／price 為正且有限、owner relationship
 包含 Director、Officer 或 TenPercentOwner。

同一 issuer／filing day 成為事件，必須同時符合：

1. 至少 2 個不同 purchase accession；
2. 這些 accession 的 reported purchase notional 合計至少 US$100,000；
3. 事件可用 deterministic symbol mapping：優先使用 as-filed trading symbol exact；若沒有，
   只接受 current CIK exact 且該 CIK 對應 watchlist 恰好一個 symbol；多 symbol CIK 一律列為
   ambiguous 而排除；沒有 fuzzy match。

同一 issuer 的相鄰披露日視為不同事件；重疊持有期保留，因本輪是 event-level mechanism
diagnostic，不把事件拼成可落盤的資金曲線。

## 3. 成交時鐘、持有期及 baseline

- Form 4 filing date 不假設有可稽核的盤中公開時間；訊號採保守的一個完整 XNYS session lag。
- 入場為 filing date 後第一個可用 XNYS session 的 adjusted Open；退出為其後第 5、10、20
  個可用 session 的 adjusted Close。
- 每個事件組合扣來回 20 bps；主要 horizon 固定為 10 sessions，5／20 只作事前固定的
  robustness readout。
- 同日 baseline 使用相同 entry／exit dates：current complete cohort 等權、當日有有效價格的
  current watchlist 等權、SPY 及 QQQ；所有 baseline 使用相同成本口徑。
- 只報 aggregate event counts、分布統計及 gates；不得輸出 ticker、symbol、CIK、accession、
  filing date、issuer、owner 或 notional。

## 4. 固定 gate 與 multiplicity

主要 10-session horizon 必須先通過以下 6 項才可稱為「診斷線索」：

1. 至少 30 個完整事件；
2. 相對同日 eligible-pool 等權平均差大於 0；
3. Newey–West mean test `t >= 1.96`；
4. 2,000 次、block size 8 的 moving-block bootstrap 95% 下界大於 0；
5. 配對勝率大於 50%；
6. 前／後固定十年相對 eligible-pool 平均差均大於 0。

全域 trial ledger 由既有 Round51 lower bound `6290` 追加本輪固定 5／10／20 三條 path，
最低下限為 `6293`；不得因結果改 horizon、cluster threshold、成本或 mapping。

即使 6/6 通過，本輪仍只授權合資格 point-in-time security-master 上的原樣重測；
`performance_present=false`、`paper_authorized=false`、`real_money_authorized=false`、
`real_money_action_usd=0` 及 `today_action="今天不下單"` 必須保持不變。

## 5. 研究邊界

現時 watchlist 倒推、current CIK mapping、adjusted OHLCV、filing-date clock 及缺乏退市／
公司行動賬本，使本輪不能證明可交易 alpha。正面結果只可寫成「值得以 point-in-time 數據
重測」；負面結果寫入研究 log，不可用再調參救援。網站只展示已驗證、可執行策略；本輪
永遠不產生行動建議或 Paper 持倉。

固定輸出：

- protocol receipt：`artifacts/short_term_form4_event_diagnostic_protocol_receipt.json`；
- validation log：`artifacts/short_term_form4_event_diagnostic_validation.json`；
- report：`docs/SHORT_TERM_FORM4_EVENT_DIAGNOSTIC_REPORT.md`。

本協議是研究與教育紀錄，不構成投資建議、Paper 成交或實金落盤指令。
