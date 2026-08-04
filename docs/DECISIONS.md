# 決策與負結果

## 2026-08-04：短線第 24 輪公平 baseline／多重檢驗只過 6/9，不升格

- 在計算任何 Holm、bootstrap 或 Reality Check 結果前，先固定 5／10／20 日、合資格池
  等權／完整現時股池等權／QQQ 三個同成本 baseline、905 個共同事件、NW lag 1／2／4、
  九假說 family、6,208 次全專案搜尋壓力，以及 52-event／20,000 路徑／seed 20260804
  共同 circular bootstrap。協議 SHA-256 為
  `1735ea7a1313aa845355074ace1d38d7fc6deef510c1227e7cd01ac1c4e64fce`，先以 commit
  `2bf27559be5b617361c0907c58ceededf32cdfea` 保存，再首次計算。
- 20 日 Top-7 對合資格池等權為 +0.319 個百分點、NW t 3.03；九假說 Holm p 0.0223、
  共同 max-t p 0.0208、Romano–Wolf p 0.0208，Reality Check p 0.0187，故不是單純在
  這個九格 family 內只挑最漂亮一格。
- 但 Top-7 對完整現時股池等權只餘 +0.238 個百分點、NW t **1.69**；歸因顯示排名效果
  +0.319 個百分點，合資格濾網效果反而為 -0.081 個百分點。完整現時股池本身仍有
  存活者偏差，這只證明不能把最有利分母當成唯一公平 baseline。
- 6,208 次全專案 Bonferroni p 為 **1.0000**，5／10／20 日合資格池亦未全數通過共同
  max-t；九項事前反證只過 **6/9**。因此保留「20 日排名在線索 family 內未被推翻」的
  窄結論，不寫成已通過全研究搜尋偏誤或可投資 alpha。
- 16/16 控制通過、16/16 突變攻擊拒收。正式就緒維持 1/18、provider 0、正式策略
  run 0、Paper 全現金、持倉 0、實金 US$0；下一步仍是取得獲授權的 point-in-time／
  退市／公司行動數據，按既有事前登記原樣運行一次。

## 2026-08-04：短線第 23 輪時間／尾部反證只過 7/8，不升格

- 在計算任何年度、block bootstrap、winsor 或刪除結果前，先固定 905 個 20 日 Top-7
  配對事件、NW lag 4／13／26／52、21 個曆年 cluster、五個市場時段、最佳 1／3 年刪除、
  1%／5% 對稱 winsor、最大 10／46 個正事件刪除，以及 52-event／5,000 路徑／seed
  20260804 circular moving-block bootstrap。協議 SHA-256 為
  `5119362c145ac7bfd4406973ab5d50ba2ec9d1ffd65c22de41c6cf03138b7273`，先以 commit
  `77679e3024318b48c6547f0e6b68f98db0aa7171` 保存，再首次計算。
- 普通平均差 +0.319 個百分點；曆年 cluster t 3.01 高於固定 t(20)=2.085963；
  52-event block bootstrap 95% 區間 +0.128 至 +0.537 個百分點，17/21 個曆年及五個
  固定市場時段平均為正。
- 貢獻最大的年份依次為 2025、2026、2009。刪除最佳一年後仍有 +0.275 個百分點、
  NW t 2.69；刪除最佳三年後只餘 +0.180 個百分點、NW t 1.947，低於事前 1.96，故
  八項主要門檻 **7/8**，不容許以「接近」或四捨五入升格。
- 對稱 winsor 1%／5% 均通過，說明結果不是單一極端列造成；但最大 46 個正事件佔全部
  正配對差 30.5%，移除後平均只餘 +0.010 個百分點、NW t 0.13，顯示幅度對上尾仍敏感。
- 15/15 控制通過、15/15 突變攻擊拒收。現有事件沒有可靠歷史永久 ID／行業身份，本輪
  沒有冒充逐股集中度分析，亦沒有修復存活者偏差。正式就緒維持 1/18、provider 0、
  正式策略 run 0、Paper 全現金、持倉 0、實金 US$0。

## 2026-08-04：20 日正面訊號通過主要合成壓力，但嚴重退出令統計證據先失效

- 在計算任何污染結果前，先固定 905 個 20 日 Top-7 事件、-25%／-50%／-80%／-100%
  四個退出回報、0.5%／1%／2%／5%／10% 五個污染率、-50%／2% 主要格、2,000 條
  共用亂數路徑、NW lag 4 及五項只可否決的門檻。候選以 1/7、同日合資格池以
  `1/(N+1)` 同時納入同一缺失股份，禁止只打擊候選。
- 父協議手寫錯最後訊號日，首次運行在載入階段以 `stress_event_order_mismatch` 停止，
  未產生亂數或壓力結果。其後先提交日期 schema-repair 附錄，只准由已綁定 SHA 的 905
  列讀取首末日；實際為 2006-08-04 至 2026-07-02。20 日、Top-7、格網、種子、統計及
  門檻全部不改。
- -50%／2% 主要格的平均配對差由 +0.319 降至 **+0.236 個百分點**，NW t 由 3.03
  降至 **2.25**；2,000 路徑平均差 95% 區間 +0.196 至 +0.273 個百分點，五項主要格
  門檻 **5/5**。這只表示固定合成格未推翻訊號，不是正式 alpha。
- 相同 2% 污染率下，-80%／-100% 退出的平均差仍為正，但 NW t 只有 **1.80／1.49**，
  已跌穿 1.96。以 -50% 退出計，平均差約在 7.70% 污染才歸零，NW t 卻約在 **2.76%**
  已失效；-100% 的兩條界線為 3.92%／**1.40%**。統計證據比平均值更脆弱。
- 協議控制 **12/12**、期限／Top-K／格網／亂數／baseline／lag 突變攻擊 **12/12
  拒收**。決定：保留 20 日排序作合格數據原樣重測線索，但真實污染率與退出分布未知；
  正式就緒仍為 1/18、逐股正式回測 0、Paper 全現金、持倉 0、實金 US$0。

## 2026-08-04：五條供應商路徑逐項補缺；公開證據 0/5 合格

- 在查看新供應商證據及寫 validator 前，先固定五條候選路徑、十四項正式能力、六級證據
  狀態、十五道控制及十五項單一替代攻擊。第十八輪的 20 年期、US$1,000、四個
  baseline、10／25／50 bps、6,208 trials DSR、PBO 及 Paper 門檻全部不改。
- CRSP Stock CIZ＋S&P DJI 事件＋CRSP Treasury 的複合路徑在公開一手文件層最多：
  **5/14 明確、5/14 部分、1/14 不符、3/14 未解**。它仍未公開證明逐列
  `AnnouncedAt`／event ID、Metadata `KnownAt`、缺失退出實收、移除後完整價格路徑、
  同步 XNYS／QQQ／SPY、精確一個月日度簡單 RF 及使用者研究授權。
- LSEG 是公開證據最完整的單一品牌候選；FactSet 具永久 ID、OHLC 及 as-of benchmark；
  Bloomberg Data License 有 20 年以上 Bulk、公司行動及 source-file tracing。但上述
  能力均未等於本研究 14/14。S&P Global Market Intelligence 的 Index Data 公開規格
  明示 `Point In Time: No`，不能以長歷史代替逐期可知成分。
- 十五道協議、來源、產品、授權、coverage、雙時鐘、raw 價、退出、日曆、RF 及決策
  控制 **15/15** 通過；十五項單一錯誤攻擊 **15/15** 按指定 error code 拒收。每日
  source probe 只核對五個官方 URL／host／identity marker；任何漂移只待人工覆核，
  不會自動改寫能力矩陣或提高 readiness。
- 決定：五條路徑最高只屬採購候選。先以九個固定問題向 CRSP＋S&P DJI 複合路徑及
  LSEG 索取授權 data dictionary 與同口徑細樣本；未有明確使用者授權，不登入、聯絡或
  購買。真實正式就緒仍為 1/18、provider package 0、完整 RF 0、正式策略運行 0；
  短線 Paper 全現金、0 持倉、實金 US$0。

## 2026-08-04：Stock CIZ 直接 5/10、overlay 5/10；Treasury 同供應商仍不可替代正式 RF

- 在寫收斂驗證器前，先固定三個台股參考 commit、兩份最新官方指南 URL／effective
  date／頁數／SHA-256、十二道控制及十二項單一替代攻擊。短線 v1、20 年期、US$1,000、
  四個 baseline、10／25／50 bps、6,208 trials DSR、PBO 及 Paper 門檻全部不改。
- CRSP Stock CIZ 指南可直接支持十份交接輸入中的五份資料字典能力：證券身份歷史、
  成分生效區間、raw 日線與交易狀態、distributions、delists。其餘五份仍須日曆或
  evidence overlay；`MbrStartDt` 不等於 `AnnouncedAt`，`SecInfoStartDt` 不等於
  `KnownAt`，缺失 `DelRet` 亦不填 0。
- CRSP Treasury 可提供個別票據 `TDRETNUA`，日度 RF 表有 4／13／26 週；但精確
  1 個月系列只在月度表，且是收益率口徑。決定不以 4 週冒充 1 個月、不把年率除 252，
  亦不以 DGS1MO、SHY、SOFR、零回報或事後選券拼接正式 RF。
- 指南／欄位／年期／單位／決策控制 **12/12**，十二項協議、版本、hash、能力、時間、
  退市、RF 及越權攻擊 **12/12** 按指定 error code 拒收。每日指南 probe 只偵測身份；
  新版只標記未合資格，不會自動提高 readiness。
- 決定：公開指南收斂不是數據交付。真實正式就緒仍為 1/18、provider package 0、完整
  RF 0、正式策略運行 0；短線 Paper 全現金、0 持倉、實金 US$0。下一步只核對已授權
  CRSP／WRDS 帳戶內的真實表、S&P 500 INDNO、五份 evidence overlay 及精確 RF 定義。

## 2026-08-04：官方 RF 真實覆蓋 5,009/5,031；缺最後 22 日仍不運行

- 第十八輪已在結果前固定一個月美國國庫券的 simple daily return、完整 XNYS 日曆及
  禁止 0／SHY 代替。今輪直接下載官方 Fama/French daily factors 202606 snapshot，
  SHA-256 為 `39f9ae1d0e9f575024bc23145980ac270cea508fb67e592578b3f4d65f36d006`；
  官方檔由 2026-05-29 推進至 2026-06-30。
- 固定 2006-08-01–2026-07-31 共有 5,031 個 XNYS session。官方 RF 可逐日對上
  5,009 個、額外 0 個，覆蓋 99.56%；仍欠 2026-07-01 至 2026-07-31 的 22 個
  session。原檔百分點只除以 100 一次，不填 0、不複製 6 月、不插值、不拼接有利替代。
- owner-only 暫存只產生 `risk_free_daily_partial.csv`、缺日清單、原始 ZIP、availability
  manifest 及 SHA-256 收據；故意不產生正式驗證器接受的 `risk_free_daily.csv` 或
  `risk_free_manifest.json`。來源／定義／單位／session／權限／決策控制 **8/8**，八項
  ZIP、日期、數值、路徑及越權攻擊 **8/8** 按指定 error code 拒收。
- 公開下載已核實，但沒有把它推論為明確本地研究授權條款。決定：完整 RF 包仍為 0，
  真實正式就緒維持 1/18；RF 補齊亦不能取代逐股 point-in-time／退市 provider package。
  正式策略運行 0、短線 Paper 全現金、實金 US$0。

## 2026-08-04：正式回測事前登記及合成就緒 18/18；真實仍為 1/18

