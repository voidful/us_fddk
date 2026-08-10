# 美股短線：人物披露動態選股設計

設計日期：2026-08-10

狀態：**只屬 result-blind 設計，不是事前協議、數據准入、選股結果、回測、Paper Trading
（模擬交易）或實金指令。** 本設計的獲准數據列、候選、策略運行及表現結果全部為 0；
Paper 維持全現金、持倉 0、不可回填，實金動作 US$0。**今天不下單。**

本文件把「參考美國議員及企業家投資動向」拆成兩條不可互相借用准入證據的來源路徑，
再定義一個可供日後獨立事前凍結的動態選股骨架。它不取代第 41 輪 Form 4 v1.1 協議；
若日後建立可執行協議，必須在任何獲准真實數據、候選名單或表現結果出現前，明確處理
兩份文件的關係、追加全域試驗帳及提交機器收據。

## 一頁設計

| 項目 | 設計決定 | 現時狀態 |
|---|---|---|
| Congress PTR | 法律、exact-use、私隱及自動存取邊界未釐清前，不收集、不解析、不選股 | 停用；數據 0 |
| SEC 路徑 | 只接受 SEC Form 4／4-A 及文件明示的 Section 16 角色 | Form 4 准入未通過 |
| 「企業家」 | 不是官方角色，不按創辦人、知名度、財富、傳媒聲量或姓名加權 | 人物權重不存在 |
| PIT 股份池 | 每個決策收市以當時已公布並生效的成分、身份、價格及公司行動重建 | 未獲准 |
| 動態選擇 | 固定 enter gate、持倉 hysteresis、Top-10、十個 10% 槽及十日退出 | 只屬設計 |
| 公平比較 | QQQ、SPY、PIT 股份池、最小成交時鐘控制及配對負控制 | 表現 0 |
| Paper／實金 | 不因設計完整、單元測試或局部准入而啟動 | 全現金／US$0 |

## 1. 來源必須分流

### 1.1 Congress PTR：法律未清，不得收集

Congress Periodic Transaction Report（PTR）只能在另一次、資料出現前完成的書面審查後
考慮。最低限度須確認官方來源、使用條款、自動存取、個人資料、姓名／家屬資料保存、
本地研究、衍生彙總發布及保留期限。未取得精確許可前：

- 不發出 request、不手動抄錄、不保存文件、姓名、代號或交易區間；
- 不建立人物榜、議員組合、買賣方向、候選分數或歷史回報；
- 不以第三方鏡像、新聞、社交媒體、追蹤網站或搜尋摘要繞過官方來源及條款；
- 不把申報截止日、交易日期或文件上載日期冒充真正 `known_at`；
- 不把披露金額區間的中點當作精確成交額，也不忽略配偶、受養人、共同持有及延遲申報；
- 不把 Congress 缺失欄位補入 SEC schema，也不讓 SEC 准入分數替 Congress 放行。

日後若獲准，Congress 必須另有封閉 schema、私有隔離、版本鏈、known-at、經濟交易去重、
延遲分母、獨立 mutation attacks 及獨立 trial family。未通過自己的全部門檻前，來源狀態
只能是 `congress_ptr_disabled_legal_scope_unresolved`。

### 1.2 SEC：只用可驗證角色，不用人物故事

SEC 路徑的 `source_scope` 必須精確為 `sec_form_4`，只處理 Form 4／4-A as-filed 文件及
官方交叉核對資料。可用角色只來自申報時可驗證的 Section 16 欄位：director、officer、
ten-percent owner，以及文件明示的重疊角色。職銜原文可以保存作語意稽核，但不增加分數。

「企業家」、「創辦人」、「明星投資者」及「成功人士」都不是 SEC 法定角色。以下資料
不得成為特徵、排序或 tie-break：姓名、知名度、社交媒體追蹤、新聞次數、估算身家、
過往命中率、事後股票回報、公司故事或人手偏好。沒有合資格申報角色的人，即使廣為人知，
亦不進入 SEC actor signal；合資格的人一律按同一經濟證據規則處理。

`P` 的語意固定為「公開市場或私人購買」，不可改寫成已證實的純公開市場買入。每列仍須
保留 raw code、A/D、直接／間接持有、joint filing、註腳、equity-swap、4/A 版本及
effective-as-known 狀態。

