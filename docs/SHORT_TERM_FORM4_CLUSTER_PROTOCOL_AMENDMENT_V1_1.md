# 美股短線第 41 輪：Form 4 cluster 事前協議 v1.1 修訂

生效日期：2026-08-10

狀態：**在獲授權 Form 4 事件 0、候選選擇 0、策略運行 0、績效結果 0 時，按獨立審閱
追加；v1.0 及其收據保留。以下條款有衝突時以 v1.1 為準。**

本修訂不增加第 41 輪原有八個比較、不改候選的 20 日窗口、金額門檻、量價確認、10 日
持有期或成本。它只消除 admission、20 年 known-at、共同持有、4/A、狀態機及控制比較的
歧義。全域試驗下限另因補記第 24–28 輪已見結果而提高；不是本修訂看見新績效。

## 1. Form 4 專屬 admission：必須 16/16

本候選不再以六來源 Disclosure Phase 1 20/20 冒充 executable gate。執行前必須有封閉
`us_fddk.short_term_form4_admission.v1` schema、manifest、verifier 及獨立收據，
`source_scope` 精確等於 `["sec_form_4"]`，並通過以下 16 項：

| ID | 機器閘門 | 精確通過條件 |
|---:|---|---|
| 01 | `versioned_parent_lineage_verified` | Disclosure v1.0、v1.1 修訂、Form 4 v1.0、v1.1 及各收據 SHA 全符 |
| 02 | `sec_exact_use_terms_verified` | SEC exact use、帶聯絡資料 User-Agent、單一指定 collector、全專案不高於 1 rps、cache、403／429 持久停止收據有效；Congress 欄位必須 absent |
| 03 | `encrypted_private_quarantine_verified` | raw/XML、姓名、CIK、accession 不入 Git／CI／網站；磁碟加密、owner-only、repository 外路徑由獨立證據驗證；chmod 不等於加密 |
| 04 | `source_scope_exact` | 所有版本與事件只屬 `sec_form_4`，form type 只可 `4`／`4/A` |
| 05 | `filing_denominator_complete` | 每季 daily/master index Form 4／4-A accession 分母完整；missing、unexpected、duplicate 均為 0 |
| 06 | `as_filed_content_complete` | 每 accession 有 as-filed raw hash、request receipt 及 record count；季度 flat file 只作交叉核對 |
| 07 | `fixed_period_coverage_verified` | 2005Q4 warm-up 與 2006Q1–2026Q2 每期均有分母列且 missing=0；不得看結果縮短 |
| 08 | `known_at_evidence_complete` | 每 accession 有真正 public／獨立 archive／live contemporaneous first-seen；accepted-as-known=0、historical-backfill fallback=0、missing=0 |
| 09 | `known_at_clock_verified` | `decision_session` 是嚴格晚於 known-at 的首個 XNYS 收市，`trade_session` 是其緊接下一個 XNYS 開市；延遲挑 D／entry 均拒收 |
| 10 | `version_amendment_chain_verified` | accession、版本、row lineage 唯一；4/A target 明確、無環、不可回填 |
| 11 | `form4_semantics_verified` | admission 保留 primary `(P,A)` 及固定 control `(A,A),(M,A),(F,D),(G,A),(G,D)` 的 Table I rows、原始 A/D 與註腳；primary filter 才只取有限正股數／價格、非 swap／Table II 的 P+A |
| 12 | `economic_event_dedupe_verified` | 修訂、joint owner、trust／entity／配偶及同一經濟交易沒有重複計 actor 或金額 |
| 13 | `pit_security_universe_verified` | 永久 security/company ID、PIT S&P 成分、GICS、股份類別、退市及公司行動全在 D 前可知 |
| 14 | `pit_market_execution_verified` | XNYS、raw OHLCV、當時有效 split／distribution、QQQ／SPY／RF 同步；禁止未來 back-adjusted close |
| 15 | `independent_mutation_attacks_passed` | accepted 提前、延遲 decision／entry、歷史回填、缺季、4/A／joint duplicate、retry-confirmation 等逐項命中精確錯誤碼 |
| 16 | `authorized_real_sample_independently_replayed` | 合法真實小樣本只驗 admission；候選選擇及策略運行仍為 0 |

現在沒有 Form 4 admission schema／manifest／收據，故 executable admission 為 **0/16**，
不得把 SEC client 單元測試、檔案權限或季度 ZIP 成功下載寫成通過。