- 第十七輪 package 已可誠實區分 provider／synthetic，但仍缺正式超額 Sharpe、PSR 及
  DSR 所需的風險免費日回報；QQQ／SPY 是風險資產，0 及 SHY 亦不可偷代。因此本輪在
  任何正式結果出現前，新增與 XNYS session 一對一的 US 1M T-bill decimal simple
  daily return package，固定來源、版本、授權、列數及 SHA-256。
- 原協議的「同一十隻股份等權漂移」曾在現時股池沙盒被實作成整個今日完整股池起點等權。
  正式 baseline 在結果前明確定義為：第一個正式訊號 Top-10 各 10% 只買一次，其後只
  處理派息、拆股、退出及 successor，不再主動輪選；現金退出款固定 0% 回報。
- 四個 baseline、US$1,000、t+1 raw open、10／25／50 bps、公司行動單次入賬、固定
  兩半／滾動／危機段、6,208 trials DSR 及四條既有路徑十段 CSCV PBO 全部事前凍結。
  合成控制 **18/18**，RF、路徑、來源、run ID、baseline、成本、統計及決策邊界攻擊
  **18/18** 按指定 error code 拒收。
- 決定：合成 18/18 不是策略成績。合法 provider package 0、同步 RF 包 0、真實就緒
  1/18、point-in-time 1/20、正式策略運行 0。輸入齊全後只准 immutable run ID 一次
  固定回測；任何門檻失敗即封存，不在同一資料上救援。Paper 全現金、實金 US$0。

## 2026-08-04：本地隔離匯入合成 16/16、攻擊 16/16；真實匯入仍為 1/16

- 稽核發現第十五輪 execution manifest 把 status 固定為
  `synthetic_execution_extension_built`，auditor 亦只接受該值。這是正確的合成測試
  標示，但不能把未來授權供應商包誠實標成真實來源。本輪不改寫第十五輪 bridge、
  manifest、報告或 16/16 收據，另立 provider-mode bridge。
- 新 bridge 明確分開 `synthetic_local_quarantine_extension_built` 與
  `authorized_provider_local_quarantine_extension_built`。正式 CLI 只接受使用者明確提供、
  repository 外的 response、CIZ、QQQ／SPY overlay 及新輸出四個絕對路徑；不掃描、
  不下載、不覆寫。輸出原子建立，目錄 0700、檔案 0600，原始列不進 Git 或 Action。
- 合成匯入通過 **16/16**，同時保留 base ledger 20/20 及 extension 16/16。相對路徑、
  repo 內路徑、symlink、輸出已存在、response hash、synthetic 冒充 provider、身份、
  授權、時間、CIZ 收據、前視成分、QQQ 缺日、舊 status 冒充及 world-readable 權限攻擊
  **16/16** 按事前固定代碼拒收。
- 決定：合成 16/16 不提高真實狀態。現時四個外部路徑未提供、provider-mode run 0、
  真實匯入 1/16、文件 1/12、逐股數據 1/20、正式回測 0、短線 Paper 全現金、實金
  US$0。未來 provider 16/16 亦只准進入一次凍結正式回測，不自動建立或回填 Paper。

## 2026-08-04：授權數據交接合成 12/12、攻擊 12/12；真實文件仍為 1/12

- 在新公開文件核對及實作前，先固定 CRSP／WRDS 來源範圍、十份 CIZ／證據輸入、
  QQQ／SPY execution overlay、十二道文件閘門、十二項攻擊及四份公開輸出；短線 v1、
  20 年期、成本、基準、統計及 Paper 門檻全部不變。
- WRDS 官方公告確認 CIZ Flat File Format 2.0 已取代 SIZ；官方 CIZ macro 公開列出
  `crsp.dsf_v2`、`crsp.msf_v2`、`StkSecurityInfoHist`、`a_stock_v2` 及 `a_indexes_v2`
  候選。公開產品目錄亦列出 `crsp_m_stock`、`crsp_m_indexes`，但完整 data dictionary
  要登入，因此只記為候選，不推論為使用者已有訂閱或十份輸入可完整交付。
- 合成文件能力回覆通過 **12/12**；多餘 key、request 漂移、授權／UTC、SIZ、少檔案、
  成分時間、覆蓋期、pay-date、DelRet 及 QQQ／SPY 價格政策攻擊 **12/12** 按指定
  error code 拒收。每項攻擊均重算 response SHA-256，沒有用 generic hash 錯誤掩蓋。
- 決定：固定請求已準備好，但尚未對外發送；供應商聯絡 0、文件回覆 0、合法樣本 0。
  真實文件只有事前凍結 1/12、逐股數據維持 1/20、正式回測 0、短線 Paper 全現金、
  實金動作 US$0。取得使用者授權後才可發送；文件 12/12 亦只准進入本地隔離細樣本。

## 2026-08-04：execution extension 合成 16/16、攻擊 16/16；真實數據仍為 1/20

- 在寫 bridge 前固定十六道控制、十六項單一錯誤攻擊及五份 extension 輸出；短線
  v1 訊號、Top-10、行業上限、成本、baseline、統計及 Paper 門檻全部不變。
- 不修改第十三輪 adapter 或原八份賬本，改用獨立 `ledger/`＋`execution/` package；
  manifest 以 SHA-256 綁定兩層，保留各輪結果的可追溯性。
- 三個合成 PERMNO 控制保留 ex-date 2026-07-30、pay-date／現金可用日 2026-08-03；
  每個月末候選至少 272 個回報及正成交量 session；移除後 13/13 個 session 覆蓋至
  2026-08-03 open；QQQ／SPY 共 46 列同步行情。
- 十六項多／少檔案、base binding、缺 pay-date、日期倒置、金額不符、251／19 日、
  移除缺價／open、SPY 缺日、QQQ 重複、非正 raw 價、補位錯綁、同日成交、成本漂移及
  非月末訊號攻擊 **16/16** 按指定 error code 拒收。
- 決定：合成 16/16 只代表 execution extension 可 fail closed，不把第十四輪舊賬本
  8/12 改寫成通過。真實入口仍為 1/20、合法供應商樣本 0、正式回測 0、短線 Paper
  全現金、實金動作 US$0；下一步只接受合法細樣本，不先跑策略。

## 2026-08-04：退出會計 8/12、攻擊 10/10，Round 13 的 20/20 不足以執行

- 在寫 auditor 前固定十二道執行閘門、十項單一攻擊及五個算術控制；短線 v1 的
  45/25/20/10 權重、Top-10、行業上限、成本、baseline、統計及 Paper 門檻全部不變。
- 官方 WRDS CIZ event-study 範例明示日回報已含退市回報。現行 adapter 正確隔離
  `DlyDelFlg=Y` storage row，只從 outcome 結算 `DelRet` 一次：100 元、-50% 終端值為
  50，而不是錯誤雙計後的 25。缺 `DelRet` 的現金及換股收購、拆細與分拆例子亦對數。
- 十項雙計、填 0、提早釋放股息、缺 successor、缺歷史、移除後缺價、缺 benchmark、
  同日成交／前向填補攻擊 **10/10** 按指定 error code 拒收。
- 十二道只過 **8/12**。未通過：dividend ex/pay-date 分離、每股訊號前 252 日、
  `removed_continues` 至下一月度 open 的價格、QQQ／SPY／QQQ 補位同步行情。
- 決定：Round 13 的 20/20 只代表八份資料賬本通過既有完整性合約；正式回測另須本輪
  12/12。現況仍是真實入口 1/20、合法樣本 0、正式回測 0、短線 Paper 全現金、
  實金動作 US$0。下一步先凍結 adapter v2／execution extension，不得先跑策略。

## 2026-08-04：CRSP CIZ 映射 20/20、攻擊 12/12，真實數據仍為 1/20

- 在寫 adapter 前先凍結現行 CIZ Flat File Format 2.0、十份本地輸入、四類 evidence
  overlay、十二項攻擊及停止規則；短線 v1、固定 20 年、公平 baseline、10／25／50
  bps、統計及前瞻 Paper 門檻全部不變。本輪沒有登入 WRDS、下載付費列或取得供應商
  樣本。
- 官方公開 guide 證明 PERMNO／PERMCO、歷史 security info、raw 日線 OHLCV、
  MbrStartDt／MbrEndDt、DelistingDt／DelDlyDt／DelRet／DelRetMissType 等欄位；但公開
  membership 表格未列逐次 announcement timestamp。DelDlyDt 只是退市回報在日檔的
  儲存日，慣例為退市後下一交易日，不能當成退出事件日期。
- adapter 因此只容許直接欄位及固定派生；membership announced_at、security-info
  KnownAt、公司行動公告／正規化條款、缺失 DelRet 的現金／換股代價必須另有可追溯
  overlay。禁止用生效日冒充公布時間、用現時 ticker／分類倒填、把 adjusted 價當 raw、
  把缺失 DelRet 補 0 或用 DelDlyDt 作退出日。
- 合成 CIZ 包成功轉成八份既有賬本並通過 **20/20**；十二項 schema、時間、歷史倒填、
  raw 價及退市語義攻擊 **12/12** 按指定 error code 拒收。合成包不含供應商列，結果
  不計入策略回報、PSR／DSR／PBO 或 Paper 樣本。
- 決定：映射橋通過，但真實 CRSP／WRDS 數據、正式回測及策略均未通過。真實入口維持
  **1/20**，合法樣本 0、正式 20 年逐股回測 0、短線 Paper 全現金、0 成交、0 持倉、
  實金動作 US$0。下一步只接受合法 CIZ 小樣本加完整 overlay；完整證據見
  `docs/SHORT_TERM_CRSP_CIZ_MAPPING_REPORT.md`。

## 2026-08-04：CRSP 樣本驗收 12/12 拒收，真實數據仍為 1/20

- 在修補驗收程式前先固定十二種攻擊、指定失敗閘門及停止規則；既有短線 v1、20 年
  主期、公平 baseline、10／25／50 bps、統計與前瞻 Paper 門檻全部不變。本機沒有
  WRDS／CRSP 憑證或套件，本輪沒有查 catalog、下載付費數據或取得供應商樣本。
- 原入口只手動檢查 manifest top-level，未完整執行巢狀 schema；identifier、membership
  及 classification 的 timestamp 又曾正規化成日期，同日較遲才知的數據可能被誤收。
  本輪強制授權欄位／額外欄位、UTC offset、匯出先於匯入、manifest 截至日對齊交易日曆，
  並以紐約生效日午夜作無前視比較。
- 退出側新增 successor 必須存在於永久主檔、`still_member` 不得夾帶退出數據、永久退出
  日須對齊 membership 終止日，以及缺失退市回報與最後交易日後行情的硬拒收。CRSP
  官方文件明示 DelRetMissType，故不能假定品牌本身消除退出偏差。
- 合成控制包通過 20/20；十二個 manifest、時間、永久 ID、退出經濟及幽靈價格攻擊
  **12/12** 在指定閘門被拒收。此結果只驗證程式，不含供應商原始列，也不計入策略
  PSR／DSR／PBO 或 Paper 樣本。
- 決定：驗收器通過，但 CRSP／WRDS、正式數據及策略均未通過。真實入口維持 **1/20**，
  合法樣本 0、正式 20 年逐股回測 0、短線 Paper 全現金、0 成交、0 持倉、實金動作
  US$0。下一步只索取凍結的 schema、細樣本及授權條款；完整證據見
  `docs/SHORT_TERM_CRSP_SAMPLE_ACCEPTANCE_REPORT.md`。

## 2026-08-04：四條數據來源預審 0/4，CRSP／WRDS 只作首輪查詢

