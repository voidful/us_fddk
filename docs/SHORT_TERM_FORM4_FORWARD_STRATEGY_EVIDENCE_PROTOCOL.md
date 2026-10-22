# 美股短線第 46 輪：Form 4 純前瞻策略證據協議

FrozenAt：`2026-08-10T08:42:17Z`

狀態：**result-blind forward-only strategy evidence protocol。** 本輪在真實 Form 4／4-A
identifier、申報文件、候選、配置及表現結果全部為 0 時，固定未來資料到達後的策略核心。
它不授權 SEC 或 TSA request、不建立 monitor start、不下載歷史資料、不計回報、不啟動
Paper Trading（模擬交易）或實金落盤。Congress PTR 仍完全停用。**今天不下單。**

## 1. 本輪解決的問題

Round41 要求 2006–2026 每個 accession 都有 contemporaneous `known_at`，但今天取得的歷史
文件只能標為 historical replay；Round43 亦明定 prospective first-seen 不可倒填修補該 20 年
閘門。因此 Round41 family 永久不能靠未來監察升格。縮短期間、把 accepted timestamp 當
public time，或把季度 ZIP 上載日倒填到每份 filing 都會改寫失敗證據。

Round46 另立一個不救援 Round41 的 **forward-only family**。觀察期只可由有效 Round45
`monitor_start_receipt` 之後開始；所有 session、事故、零訊號日及延遲 observation 都保留。
策略、成本、估計量、成功／拒收門檻及尾段處理，必須在任何真實輸入及 Round45 的唯一
TSA POST 前，由本協議、純函式 kernel、mutation tests、versioned trial tip及機器 receipt
綁定。若 Round45 `GenTime-Accuracy` 的最早邊界不嚴格晚於 Round46 exact-head CI 的
`completed_at`，該 start 永久不合資格，必須另作未來 start；不能回填或沿用已見 cohort。

本輪只證明「規則可決定性重播並對越權輸入 fail closed」。synthetic fixture 的通過不證明
來源完整、策略有 alpha、可 Paper 或可用 US$1,000 實際交易。

## 2. 父證據及前置閘門

Round46 必須引用但不改寫：

- Round43 multipath v1.0／v1.1：完整分母、`d0/d1`、canonical path、first-observed及 4/A；
- Round45 authorization／未來 start receipt：六條 genesis chain、外部時間錨、零戶口；
- 全域不可回減 trial ledger：本輪前下限 6,287；
- Round41 v1.1 的 cluster、PIT、成交、控制及反證定義。

Round45 exact parent固定為 commit `568ccc5c695e3f0546d48617f95a19a59f99c3d9`；其
authorization canonical receipt為
`e2e255334660f17d862ce42298b8759e8ba5f9480bc56a338a03f995b21a7947`。Round46 PR只可
以同 repository 的 `codex/round45-form4-monitor-start`、該 exact SHA為base；改base、merge
ref、fork或其後漂移的base SHA均不是有效 freeze。

本輪不假稱 Round45 start 已建立。未來 production invocation 必須逐 byte 驗證：

1. Round45 start receipt 狀態精確為 `monitor_started_collection_locked`，且時間次序通過；
2. authorization commit、RFC 3161 anchor、私人 volume attestation及六個 chain head完整；
3. 另行事前凍結的 collector authorization、retention／容量／low-space gate及 SEC User-Agent；
4. Form 4 prospective admission、PIT universe、行情、公司行動及 XNYS clock 全部通過；
5. decision ledger 為全新 create-once successor namespace，沒有歷史 row、candidate或 NAV。

任一缺失只能輸出停止碼及 aggregate readiness；不得用 synthetic row、caller JSON、季度
Insider Transactions ZIP、accepted time或 Round42 私有樣本代替。

## 3. 唯一輸入邊界

Kernel 只接受已在私人 admission 層以獨立密鑰及 domain-separated HMAC-SHA-256 建立的token，
不接受 plain hash、姓名、ticker、CIK、accession原文、地址、新聞、社交媒體或人物知名度。
kernel不能自行證明token來源；production admission receipt必須綁定key identity、domain及
collision audit，密鑰永不寫入repository或公開輸出。每列 schema 精確綁定以下欄位，沒有
「最少欄位」或 caller extension：

