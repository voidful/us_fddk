# 美股短線第 41 輪：Form 4 多內部人申報購買 × 公開後量價確認事前協議

凍結日期：2026-08-10

狀態：**在官方文件及隔離語意例子覆核後、任何獲授權 Form 4 資料包、候選選擇或績效
計算前凍結。**

研究角色：只定義未來可否證候選；Disclosure Phase 1 仍為 2/20、事件 0、策略運行 0。
未通過全部資料與合法使用門檻前，不得回測、產生最新標的、建立 Paper 或授權實金。
凍結前只覆核 SEC 官方文件、下載目錄結構及隔離 filing 語意例子；沒有保存或建立可供本候選
運行的真實事件包，亦沒有計算任何 cluster、選股或回報。

## 唯一研究問題

台股三個參考專案可移植的部分，是「至少兩個獨立證據同向」、「只用上一個完整時點已知
資料」、「D 後下一開市成交」及「研究結果不得回寫訊號」。台股法人、權證、鉅額交易、
融資融券、漲跌停、稅項、0050、ATR 止賺止蝕及台股參數全部不搬用。

本輪只回答：在合法、可重播的 point-in-time S&P 500 股份池內，某公司於 20 個日曆日內
有至少兩名不同 Section 16 reporting persons 申報 `P` 類購買，並於資料真正公開後出現固定
價格及成交量確認時，十個交易日的無槓桿替換式持倉能否穩健勝過 QQQ、SPY、同股池、
只用披露、只用量價及三個負控制。

Congress PTR、13F、13D 及 13G 不混入這個候選。Congress 精確用途仍需有效書面法律／授權
判定；PTR 的金額區間、配偶／受養人及延遲語意亦與 Form 4 不同。13F 是季度末持倉快照，
13D／13G 是實益擁有權／意圖快照，不能冒充逐筆內部人購買。

## 官方語意及必要資料

主來源固定為 SEC Insider Transactions Data Sets 及對應 EDGAR as-filed 文件／版本鏈。
官方季度 flat files 由 2006 年 1 月起提供 Forms 3、4、5 的結構化資料，但不是 filing 全部
metadata 的替代品，亦不能單獨證明歷史 `public_at`。SEC 明示網站沒有 first-available
timestamp，受理後亦可能有不可預測延遲；`accepted_at` 不得冒充真正公開時間。

Form 4 transaction code：

- `P` 的正式語意是 **open market or private purchase**，內部正規化固定為
  `open_or_private_purchase`，不得寫成純公開市場買入；
- `S` 同理是 `open_or_private_sale`；
- 必須保留 raw code、A/D、直接／間接持有、footnote、joint filing、amendment 及 equity-swap
  標記，不能用清洗後標籤刪去原語意。

正式運行前必須同時：Disclosure known-at 20/20、PIT／退市／公司行動 20/20、execution
extension 16/16、合法 provider package、完整 XNYS 日曆及同步 QQQ／SPY／風險免費序列。
SEC quarterly ZIP 或現時 ticker 倒推只能做資料工程控制，不能觸發本候選績效。

## 固定事件

只接受每個版本在當時已知的：

1. Form 4（包括獨立處理的 4/A），Table I 非衍生普通股；
2. transaction code `P`、acquired/disposed=`A`；
3. 股數及每股價格均為有限正數；
4. 非 equity swap／相似工具，非 Table II 衍生證券；
5. reporting person 為 director、officer、ten-percent owner 或 officer/director；
6. 原版及 amendment 逐版 append-only；最終修訂不得回填舊決策。

「企業家」不是 SEC 法定角色。本候選不按知名度、創辦人故事、姓名或事後回報挑人物；
同一 joint filing 即使列出多人，必須有至少兩個不同 `actor_token` 及兩個不同 accession／
source document 才算兩份獨立申報。每列 reported purchase dollars 固定為 shares × price，
不以事後市價重估。

## known-at 與成交時鐘

完全沿用 Phase 1：

```text
known_at = 可綁定內容 hash 的官方 public_at
        else 獨立不可回填 archived first-seen
        else 本系統 first_observed_at

decision_at = 嚴格晚於 known_at 的第一個 XNYS 正式收市
trade_at    = decision_at 後下一個 XNYS raw open
```

`transaction_date` 只界定 20 日 cluster；法定申報期限、`filed_at`、SEC `accepted_at`、季度
ZIP 發佈日及 nightly index 均不可單獨當作 `known_at`。休市、提早收市、收市同一 timestamp
才公開、late filing、4/A、PAC、刪除及再發佈都按實際版本逐列重播。不得同日開市成交。

## 唯一候選 `form4_cluster_confirmed_10d`

在 `decision_at=D` 對每個 issuer：

1. 只計當時 `known_at <= D`、reported transaction date 位於過去 20 個日曆日的合資格列；
2. 至少兩個 distinct `actor_token` 及兩份 distinct source document；
3. 每份報告購買額至少 US$10,000，cluster 合計至少 US$100,000；
4. `total-return close_D > total-return close_{D-1}`；
5. `raw close_D × volume_D` 高於之前 20 個完整 XNYS sessions、排除 D 的中位成交金額；
6. 同 issuer 上次成立後須已過 20 個 XNYS sessions，不能靠 amendment 重啟 cooldown。

若 D 不通過量價確認，該 cluster 結案，不向後逐日等待較好時點。2023-04 後的 10b5-1
checkbox 只作 checked／unchecked subgroup；早期沒有一致欄位，不能作 20 年主篩選或缺值補零。