- 在閱讀任何新供應商文件前，固定 CRSP／WRDS、Norgate、Nasdaq Data Link Sharadar
  及 Polygon.io Stocks 四條路徑、既有 20 道 point-in-time／退市閘門、五種狀態詞與
  停止規則。首次檢查發現 CRSP 官方內容已遷移至 Morningstar Indexes、Polygon.io
  已遷移至 Massive；原 domain scope 先按設計失敗，之後另立只容許兩個精確 alias 的
  schema-informed repair，不增加來源、不改閘門或策略，故不是獨立 first-seen 證據。
- CRSP 股票 guide 明確支持 PERMNO／PERMCO、歷史證券資料、membership 起訖、raw
  OHLCV、總回報、公司行動、分類及 D+1 開市，合計 10/20 明確、2/20 部分；但沒有找到
  S&P 500 成分公布時間，DelRetMissType 亦代表部分退出回報可能缺失。未取得合法授權、
  20 年細樣本與逐列稽核前，只可作第一個正式查詢對象，不能宣稱通過。
- Norgate 官方明示沒有歷史成分公布日期、舊 ticker、完整公司行動事件或 delisting
  return，最後交易 bar 近似不能代替破產全損、現金收購或換股代價。Sharadar 公開
  metadata 未證明歷史 S&P membership 與退出經濟回報；Massive 可補日價、reference、
  股息及拆股，不能單獨修復成分與退出偏差。
- 決定：四條路徑採購前通過 **0/4**，本地驗證全部 false，真實逐股數據仍為 **1/20**。
  正式 20 年逐股回測 0 次、短線 Paper 全現金、0 成交、0 持倉，實金動作 US$0。
  下一步只向 CRSP／WRDS 索取 data dictionary、細樣本及授權條款；完整證據見
  `docs/SHORT_TERM_PROVIDER_QUALIFICATION_REPORT.md`。

## 2026-08-04：每日動量環境共振近期失效，schema repair 只過 27/48

- 參考三個台股專案，但不照搬市場結構：在任何新日檔前固定唯一候選，以 French
  `Hi PRIOR 12–2` 配合市場高於 20／60 日平均、十組至少 60% 高於各自 60 日平均，
  以及 Hi PRIOR 相對同池等權在 5／10／15／20 日至少兩窗領先。總分只對應
  0／50／100% 持倉，所有訊號延遲一日，不借款、不沽空、不加止蝕或事後例外。
- 同時固定 5% 年度學術實作拖累、10 bps 主要轉倉成本、25／50 bps 壓力、2／5／10%
  拖累敏感度、1963–2006 早期、2006–2026 近期、QQQ、SPY、French 市場、十組
  等權、永久 Hi PRIOR、相同持倉比率市場、固定平均持倉、60 日二元開關、拆除共振，
  以及 NW／PSR／6,208 次搜尋校正 DSR／四路 PBO 共 48 道門檻。
- 首次官方 ZIP、member 及 SHA-256 正確，但官方 marker 是 `Average Value Weighted
  Returns -- Daily`，原映射少了 `Average `。原輪按設計在解析回報及計算策略前以
  **4/9** 停止。看過 schema 後另立 repair，只容許精確增加該前綴，不重新下載、
  不改候選或門檻；因此 `independent_first_seen_evidence=false`。
- Repair 後數據 10/10。1963–2006 候選 CAGR 14.59%，市場 10.60%，但後半已落後
  1.77 個百分點，NW t 1.64、DSR 2.65%、PBO 61.90%，早期只過 10/15。
  2006–2026 候選 CAGR 0.58%、最大跌幅 −49.8%，QQQ CAGR 16.81%；兩個固定十年
  分別落後 12.95／19.69 個百分點，204 個滾動三年窗只有 4.90% 勝出，NW t −4.21、
  PSR 0.01%、DSR 接近零，近期只過 5/19。
- 金融海嘯、新冠急跌及 2022 年候選最大跌幅都比 QQQ 淺，證明減倉腿有風控作用；
  但回報犧牲過大，近期三因子 alpha −4.00%，並同時輸永久 Hi PRIOR、相同持倉
  French 市場及固定平均持倉。機制只過 2/4，總計 **27/48，失敗**。
- 決定：結果封存，不改 20／60 日、廣度、共振、成本或日期救援。French 組合不是
  可買證券，逐股 point-in-time／退市入口仍為 1/20；正式逐股回測 0 次、短線 Paper
  0 成交、持倉 0、實金動作 US$0。完整證據見
  `docs/SHORT_TERM_DAILY_MOMENTUM_REGIME_RESEARCH_REPORT.md`。

## 2026-08-04：逐股 point-in-time／退市數據入口只過 1/20

- 第八輪已證明全池 12–2 排名傾斜的早期優勢沒有延續至近期；本輪禁止再在同一已見
  French cells 上調權重或集中度。既有個股 v1 的 12–1／6–1、200 日趨勢、63 日低波幅、
  月度 Top-10，及台股 20 日 Top-7 訊號層診斷全部保持不變。
- 在任何已授權逐股數據匯入前，凍結 `SHORT_TERM_POINT_IN_TIME_LEDGER_CONTRACT.md`
  及 manifest schema。入口固定 20 道，涵蓋合法授權、精確檔案集合、SHA-256、永久
  security ID、歷史 ticker、成分公布／生效時間、2006-08-01–2026-07-31 交易日、每日
  495–510 隻成分、至少 99.5% 在籍價格／停牌、原始價、公司行動、每段 membership
  outcome、退市／收購經濟回報、幽靈價格、歷史行業、股份類別及 D+1 成交。
- 驗證器正反測試通過：完整合成 fixture 20/20；CSV 雜湊改變、成分事後才知、同日
  ticker 重疊、永久退出沒有經濟回報、最後交易日後仍有價格，全部失敗關閉。合成 fixture
  只驗證程式，不計作市場數據或策略證據。
- 現時沒有配置合法 point-in-time／退市供應商數據包，所以真實入口 **1/20**；唯一通過
  是凍結收據及三組文件雜湊。正式 20 年逐股回測 0 次、短線 Paper 0 成交、持倉 0，
  實金動作 US$0。數據 20/20 後亦只准沿用 v1 重跑一次；經濟／統計門檻及 252 日／
  12 次前瞻 Paper 門檻仍全部適用。完整記錄見
  `docs/SHORT_TERM_POINT_IN_TIME_READINESS_REPORT.md`。

## 2026-08-04：全池 Size × Momentum 傾斜只過 23/48

- 參考 `tst_wocker_filter_lab`「Top 7 路徑噪音可能高於全池傾斜」的未解問題，
  在任何新 ZIP 或數值列前固定唯一候選：French value-weighted 25 Size × Prior
  12–2 cells，五個 size 各佔 20%，每個 size 內按 prior 五分位使用 1:2:3:4:5
  權重。等權、平方、Top 2、Top 1、短窗 Prior 1–1、French 市場、QQQ／SPY、
  10／25／50 bps、固定分段、30 路 PBO 及 48 道門檻同時凍結；全域搜尋懲罰
  增至 6,204 次。
- 官方 `25_Portfolios_ME_Prior_12_2_CSV.zip` 首次下載只進行一次；兩個月表各
  1,193 月、25 欄，正式 1963-01–2026-05 共 761 月零缺值。URL、member、
  SHA-256、欄序、固定權重、日期、形成時序及重用快照合計 10/10 通過。
- 1963–2005 候選 CAGR 12.36%，高於市場 10.82%、全池等權 10.01%及短窗傾斜
  8.43%；但低於 Top 2 的 14.80%及 Top 1 的 16.82%，只保留 Top 1 CAGR 的
  73.5%，Sharpe 及最大跌幅亦未勝集中組合。主要期通過 9/19。
- 2006–2026 候選 CAGR 8.31%，只略高於全池等權 7.66%及短窗傾斜 7.34%，
  低於市場 11.38%、SPY 11.26%及 QQQ 16.18%。兩個固定分段都落後市場；60 月窗
  勝市場 11.29%，NW t −1.71，DSR 接近零，PBO 23.81%。50 bps 成本後 CAGR
  −1.63%，US$1,000 只餘約 US$715。近期通過 4/19。
- 集中度前沿是關鍵反證：主要期由等權 10.01%至 Top 1 16.82%單調上升；近期
  線性／平方／Top 2 只在 8.31%–8.50%，Top 1 反降至 8.18%。Prior 五分位近期
  亦由第三分位開始轉平，不能把早期集中紅利推論為現代高回報策略。全歷史五因子
  alpha −1.87%、市場 beta 1.01、SMB beta 0.51、R² 98.29%，大部分風險不是
  獨立 alpha。
- 決定：數據 10/10、主要 9/19、近期 4/19，總計 **23/48，失敗**。French cells
  不是證券，沒有逐股 point-in-time／退市、公司行動、流動性及精確買賣差價；
  `paper_eligible=false`、`trade_ready=false`、實金動作 US$0。完整證據見
  `docs/SHORT_TERM_FRENCH_SIZE_MOMENTUM_TILT_RESEARCH_REPORT.md`。

## 2026-08-04：大型股 Size × Prior 首次驗證只過 14/44

- 在任何新 ZIP、schema 或數值列前，固定唯一候選為 French value-weighted
  `Big Hi PRIOR 1–1`；25 cells、Big row 等權、全池等權、Big Lo、未分 size
  的短窗贏家、12–2 長窗贏家、QQQ／SPY、10／25／50 bps、固定分段及 44 道
  門檻全部預先提交。全域搜尋次數由 6,150 增至 6,175。
- 官方 `25_Portfolios_ME_Prior_1_0_CSV.zip` 只下載一次；兩個月表各 1,204 月、
  25 欄、零缺值，正式 1963-01–2026-05 共 761 月完整。URL、member、SHA-256、
  欄序、日期、既有因素及 QQQ／SPY 快照合計 10/10 通過。
- 1963–2005 候選 CAGR 4.61%，低於市場 10.82%、大型股同 size 等權 8.01%、
  全 25 cells 等權 10.12%、Big Lo 9.36%及 12–2 贏家 16.45%；最大跌幅
  −68.70%，17 道只過 PBO。兩個固定分段分別落後市場 5.87／6.59 個百分點，
  60 月窗勝市場只有 7.22%。
- 2006–2026 候選 CAGR 9.71%，仍低於市場 11.38%、SPY 11.26%及 QQQ
  16.18%；只勝全 25 cells 等權與 Big Lo，並通過跌幅限制，合計 3/17。
  近期 50 bps 後 CAGR −0.36%，對市場／大型股等權成本 break-even 只有
  3.71／15.32 bps；60 月窗勝市場 16.13%，NW t −0.66，DSR 0.0005%，PBO
  23.81%。
- Size 拆解沒有支持事後換組：1963–2005 五個 size 的 Hi−Lo CAGR 全為負；
  2006 後才在部分 size 轉正，Big Hi−Lo +6.23 個百分點主要反映 Big Lo 很弱，
  候選本身仍落後市場及 QQQ。五因子 alpha −1.57%，ST_Rev beta −0.59。
- 決定：數據 10/10、主要 1/17、近期 3/17，總計 **14/44，失敗**。
  `independent_first_seen_evidence=true` 只代表凍結順序有效，不代表可交易；French
  cells 不是證券，也沒有逐股 point-in-time／退市、公司行動、流動性及精確成本。
  `paper_eligible=false`、`trade_ready=false`、實金動作 US$0。完整證據見
  `docs/SHORT_TERM_FRENCH_SIZE_PRIOR_RESEARCH_REPORT.md`。

## 2026-08-04：短窗贏家 schema repair 可計算，但經濟診斷只過 11/38

- 2026-08-03 的 French prior-return 首次下載已按凍結契約在 6/8 停止；兩個
  value-weighted 月表 marker 與事前映射不符，當時沒有解析數值或計算策略。
  原收據、協議及五份 ZIP 雜湊永久保持原樣。