## 2. 執行前資料閘門

任何動態候選計算前，必須同時具備：

1. Form 4 source-specific admission 全部通過；局部通過或真實細樣本不等於准入；
2. point-in-time 股份池、永久證券／公司 ID、歷史身份、股份類別及 GICS 完整；
3. raw OHLCV、總回報因子、拆股、派息、停牌、退市、現金／換股退出經濟完整；
4. 官方 XNYS 開收市日曆及同步 QQQ、SPY、美元一個月國庫券日回報；
5. 所有原始文件、人物資料及不可逆前的識別資料只在 repository 外、加密、owner-only
   私有隔離保存；公開輸出只准彙總；
6. 協議、schema、verifier、數據 cut、比較 family、成本、統計及全域 trial 下限的 SHA-256
   收據早於任何候選或表現結果。

`known_at` 只可用可雜湊綁定的官方 public time、獨立不可回填 archive first-seen，或真正
同時期 live monitor 的 `first_observed_at`。SEC accepted time、交易日、季度 ZIP、nightly
index 日期及事後下載時間均不可單獨替代。決策時鐘固定為嚴格晚於 `known_at` 的第一個
XNYS 正式收市；成交只可在其後下一個 XNYS raw open。

任一資料閘門未通過，唯一輸出是缺口及停止碼；候選數、Top-N、配置及回報維持 0。

## 3. Point-in-time 合資格股份池

每個決策收市 `D` 先獨立建立 `pit_eligible_pool(D)`，完成後才可讀 actor signal：

1. 只接受 `D` 前已公布、且在 `D` 已生效的 S&P 500 美國 USD 普通股；
2. 以永久 `security_id`／`company_id` 連接；ticker 只是一個有生效期的顯示屬性；
3. 同一公司多個股份類別只保留 `D` 前 20 個完整 sessions 中位美元成交額最高者，同值以
   永久 `security_id` 升序決定；
4. 至少有 252 個截至 `D` 的有效總回報 sessions；
5. `D` raw close 嚴格高於 US$5，先前 20 個完整 sessions 的中位
   `raw close × volume` 不低於 US$20m；
6. `D` 時可知的交易所、股份類別、GICS、拆股、派息、停牌及退出狀態全部可重播；
7. 不前向填補、不用未來 back-adjusted close、不把今天成分或今天 ticker 倒填歷史；
8. 缺價格、缺公司行動或退出經濟的股份不能靜默刪除；整個相關決策日 fail closed。

股份池是候選及 `pit_pool_equal_weight_monthly` 基準的共同母體。不得先看 actor signal，
再縮窄行業、規模、成交額或成分範圍。

## 4. Actor signal：只量度獨立資本及申報強度

### 4.1 合資格經濟事件

每個版本在 `D` 當時可知的列，必須同時符合：

- Form 4／4-A Table I 非衍生普通股；
- `TRANS_CODE=P`、`A/D=A`，股數及每股價格均為有限正數；
- 非 equity swap、非 Table II 衍生證券；
- reporting person 有文件明示的合資格 Section 16 角色；
- 4/A、joint owner、trust、entity、配偶及同一經濟交易已依 effective-as-known 版本鏈去重；
- `independence_status=verified_independent`，`shared` 或 `unresolved` 一律不計；
- transaction date 位於 `[D_date-19, D_date]`，且事件在 `D` 前未 consumed。

每份 distinct accession 去重後的 reported purchase dollars 固定為 `shares × filed price`。
每份至少 US$10,000；同 issuer 須有至少兩個 distinct capital groups、兩份 distinct
accession，合計至少 US$100,000。價格未知、修訂 target 含糊或獨立資本關係未解均失敗
關閉，不用市場價、相似姓名或人手判斷補值。

### 4.2 決定性分數及排序

`actor_signal` 不包含人物身份權重。對首次跨過上述 enter gate 的 issuer，只計：

- `actor_breadth`：distinct verified capital groups 數目；
- `actor_intensity`：去重 reported purchase dollars ÷ `D` 前 20-session 中位美元成交額；
- `reported_purchase_dollars`：去重申報總額，只作第三順位 tie-break。

