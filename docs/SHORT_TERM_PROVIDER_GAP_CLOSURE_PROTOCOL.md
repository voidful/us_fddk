# 短線個股第 21 輪：多供應商正式數據補缺協議 v1.0

凍結時間：2026-08-04T02:13:11Z

狀態：`frozen_after_local_access_audit_before_new_provider_evidence_inspection_and_implementation`

## 目的與不可移動邊界

第 20 輪已證明最新 CRSP Stock CIZ 公開指南可直接支持十份交接輸入中的 5 份能力，
另外 5 份仍須 evidence overlay；CRSP Treasury 的 4 週日度 RF 亦不能冒充凍結的 1 個月
日度簡單回報。現時重新核對沒有已設定供應商環境變數、供應商 client 或 repository 內
真實 provider package，正式就緒仍為 1/18。

本輪不再測策略、不改短線 v1、不運行回測，也不因某家供應商宣傳頁用詞較接近而降低
合約。本輪只在查看新的候選供應商文件前，固定回答：哪一條可合法取得的產品組合，能
逐項關閉全部 14 項正式能力；哪些仍只屬採購候選；以及收到資料後應按甚麼次序驗收。

第 18 輪固定的 2006-08-01–2026-07-31、至少 252 個訊號前 session、US$1,000、
Top-10、行業上限、t+1 raw open、QQQ／SPY／同池等權／首輪 Top-10 漂移四個 baseline、
10／25／50 bps、公司行動單次入賬、6,208 trials DSR、四路十段 PBO、一次性 run ID、
全現金 Paper 及實金 US$0 全部保持不變。

## 凍結的台股參考版本

- `appr1ciat1/tst_wocker@3372aa088328700feafeeb07c72ab832ea2d3ecb`；
- `appr1ciat1/tw-block-warrant@37463c54796ba36f4aac262519ea7fc2ef797de6`；
- `appr1ciat1/tst_wocker_filter_lab@06c87b7a1735877c9ccbab3a339c1742814a5058`。

只保留其 D+1、研究／訊號／Paper 分層、同池 baseline、凍結快照、負結果及雜訊帶紀律；
不搬用台股參數、權證或鉅額交易 proxy，也不以參考專案成績替代美股正式證據。

## 查看新證據前固定的五條候選路徑

| 路徑 ID | 固定候選 | 待核對範圍 |
|---|---|---|
| `crsp_spdj_composite` | CRSP Stock CIZ＋S&P Dow Jones Indices 事件／日曆證據＋CRSP Treasury | 第 20 輪 5 份 overlay、S&P 500 公布時間、精確 RF 映射及同一授權 |
| `sp_global_market_intelligence` | S&P Global Market Intelligence／Capital IQ Pro 相關產品 | point-in-time 指數成分、Security Daily、公司行動、退出經濟條款及版本證據 |
| `lseg_data_analytics` | LSEG Data & Analytics／Workspace／Datastream 相關產品 | 歷史成分事件、逐股 raw 日線、公司行動、退市與 point-in-time 可知時間 |
| `factset` | FactSet 相關市場、基準、實體、公司行動及 symbology 產品 | 公布／生效時鐘、永久 ID、退市經濟回報及可重播 export |
| `bloomberg_enterprise` | Bloomberg Enterprise／Data License 相關產品 | INDX membership events、raw 價格、公司行動、退出條款、授權及逐列 provenance |

候選名稱只固定搜索範圍，不宣稱產品存在、使用者已有訂閱或單一路徑足以通過。若官方
文件顯示產品已改名，只可記為 `product_identity_unresolved`，不能事後換入第六條路徑。

## 十四項正式必備能力

所有能力均須覆蓋 2005-08-01 buffer 至 2026-07-31，或由 manifest 明確證明更早起點；
公開文件只可支持採購判讀，正式通過仍要使用者帳戶內授權、真實細樣本及列級驗收。

1. `authorized_research_license`：明確容許本地研究、回測、保存收據及必要衍生結果；
2. `point_in_time_sp500_membership`：逐證券歷史 S&P 500 加入／移除紀錄；
3. `membership_announced_at`：公布 timestamp，含時區及來源 event ID；
4. `membership_effective_at`：生效 timestamp，與公布時間分開；
5. `permanent_security_company_ids`：永久 security／company ID 及 successor 關係；
6. `security_metadata_known_at`：歷史 ticker、交易所、股份類別、行業及逐列 KnownAt；
7. `raw_daily_ohlcv_status`：未調整 OHLCV、停牌／交易狀態及來源 record ID；
8. `distribution_event_clock_terms`：announce／ex／record／pay date、現金／股份條款及 successor；
9. `delist_exit_economics`：退出日、DelRet 或等價回報、缺失原因、現金／換股條款及 successor；
10. `post_removal_price_path`：成分移除日至下一次正式重新平衡 open 的完整可交易路徑；
11. `xnys_session_open_close`：同一研究日曆的 session、開市／收市時間及早收市；
12. `synchronized_qqq_spy_execution`：QQQ／SPY 同 session raw open、總回報因子及交易狀態；
13. `exact_one_month_daily_simple_rf`：`US_1M_TBILL_DAILY_RETURN` 相同經濟定義、日度簡單回報；
14. `row_level_provenance_replay`：產品、版本、cutoff、export ID、逐列 source ID、列數及 SHA-256。