- 看過 schema 後另立 `schema-informed engineering diagnostic`：只准把 parser
  改為原檔兩個精確 marker，不重新下載、不模糊搜尋，也不更改 `VW Hi PRIOR
  1–1` 候選、六路敏感度、四個 baseline、10／25／50 bps 成本、固定時期、
  15+15 道門檻或 6,150 次搜尋校正。Repair 協議在任何策略數字前提交為
  `66779aa3800a0abadaed0387a12f70f07d2bd978`，但結果固定不是獨立首次證據。
- 1963–2005、10 bps 的候選 CAGR 4.14%，低於市場 10.82%、同母體十分位等權
  8.64%、短窗輸家 9.24%及 12–2 長窗贏家 16.45%；最大跌幅 −68.83%，15 道
  只過 PBO 一項。兩個固定分段都落後市場及等權，零候選成本亦無法追上四個
  baseline。
- 2006–2026 候選 CAGR 9.41%，仍低於市場 11.38%及 12–2 長窗贏家 10.88%；
  只勝短窗輸家並通過最大跌幅限制，合計 2/15。2006–2015 CAGR 只有 1.53%，
  2016 後才反彈；60 月窗勝市場只有 15.59%，NW t −0.41，近期 PBO 27.78%。
- 完整月度換倉令假設年換手接近 24 倍。近期相對市場及 12–2 贏家的每月單邊
  成本 break-even 只有 2.56／4.44 bps；50 bps 下近期 CAGR −0.63%，全歷史
  CAGR −3.90%。五因子年率化 alpha −1.90%，ST_Rev beta −0.67，R² 86.66%。
- 決定：數據工程 8/8、主要 1/15、近期 2/15，總計 **11/38，失敗**；
  `independent_first_seen_evidence=false`、`paper_eligible=false`、
  `trade_ready=false`、實金動作 US$0。不把線性傾斜的事後較高值升格；下一關
  只接受已授權逐股 point-in-time 成分、退市／收購、公司行動及精確成交成本，
  另立首次未見協議後才可由全現金開始 Paper。完整報告見
  `docs/SHORT_TERM_FRENCH_PRIOR_RETURN_SCHEMA_REPAIR_RESEARCH_REPORT.md`。

## 2026-08-03：v25 三條實際 20 年產品路徑通過，啟動隔離 Paper

- v25 在第一次下載 VUG／IWF／SPYG 與黃金產品聯合日線前，固定唯一候選為
  每月 80% 美國大型成長 ETF／20% 實物黃金 ETF。不借款、不放空、不用槓桿
  ETF、不擇時、不停損，也不搜尋權重。正式月報酬固定 2006-08–2026-07 共
  240 個月；全域搜尋次數由 6,131 增至 6,132。
- Vanguard 路徑 80% VUG／20% GLD、iShares 路徑 80% IWF／20% IAU、
  State Street 路徑 80% SPYG／20% GLD，事前各設 12 道門檻，全部 12/12
  通過。三條路徑都不是合成指數；VUG 6:1 拆股調整、日期、OHLC、240 個完整
  月末與快照雜湊皆通過。
- 三路徑等權敏感度彙總 CAGR 12.94%、SPY 11.25%，Sharpe 0.934 對 0.776，
  最大回撤 −37.41% 對 −50.78%。50 bps 壓力後仍領先 1.60 個百分點；前十年
  領先 1.87 個百分點、後十年領先 1.50 個百分點；181 個五年窗勝率 72.93%、
  中位差 1.40 個百分點，彙總 10/10 通過。
- 公平基準不是只用 SPY：相同 80% 成長股／20% SHY 彙總 CAGR 11.18%、
  Sharpe 0.860、最大回撤 −38.82%。v25 在複利與 Sharpe 都較高，回撤也略淺；
  相對此控制的 Newey-West t = 2.40。這支持黃金袖套的歷史貢獻，不只是少持
  20% 股票。
- 仍保留反證：相對 SPY 的 Newey-West t 只有 0.98；以全專案 6,132 次搜尋
  懲罰後 DSR 機率約 0.41%。最差五年窗仍曾落後 SPY 1.67 個百分點，黃金也可能
  長期落後或與股票同跌。因此歷史入口通過不等於實金可用。
- 通過後另做不參與凍結門檻的透明診斷：100% 大型成長 ETF 彙總 CAGR 13.30%，
  高於 v25 的 12.94%；v25 犧牲約 0.36 個百分點年化，換到 Sharpe 高 0.10 與
  最大回撤改善約 10.07 個百分點。181 個五年窗只有 19.34% 勝純成長；策略自身
  最長低於前高 35 個月，相對 SPY 最長水下 168 個月，相對純成長則 179 個月且
  期末尚未復原。這些結果明確否決「跑贏所有 ETF」的說法，定義與解讀見
  `docs/V25_POST_ENTRY_DIAGNOSTICS.md`。
- 決定：三路徑 12/12、彙總 10/10、資料 8/8，`paper_eligible=true`、
  `trade_ready=false`。建立相同起點的 v25、SPY、80% VUG／20% SHY 三個隔離
  LIVE Paper 帳戶；截至 2026-07-31 都只有待下一個真正新增交易日成交的委託，
  前瞻 sessions 0、成交 0。至少 252 個新增交易日與 6 次完成再平衡前，網站只
  顯示 Paper，不顯示實金指令。正式證據見
  `docs/V25_GROWTH_GOLD_DIVERSIFICATION_PROTOCOL.md`、
  `docs/V25_PRODUCT_MAPPING.md`、`artifacts/v25_data_receipt.json`、
  `artifacts/v25_growth_gold_diversification_validation.json` 與
  `artifacts/v25_growth_gold_diversification_report.html`；三帳戶同步進度另寫入
  `artifacts/v25_forward_paper_evidence.json`。
- 日更上線鏈已補入 v25：VUG／GLD／SPY／SHY 只下載一次並凍結成共同快照，三個
  帳戶先在記憶體全部通過日期、快照、成本、初始資金與交易日序列檢查才寫入。
  網站重建後另做 v25 專用交叉稽核，逐日證據寫入不可靜默改寫的 SHA-256 鏈；
  舊主鏈與 v25 兩份部署收據必須同時通過才可建立私人版本。完整操作規範見
  `docs/V25_LIVE_OPERATIONS.md`。

## 2026-08-03：v24 學術品質動能有效，但實際 ETF 沒有保留穩健優勢

- v24 吸收參考專案「訊號、部位、退出、驗證分層」以及「固定資料快照、保留負結果」
  的做法，在任何本輪學術資料、QUAL／MTUM、SPHQ／PDP 日線下載或組合計算前，
  固定唯一候選為每月 50% 品質／50% 動能；不擇時、不停損、不槓桿、不做空，
  也不搜尋權重。全域搜尋次數由 6,130 增至 6,131。
- 20 年學術入口使用 2006-05–2026-04 共 240 個月：Ken French 的大型股高營運
  獲利能力與大型股高 12–2 動能各半，機械扣除年化 0.15%，對照市場總報酬。
  候選 CAGR 11.99%、市場 10.99%，Sharpe 0.816 對 0.743，最大回撤
  −44.35% 對 −50.31%；前後半都領先，181 個五年窗勝率 72.38%，十道事前
  經濟門檻全部通過。1964-07–2006-04 的較早診斷也保留正方向。
- 但學術因子不是可直接買到的產品。iShares 實際 QUAL／MTUM 段
  2013-08–2026-07，50/50 CAGR 14.60%、SPY 14.04%；Sharpe 略低、最大回撤
  較深，後半落後 0.73 個百分點，97 個五年窗只有 45.36% 勝出，十道門檻只過
  五道。另一管理人的 SPHQ／PDP 段 2007-04–2026-07，CAGR 9.92%、SPY
  10.97%，前後半與滾動穩定性都失敗，七道門檻 0/7。
- 學術主動報酬的 Newey-West t 值只有 0.93；經全專案 6,131 次搜尋懲罰後，
  不能用學術代理的完整期成功掩蓋產品實作落差。資料與治理 8/8 通過，只代表
  結果可重現，不代表策略可交易。
- 決定：學術 10/10、iShares 5/10、Invesco 0/7、資料 8/8；
  `paper_eligible=false`、`trade_ready=false`。不建立 v24 Paper、不顯示
  QUAL／MTUM 50/50 為今日配置。正式證據見
  `docs/V24_QUALITY_MOMENTUM_FACTOR_PROTOCOL.md`、`docs/V24_PRODUCT_MAPPING.md`、
  `artifacts/v24_data_receipt.json`、
  `artifacts/v24_quality_momentum_factor_validation.json` 與
  `artifacts/v24_quality_momentum_factor_report.html`。

## 2026-08-03：v23 管理期貨改善回撤，但沒有穩健跑贏 SPY

- v23 在任何 KMLM／FMF 日線下載與聯合組合計算前，固定唯一候選為每月
  50% SSO／50% KMLM，不借款、不做空 ETF，也不搜尋其他權重。長期入口固定
  2006-07–2026-06 共 240 個月；股票袖套使用實際 SSO，管理期貨袖套使用
  KraneShares 官方月表中 2005 年起同一 EV 方法的 KFA MLM Index，並機械扣除
  年化 1.05%。全域搜尋次數由 6,129 增至 6,130。
- 20 年候選 CAGR 11.31%、SPY 11.27%，只領先 0.04 個百分點，低於事前要求的
  0.25%；Sharpe 0.813 對 0.777，最大回撤 −41.51% 對 −50.78%，確實改善風險
  路徑。但提高到 50 bps 成本後 CAGR 反而落後 0.18 個百分點，前十年領先
  1.68 個百分點、後十年轉為落後 1.69 個百分點；181 個五年窗勝率 58.0%，
  低於凍結的 60%。長期入口只過 6/10。
- KMLM 實際產品段 2021-01–2026-07 的完整期候選 CAGR 15.33%、SPY 14.70%，
  最大回撤 −12.50% 對 −23.93%；但後半段落後 4.72 個百分點，八個五年窗沒有
  一個以 10 bps 門檻勝出。KFA 指數與 KMLM 月報酬相關 0.978，幾何追蹤差卻達
  年化 2.86%，超過事前 2.00%；產品橋接只過 7/10。
- FMF 是不同管理人的外部方向檢查，不假裝可與 KMLM 互換。2013-09–2026-07
  候選 CAGR 13.25%、SPY 14.40%，前後半與 96 個五年窗都沒有保留跑贏方向，
  七道門檻只過最大回撤與 Calmar 兩道。全專案 6,130 次搜尋懲罰後，長期主動
  DSR 機率約 0.007%，不能用風險改善取代超額報酬證據。
- 決定：20 年 6/10、KMLM 7/10、FMF 2/7、資料 7/7；
  `paper_eligible=false`、`trade_ready=false`。不建立 v23 Paper、不顯示
  SSO／KMLM 50/50 當成今日訊號。正式證據見
  `docs/V23_MANAGED_FUTURES_CAPITAL_EFFICIENCY_PROTOCOL.md`、
  `docs/V23_PRODUCT_MAPPING.md`、`artifacts/v23_data_receipt.json`、
  `artifacts/v23_managed_futures_capital_efficiency_validation.json` 與
  `artifacts/v23_managed_futures_capital_efficiency_report.html`。

## 2026-08-03：pre-v23 單一股指擇時／降風險家族封存

- v22 未通過五年滾動穩定性後，只在既有六個美國廣泛市場與九產業資料探索五個
  機制：趨勢切換 2 倍／1 倍、連續波動縮放、低波動加槓桿、每月 2 倍／SHY
  衛星切換、以及只在狀態改變時交易。全域搜尋次數由 6,124 增至 6,129。
