# 美股短線第 43 輪：Form 4 多路徑前瞻准入協議 v1.1 修訂

FrozenAt：`2026-08-10T02:34:43Z`

狀態：**result-blind、append-only 修訂。** v1.0 原文及其 SHA-256
`845b13b1c01a0edef887ac490764ef8359cb382184430f483ab7093ca2b013eb` 永久保留，不覆寫。
以下條文如與 v1.0 衝突，一律以 v1.1 為準。

修訂時 Round43 SEC request 0、前瞻 accession 0、候選選擇 0、配置 0、策略運行 0、績效結果
0。本文只收窄 Round43 權限及修正契約歧義；不授權網絡擷取、候選、績效、Paper Trading
（模擬交易）或實金落盤。

## 1. Round43 永久只准資料工程

Round43 的唯一可授權工作是：在 repository 外的加密隔離區，前瞻接收 SEC Form 4／4-A
index 及完整 as-filed content、記錄不可回填首次觀察時間、建立 1–10 path 的專案級對賬、
重播版本／4-A lineage，並輸出不含 identifier 的 aggregate admission evidence。

整個 Round43 authorization 生命週期內，以下欄位必須精確維持：

```text
candidate_selection_count = 0
candidate_allocation_count = 0
strategy_run_count = 0
performance_result_present = false
paper_authorized = false
paper_state = all_cash
paper_positions = []
paper_backfilled_trades = 0
real_money_action_usd = 0
```

不得建立 shadow portfolio、slot allocation、order、entry／exit、NAV、PnL、回報、勝率、CAGR、
Sharpe、Sortino、最大回撤、比較表或任何可由價格結果推回策略表現的中間值。資料工程可以保存
獲准的 point-in-time 市場輸入以供完整性核對，但不得把它們交給 Round43 績效 engine；Round43
不得存在可解鎖的績效 engine。

任何 candidate、allocation、strategy、performance、Paper 或實金欄位不符上述零邊界，立即以
唯一 stable code `form4_forward_non_engineering_action_forbidden` 停止。不得以研究、shadow、
dry-run、readout eligibility 或「只看 aggregate」改名繞過。

## 2. v1.0 的 504／100／50 全部不可執行

v1.0 第 7、8、9、10、11 節中所有關於以下項目的可執行文字全部由本修訂取代：

- `prospective_sessions = 504`；
- `candidate_allocations >= 100`；
- `distinct_issuers_allocated >= 50`；
- `readout_eligibility_receipt`；
- 解鎖績效 engine、八比較前瞻回報或 insufficient-power 判定；
- `insufficient_power_no_performance_readout` 及 `form4_forward_insufficient_power`。

Round43 不計 candidate allocation，故 100／50 沒有合法計數器；不建立績效 horizon，故 504
不是 endpoint、minimum、progress、power gate 或公開 readiness。上述兩個舊 insufficient-power
字串均不得由 Round43 receipt 發出。任何程式嘗試建立、遞增、判讀或公開 504／100／50，或
建立 readout receipt，統一使用
`form4_forward_non_engineering_action_forbidden`，沒有第二個同義 stop code。

將來若要研究前瞻交易策略，必須在任何候選選擇、配置或績效計算前另行：

1. 建立新 Round、新 authorization ID、新 protocol／schema／verifier／receipt；
2. 事前固定 cohort、horizon、入場／退出、最低已成交或已完成配置數、發行人數、比較 family、
   成本、統計、停止規則及 Paper 邊界；
3. 在 global trial ledger 追加新 family／trial，綁定上一 chain head；
4. 不把 Round41 已預留的八次歷史比較冒充新前瞻試驗已經付出的 multiplicity；
5. 不得先看 Round43 identifier、訊號、配置或價格結果才決定新 protocol；如設計者已看見會
   影響選擇的資料，必須另用其後全新、未見的 prospective cohort。