`effective_at` 不得填入 `announced_at`；資料有效期不得填入 `KnownAt`；adjusted close 不得填入
raw open；缺失退出代價不得填 0；4 週、年率／252、DGS1MO、SHY、SOFR 或零回報不得填入
精確一個月日度 RF。

## 固定證據等級與資格規則

每一能力只可取以下一個狀態：

- `explicit_primary_documentation`：當前官方文件明示產品、欄位或能力；
- `partial_primary_documentation`：官方文件只支持部分日期、口徑或範圍；
- `contradicted_by_primary_documentation`：官方文件明示缺失或口徑不符；
- `unresolved_primary_documentation`：官方公開證據不足；
- `validated_authorized_sample`：使用者帳戶內授權細樣本通過既有 20/20＋16/16；
- `qualified_provider_package`：完整真實 package 通過 18/18 前置驗收。

公開文件矩陣的最高決策只能是 `procurement_candidate`。正式路徑必須同時：14/14 能力有
明確產品身份、授權條款 3/3、使用者訂閱確認、真實細樣本 20/20、execution extension
16/16、RF 完整、row-level provenance 完整，才可成為 `qualified_provider_package`。
不同供應商混合時須逐列保留來源、授權、日曆與 cut；不能因聯名或同集團自動視為同授權。

## 十五道固定控制

1. 本協議、收據、第 18／20 輪父契約 SHA-256 完整；
2. 三個台股參考 commit 精確；
3. 五條候選路徑集合及次序精確；
4. 十四項能力集合及次序精確；
5. 只接受供應商或資料擁有者的一手文件；
6. 產品名稱／代碼沒有由品牌宣傳推算；
7. 公開可下載沒有被寫成研究授權；
8. 20 年 coverage 沒有由「歷史數據」宣傳推算；
9. membership announce／effective 時鐘分開；
10. security metadata effective range／KnownAt 分開；
11. raw open／adjusted price 分開；
12. delist 缺失原因／退出經濟代價分開且不補 0；
13. XNYS 日曆、QQQ／SPY 同步 execution 不能省略；
14. 精確 1 個月日度簡單 RF 不接受相近年期或單位；
15. 文件通過不提高真實 readiness、不運行策略、不啟動 Paper 或實金。

## 十五項固定攻擊

| # | 單一錯誤 | 指定拒收代碼 |
|---|---|---|
| 01 | 協議或父契約 SHA 漂移 | `gap_protocol_mismatch` |
| 02 | 台股參考 commit 漂移 | `gap_reference_mismatch` |
| 03 | 增刪或調換候選路徑 | `candidate_set_mismatch` |
| 04 | 少一項正式能力 | `capability_set_mismatch` |
| 05 | 以第三方文章當一手證據 | `non_primary_evidence` |
| 06 | 由品牌宣傳推算產品 identity | `product_identity_inference` |
| 07 | 由公開下載推算授權 | `license_inference` |
| 08 | 由「歷史數據」推算完整 20 年 | `coverage_inference` |
| 09 | effective time 冒充 announced time | `membership_time_substitution` |
| 10 | metadata effective range 冒充 KnownAt | `known_at_substitution` |
| 11 | adjusted price 冒充 raw open | `adjusted_price_substitution` |
| 12 | 缺失 delist economics 填 0 | `delist_imputation` |
| 13 | 省略 XNYS 或 QQQ／SPY 同步 execution | `calendar_benchmark_omission` |
| 14 | 4 週／年率除 252 冒充一個月日度簡單 RF | `risk_free_substitution` |
| 15 | 文件分數提高 readiness 或啟動 Paper | `gap_decision_boundary_violation` |

每項攻擊只保留一個語義錯誤並直接命中指定代碼，不能用 generic hash 失敗掩蓋。
15/15 控制及攻擊只證明採購證據 validator fail closed，不等於取得任何市場列。

## 預定輸出、停止規則與下一步

- `artifacts/short_term_provider_gap_closure_protocol_receipt.json`；
- `artifacts/short_term_provider_gap_closure_validation.json`；
- `site/data/short-term-provider-gap-closure.json`；
- `docs/SHORT_TERM_PROVIDER_GAP_CLOSURE_REPORT.md`；
- current-source probe 只保存官方 URL、identity、版本及 hash，不保存受限文件內容。

若五條路徑沒有一條在公開證據層達 14/14，只輸出缺口最少的固定詢價清單，不事後加入
新路徑或放寬門檻。未有使用者明確授權，不登入、聯絡、購買或接受供應商條款。收到真實
細樣本後依次運行文件 12/12、本地匯入 16/16、point-in-time 20/20、execution 16/16、
RF 完整及正式 18/18；全部通過才可只運行一次凍結回測。

本協議只作研究及專業資訊參考，不構成供應商背書、採購建議、投資建議或盈利保證。