- A／B 雖在多數完整期改善 CAGR、Sharpe 與回撤，15 組的五年滾動門檻分別
  只有 1／15 與 0／15；C 的五年勝率較好，卻在 15／15 組都未改善最大回撤。
- D／E 能改善部分大型股回撤；狀態變化版 S&P 500 CAGR 11.74% 對核心
  11.25%、最大回撤 -45.0% 對 -55.2%、五年勝率 65.0%。但它未通過 50 bps，
  又低於固定 80/20 的 12.35%；中小型三組都只過 2/9 且 CAGR 低於核心。
- 金融、能源等局部成功是看過結果後才知道，禁止用來縮窄市場或再調參數。
  決定封存整個單一股指擇時／降風險家族：`paper_eligible=false`、
  `trade_ready=false`，不建立 Paper、不顯示今日配置。下一個假說必須引入不同
  報酬來源。完整紀錄見 `docs/PRE_V23_EQUITY_OVERLAY_DESIGN_EXPLORATION.md`
  與 `artifacts/pre_v23_equity_overlay_design_receipt.json`。

## 2026-08-03：v22 九產業完整期勝出，但五年穩定性否決 Paper

- v18 在六個已見美國廣泛市場的 20／18 年設計資料表現良好、海外卻失敗後，
  v22 明確把假說縮窄為「美元債券與黃金是否只對美國股票較一致」。同一套每月
  50% 實際每日 2 倍產業 ETF／25% IEF／25% GLD 不再調權重；九組產品、
  2007-07-31–2019-06-21 定義一致區間、10／50 bps、前後半、五年滾動與全部
  成功門檻都在第一次下載本輪日線前凍結。協議 SHA-256 為
  `e9e9f43b30833c8131889b1967b0f47c3106f34611ef37e89a9cc62df2c72254`。
- 首次面板含 21 檔 ETF、4,146 列，面板 SHA-256 為
  `52450c125c53919133457fcf57c90f3d13b2ec96e42ff06a571aab2da010f749`。
  DIG 在 2008-10-13 的 +36.29% 超過機械跳變門檻；ProShares 官方歷史 NAV
  同日為 +37.61%，確認是金融海嘯反彈而非拆股或供應商錯誤。保留原始 ZIP、
  人工稽核與相同面板的驗證 ZIP，沒有重新下載；資料門檻 11/11 通過。
- 九個產業完整期的 v22 CAGR 全都高於普通 ETF，Sharpe 與 Calmar 也 9/9
  勝出；九產業等權 CAGR 9.99% 對普通 ETF 8.23%，Sharpe 0.619 對 0.505，
  最大回撤 −52.18% 對 −53.07%。個別門檻合計 51/63，完整期平均確實有改善。
- 事前要求的 1,260 交易日滾動 CAGR 優勢至少 10 bps、勝率至少 60%。九個
  產業的勝率只有 36.9%–56.0%，沒有一組通過；等權合併也只有 51.2%。因此
  「七種門檻各至少 6/9 通過」與合併滾動門檻同時失敗，經濟入口只過 13/15。
- 同資產不槓桿等權配置的 CAGR 7.88%，雖低於 v22，Sharpe 0.655、最大回撤
  −36.17%、Calmar 0.218 卻都優於 v22；不能只用完整期報酬掩蓋約 −52% 的
  歷史虧損路徑。合併主動報酬 NW t = 0.86、PSR = 76.05%；以 6,124 次搜尋
  懲罰後 DSR 機率只有 0.12%，統計門檻 0/3。
- 決定：`paper_eligible=false`、`trade_ready=false`。不建立 v22 Paper、
  不顯示 SSO／IEF／GLD 的 50/25/25 當成今天配置，也不在看到結果後把五年
  勝率門檻降到 50%。正式證據見
  `docs/V22_US_SECTOR_CAPITAL_EFFICIENCY_PROTOCOL.md`、
  `docs/V22_PRODUCT_MAPPING.md`、`artifacts/v22_data_receipt.json`、
  `artifacts/v22_us_sector_capital_efficiency_validation.json` 與
  `artifacts/v22_us_sector_capital_efficiency_report.html`。

## 2026-08-03：v20 分散器強弱輪替在十一組資料都輸固定配置

- v19 原本固定 50% 實際每日 2 倍股票 ETF，並以 12–1 月相對強弱從
  IEF／GLD／SHY 每月選兩個、各配 25%。產品映射先發現 VGK 與 UPV 在
  2015-10-01–2016-08-31 的歷史指數範圍不一致，因此在任何新日線下載與策略
  計算前停止 v19，保留產品稽核收據，不換代號或事後移動起點。
- v20 只把外部驗證改成定義相容的日本 EWJ／EZJ、中國大型股 FXI／XPP、巴西
  EWZ／UBR，策略規則、10／50 bps、前後半、五年滾動與門檻均不變。協議
  SHA-256 為
  `a6fdca00b3a4d69cf42cd507f1a3fbd278275bb490ddb9ea7b980e3dc4e0f81c`。
- 新外部面板 5,029 列、9/9 代號、OHLC 違規 0，面板 SHA-256 為
  `e30b403220d7863243a60cc9e672d3310a1f2658c7cbdd0ef70c8cdc2ddfe0d7`；三個
  市場在 2016-09-01 起算前都有至少 252 個有效交易日，資料門檻總計 13/13。
- 六個美國設計市場保留大型股 20 年、中小型股 18 年，另納入 EFA／EEM 16 年
  診斷。動態策略在 11/11 組的 CAGR 都低於固定 50% 2 倍股票／25% IEF／25%
  GLD；這直接反駁「挑當時較強的分散器能改善固定配置」。
- 外部期日本策略 CAGR 8.08% 對 EWJ 8.66%，中國大型股 1.33% 對 FXI 2.23%，
  巴西 6.19% 對 EWZ 6.25%；日本與中國回撤也比核心更深。三市場經濟門檻只過
  3/14、0/14、4/14，外部 NW／PSR／DSR 共 0/27。
- 決定：設計經濟 38/112、外部經濟 7/42、合計 45/154，
  `paper_eligible=false`。不顯示最後配置、不建立 v20 Paper、不調權重或回顧期
  救援。正式證據見 `docs/V20_DIVERSIFIER_RELATIVE_STRENGTH_PROTOCOL.md`、
  `artifacts/v20_diversifier_strength_validation.json` 與
  `artifacts/v20_diversifier_strength_report.html`。

## 2026-08-03：v18 美國股債金設計未能通過海外路徑

- v17 失敗後只探索七個無擇時、每月固定再平衡的股／債／金結構。鎖定中央且
  對稱的 50% 實際每日 2 倍股票 ETF／25% IEF／25% GLD，而不是樣本內報酬
  最高的純金分散版本。全域搜尋次數由 6,114 增至 6,121。
- 六個已見美國市場的完整期都同時提高 CAGR、Sharpe、Calmar 並略減回撤；
  50 bps 與兩個固定半期也維持正 CAGR 優勢。但 Nasdaq-100 五年滾動有效勝率
  只有 53.3%，相對核心的六組 NW t 只約 0.66–1.05；同資產不槓桿組合的
  Sharpe、Calmar 與回撤又全面較佳。這些只算設計資料。
- 在第一次下載 EFO/EET 日線前固定兩組海外市場、2010-07-30–2026-07-31、
  10／50 bps、固定前後半期、五年滾動、18 道經濟與 12 道統計關卡。協議
  SHA-256 為
  `5d88a1a11746f87ceee17fcf805bb570ae5992fa220e72b3711477984e2bd263`。
- 新快照 4,570 列、7/7 代號、OHLC 違規 0，面板 SHA-256 為
  `dd920b902fcc0054c411d78a5255b9b2cbc699fbfda2d17a5d04aa38a249ef2c`；
  EFO/EET 在正式期前各有 291 個有效日，資料門檻 3/3 通過。
- 已開發市場策略 CAGR 8.00% 對 EFA 7.70%，但 Sharpe、最大回撤、Calmar、
  前半期與五年滾動都失敗，只過 4/9。新興市場 CAGR 5.12% 對 EEM 4.98%，
  最大回撤由 −39.82% 加深到 −46.68%，並落後同資產不槓桿組合，只過 1/9。
- 凍結前已用官方頁確認成立日、每日 2 倍目標並看過摘要績效；沒有看過日線組合
  路徑。因此本輪明示為半獨立、不是完全盲測，也不把 16 年產品史冒充 20 年。
- 決定：外部經濟 5/18、資料 3/3、統計 0/12，`paper_eligible=false`。不調
  IEF／GLD 比例、不換海外 ETF、不建立 v18 Paper。正式收據見
  `docs/V18_DESIGN_EXPLORATION.md`、
  `docs/V18_EQUAL_DIVERSIFIER_CAPITAL_EFFICIENCY_PROTOCOL.md`、
  `artifacts/v18_equal_diversifier_validation.json` 與
  `artifacts/v18_equal_diversifier_report.html`。

## 2026-08-03：v17 資本效率股債提高報酬，但尾部風險否決 Paper

- 在第一次 v17 組合計算前固定每月 60% 實際每日 2 倍股票 ETF／40% IEF、
  三個公平基準、10／50 bps 成本與六市場 84 道經濟門檻。協議 SHA-256 為
  `b2f83e64b744d6d57a3aa0454943a094b987b767ee505695c63cd75c6c357a5c`。
- 合併快照含 14 檔 ETF、5,680 列，面板 SHA-256 為
  `4c948bf6e98055823bb4b722809040eaeeb4cb0cf3606417ad6a2a5dcdaec0c4`；資料、
  暖機、月末時序與權重 7/7 通過。大型股三組正式期為完整 20 年；中小型三組
  因產品史限制保留 18 年，不合成補齊。
- 六組策略 CAGR 分別為 12.08%、18.43%、11.28%、10.97%、9.73%、11.04%，
  除 Russell 2000 只略高外，多數明顯勝原始 ETF，也全數勝相同股票曝險的
  60% 2 倍 ETF／40% SHY 對照。
- 但六組最大回撤皆約 −57.76% 至 −62.70%，全都比原始 ETF 更深；Sharpe 與
  Calmar 多數也不如原始 ETF及未槓桿 75/25。等權 pooled 相對原始 ETF 的
  NW t 只有 1.35，相對 SHY 對照只有 0.89。
- 決定：經濟 48/84、資料 7/7、統計 9/54，`paper_eligible=false`。不把較高
  CAGR 描述成穩健超額，不調 60/40 比例，不建立 v17 Paper。正式收據見
  `docs/V17_CAPITAL_EFFICIENT_EQUITY_BOND_PROTOCOL.md`、
  `artifacts/v17_capital_efficient_validation.json` 與
  `artifacts/v17_capital_efficient_report.html`。

## 2026-08-03：v16 週度趨勢與波動煞車降低回撤但嚴重踏空

- 在首次下載 MVV、UWM、SAA 前固定 200 日趨勢、21 日實現波動、18% 目標波動、
  100%–150% 股票名目曝險、週末訊號、下一開盤、10／50 bps 成本與三市場
  48 道經濟門檻。協議 SHA-256 為
  `cde8c76f0fff818b2253b9d8d65d5c3b55ab11eefacd2e34ab04d95c41c4479e`。
- 2008-07-31–2026-07-31，MidCap 400／Russell 2000／SmallCap 600 策略 CAGR
  為 5.56%／4.99%／2.79%，原始 ETF 為 10.58%／9.61%／10.58%；最大回撤則
  由約 −50% 至 −54% 降為約 −38% 至 −44%。