```text
source_scope, source_type, form_type, first_observed_basis,
first_observed_at, external_anchor_verified, external_anchor_at,
external_anchor_sha256, known_at, source_receipt_sha256,
tokenization_receipt_sha256,
issuer_token, security_token, accession_token, economic_event_id,
row_lineage_token, effective_version_id, effective_version_known_at,
effective_version_evidence_sha256,
capital_group_token,
capital_group_known_at, capital_group_evidence_sha256,
independence_status,
pit_mapping_known_at, pit_mapping_evidence_sha256,
pit_eligibility_known_at, pit_eligibility_evidence_sha256,
role_set, direct_or_indirect, table, security_type,
transaction_code, acquired_disposed, economic_semantics,
shares, filed_price, transaction_date, equity_swap,
correction_action, corrects_economic_event_id
```

`first_observed_at` 只可為完整 body及相應 chain head均durable後的prospective
first-observed，並引用不可回填外部錨。`filed_at`、`accepted_at`、交易日期、HTTP Date、季度
ZIP時間及本地mtime均不可替代。4/A 的 replace／cancel／add只由自己的effective known-at
向前生效；不可修改
已封存決策、釋放 consumed event或重啟 cooldown。

calendar schema精確為`session, exchange, open_at, close_at, session_complete,
source_receipt_sha256, daily_completeness_receipt_sha256, pit_receipt_sha256,
integrity_outage`。完整session的`pit_receipt_sha256`必須綁定該日按
`(security_token, session)`穩定排序的全部PIT rows；`daily_completeness_receipt_sha256`再綁定
session、open／close、PIT receipt、PIT row count及`integrity_outage`。兩者缺失、重算不符或
`integrity_outage=true`都不是zero-signal證據；planned session的兩個receipt必須為null且
`integrity_outage=false`。PIT row schema亦為exact：`security_token, issuer_token, session,
mapping_known_at, mapping_evidence_sha256, eligibility_known_at, eligibility_evidence_sha256,
market_data_known_at, source_receipt_sha256, point_in_time_verified, sp500_eligible, gics_token,
share_class_token, most_liquid_eligible_share_class, fractional_shares_supported, open_raw,
close_raw, volume, split_factor, cash_distribution, future_adjusted, source_status,
total_return_session_count, market_cap_decile, adv_decile, settlement_verified,
settlement_terms_sha256`。今天ticker、future-back-adjusted close、
未來成分、未經PIT admission receipt驗證的caller decile或缺失後補一律拒收。decile及
`most_liquid_eligible_share_class`由尚未實作的PIT admission engine按當日完整PIT pool、升序
`(value, security_token)`作穩定rank後分成十個等數bucket；同公司股份類別以D前20-session
中位raw ADV降序、`security_token`升序唯一決定。現有synthetic kernel只驗exact欄位、時計及
receipt commitments，不得把自己稱為PIT admission完成。

日更calendar input固定為一段無缺口的complete XNYS前綴，後接最多20個由同一官方calendar
receipt綁定的planned sessions，足以在最新收市封存D+1／D+10／D+20。planned row只可含
時鐘及`session_complete=false`，不得附PIT價格、成交量或完成聲明；下一次重播變成complete
時，其日期／open／close必須逐byte相同。

所有input objects、source receipts及上一個ledger head須先canonical hash；數值只用finite
base-10 Decimal字串，強度比較以整數／Decimal交叉相乘，不轉binary float。bool-as-int、NaN、
duplicate key、extra／missing key、非 UTC、非遞增 session、hash drift或 token collision均失敗。

## 4. 固定事件、known-at及成交時鐘

合資格 primary event 必須同時是 Form 4／4-A、Table I 非衍生普通股、`P`、`A`、有限正
shares及 filed price、非 equity swap，並有文件明示 director／officer／ten-percent owner角色。
`P` 只可稱為 `open_or_private_purchase`，不得改寫成純公開市場買入。「企業家」不是 SEC
法定身份，不加入人物權重。

每列的可用證據時間固定為：

```text
evidence_known_at = max(first_observed_at,
                        external_anchor_at,
                        effective_version_known_at,
                        capital_group_known_at,
                        PIT mapping / eligibility known-at)
```

唯一決策及成交session：

```text
decision_session = close_at(s) 嚴格晚於 evidence_known_at 的第一個完整 XNYS session
trade_session    = decision_session 的緊接下一個 XNYS session raw open
```