## 2. 固定 20 年覆蓋：做不到就拒絕，不可縮短

研究窗口維持 `2006-01-03` 至 `2026-06-30`，事件 warm-up 為 `2005-12-14` 起。每季至少
保存：`expected_accessions`、`observed_accessions`、`missing_accessions`、
`unexpected_accessions`、`duplicate_accessions` 及三種 known-at basis 計數。

分母是 EDGAR daily/master index 中 filing date 落在窗口的全部 Form 4／4-A accession；
季度 Insider Transactions ZIP 是 as-filed 輔助資料，不能代替 raw filing 或 historical
public-time。以下全部為 0 才可寫 `twenty_year_form4_coverage_validated=true`：

- missing、unexpected、duplicate accession；
- `accepted_at_used_as_known_at`；
- `historical_backfill_fallback_count`；
- `missing_known_at_evidence`。

本地 `first_observed_at` 只有在 live monitor 成功讀完同一 content hash、append-only checkpoint
於下一個合資格 XNYS 收市前封存時，才是 contemporaneous。今天下載 2006 年 filing 只可標為
`historical_backfill`，不能倒填 2006 年 known-at。若 2006–2026 無法逐 accession 建立上述
證據，唯一合法結果是 `form4_twenty_year_admission_failed`；不得改稱 20 年回測，也不得看完
observed-only 結果後縮短期間。prospective first-seen 可供未來資料工程與獨立前瞻研究，
但不能補救歷史 20 年候選。

## 3. 4/A、共同持有與獨立資本去重

每個正規化 row 必須新增：`economic_event_id`、`row_lineage_id`、`effective_version_id`、
`correction_action=original|replace|cancel|add`、`corrects_economic_event_id`、
`effective_version_known_at`、`capital_group_token`、`ownership_chain_hash`、
`capital_group_evidence_sha256`、`capital_group_known_at` 及
`independence_status=verified_independent|shared|unresolved`。

- 4/A 的 `replace`／`cancel` 自它自己的 known-at 起，只改同一 `economic_event_id` 的
  current-as-known 狀態；不新增購買、不可 unconsume、不可重啟 cluster／cooldown。
- 只有文件明示的新增交易才可用 `add` 建新 ID。無法逐 row 明確對應原交易時，
  `amendment_mapping_ambiguous` 失敗關閉，不以申報日、相近股數或註腳文字 fuzzy match。
- `original`／`add` 的 `corrects_economic_event_id` 必須為 null；`replace`／`cancel` 必須明確
  指向既有 ID。`effective_version_id` 必須存在於 append-only version chain，且其
  `effective_version_known_at` 不晚於使用該 row 的 D。
- 同一 accession 多名 reporting owner、不同 accession 的同一 economic event，以及共同／
  配偶／trust／entity ownership chain，只計一次 dollars 並共享 `capital_group_token`。
- cluster 必須有兩個 distinct `capital_group_token`、兩份 distinct accession，且兩組均為
  `verified_independent`；每組的 `capital_group_known_at <= close_at(D)` 且 evidence hash 可
  重播。D 時關係仍未知必須是 `unresolved`，不可用後來得知的 trust／配偶／entity 關係
  回寫。`shared` 或 `unresolved` 不合資格；「不同姓名／token」不等於兩注獨立經濟資本。

## 4. 唯一 cluster 狀態機

按 XNYS session close 遞增處理每個 issuer：

1. 對每列固定 `decision_session=min{s: close_at(s) > known_at}`，`trade_session` 必須是它的
   XNYS successor；不得延後至價格較有利的 D；
2. 在第一個不處於 cooldown 的 D，只取未 consumed、current-as-known active、
   `known_at < close_at(D)`，且 transaction date 在 `[D_date-19, D_date]` 的 P/A 事件；
3. 每份計入的 distinct accession 在經濟事件去重後各自 reported dollars 至少 US$10,000；
   只有合資格 accession 才可在同一 verified capital group 內聚合。distinct groups 至少 2、
   去重後總額至少 US$100,000 時，只在首次跨過門檻的 D 建立一次；