- 三組都只有「回撤勝原始 ETF」與「回撤勝固定 150% 控制 10pp」兩項通過；
  週度退出與數百次實際再平衡造成長期報酬嚴重落後。等權 pooled 主動報酬相對
  原始 ETF、同趨勢未槓桿、固定 150% 的 NW t 分別為 −1.76、−0.75、−1.97。
- 決定：經濟 6/48、資料 4/4、統計 0/27，`paper_eligible=false`。不調目標
  波動或均線救援，不建立 v16 Paper。正式收據見
  `docs/V16_TREND_VOLATILITY_BRAKE_PROTOCOL.md`、
  `artifacts/v16_trend_volatility_brake_validation.json` 與
  `artifacts/v16_trend_volatility_brake_report.html`。

## 2026-08-03：v15 三市場報酬都較高，但回撤與風險效率否決 Paper

- v15 明確承認是看過 v14 後才提出的架構修正：平時 100% 原始核心；核心連續
  兩個完整月站上 200 日均線時，改為 90% 核心／10% 實際每日 3 倍 ETF，約
  120% 名目股票曝險。20 年 v14 只算設計探索，不是 v15 的獨立證據。
- 在第一次下載 UPRO、TQQQ、UDOW 前，已固定 2011-07-29–2026-07-31 的 15 年
  正式期、10／50 bps 成本、三市場 36 道經濟門檻與 18 道統計門檻。協議
  SHA-256 為
  `e5254470ce00a0bf0941fd6ca15a5400323bdf837034968f41046fabcb9ef2a6`。
  3 倍產品成立日期不支援 20 年正式期，因此不把 v14 與 v15 拼接成獨立 20 年。
- 首次資料契約把台北時間 8/3 誤當成尚未收盤的美股 8/3 已完成，因此正確拒絕
  7/31 最後 bar；失敗 ZIP 保留。相同、未修改的價格面板改以 8/2 檢查，預期與
  實際最後 session 都是 7/31，契約通過。面板 SHA-256 為
  `57527472113333ac0fa67c900983b063652be6c112aeed477fd0b99f7fe86e6f`。
- S&P 500 組策略 CAGR 15.49%、Sharpe 0.832、MDD −38.92%；SPY 為 14.39%、
  0.870、−33.72%，固定 90/10 為 16.36%、0.847、−38.92%。報酬勝 SPY，但
  回撤深 5.20pp、Sharpe 與 Calmar 都較差，只過 4/12。
- Nasdaq-100 組策略 CAGR 21.47%、Sharpe 0.933、MDD −37.40%；QQQ 為
  18.94%、0.936、−35.12%，固定 90/10 為 21.66%、0.916、−41.76%。它是三組
  最接近的結果，仍因 Sharpe 沒有嚴格勝 QQQ、回撤較深且未把固定控制回撤改善
  5pp，只過 9/12。
- Dow 30 組策略 CAGR 13.27%、Sharpe 0.753、MDD −42.02%；DIA 為 12.58%、
  0.799、−36.70%，固定 90/10 為 14.24%、0.778、−42.02%。同樣是報酬增加但
  風險效率惡化，只過 4/12。
- 三市場等權主動報酬相對原始 ETF 年化 +1.76%、NW t 2.62，但 6,112 次搜尋後
  DSR 只有 8.90%；相對固定 90/10 年化 −0.74%、NW t −2.08。pooled 診斷不能
  抵銷單一市場失敗。總計經濟 17/36、資料 4/4、Paper 入口 21/40、統計 4/18。
- 決定：`paper_eligible=false`、`reference_trade_candidate=false`。不建立 v15
  Paper、不顯示 90/10 研究比例；CLI 守門會拒絕帳戶。正式收據見
  `docs/V15_MODEST_LEVERAGE_OVERLAY_PROTOCOL.md`、
  `artifacts/v15_protocol_receipt.json`、`artifacts/v15_data_receipt.json`、
  `artifacts/v15_modest_leverage_overlay_validation.json` 與
  `artifacts/v15_modest_leverage_overlay_report.html`。

## 2026-08-03：v14 使用實際槓桿 ETF；Nasdaq 單一勝出不足以進 Paper

- 在第一次下載 SSO、QLD、DDM 與第一次計算前，固定 200 日均線、連續兩個
  完整月確認、風險開啟 60% 實際 2 倍每日目標 ETF／40% SHY、風險關閉
  100% SHY、月末訊號、下一開盤成交、10／50 bps 成本與三市場 36 道門檻。
  協議 SHA-256 為
  `089d323fb76b8080297d0403dcfbf40a7b1627fc5182466634d1d123ec260f48`。
- 凍結後才下載 `DDM/DIA/QLD/QQQ/SHY/SPY/SSO`，2004-01-02–2026-07-31
  共 5,680 列。面板 SHA-256 為
  `d7dc527ad678e54304419307847ef94467eda4d5926e8e01b258317129288191`，資料契約
  4/4 通過；三組 2 倍 ETF 在正式起點前各有 27 個有效日。
- 2006-07-31–2026-07-31，S&P 500 組策略 CAGR 9.21%、Sharpe 0.606、MDD
  −37.92%；SPY 為 11.25%、0.647、−55.19%，固定 60/40 為 11.37%、0.602、
  −64.24%。策略降低回撤，卻沒有跑贏 SPY 或同產品控制，只過 4/12。
- Nasdaq-100 組策略 CAGR 17.01%、Sharpe 0.868、MDD −33.09%，略勝 QQQ 的
  16.63%、0.808、−53.40%；但固定 60% QLD／40% SHY 為 17.69%。相對 QQQ 的
  NW t 只有 0.01，相對固定 60/40 為 −0.55，只過 7/12，不能把單一市場樣本差
  宣稱成趨勢 alpha。
- Dow 30 組策略 CAGR 7.28%、Sharpe 0.518、MDD −40.60%；DIA 為 10.44%、
  0.630、−51.87%，固定 60/40 為 10.57%。只過 2/12，直接反駁跨大型股指數
  泛化。
- 三市場等權主動報酬相對原始 ETF 年化 −1.87%、NW t −0.82；相對固定 60/40
  年化 −2.84%、NW t −1.08。整體經濟門檻 13/36、資料 4/4、Paper 入口
  17/40、統計 0/18。
- 決定：`paper_eligible=false`、`reference_trade_candidate=false`。不建立 v14
  Paper、不顯示最後研究比例、不用 Nasdaq 單一成功抵銷 S&P 500 與 Dow 失敗。
  收據見 `docs/V14_MODEST_LEVERAGE_TREND_PROTOCOL.md`、
  `artifacts/v14_protocol_receipt.json`、`artifacts/v14_data_receipt.json`、
  `artifacts/v14_modest_leverage_validation.json` 與
  `artifacts/v14_modest_leverage_report.html`。

## 2026-08-02：v10/v11 取數失敗封存；v12 降回撤但仍未跑贏 SPY

- v10 在任何權重或績效計算前，依凍結契約向 Yahoo 取 1971–1988 `^DJI`，
  供應商明確回覆該區間無資料。失敗收據 SHA-256 為
  `7b4a1b2d436b003d2b5d6b1d79e234a165b86d8113720530e40919d025f0c5b2`；沒有
  代理替換、沒有 v10 回測、沒有 Paper。
- v11 在首次下載前另鎖定 S&P DJI 官方 `DJIA Daily Performance History`
  Excel、唯一 GET、自動掃描全部工作表、共同日期與 4,300 筆門檻；唯一一次
  GET 回覆 HTTP 403。失敗收據 SHA-256 為
  `a020faffcfc2204bf046cb535e6876df05002678d5ef562898cea42ca6cbf642`；依契約不
  重試、不換來源、不計算 v11。
- v12 不回改兩次資料失敗，只在第一次計算前把三段既有凍結資料與同一套
  60% 永久核心／40% growth→core→defense 階層規則鎖定；協議 SHA-256 為
  `902fd24841a323c70023b240e695a9bcc0a32c4eb21cbd96b7cfdff9a9918c34`，並按
  全專案 6,109 次搜尋揭露 DSR。
- 2006-07-31–2026-07-31，v12 CAGR 11.10%、Sharpe 0.714、MDD −41.23%，
  SPY 為 11.25%、0.647、−55.19%。回撤改善 13.96pp，但 CAGR 落後 0.15pp；
  50 bps 下再落後 1.19pp／年，固定後十年落後 1.13pp，五年滾動勝率 26.7%。
- 1989–2006 舊代理全期 CAGR 領先市場 1.86pp，回撤也略淺；但 NW t 只有
  1.07。1973–1988 外部期全期領先 0.57pp，卻在 50 bps、固定後半期與五年
  勝率門檻失敗。三段 NW t 為 −0.51／1.07／0.10，PSR 與 6,109 次搜尋 DSR
  全數未過。
- 決定：v12 Paper 入口 16/23、完整歷史 16/29，`paper_eligible=false`。
  最後 60% SPY／40% QQQ 只是淘汰研究的歷史狀態；CLI 會拒絕建立 v12 Paper。
  收據見 `docs/V10_HIERARCHICAL_DEFENSE_PROTOCOL.md`、
  `docs/V11_HIERARCHICAL_DEFENSE_OFFICIAL_DJI_PROTOCOL.md`、
  `docs/V12_HIERARCHICAL_DEFENSE_THREE_SAMPLE_PROTOCOL.md`、
  `artifacts/v11_official_dji_data_receipt.json`、
  `artifacts/v12_hierarchical_validation.json` 與 `artifacts/v12_hierarchical_report.html`。

## 2026-08-02：v9 降低月度再平衡，三個年代仍未取得 Paper 資格

- v9 是看過 v8 負面結果後才提出的結構修正：風險開啟改為 60% 核心／40%
  成長，風險關閉 100% 核心；每個完整月末判斷，但只在布林狀態改變時交易，
  兩次切換間讓權重漂移。第一次計算前協議 SHA-256 為
  `3c147b87cf59c73c4a00ceb934763a9a7d75ffc25eb62cde3a1727c735954d8c`。
- 在首次下載 `^IXIC`／`^GSPC` 前，另把 1971-02-05–1988-12-30 的供應商、
  代號、日期、OHLCV、35% 跳變與共同暖機契約凍結；契約 SHA-256 為
  `b4250178d43a9d8eb75d1e03e5d44f4303d5a3e677ef1c88d3010d2e6782b00b`。
  兩份首次下載快照各 4,524 筆、無缺值，正式期前共同暖機 481 日，契約全過。
- 2006-07-31–2026-07-31，策略 CAGR 12.10%、Sharpe 0.674、MDD −56.47%，
  SPY 為 11.25%、0.647、−55.19%。241 個完整月末只有 47 次完成成交，但年換手
  仍為 1.89 倍；50 bps 下只領先 SPY 0.004pp／年，低於凍結的 0.10pp 門檻。
- 1989-01-03–2006-07-28 舊代理策略 CAGR 10.75%，高於 S&P 500 的 9.14%，
  但 MDD −57.08% 比市場 −49.15% 深 7.94pp，超過 5pp 上限。
- 1973-01-03–1988-12-30 的下載前未見外部期，策略 CAGR 6.13% 高於市場
  5.41%，50 bps 與五年滾動通過；固定後半期卻落後市場 0.15pp／年。
- 三段 NW t 為 1.56／1.40／1.16，PSR 為 92.27%／90.04%／85.98%，全數未達
  1.96／95%。計入全專案 6,106 次搜尋後，DSR 只有 1.03%／0.71%／0.39%。