若任何上述known-at等於收市，該日不合資格。D的raw close／volume只可在該完整收市封閉後
用作同一D gate；它不冒充較早known-at，亦不把成交提前至D。遲取只把決策向後移；不能等待
價格較好的一日。
第一個prospective session的`close_at(s)`亦必須嚴格晚於monitor start最遲可能時間；早收市、
假日及等號都不可放寬。對每個issuer，未consumed singleton會在20 calendar-day window累積，
不會因只有一組資本而提早consume；只有在第一個不處於cooldown且首次跨完整gate的D才封閉。

## 5. 固定 cluster、排序及狀態機

cluster enter gate沿用核心思想，但以下是Round46新family的完整規則；第三順位purchase-dollars
tie-break是新規則，不聲稱與Round41逐byte相同：

1. 至少兩個 `verified_independent` capital groups及兩份 distinct accession；
2. 每份去重 reported purchase dollars不少於 US$10,000；
3. 全 cluster 去重總額不少於 US$100,000；
4. D 當時有效公司行動建立的一日總回報為正；
5. D raw close×volume高於排除 D 的前 20 個完整 sessions中位美元成交額；
6. security屬 D 的 PIT pool：raw close>US$5、前20-session中位ADV≥US$20m、至少252個
   total-return sessions，且依上述prior-20-ADV規則為同公司最流通合資格股份類別。

所有issuer先在D收市封閉，再作容量排序。所有總額及ratio以exact Decimal／rational比較；新
confirmed clusters的lexicographic次序固定：

1. distinct verified capital groups降序；
2. 去重 purchase dollars ÷ D前20-session中位ADV降序；
3. 去重 purchase dollars降序；
4. permanent `security_token`升序。

十個10%槽先保留 active positions，再依此順序填空槽；不得沽出舊持倉讓路。confirmed但
無槽、量價未確認及已配置的cluster都 consume member events，並設定
`cooldown_through=session_index(D)+20`；下一次最早D+21。新事件在cooldown期間保持未
consumed，期滿仍在20日窗口才可評估。

獲槽後只記排定：D+1 raw open由該槽QQQ換入股票，第10個持有session（D+10）raw close
退出並換回QQQ。沒有同日成交、止蝕、止賺、加碼、槓桿、持有期延長或途中重排。碎股固定
允許，數量以Decimal計至12位並向下取整，餘款不生息；缺D+1 open會永久停止該cohort，不能
找下一個open。停牌、退市、現金收購或換股只可依PIT公司行動在首個可強制結算時點記
`forced_settlement`，不可刪除該路徑。本輪kernel不計NAV或return，只封存待提交decision、
槽位、時鐘、成本契約及hash chain；durable create-once writer仍未實作、未授權。

## 6. 成本及固定比較 family

未來execution/readout必須用US$1,000研究名義、十個起始等值US$100自融資槽、空槽QQQ，
不在槽間再平衡。五個全部必報、共同否決的deterministic成本情境固定為：10／25／50 bps
per actual asset leg，以及10 bps另加每child order US$0.01／US$0.05；固定費只加在10 bps，
不是3×3 factorial。QQQ沽出、股票買入、股票沽出及QQQ買回四腿全收；沒有真實換倉不得
製造ghost order。所有策略及baseline在同一起始open、同一terminal close按相同可適用成本、
派息、公司行動及碎股規則計算；五種成本不能挑最好者。

Round46重新登記八個 forward-only比較，不沿用Round41的歷史trial：

1. `qqq_buy_hold`；
2. `spy_buy_hold`；
3. `pit_eligible_equal_weight_monthly`；
4. `form4_cluster_unconfirmed`；
5. `price_volume_only_matched`；
6. `single_actor_purchase_confirmed`；
7. `non_signal_code_confirmed`；
8. `issuer_month_actor_permutation`。

`minimal_execution_clock_control`只驗證時鐘／會計identity，不是alpha hypothesis，不增加trial。
既有canonical ledger v1.0及其tip `c0e754cee5603c5eb9d2d142db1af6ec21b465d3492097b02112b94a18574085`
永久保留在6,287。本輪另建versioned successor extension：必須逐byte綁定舊ledger file hash、
舊tip、sequence=12、`seen_result=false`、increment=8及新entry hash；combined-tip validator只有
完整驗過predecessor與successor才回傳有效下限 **6,295**。單獨旁支receipt或文字聲明不能作
readout gate，亦不能覆寫舊ledger。