Round41 的八個 comparison ID 可在新 protocol 中作事前參考，但新樣本、新 horizon 或新
readout 均是新 trial family，必須重新記帳。Round43 trial increment 維持 0，因為本輪永遠不
產生績效；global lower bound 暫維持 6,287，不追加、不改寫。

## 3. 資料 `known_at` 只取完整 content 的真正首次觀察

對每個 accession，Round43 唯一資料時鐘固定為：

```text
content_full_body_first_observed_at = 本系統第一次成功完整讀取 canonical
                                      as-filed submission body、驗證 byte count
                                      及 content SHA-256，並 create-once 封存的 UTC 時間
data_known_at = content_full_body_first_observed_at
data_known_at_basis = prospective_local_full_body_first_observed
```

receipt 必須證明 body 已讀至 EOF、hash 與 immutable object 相符、時間不早於 request start，且
同一 content hash 日後重播不能把首次觀察時間改早。只取得 daily index row、HTTP headers、
partial body、primary XML、季度 flat file 或搜尋結果均未建立 `data_known_at`。

SEC `accepted_at`、filing／transaction date、index filename date、nightly build 時間、HTTP
`Date`／`Last-Modified`、法定期限、估算公開時間及回看歷史檔案的日期不得替代或提前
`data_known_at`。若未完整取得 content，唯一狀態是 known-at missing，不可補值。

這是 **資料工程 known-at**，不授權 decision／trade clock。Round43 不建立
`decision_session` 或 `trade_session`。Round41 的 known-at hierarchy、首個嚴格較後 XNYS 收市
及下一開市規則沒有被本修訂重寫；未來新策略 protocol 必須另行綁定其適用時鐘。

## 4. `d0`／`d1` 只作後續 reconciliation

首次在一個合法 daily Form index 看到 accession 時，先按 v1.0 的 index-row schema 建立
equivalence-class seal、以 result-blind canonical rule 選 path，再擷取一次 canonical full body。
完整 content receipt 一旦 create-once 寫入，立即固定第 3 節的 `data_known_at`。

其後才按 v1.0 的 `d0`／`d1` 窗口完成 index reconciliation。`d0`／`d1` 的用途只限驗證 filing
date、承載 index、cross-day duplicate／missing 及 denominator 完整性：

- reconciliation 成功不得把 `data_known_at` 延後至 d1 receipt；
- reconciliation 找到更早的 d0、nightly index 或其他時間亦不得把 `data_known_at` 提前；
- d0／d1 皆有、皆無、窗口／manifest 漂移或 row identity 不符時，該 evidence fail closed，
  但已封存的 first-observed receipt 仍不可刪除、改早或改遲；
- reconciliation 未完成時只可標為 pending，不得把該 accession 宣稱已 admitted；
- 這些資料永遠不觸發 Round43 候選，所以不存在「等 d1 後挑較有利 D」或提早入場。

v1.0 名稱 `index_pair_first_observed_at` 由本修訂廢止；正確名稱是
`index_pair_reconciliation_completed_at`。它只屬 audit timestamp，不得成為或覆寫
`data_known_at`。

## 5. Round41／Round42 parent admission 完全不變

Round41 v1.1 的 Form 4 admission 仍必須使用封閉
`us_fddk.short_term_form4_admission.v1` schema／manifest／verifier／獨立 receipt 並通過 16/16。
Round43 的資料工程、fixture、合法多路徑、前瞻 first-observed、reconciliation 或 private bytes
不得自動令任何 Round41 gate 通過。

尤其：

- gate 07 仍要求 2005Q4 warm-up 及 2006Q1–2026Q2 固定歷史期完整；
- gate 08 仍要求每個歷史 accession 有合資格 historical known-at evidence；
- prospective `data_known_at` 只證明實際將來首次觀察，不能回填或補救歷史 gate 07／08；
- gate 05 的 daily／master denominator、gate 06 complete content、gate 10 版本／4-A、gate 12
  經濟事件去重及 gate 16 獨立真實小樣本重播均不得由單一工程測試冒充；