當日新候選依以下 lexicographic 次序排列，不把三項事後調成加權分數：

1. `actor_breadth` 降序；
2. `actor_intensity` 降序；
3. `reported_purchase_dollars` 降序；
4. 永久 `security_id` 升序。

此外，入場日 `D` 必須同時通過最小量價確認：以 `D` 當時已生效的拆股／派息事件建立的
一日總回報為正，且 `D` 的 `raw close × volume` 高於先前 20 個完整 sessions 的中位值。
量價確認只是一道固定 enter gate，不改 actor 排序；不通過即結案，不等待下一日救援。

## 5. Enter／stay hysteresis、Top-N 與單一狀態

每個永久公司／證券組只可同時有一個狀態：

```text
outside -> enter_pending -> active -> scheduled_exit -> cooldown -> outside
                      \-> capacity_rejected -> cooldown
                      \-> unconfirmed -> cooldown
```

- **Enter**：只有 `outside`、不在 cooldown、屬 `pit_eligible_pool(D)` 且首次通過 actor 及
  量價 gate 的股份可進 `enter_pending`。當日先封閉所有 issuer 狀態，再作容量排序。
- **Top-N**：`N=10`。先保留所有 `active` 持倉，再從當日新候選次序取最多
  `min(10 - active_count, 10)` 隻；不得沽出較早持倉為當日較高分股份讓路。
- **Stay hysteresis**：入場後不再每日重排；actor signal 下降、沒有新申報、跌出當日 Top-N
  或量價轉弱都不提前沽出。這避免把噪音變成高換手及結果後止蝕。
- **Exit days**：於入場後第 10 個 XNYS session raw close 固定退出，其後相應槽回到 QQQ。
  不設止賺、止蝕、加碼、延長持有或同日反轉。
- **Cooldown**：第一次形成訊號的 `D` 至 `D+20` session 不可重啟；下一次最早為 `D+21`。
  unconfirmed、capacity-rejected 及 active 都消耗該 cluster。持倉期間的新列不加倉、不延長
  exit days；只有尚未 consumed、到 cooldown 結束仍在 20 日窗口的全新經濟事件可重評。
- **單一股票單一狀態**：同公司多股份類別、同一 accession 多 owner、多份文件及日後 4/A
  都聚合到同一 permanent company/security state；不可同時佔兩槽或以兩個 ticker 重複入場。
- **強制事件**：停牌、退市、現金收購、換股或 successor 依 PIT 公司行動賬本結算一次；
  不是可選擇的策略退出，也不得因結果刪除該路徑。

## 6. 最小成交投資組合

研究名義資金固定 US$1,000，只作清楚展示比例；不代表券商碎股、稅項或市場容量可行。

- 十個固定槽，每槽 10%；未使用槽持有 QQQ，總名義持倉比率不高於 100%；
- `D` 收市封存訊號，下一個 XNYS raw open 先沽出該槽 QQQ，再買入股份；
- 第 10 個持有 session raw close 先沽出股份，再買回 QQQ；
- 每個訊號只有一次入場、一次固定退出，沒有日內優化、途中重新平衡、止賺或止蝕；
- primary 每個真實資產腿 10 bps，完整重跑每腿 25／50 bps；另按實際 child order 數重跑
  每單 US$0.01／US$0.05；
- QQQ 沽出、股票買入、股票沽出、QQQ 買回四腿全收；同一資產沒有真的轉換時不得加入
  ghost order；
- 每日 NAV、現金、應收款、持股、成本、公司行動及 terminal liquidation 必須逐日對賬；
  不借貸、不沽空、不加槓桿。

`minimal_execution_clock_control` 使用相同十槽、日期及狀態機，但所有槽一直持有 QQQ，
不執行虛構切換；扣相同初始／最終實際交易後必須逐日等於 `qqq_buy_hold`。它只驗證資金及
成交時鐘 identity，不作額外 alpha 假說。

## 7. 公平基準與配對負控制

全部路徑使用相同 XNYS sessions、US$1,000、raw-open／raw-close 時鐘、公司行動及
10／25／50 bps 成本。正式 protocol 不得在看到表現後刪除較強基準。