matched controls必須同D、GICS、market-cap decile、ADV decile及reported-notional decile
一對一無放回；decile算法沿用第3節，tie以security token升序。permutation固定在同calendar
month、role-set、notional decile內以receipt所綁定seed及counter-based SHA-256排序，draw數等於
allocated event數且無放回。`matched_rate=1.0`；缺配對整輪永久停止，不得刪candidate、放寬
bucket、換seed或補抽。控制只封存assignment；統計計算仍由已凍結但未授權的readout engine執行。
permutation seed逐字固定為整數`41202608`；它不是可重抽參數。

## 7. Append-only輸出及公開邊界

私人輸出只有三類：

- `decision_records`：cluster state、member commitments、排序、槽位及D/D+1/D+10；
- `control_records`：固定matched／permutation assignment commitments；
- `aggregate_progress`：只供私人稽核的session、completed round trip、distinct issuer及鏈頭計數。

kernel產出的每筆待提交record必須含ordinal、prev SHA-256、entry SHA-256及父input commitments。
本輪沒有durable writer，故不得聲稱已create-once／fsync；未來writer須另行事前freeze並測每個
crash point、parent fsync、re-entry及partial state。上一個鏈頭、session或狀態不符即永久停止，
不能截斷、重排、重算或回填。

504-session final前，公開輸出只可包含protocol/code版本、`今天不下單`、整體collection／stop
狀態及不含計數的readiness；不得每日發布稀疏allocation delta。final aggregate只有每個公開
cell不少於10筆才可發布，否則合併或隱藏。public commitment只hash已redact的aggregate，不得
hash private manifest或低熵token。任何時點都不得包含token、精確日期、角色組合、金額、
issuer、ticker、姓名、CIK、accession、path、文件內容、候選名單或可逆映射。

## 8. 唯一readout時點

由有效monitor start後第一個完整XNYS session起，`prospective_sessions`逐日累積。只有當日
collector及PIT completeness receipt完整而候選為0才是合法zero-signal session；任何停機、
遺失分母、延遲取得或integrity outage都保留該session並把cohort永久轉為
`stopped_no_readout`，不得後補、重開或延長。第一次且唯一的eligibility check固定於第504個
session收市，並立即停止接受新signal：

```text
prospective_sessions == 504
completed_round_trips_or_forced_settlements >= 100
distinct_issuers_completed >= 50
integrity_outages == 0
```

本輪 kernel只可輸出：

- 504日前：`collecting_no_readout`；
- 任一integrity outage：永久`stopped_no_readout`；
- 504日且樣本不足：永久`insufficient_power_no_performance_readout`；
- 504日且100／50達標：`eligible_pending_fixed_maturation_embargo`。

eligible後只可等待D504前已入場持倉按原定時鐘退出，最遲D514；不接受新signal、不以後來
completion補足100／50，不能延長、重設起點或terminal選日。所有持倉成熟後，策略及baseline
在同一terminal close結算；合資格狀態才可成為`eligible_for_pre_frozen_readout_engine`。若D514
仍因缺資料無法唯一結算，永久`stopped_no_readout`。

### 8.1 現在固定、將來只可解鎖的readout

readout程式必須在首個真實row前另有exact-byte實作／tests／receipt，但下列estimand及否決規則
已在本協議固定，未來只能忠實實作：

1. primary為10 bps下策略每日總回報相對QQQ的同期差；另報相對SPY及PIT equal-weight；
2. 報五個成本情境的總回報、年化回報、年化波幅、Sharpe、Sortino、最大跌幅、Calmar、換手、
   成本拖累、US$1,000期末值、completed／forced counts及issuer集中度；
3. 兩半及八個連續63-session blocks事前固定；rolling 3／5年及歷史危機段標為不可判定，不能
   換成別的窗口；
4. primary統計固定為63-session moving-block bootstrap 20,000 paths、seed
   `round46-form4-forward-20260810`，對八個comparison family作共同max-t／Holm one-sided 5%；
5. DSR使用combined lower bound 6,295，不能以較小trial數重算；
6. 只有primary 10 bps相對QQQ、SPY、PIT三者總回報均為正、QQQ-relative兩半均正、八段至少
   六段為正、Holm/max-t均通過、DSR probability≥0.95，且所有matched/permutation control的
   配對差均為正，才可稱`forward_evidence_passed`；