- 未有新的完整 16/16 machine receipt 前，Round41 candidate selection、strategy run 及
  performance 必須維持 0。

Round42 `round42-form4-admission-one-shot-v1` 的 12 樣本、5 個完成 request、0 個 complete-
submission request、cold replay 未完成、2/16 及
`stopped_no_admission_claim` 全部永久保留。Round43 不重啟、續跑、補抓、replay、換 path 或
使用 Round42 private evidence 通過任何 gate。

未來 Round43 authorization receipt 必須綁定以下父文件及各自既有 receipt／artifact SHA，而非
只寫模糊的「parent」或「stop receipt」：Disclosure known-at v1.0／v1.1、Round41 Form 4 v1.0／
v1.1、Round42 feasibility v1.0／schema v1.1／collection authorization、Round42 公開 stop
validation，以及 global trial ledger protocol／chain head。任何缺失或 hash 漂移均在網絡前停止。

## 6. `source_scope` 及 Congress 硬隔離

Round43 的封閉 schema 必須精確滿足：

```text
source_scope = ["sec_form_4"]
每個 source_type = "sec_form_4"
form_type in {"4", "4/A"}
Congress source count = 0
Congress request count = 0
Congress row count = 0
Congress field count = 0
```

schema 必須拒絕額外來源及未知欄位。任何 `congress_*`、`house_*`、`senate_*`、`ptr_*` 欄位，
或 `congress_house_ptr`／`congress_senate_ptr` source type，不論值是 null、0、空字串或 false，
都屬 injection，立即以唯一 stable code `form4_forward_congress_field_injection` 停止。不得以
「沒有使用該值」保留欄位。

Form 4 as-filed content 自身若明示配偶、trust、共同或間接擁有關係，仍須按 Round41 的經濟
事件及 capital-group 去重保存；這不等於 Congress PTR 的 `owner`／金額區間欄位，也不准
觸發 Congress collector。Congress PTR 的法律／商業用途 gate 仍是分離、未通過及不在本輪
範圍；公開可讀不等於可收集或用作選股。

獨立 mutation tests 必須注入每種禁止 source type／prefix、把 Congress 欄位藏在 nested object／
array、以 null 或 alias key 繞過、混合 Form 4 與 PTR row，以及嘗試呼叫 Congress URL／collector；
全部都必須命中同一 stable code，且網絡 attempt 為 0。

## 7. Cohort 只按 post-start content first-observed

cohort membership 的唯一規則是：

```text
content_full_body_first_observed_at > monitor_started_at
```

filing date、transaction date、d0、d1、accession 年份及事件日期均不決定 cohort membership。
因此 start 後首次完整取得的 late filing 可以有 start 前 event／filing date；它仍屬前瞻觀察的
資料分母，但必須保存：

```text
pre_start_event_date = true|false
pre_start_filing_date = true|false
historical_event_used_for_backfill = false
historical_filing_used_for_backfill = false
```

舊 event／filing date 只描述申報內容，不代表系統當時已知。不得倒填 start 前 candidate、配置、
order、Paper、持倉或績效；Round43 本身亦永遠不產生這些狀態。若同一 content hash 在 start 前
已有有效 owner-only first-observed receipt，日後重抓不得改成 post-start cohort member。若 start
前只有 partial body、未驗 hash 或不合資格 receipt，仍不得捏造較早 known-at；須按實際首次
完整成功時點及 failure ledger 處理。

這一條取代 v1.0「start 前 filing 不得加入」與「start 後 index 全部屬分母」的衝突：是否加入
只看 full-body first-observed 是否嚴格晚於 start，而不看 event date 是否較舊。

## 8. 1–10 path 是專案 cap，不是 SEC 身份規則

v1.0 的 1–10 path 保留為 **Round43 project safety cap**。它不是 SEC 對 archive alias path
cardinality 的官方保證，不等於 Ownership XML reporting-owner 上限，亦不可用來推論 actor、
joint filer、capital group、文件或交易數。