- 決定：Paper 入口 20/23、完整歷史 20/29，`paper_eligible=false`。不建立
  v9 Paper、不把最後 60% SPY／40% QQQ 政策狀態當成訊號；`paper update
  --strategy v9` 也會讀取守門收據並拒絕建帳。正式收據見
  `docs/V9_LOW_TURNOVER_EXTERNAL_PROTOCOL.md`、`docs/V9_EXTERNAL_DATA_CONTRACT.md`、
  `artifacts/v9_external_data_receipt.json`、`artifacts/v9_low_turnover_validation.json`
  與 `artifacts/v9_low_turnover_report.html`。

## 2026-08-02：v8 兩段全期跑贏市場，仍被成本與舊期尾部風險否決

- 看過 v7 後，第一次 v8 計算前固定永遠 100% 股票曝險：50% SPY 核心，
  另一半只在 QQQ 的 12–1 動量領先 SPY 且站上 200 日均線時持有 QQQ，否則
  也持有 SPY。協議 SHA-256 為
  `2d21d2b81ad9285839a7036085231b6c670bbf63559179a144d6e6a8ddc9769c`。
- 這次把 Paper 入口與實金確認分開：16 道經濟、風險、成本、跨期與資料條件
  全過才准開隔離 Paper；再加四道 NW／PSR 才算 20/20 歷史確認。Paper 即使
  通過也仍需 252 個新增交易日與 6 次換倉。
- 2006-07-31–2026-07-31、10 bps 下，策略 CAGR 12.32%、Sharpe 0.680、MDD
  −56.81%；SPY 為 11.27%、0.648、−55.19%。前後十年同勝，五年滾動有效
  勝率 80.0%，顯示同樣 100% 股票曝險下有 1.05pp 年化差。
- 但 50 bps 下策略 CAGR 11.23%，略低於 SPY 11.25%；年換手 2.45 倍使成本
  壓力吃掉優勢。主期 NW t = 1.60、PSR = 92.82%，未達 1.96／95%。
- 1989-01-03–2006-07-28 舊代理策略 CAGR 10.98%，勝 S&P 500 的 9.14%，
  前後兩半與五年滾動 86.8% 都通過；但 MDD −56.12% 比市場 −49.15% 深
  6.97pp，超過事前容許 5pp。NW t = 1.48、PSR = 91.30%。
- 全專案 6,105 次搜尋懲罰後，主期／代理 DSR 機率只有 1.14%／0.87%，選擇
  偏誤沒有排除。
- 決定：Paper 入口 14/16、完整歷史 14/20，`paper_eligible=false`。不建立
  v8 Paper、不依結果降低成本門檻或放寬舊期回撤。正式收據見
  `docs/V8_ALWAYS_INVESTED_PROTOCOL.md`、`artifacts/v8_data_receipt.json`、
  `artifacts/v8_always_invested_validation.json` 與
  `artifacts/v8_always_invested_report.html`。

## 2026-08-02：v7 相對成長衛星降低市場風險，但未穩健跑贏 SPY

- 第一次 v7 計算前固定 50% SPY 核心、50% 成長／防守槽位、12–1 相對動量、
  QQQ 200 日均線、月末訊號與下一調整開盤成交；協議 SHA-256 為
  `2836a94c10973a498b59f33d1812984f5a32b5f1682b63add31e40a293d8ccac`。
- selection-matched control 每月持有完全相同股票比例：風險開啟時 100% SPY，
  關閉時 50% SPY／50% SHY。這把「少持股票」的政策效果與「選 QQQ」的
  alpha 分開，避免只用相對 SPY 的淺回撤宣稱策略有效。
- 2006-07-31–2026-07-31、10 bps 下，策略 CAGR 10.59%、Sharpe 0.717、MDD
  −40.33%；SPY 為 11.27%、0.648、−55.19%，matched 為 9.30%、0.671、
  −38.28%。策略報酬落後 SPY 0.68pp，回撤雖比 SPY 淺 14.86pp，卻比 matched
  深 2.05pp。
- 相對 SPY／matched 的五年滾動有效勝率為 45.6%／87.8%；NW t 為 −0.82／
  1.95。相對 matched 的 PSR 為 96.22%，但事前規定兩個公平問題都必須通過，
  不能只挑接近門檻的一邊。50 bps 與前後兩半也沒有同勝兩基準。
- 1989-01-03–2006-07-28 舊指數代理全期 CAGR 9.40%，略勝 S&P 500 9.14% 與
  matched 7.33%；但前半期落後市場 1.96pp，最大回撤 −40.47% 比 matched
  −31.21% 深，NW 與 PSR 未同時通過。
- 決定：19 道只過 6 道，`paper_eligible=false`。不建立 v7 Paper、不調比例、
  不把最後歷史配置當成訊號。正式收據見 `docs/V7_RELATIVE_GROWTH_PROTOCOL.md`、
  `artifacts/v7_data_receipt.json`、`artifacts/v7_relative_growth_validation.json` 與
  `artifacts/v7_relative_growth_report.html`。

## 2026-08-02：v6 產業動能長期代理有效，但可交易 20 年失敗

- 在下載九檔產業 ETF 與 Kenneth French 官方資料前，固定 50% SPY 核心、三個
  各 1/6 的產業槽位、12–1 動量、200 日均線、SHY 門檻與下一開盤成交；協議
  SHA-256 為 `bec68668983bfc3a778843337b7441df256fd805a75df758c60adceeb3a4072f`。
- selection-matched control 每月使用完全相同的入選槽位數 `n`，把 `n/6` 平均
  分配九產業，其餘放 SHY；因此策略不能靠降低股票曝險冒充選產業能力。
- 2006-07-31–2026-07-31、10 bps 下，策略 CAGR 10.00%、Sharpe 0.694、MDD
  −33.35%；SPY 為 11.27%、0.648、−55.19%，matched 為 10.20%、0.718、
  −34.10%。回撤較 SPY 淺，但 CAGR 同時落後兩基準，Sharpe 也落後 matched。
- 2003-07-31–2006-06-30 早期 ETF 期的 CAGR 為 14.16%，勝 SPY 10.90% 與
  matched 12.48%，但最大回撤反而較兩者深，不能用短期成功抵銷主期失敗。
- 1927–2005 French 代理期 CAGR 11.40%，勝市場 9.80% 與 matched 10.09%，
  七個完整十年中五個同勝兩基準；然而代理期最大回撤略深於 matched，且相對
  兩基準的 NW／DSR 未同時通過。代理只支持機制，不等於 ETF 可交易績效。
- 決定：22 道只過 11 道，`paper_eligible=false`。不建立 v6 Paper、不調參救援，
  最後歷史配置不在網站提供金額試算。正式收據見
  `docs/V6_INDUSTRY_TILT_PROTOCOL.md`、`artifacts/v6_data_receipt.json`、
  `artifacts/v6_industry_validation.json` 與 `artifacts/v6_industry_report.html`。

## 2026-08-02：資料一致不再被誤寫成實金可交易

- readiness 合約 v3 再把 `allocation_visible` 與 `ui_mode` 納入唯一授權來源；
  前端不再自行組合歷史候選與 readiness 旗標。只有 11/11 導致
  `trade_ready=true` 時才同時得到 `allocation_visible=true`，缺欄位或任何失敗
  都維持 Paper-only 並隱藏百分比與金額試算。這次方法改版提高
  `contract_version`，同日的新收據不得覆寫 v2 證據。

- 問題：舊版 `reference-check` 的 `ok=true` 只證明網站、快照與 LIVE Paper
  互相一致且未過期，但輸出沒有獨立的實金結論，容易被誤讀成策略已可上線。
- 修正：readiness 合約 v2 將 `integrity_ok`／`safe_to_publish_paper_status` 與
  `trade_ready` 分開。實金必須 11 道全過：資料完整、歷史、公平曝險、統計，
  再加 252 個前瞻交易日、6 次換倉、扣成本為正、報酬勝 SPY 與被動 90/10、
  回撤不深於兩者。
- 防止過早成功：未同時滿足 252 日與 6 次換倉前，五道前瞻績效門檻不評為
  通過；零日帳戶的 0% 回撤不再算成成功。
- 防回填：`live_evidence_ledger.jsonl` 以 SHA-256 串接每筆收據；完全相同重跑
  保持冪等，同日期同快照若績效內容改變則拒絕。readiness 方法改版必須提高
  `contract_version` 並另留一筆收據。
- 當前證據：`integrity_ok=true`、`trade_ready=false`、`decision=paper_only`，
  readiness 只通過 2/11。這使 Paper 站可持續更新，但不能被當成實金授權。

## 2026-08-02：v13 兩月確認降低換手，但新 ETF 驗證否決泛化

- 既有三年代的探索顯示，把相對成長狀態改為連續兩個月確認，主期完成交易可由
  47 次降至 19 次；再於核心市場也低於 200 日均線時使用 70% 核心／30% 防守，
  已知三段的 10／50 bps CAGR 與回撤門檻看似比 v9/v12 更接近目標。
- 因為那些資料已參與提出規則，先把 `252/21/200/2`、成長態 40/60、核心態
  100/0、防守態 70/30、固定 2006-07-31 起點與 30 道淘汰條件寫入
  `docs/V13_CONFIRMED_RELATIVE_GROWTH_PROTOCOL.md`。協議雜湊為
  `177e727f3a2c59ef9f5eb7b83b67b67468a8740bbeff0f22a9921fdbb034e0f1`，之後才
  第一次下載 IWF/IWB、IWO/IWM、EFG/EFA、SHY 驗證面板。
- Russell 1000 組 20 年策略 CAGR 10.94%，低於 IWB 11.17%；50 bps 年化差
  −1.16pp、後十年與五年滾動失敗，十道只過六道。雖然最大回撤由 −55.38%
  改善到 −41.90%，不能用較淺回撤掩蓋長期報酬落後。
- Russell 2000 組策略 CAGR 7.30%，低於 IWM 8.86%；50 bps 年化差 −2.60pp，
  前後半期與五年滾動均失敗，十道只過三道。相對同狀態曝險對照的 CAGR 與
  Sharpe 也落後，直接反駁「成長替代核心」可跨股票母體創造 alpha。
- EAFE 組在固定起點前只有 247 個共同有效交易日，少於協議要求的 252 日；保留
  較晚起點診斷，但不計門檻，不替換 ETF 或移動起點。
- 決定：新資料經濟門檻 9/30、資料門檻 3/4、統計門檻 0/9；
  `paper_eligible=false`。封存 `v13_confirmed_growth_validation.json` 與新手報表，
  不建立 v13 Paper、不把最後歷史狀態當下單訊號，也不以事後調參救援。

## 2026-08-01：v5 三時鐘集成近期成功，但舊年代與五市場失敗

- 第一次計算前固定三個各 1/3 袖套：QQQ 固定持有、18%／21 日波動管理、252 日
  趨勢連續兩月確認；總權重只取算術平均，不搜尋袖套比例、不槓桿。協議 SHA-256
  為 `67cfc566116497d2d32df904c91ff90f554380cfcdd3e47b41a41eaab1fac90f`。
- 2006-07-31–2026-07-31、10 bps 下，v5 CAGR 16.69%、Sharpe 0.895、MDD
  −42.10%；QQQ 為 16.68%、0.810、−53.40%，固定 95/5 為 16.00%、0.815、
  −51.17%。近期 9 道門檻通過 7 道，50 bps 後仍以 16.26% 勝過 SPY 與 95/5，
  相對 SPY 的 5 年滾動有效勝率為 100%、相對 95/5 為 60%。
- 但相對 matched 95/5 的平均每日主動報酬年化只有 0.29%、NW t = 0.41；6,102
  次搜尋懲罰後 DSR 機率只有 0.032%。相對 SPY 的 NW t 雖為 2.69，DSR 也只有
  7.21%，不足以排除 post-selection。