7. 25／50 bps及兩個fixed-fee stress須相對QQQ總回報仍為正；任一失敗整體拒收，不挑情境；
8. 其他任何結果、樣本不足或完整性失敗一律保存為negative／inconclusive，不調參救援。

Round46 kernel及本輪CI仍不得讀價格回報或執行readout；以上freeze不是績效授權。

## 9. 權限及現時零狀態

本輪permission固定：synthetic kernel與combined trial-tip verifier可執行；durable writer、monitor
start、SEC collection、真實row解析、candidate publication、performance、Paper及real money
全部false。現時：

```text
TSA requests = 0
SEC requests = 0
real identifiers / filings / rows = 0 / 0 / 0
candidate selections / allocations = 0 / 0
strategy runs / performance results = 0 / 0
PIT admission / control assignment = false / false
durable private writer / readout implementation = false / false
Paper funding / positions / orders / fills / backfill = 0 / 0 / 0 / 0 / 0
real-money action = US$0
Congress requests / rows / fields = 0 / 0 / 0
```

## 10. 必須拒收的攻擊

Tests最少覆蓋並映射到固定stable code family：歷史row、accepted-as-known、未錨first-seen、
plain token／Congress欄位／raw identifier、
錯form／table／code／A-D／role、swap、零／NaN shares或price、shared／unresolved capital、
同accession或同capital重複、4/A回填／unconsume、max-evidence時鐘任一分量延遲、20日邊界漂移、
D延遲、同日open、量價窗口
包含D或未來、future constituent／adjusted price、低價／低ADV／不足252 sessions、排序改權重、
active持倉被新候選擠走、slot>10、持有期／cooldown漂移、chain truncation／reorder／duplicate
ordinal、舊trial tip漂移／fork／reorder／truncate、控制缺項／多項／配對不足／seed漂移、
503日readout、504日99 completed或49 issuers、D504後新signal、D515仍延長、outage後重開、
token／日期／名單公開、Paper回填或任何實金動作。

合法synthetic fixtures須證：兩個獨立capital groups第一次跨gate即關閉；unconfirmed及capacity
rejected不會翌日救援；singleton未跨gate不提早consume；任何較遲證據時間只把D及trade向後移；
active優先、exact-rational tie-break、D+10退出、D+21可重評；公開aggregate無identifier；
504／100／50只進入固定maturation embargo而不產生表現。

stable code family逐字固定為：`form4_strategy_schema_invalid`、
`form4_strategy_token_invalid`、`form4_strategy_token_collision`、
`form4_strategy_congress_forbidden`、`form4_strategy_raw_identifier_forbidden`、
`form4_strategy_timestamp_invalid`、`form4_strategy_prospective_evidence_invalid`、
`form4_strategy_source_receipt_invalid`、`form4_strategy_event_semantics_invalid`、
`form4_strategy_amendment_invalid`、`form4_strategy_capital_independence_invalid`、
`form4_strategy_calendar_invalid`、`form4_strategy_pit_invalid`、
`form4_strategy_price_history_invalid`、`form4_strategy_execution_clock_invalid`、
`form4_strategy_execution_outcome_invalid`、`form4_strategy_slot_invalid`、
`form4_strategy_hold_period_invalid`、`form4_strategy_cooldown_invalid`、
`form4_strategy_comparison_family_invalid`、`form4_strategy_trial_ledger_invalid`、
`form4_strategy_ledger_invalid`、`form4_strategy_create_once_violation`、
`form4_strategy_public_boundary_invalid`、`form4_strategy_performance_forbidden`、
`form4_strategy_paper_forbidden`及`form4_strategy_real_money_forbidden`。未來durable writer須把首個
錯碼及private evidence commitment create-once封存為永久stop；本輪尚未實作該writer。

## 官方參考

- SEC Insider Transactions Data Sets：
  https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets
- SEC Accessing EDGAR Data：
  https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
- SEC Webmaster FAQ／automated access：
  https://www.sec.gov/about/webmaster-frequently-asked-questions
- SEC Ownership XML Technical Specification：
  https://www.sec.gov/info/edgar/ownershipxmltechspec-v3.pdf

SEC季度資料由2006年1月起提供、按季更新，且官方明示不能取代完整filing；它可作將來
完整性對賬，不可製造historical known-at。SEC網站現行公平存取上限為全來源10 rps；本專案
未來collector仍固定為更保守的單一指定host、全專案不高於1 rps及帶聯絡資料User-Agent。