同日訊號超過可用槽位時，事前排序固定為：distinct actors 降序、cluster reported purchase
dollars ÷ D 前 20-session 中位成交金額降序、永久 `security_id` 升序。不得按後續回報排名。

## 股份池、組合及成本

- 研究期固定 2006-01-03 至首個獲完整驗證、且不晚於 2026-06-30 的共同日期；價格及成分
  前置資料至少由 2005-01-03 起，不能縮短 20 年只保留有利期。
- 只用當時已公布並生效的 S&P 500 美國 USD 普通股；raw close > US$5、前 20 sessions
  中位成交金額 ≥ US$20m、至少 252 個總回報 sessions；同公司只保留最流通股份類別。
- 初始 US$1,000，十個固定 10% 槽；每個訊號 D+1 raw open 取一槽，持有至第 10 個 session
  raw close，其後回到 QQQ。空槽持有 QQQ；不借貸、不沽空、不集中未用權重。
- Primary 每個真實資產腿 10 bps；壓力為每腿 25／50 bps。QQQ 沽出、股票買入、股票
  沽出、QQQ 買回四腿全收。另以每 child order US$0.01／US$0.05 重建 US$1,000 路徑。
- 不設止蝕、止賺、加碼、槓桿、同日反轉或看結果改持有期。

## 八個固定比較：預留八次 trial

候選對以下八條路徑形成不可縮小的共同 family：

1. `qqq_buy_hold`；
2. `spy_buy_hold`；
3. `pit_eligible_equal_weight_monthly`；
4. `form4_cluster_unconfirmed`：相同 cluster、槽位及時鐘，但取消 D 的量價確認；
5. `price_volume_only_matched`：同日同 GICS sector、size decile、ADV decile，沒有 Form 4
   cluster 的股份，以永久 ID 決定匹配；
6. `single_actor_purchase_confirmed`：相同購買額及量價條件，但只有一名 actor；
7. `non_signal_code_confirmed`：以 A／F／M／G acquisition matched cohort 作負控制；
8. `issuer_month_actor_permutation`：固定 seed `41202608`，在同月跨 issuer 置換 actor token，
   保留角色、時間及金額分布。

各比較使用相同研究日曆、槽位、持有期、成本、公司行動及退出經濟。全專案已知下限在本輪
前為 6,240；八個比較在結果前完整預留，因此本輪及之後不得少於 **6,248**。

## 固定統計及反證門檻

全部路徑呈列總回報、CAGR、風險免費超額 Sharpe／Sortino、波幅、最大跌幅、Calmar、
US$1,000 期末值、年換手、四腿及固定費拖累、平均股票／QQQ 曝險、事件／cluster／actor
數、known-at 延遲、late／amendment／missing 比率。

每日 active return 固定 Newey–West lag 10；八比較一起計 Holm 及 63-session circular
moving-block、20,000 共同路徑、seed `41202608` 的 single-step max-t。候選對 QQQ 另計
至少 6,248 trials 的 DSR／Bonferroni。固定兩半、rolling 1／3／5 年、2008、2020、2022、
最佳三年移除、每腿 25／50 bps、固定費及 10b5-1 近代 subgroup；不得看結果換窗口。

要避免被本輪推翻，至少全部通過：

1. 所有資料、版本、known-at、PIT 成分、識別碼、成交及公司行動閘門；
2. 候選 CAGR ≥ QQQ +2.0pp、超額 Sharpe高於 QQQ；
3. 最大跌幅不比 QQQ 深超過 5pp；
4. 50 bps 後 CAGR ≥ QQQ +0.5pp；
5. 前後半各 ≥ QQQ +0.5pp，rolling 3 年勝率 ≥60%；
6. 候選同時勝 `cluster_unconfirmed`、`price_volume_only_matched` 及 PIT 等權；
7. 相對 QQQ NW t ≥1.96、Holm／max-t ≤0.05、6,248-trial DSR ≥95%；
8. 移除最佳三年、三個危機段及 US$0.01 固定費後仍不失去上述主要經濟次序；
9. 三個負控制不得顯示與候選同等或更強、同樣穩健的效果；
10. 結果前 family、門檻、seed、成本、時鐘及停止規則完全未改。

任一失敗即 `form4_cluster_candidate_rejected_no_rescue`，保留負結果，不在同一資料改兩人門檻、
20 日窗口、金額、量價、10 日持有或角色集合。即使全通過，亦只准由下一個真正新增交易日
全現金開始 Paper，且至少累積 252 個新 sessions 及 12 次完成換倉；不得回填歷史成交。

## 固定 mutation attacks

必須拒收：把 P 寫成純公開市場、以 transaction／filed／accepted time 提前訊號、同日 open、
final amendment 回填、PAC 刪除消失、現時 ticker 倒填、joint filing 重複算 actor、量價窗口
包含 D 或未來、P/K equity swap、10b5-1 缺值當 false、cluster 或 cooldown 漂移、未收四腿、
family 少於八、global trials 低於 6,248、負控制按結果置換、Paper 回填及實金越權。

## 決策邊界

本協議不是選股結果。現在 Disclosure readiness 2/20、真實事件 0、候選運行 0、Paper 全現金、
持倉 0、實金動作 US$0；不展示人物、代號、最新申報或金額試算，**今天不下單**。

## 官方參考

- SEC Insider Transactions Data Sets：
  https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets
- SEC Form 4 instructions：
  https://www.sec.gov/files/form4data%2C0.pdf
- SEC Accessing EDGAR Data：
  https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
- SEC Webmaster FAQ（自動存取、延遲及 timestamp 限制）：
  https://www.sec.gov/about/webmaster-frequently-asked-questions