- 1986-10-01–2006-07-28 全期 CAGR 13.38%，高於 NDX 12.81% 與固定 95/5
  的 12.10%，回撤也改善；但相對兩基準的五年滾動有效勝率只有 36.9%／37.4%，
  CAGR 差中位數為 −1.31pp／−0.30pp，前後十年與 NW t 門檻失敗。
- 五市場完整期同時勝 buy-and-hold 與 95/5 只有 DAX，合計 1/5；回撤改善 10pp、
  50 bps 同勝、滾動同達 60%、前後半期同勝均為 0/5。五市場等權相對買進持有
  年化主動報酬 −0.76%、NW t = −1.36。
- 決定：22 道只通過 10 道，`paper_eligible=false`。近期結果顯示集成比單一 v3
  更接近目標，但外部證據直接反駁可泛化性；不建立 v5 Paper、不改袖套比例救援。
  正式收據見 `docs/V5_THREE_CLOCK_PROTOCOL.md`、
  `artifacts/v5_three_clock_validation.json`、`artifacts/v5_three_clock_report.html`。

## 2026-08-01：v4 股權風格輪動只改善回撤，14 道門檻僅通過 2 道

- 在下載資料前固定 `IWF`／`IWD`／`IJR` 的 12–1 月相對動量、兩個 50% 槽位、
  未入選槽位放 `SHY`，不使用均線、波動目標、停損、槓桿或參數鄰域。協議
  SHA-256 為 `9be20a10a0d27809d9e420e6bf41cc6ce04c4d46a51c5b4651c54a4b28efae48`。
- 2006-07-31–2026-07-31、10 bps 成本下，策略 CAGR 10.85%、Sharpe 0.726、
  MDD −34.96%；SPY 為 11.27%、0.648、−55.19%，風格靜態等權為 10.71%、
  0.604、−56.33%。因此只通過 Sharpe 與相對 SPY 回撤改善兩項。
- 策略 CAGR 落後 SPY 0.42pp；50 bps 後同時落後 SPY 2.07pp、風格等權
  1.44pp。前十年勝過兩個基準，後十年則分別落後 3.61pp／1.99pp；五年滾動
  有效勝率只有 17.8%／15.6%，相對兩者 NW t 為 −0.41／−0.26。
- QQQ 的 CAGR 為 16.68%；策略落後 5.82pp，雖改善 18.44pp 回撤，仍未通過
  事前機會成本門檻。
- 舊代理固定用 `^RLG`／`^RLV`／`^SP600`。實際凍結後，前兩者在 Yahoo 只從
  2002-09-30 開始，1996-07-31 起算前有效暖機為 0；協議禁止換代號，六道舊代理
  績效門檻因此依資料失敗關閉。
- 決定：`historical_gate_passed=false`、`paper_eligible=false`，不建立 v4 Paper、
  不用回撤較淺掩蓋報酬失敗，也不事後換代理或調參。正式收據見
  `docs/V4_STYLE_ROTATION_PROTOCOL.md`、`artifacts/v4_style_validation.json` 與
  `artifacts/v4_style_report.html`。

## 2026-08-01：v3 五市場事前凍結測試失敗，不再視為可泛化機制

- 在下載前凍結 `^GSPC`、`^FTSE`、`^GDAXI`、`^N225`、`^HSI`，固定用
  1989-01-03–2006-07-28、零報酬 CASH、10 bps 主成本與 50 bps 壓力成本；協議
  SHA-256 為 `8de1eafd2e8cbf28ee68dfc7322187d9b6c06e3b8aefc32d76d516046ec88117`。
- 完整期只有 DAX 的 CAGR 勝過同口徑 buy-and-hold，合計 1/5；Sharpe 勝出 3/5、
  回撤改善至少 10pp 為 1/5、50 bps 後仍勝出 1/5、五年滾動勝率達 60% 為 0/5、
  前後半期都勝出 1/5，七道集合門檻全數失敗。
- 五市場等權每日主動報酬年化平均 −0.88%，Newey–West t = −1.20；以全域 6,100
  次搜尋懲罰的 Deflated Sharpe 機率約 0.000056%。
- 決定：`cross_market_passed=false`，v3 的可信度進一步下降。保留隔離 Paper 只為
  收集前瞻實作證據，不調參救援、不用 DAX 單一成功作宣稱、不替換 v2，也不升級
  成實金參考交易候選。正式協議與結果分別見 `docs/V3_CROSS_MARKET_PROTOCOL.md`、
  `artifacts/cross_market_validation.json` 與 `artifacts/cross_market_report.html`。

## 2026-08-01：v3 主樣本勝過 QQQ，但較舊代理期滾動一致性失敗

- 凍結規則：QQQ 252 日趨勢需連續兩個月確認；正 regime 100% QQQ，負 regime 才套用 18%／21 日波動目標，其餘 SHY。
- 2006–2026 CAGR 17.61% 對 QQQ 16.68%，MDD −36.19% 對 −53.40%；1／2／3 月確認鄰域、前後十年、25 bps 與固定 96/4 曝險控制全部通過。
- 1986–2006 `^NDX`＋零報酬 CASH 的隔離代理期全期 CAGR 15.01% 對 12.81%，但以 10 bps 年化為最低有效優勢後，五年滾動勝率只有 36.9%，前十年落後 0.74pp。
- 相對 QQQ 的 Newey–West t = 0.31；以 6,100 次搜尋懲罰後 DSR = 0.024%。
- 另以 FRED 官方 DGS3MO／DTB3 日利率按實際日數累積為短債現金代理：全期 CAGR
  優勢略增至約 2.43pp，但有效五年滾動勝率仍為 36.9%，前十年仍落後約
  0.67pp。故失敗不是「零報酬現金」假設造成，這項敏感度測試不改寫原凍結代理。
- 決定：`proxy_validation_passed=false`、`reference_trade_candidate=false`。建立隔離 `paper_v3_state.json` 累積前瞻證據，但不取代 v2 主網站，也不宣稱已找到穩健 alpha。

## 2026-08-01：新增被動 90/10 曝險控制，v2 降級為 Paper-only

成長守門員 v2 的歷史平均 QQQ 訊號權重約 88.4%，因此只比 SPY 可能把科技股曝險誤當成策略能力。新增透明控制組：固定 90% QQQ／10% SHY、每月末再平衡、同一下一開盤時鐘與成本。這是 v2 選定後補上的 post-selection 稽核，不聲稱預先註冊。

在同一份 `2026-07-31` 凍結快照與 10 bps 成本下，v2／被動 90/10 的 CAGR 為 15.61%／15.31%，MDD 為 −35.96%／−48.86%。v2 的確降低回撤，但報酬優勢不穩健：後十年 CAGR 落後 1.02 個百分點；以至少 10 bps 年化才算有效勝出的修正版口徑，5 年滾動勝率為 47.8%；25 bps 時 CAGR 差轉為 −0.07 個百分點；平均每日主動報酬年化 −0.24%，NW t −0.19。

決策：保留 v2 的 SPY 歷史門檻原始結果，但新增 `exposure_control_passed=false` 與 `reference_trade_candidate=false`。LIVE paper 再加入同起點被動 90/10，前瞻升級必須同時勝過 SPY 與被動 90/10。網站不得把配置寫成實金照單訊號。

## 2026-08-01：零利率 Sharpe > 1，但標準超額 Sharpe 未達標

同一份 `2026-07-31` 凍結快照、2006-07-31 起算、下一交易日開盤成交與 10 bps 成本下，75% 平衡趨勢核心＋25% QQQ 的結果為 CAGR 8.15%、零利率 Sharpe 1.071、MDD −14.36%。前後十年零利率 Sharpe 約 1.003／1.135。

Sharpe 的教科書分子應是超額報酬。以 SHY 調整後總報酬作可交易短債代理後，候選超額 Sharpe 只有 0.799，PSR（超額 Sharpe > 1）18.7%，6,000 次搜尋 DSR 42.2%。2012 年起 walk-forward 的零利率／超額 Sharpe 為 1.143／0.985。故沒有找到標準口徑 Sharpe > 1 的策略；獨立 LIVE paper 僅用來驗證實作與收集前瞻紀錄。

## 2026-08-01：擴充 ETF 池仍未達標，停止擴張搜尋

第二份凍結快照加入 33 檔長歷史產業、國家、債券與實體資產 ETF，固定測試 128 個多週期趨勢／廣度／倒數波動與雙動量組合。最佳 SHY 超額 Sharpe 為 0.759，低於原十資產候選的 0.799。月底／月初 pilot 在排程稽核時發現負位移被重複編碼，因此整組作廢，只保留為搜尋次數，不作策略證據。

決策：不再增加任意技術指標或特殊期間。繼續挖掘只會擴大假發現率；後續改善必須來自新資料、預先註冊假說或真正的 LIVE 觀察期。

## 2026-08-01：保留 Sharpe 搜尋的負結果

- 144 個多週期趨勢／廣度設定最佳 Sharpe 0.937。
- 80 個波動管理設定最佳 0.922。
- 48 個收縮共變異數設定最佳 0.989。
- 18 個 RSI2 趨勢回檔設定最佳 0.708，且換手高。
- 固定風險預算雖把 Sharpe 拉到 1.112，但 CAGR 只有 5.02%。
- 趨勢核心＋趨勢衛星雖達 1.018，但 CAGR 只有 7.54%。

上述家族沒有因失敗而從多重測試母數刪除；DSR 使用的 6,000 次上限還納入中止與已規劃組合。

## 2026-08-01：不把 Top 3 當成正式版

在同一份 `2026-07-31` 快照、2006-07-31 起算、10 bps 成交成本下：

- Top 3 雙動量：CAGR 約 9.1%、Sharpe 0.69、MDD 約 −20.1%。
- Top 4 雙動量：CAGR 約 9.1%、Sharpe 0.75、MDD 約 −16.0%。
- 三種回顧長度的 Top 4：CAGR 約 8.2–9.3%、Sharpe 0.69–0.77、MDD 約 −15.4% 至 −17.5%。

252 日設定下 Top 3／4 的樣本 CAGR 幾乎相同，Top 4 回撤更淺且分散較好，故採 Top 4。

## 2026-08-01：不宣稱雙動量打敗 SPY

同一回測中：

- SPY CAGR 約 11.3%，Sharpe 0.65，MDD 約 −55.2%。
- Top 4 雙動量 CAGR 約 9.1%，Sharpe 0.75，MDD 約 −16.0%。
- 主動報酬相對 SPY 為負，Newey–West t 約 −0.97。

結論：這條 20 年樣本中雙動量報酬低於 SPY，但差異未達顯著；三次固定壓力期的回撤都較淺。它的定位是分散／風險控制策略，不是已證實的高報酬替代品。

## 2026-08-01：大型股動量傾斜不升格

今天的 30 檔大型股池回填歷史後，動量傾斜相對等權約 +0.8pp CAGR，主動報酬 t 約 0.66，且換手更高。再加上生存者偏誤，沒有足夠證據升格為正式策略。

保留價值：當期排名可作研究觀察；傾斜池的程式與基準可等取得 point-in-time 母體後重跑。

## 待做但不應偷跑的改善

1. 取得逐期成分股與下市報酬後，重建無生存者偏誤的美股傾斜池。
2. 用 SEC filing date 建立 point-in-time 品質／價值因子。
3. 固定假說後做 purged walk-forward＋embargo；不可再用同一全期挑參數。
4. 連續保存多日供應商快照，量化歷史修訂造成的績效誤差帶。
5. 累積至少一個完整市場循環的 LIVE paper log；在此前不以 REPLAY 代替真實前瞻證據。