1、2 或 10 條通過相同 identity／path／canonical mutation tests 的 row 可進一步對賬；超過 10
只表示超出本專案已凍結及已測試範圍，必須用
`form4_forward_project_path_cap_exceeded` 停止。不得標為 SEC filing 無效、身份不合法、資料
錯誤或 fraud，也不得刪除第 11 條後繼續。要研究更高 cap 必須另作 result-blind amendment／
tests／receipt，且不能救援已停止 authorization。

## 9. Canonical stable code 及 mutation closure

以下取代 v1.0 所有同義或矛盾字串：

| 情況 | 唯一 stable code |
|---|---|
| 候選、配置、績效、504／100／50、readout、Paper 或實金越界 | `form4_forward_non_engineering_action_forbidden` |
| Congress source／field／collector injection | `form4_forward_congress_field_injection` |
| path count 超過 project cap 10 | `form4_forward_project_path_cap_exceeded` |
| full-body first-observed 缺失、捏造、改早或被 reconciliation 覆寫 | `form4_forward_known_at_invented` |
| d0／d1 皆無或兩日皆有 | `form4_forward_cross_day_missing_or_ambiguous` |

`insufficient_power_no_performance_readout`、`form4_forward_insufficient_power`、
`form4_forward_readout_too_early` 及 v1.0 任何暗示 Round43 可有 readout 的 code 全部不可發出。
其他不衝突的 v1.0 data-engineering stable code 繼續有效。

除 v1.0 既有 attacks 外，v1.1 tests 必須逐一證明：

1. 任何 504／100／50 計數器或績效 engine 入口均失敗；
2. d0 content 在 d1 reconciliation 前已有固定 data known-at，d1 成功／失敗／時間改動都不改它；
3. content 未讀至 EOF、hash 未驗或只有 XML 時沒有 data known-at；
4. prospective evidence 不能令 Round41 gates 07／08 或總 admission 16/16 通過；
5. Congress source／field／nested alias／network call 全部在網絡前拒收；
6. start 後 first-observed 的舊 event date 留在分母但不回填，start 前已有 receipt 的 content 不得
   重新加入；
7. 11-path fixture 命中 project-cap code，而不是 SEC identity-invalid code；
8. 每種同義越界只返回本節唯一 canonical code。

## 10. 現時決策邊界

本修訂沒有處理新 SEC 資料、沒有建立任何候選或配置，亦沒有產生新績效。Round41 的歷史
Form 4 admission 仍未通過；Round42 維持 2/16 及永久停止；Round43 只可等待另行資料工程
authorization。

隨本修訂提交的 v2 resolver／admission contract 只可驗證 **synthetic structural fixture**，其
固定狀態必須是 `evidence_mode=synthetic_fixture_only`、`admission_authorized=false`。它不是 SEC
response authenticity、完整 published-date manifest、owner-only create-once registry、監察開始
收據、候選／策略 ledger 或 Paper 帳戶的外部信任根；單靠 caller 提供的 body、hash、時間或零
狀態不能批准真實證據。任何真實網絡收集前，必須另有 result-blind authorization 及獨立信任根，
逐 byte 綁定官方 URL／index filename／完整 response receipt／byte count、不可回填 registry 的
前一 chain head、實際帳戶及 ledger 狀態；未完成前不得把 synthetic pass 稱為 admission。

獨立審核已證明 v1.0 的舊 executable API 只憑 caller 自報 504／100／50 便可錯誤批准績效
readout。因此該 implementation 及其正向 tests 已從目前 branch 的 import／test path 移除，不能再
被 workflow 當成有效契約；v1.0 protocol、receipt 及舊程式的精確 bytes 只保留在 frozen commit
`0e326d75e87d0ca8ee3e2260ad3c4a3c4f6c1a02`，供歷史稽核，不得復活、包裝或轉呼叫。

Paper 戶口維持全現金、持倉 0、backfilled trade 0；實金動作 US$0。不展示人物、發行人、
股份代號、配置、持倉比例或 US$1,000 金額試算。**今天不下單。**