4. `cluster_id=sha256(issuer_id|D|sorted economic_event_id|sorted effective_version_id)`；
5. 同一 D 只評一次量價；通過為 `closed_confirmed`，失敗為 `closed_unconfirmed`；
6. 在任何槽位排序前先關閉當日所有 cluster。confirmed 但因十槽已滿而落選者標為
   `closed_capacity_rejected`；confirmed／unconfirmed／capacity-rejected 全部 consume member
   IDs 並設定 `cooldown_through=session_index(D)+20`，不能翌日重試；
7. 下一個可成立
   session 是 D+21；
8. cooldown 內的新事件保持未 consumed，期滿時仍在 20 日窗口才可使用；舊 consumed event
   的修訂只進 audit，只有明示 `add` 可成為新輸入。

因此失敗 cluster 不可逐日重試，rolling window 新舊事件亦不可重複湊到有利 D。

量價確認改以 D、D-1 **raw close** 及 D 當時已生效的 split／cash-distribution ledger 建立
一日總回報；禁止 vendor future-back-adjusted close。252-session 歷史、最流通股份類別、
PIT GICS、market-cap／20-session ADV decile 全部只用 D 前已知資料。

## 5. 八個比較的可執行配對

比較 family 仍是 v1.0 的八條，未新增試驗：

- `form4_cluster_unconfirmed`：同一 first-trigger D、state、slots，唯一差異是忽略量價確認；
- `price_volume_only_matched`：每個實際 allocated confirmed signal 在同 D 一對一、無放回
  配對；control 自身必須通過完全相同 D raw-price／volume confirmation；PIT GICS、
  market-cap decile、20-session ADV decile相同，過去 20 日無 Form 4 cluster。距離固定為
  `abs(log(mcap_control/mcap_candidate))+abs(log(ADV_control/ADV_candidate))`，最小後以
  permanent ID 決勝。無配對即 `control_match_incomplete`，不得丟掉 candidate；
- `single_actor_purchase_confirmed`：exactly one verified capital group，並按同日、GICS、size、
  ADV 及 purchase-notional decile 一對一無放回；無配對即 fail；
- `non_signal_code_confirmed`：保留各 code 的 A/D，只允許 `(A,A)`、`(M,A)`、`(F,D)`、
  `(G,A)`、`(G,D)`；notional 統一用 shares × D-1 split-consistent raw close，再按同日、
  GICS、size、ADV、notional decile 配對；缺 price/share 或無配對即 fail；
- `issuer_month_actor_permutation`：以 `capital_group_token` block 在 month×role strata 跨 issuer
  置換，保留文件、時間、金額及 group size；20,000 draws、seed `41202608`，
  統計量固定 `T=候選相對 QQQ 每日 active return 的 NW lag-10 t`；
  `p=(1+#T_perm>=T_obs)/20001`。

每個 matched control 必須 `matched_rate=1.0`，event、session 及 slot count 相同。

## 6. 數值反證門檻取代主觀文字

v1.0「勝過」及「同等或更強」固定解釋為：

1. 對 QQQ 及 SPY：10 bps CAGR 差各 ≥2.0pp；50 bps 各 ≥0.5pp；active NW t≥1.96、
   對應 Holm／max-t adjusted p≤0.05；最大跌幅差不低於 -5pp；
2. 對 PIT 等權、unconfirmed、price-volume、single-actor 及 non-signal：10 bps
   `delta CAGR≥0.50pp` 且 `delta excess-Sharpe≥0.10`，50 bps `delta CAGR>0`；
3. permutation：observed statistic 高於 95th percentile 且 randomization p≤0.05；
4. 任一 single-actor／non-signal control 自己同時通過候選對 QQQ 的全部經濟、穩健及
   adjusted-p 門檻，即 `negative_control_equivalent=true`；permutation 若 `T_obs` 不高於
   第 95 percentile 或 randomization p>0.05，即 `permutation_equivalent=true`；任何一項
   成立候選即拒收；
5. 最佳三年按 candidate-minus-QQQ 的 calendar-year contribution 固定排序；2008、2020、
   2022 各自移除並分開重算；「主要經濟次序」只表示 candidate CAGR 同時高於 QQQ 及上述
   五個 control，不作人手判斷。

## 7. 決策邊界

本修訂只令 candidate specification 更可否證，沒有建立 admission schema、沒有擷取真實
事件、沒有生成標的或回報。現時 Form 4 admission 0/16、候選選擇 0、策略運行 0；Paper
全現金、持倉 0、實金動作 US$0，**今天不下單**。
