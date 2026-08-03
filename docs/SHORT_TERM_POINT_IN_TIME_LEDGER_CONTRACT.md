# 短線個股第九輪：Point-in-time／退市賬本合約 v1.0

凍結日期：2026-08-04（亞洲／台北）

狀態：`frozen_before_first_authorized_provider_import`

## 目的與邊界

本合約是美股短線個股研究的數據硬閘門，不是新策略、選股名單或盈利承諾。正式回測仍
沿用已凍結的 [`SHORT_TERM_HIGH_RETURN_PROTOCOL.md`](SHORT_TERM_HIGH_RETURN_PROTOCOL.md)
v1.1：月末以 12–1、6–1、200 日趨勢及 63 日波幅排序，下一交易日開市等權買入 Top-10；
台股參考訊號只保留事前已定義的 20 日動量／60 日趨勢 Top-7 固定持有期診斷。

在本合約全部通過前：

- 個股 20 年結果不得稱為無存活者偏差回測；
- 不顯示可執行個股名單；
- 短線 Paper 維持全現金，不回填歷史成交；
- 實金落盤及新增資金均為 US$0。

## 可接受來源

只接受使用者已合法取得、且授權容許本專案本地研究的 point-in-time 來源。數據必須同時
回答歷史指數成分、退市回報、公司行動及歷史分類；只提供今日仍存在股份、只提供現時
代號，或把免費歷史名單與殘缺價格拼接的數據一律拒收。本專案不會自行購買訂閱、繞過
登入、公開再分發受限制原始數據，亦不把供應商名稱當成數據完整性的替代證據。

## 固定輸入包

供應商轉換層須輸出一個唯讀目錄，包含 `manifest.json` 及下列 UTF-8 CSV。日期均為
`YYYY-MM-DD`；時間均為帶 UTC offset 的 ISO-8601；金額以 USD；空白只能出現在欄位表
明示容許的位置。

### `security_master.csv`

| 欄位 | 要求 |
|---|---|
| `security_id` | 不隨代號、交易所或公司名稱改變的永久證券 ID；唯一、非空 |
| `company_id` | 永久公司 ID；非空 |
| `security_type` | 本輪只接受 `common_stock` |
| `share_class` | 股份類別；可用 `single`，但不可空白 |
| `country_of_incorporation` | ISO alpha-2；本輪固定 `US` |
| `currency` | 固定 `USD` |

### `identifier_history.csv`

| 欄位 | 要求 |
|---|---|
| `security_id` | 必須存在於 master |
| `ticker`、`exchange` | 當期可交易代號與上市地；非空 |
| `cusip`、`isin` | 可空白，但兩者不可同時空白 |
| `effective_from`、`effective_to` | 半開區間 `[from, to)`；現行記錄的 `to` 可空白 |
| `known_at` | 該映射最遲可知時間；不得晚於 `effective_from` |

同一證券的代號區間不得重疊；同一交易日同一 `ticker + exchange` 亦不得指向兩個證券。
研究以 `security_id` 連接，絕不以今天的 ticker 倒填歷史。

### `membership_history.csv`

| 欄位 | 要求 |
|---|---|
| `index_id` | 固定 `SP500` |
| `security_id` | 必須存在於 master |
| `effective_from`、`effective_to` | 實際生效的半開成分區間；現行成分 `to` 可空白 |
| `announced_at` | 指數供應商公布時間；不得晚於 `effective_from` |
| `source_record_id` | 可追溯至供應商原記錄的唯一鍵 |

成分區間不得重疊；每個正式交易日須有 495–510 隻合資格證券，並須覆蓋固定 20 年主期。
若供應商只能提供事後修訂名單而沒有宣布／可用時間，入口失敗關閉。

### `trading_calendar.csv`

欄位為 `session`、`exchange`、`open_at`、`close_at`。本輪只接受 `XNYS`／`XNAS` 正式
交易日，UTC 時間次序須正確，交易日唯一且嚴格遞增。主期固定要求由 2006-08-01 或更早
至 2026-07-31 或更後，不因結果移動起訖日。

### `daily_prices.csv`

| 欄位 | 要求 |
|---|---|
| `security_id`、`session` | 複合唯一鍵；不得用 ticker 作主鍵 |
| `open_raw`、`high_raw`、`low_raw`、`close_raw` | 觀察日為正數且 OHLC 關係正確；只有明確 `suspended` 日可全部空白 |
| `volume` | 非負整數 |
| `cash_distribution` | 當日每股現金派發；沒有則為 0 |
| `split_factor` | 當日拆細／合股因子；沒有則為 1，必須為正數 |
| `total_return_factor` | 由上一有效收市至本日收市、已包括派息及退出回報的非負因子；只有永久全損退出可為 0 |
| `source_status` | `observed`、`delisted`、`cash_acquisition` 或 `suspended` |