| 類別 | 固定路徑 | 要回答的問題 |
|---|---|---|
| 高回報機會成本 | `qqq_buy_hold` | 動態個股替換是否真正勝過持有 QQQ |
| 廣泛市場 | `spy_buy_hold` | 結果是否只來自美股整體升市 |
| 股份池 | `pit_pool_equal_weight_monthly` | actor signal 是否勝過同一 PIT 母體 |
| 成交控制 | `minimal_execution_clock_control` | 槽位、日曆及成本會計是否無幽靈交易 |
| 披露消融 | `actor_cluster_unconfirmed` | 量價確認是否提供增量 |
| 市場負控制 | `price_volume_only_matched` | 沒有 actor cluster 的相似升量股份是否同樣強 |
| 人數負控制 | `single_actor_purchase_matched` | 兩組獨立資本是否勝過單一 actor |
| 語意負控制 | `non_signal_code_matched` | A／F／M／G 等非主要 code 是否產生相同結果 |
| 隨機化控制 | `issuer_month_actor_permutation` | 把相同月份／角色／金額分布換 issuer 後是否仍可重現 |

所有 matched controls 必須與實際 allocated candidate 在同一 `D`、GICS、market-cap decile、
20-session ADV decile及必要的申報金額 decile一對一無放回配對，event、session、槽位及
持有期數相同。距離相同時以永久 ID 決勝。`matched_rate` 必須為 100%；找不到配對便整輪
`control_match_incomplete`，不得刪除 candidate、換較寬 decile 或只報已配對樣本。

Congress PTR 不可成為任一 control、特徵或補值來源。日後即使合法放行，也必須先作獨立
候選及比較 family，不能在看過 SEC 結果後把兩者合併成較好分數。

## 8. 日後事前協議最低反證要求

本設計不產生回報。若日後升格為事前協議，至少須在數據前固定：

- 完整研究期；20 年證據做不到時，使用由首次 contemporaneous observation 起的誠實較短
  分母，明示 session、訊號、issuer 及完成退出數，不得歷史回填或按結果延長；
- 各路徑的總回報、CAGR、風險免費超額 Sharpe／Sortino、波幅、最大跌幅、Calmar、換手、
  成本拖累及 US$1,000 期末值；
- 相對 QQQ 的 Newey–West lag 10、共同 Holm、63-session moving-block 20,000 paths
  max-t、固定 seed，以及不低於當時不可回減帳本的 DSR／Bonferroni trial 下限；
- 固定前後段、rolling 1／3／5 年、危機段、每腿 25／50 bps、固定費、最佳年份移除及
  issuer／actor 集中度壓力；較短前瞻分母不具備的窗口須預先標為不可判定，不能換成較易門檻；
- 候選須同時勝 QQQ、SPY、PIT 股份池及 matched controls；負控制若同等或更強，候選拒收；
- 資料、語意、時鐘、單一狀態、容量、成本、比較及私隱 mutation attacks 全數命中固定
  error code；
- 任一門檻失敗即保存負結果；不得改 Top-N、enter gate、stay rule、exit days、角色、
  金額、量價、成本或比較 family 救援。

即使歷史研究全部通過，也只可由下一個真正新增交易日、全現金開始另行評估 Paper；
不得回填歷史成交。Paper 仍須通過獨立前瞻門檻，亦不等於實金授權或保證盈利。

## 9. 現時決策邊界

| 狀態 | 現值 |
|---|---:|
| Congress PTR 法律／exact-use 准入 | 未通過；收集 0 |
| 本設計獲准 SEC 真實列 | 0 |
| 動態候選 | 0 |
| 策略運行 | 0 |
| 表現結果 | 0 |
| Paper Trading（模擬交易） | 未授權；全現金；持倉 0；回填 0 |
| 實金動作 | US$0 |
| 今日動作 | **今天不下單** |

設計文件、資料工程測試或局部 admission 不能產生人物榜、股票名單、買入／沽出比例或落盤
指示。公開報告只可呈列來源准入、覆蓋率、缺失、延遲、修訂、控制及彙總研究結果；不得公開
姓名、CIK、accession、文件路徑或可逆人物 token。本文件只作研究及專業資訊參考，不構成
投資或法律建議。