訊號只使用當時原始價格及截至當日已生效公司行動；禁止用今天的調整股價重建當時
`US$5` 流動性門檻。每個在籍成分交易日須有價格或同日明確停牌記錄，整體覆蓋至少
99.5%；缺值不可靜默前向填補。永久退出後不得再出現觀察價格。

### `corporate_actions.csv`

欄位為 `event_id`、`security_id`、`event_type`、`announced_at`、`ex_date`、
`effective_date`、`cash_amount`、`share_ratio`、`successor_security_id`、`source_record_id`。
`event_type` 只接受 `dividend`、`split`、`spinoff`、`merger_cash`、`merger_stock`、
`bankruptcy`、`delisting`、`rights`。事件唯一；宣布時間不得晚於研究可用時間；現金與
換股條款要與價格賬本對數。

### `classification_history.csv`

欄位為 `security_id`、`scheme`、`sector_code`、`industry_code`、`effective_from`、
`effective_to`、`known_at`、`source_record_id`。本輪接受 GICS 或供應商的穩定等價分類；
每個在籍日恰有一個當時可知分類，區間不得重疊。禁止用 2026 年行業回填 2006 年。

### `security_outcomes.csv`

每段成分資格須有一行結果，欄位為 `source_record_id`、`security_id`、
`membership_effective_to`、`outcome_type`、`last_trade_date`、`exit_effective_date`、
`delisting_return`、`cash_consideration`、`successor_security_id`、`reason_code`、
`known_at`。`outcome_type` 只接受：

- `still_member`：截至數據終點仍在籍；退出欄位可空白；
- `removed_continues`：離開指數後仍交易；須保留足夠後續價格以證明不是退市；
- `delisted`、`acquired_cash`、`acquired_stock`、`bankrupt`：須有最後交易日及退出事件；
  `delisting_return` 或可對數的現金／換股代價不可同時缺失。

任何永久消失的證券沒有 outcome、退市回報或可對數代價，整包拒收。這是避免把輸家
從歷史中刪走的核心閘門。

## `manifest.json`

必須符合 `schemas/short_term_point_in_time_manifest.schema.json`，並至少記錄：schema
版本、供應商及產品、授權聲明、匯出及首次匯入時間、數據截至日、時區／幣種、調整政策、
成分時間政策、退市政策、固定 `signal_close_t_trade_open_t_plus_1` 成交時鐘、原始檔名／
列數／SHA-256，以及使用者本地轉換版本。雜湊不符、
檔案多一個或少一個、列數不符，均拒收。

## 固定稽核閘門

數據入口共 20 項，必須 20/20：

1. 合法授權聲明及供應商產品非空；
2. manifest schema 與精確檔案集合正確；
3. 所有檔案 SHA-256 及列數吻合；
4. 凍結收據早於首次供應商匯入；
5. 永久 `security_id` 完整且 master 唯一；
6. 歷史 identifier 無重疊、無同日歧義；
7. 成分 `announced_at <= effective_from`；
8. 成分區間無重疊；
9. 固定 20 年交易日覆蓋完整；
10. 每日成分數在 495–510；
11. 在籍股份價格／明確停牌覆蓋至少 99.5%；
12. OHLC、成交量、拆細及總回報因子有效；
13. 原始價格與今天調整價格用途分離；
14. 公司行動唯一且條款可對數；
15. 每段 membership 都有 outcome；
16. 永久退出均有退市回報或現金／換股代價；
17. 退出後沒有幽靈價格；
18. 歷史行業分類完整、無重疊且當時可知；
19. 同公司多股份類別可按當時成交金額去重；
20. 研究時鐘可強制 `t` 日收市訊號、`t+1` 日開市成交。

任何一項不通過，狀態只可為 `blocked_by_point_in_time_data_contract`；不得以警告、補值、
較短樣本或刪除問題證券繞過。

## 通過後仍不自動升級

20/20 只授權按既有 v1 規則進行一次正式 20 年回測。回測仍須同時對照 QQQ、SPY、
逐期成分等權及同股漂移；扣 10／25／50 bps；列出前後十年、滾動窗口、危機段、
Newey–West、PSR、全專案 DSR 及 PBO。所有既有搜尋與負結果繼續計入多重測試懲罰。

只有正式經濟／統計門檻全部通過，才可另開由全現金開始、不能回填的前瞻 Paper；Paper
至少 252 個真正新增交易日及 12 次完整輪選仍然適用。通過 Paper 亦不等於真倉授權，
更不代表必然「賺大錢」。
