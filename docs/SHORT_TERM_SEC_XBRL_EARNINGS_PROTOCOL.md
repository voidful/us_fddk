# SEC XBRL fundamental acceleration 事件研究協議

版本：v1；用途：短線個股研究診斷，不授權 Paper 或公開策略。

## 研究問題與資料邊界

研究問題是：在固定的大型股觀察池內，於 10-Q 公布後，若已申報的 diluted EPS 及營收
均較同一財政季度上年同期為高，下一個 XNYS session 入場並持有 20 sessions，能否在
成本及固定分段下跑贏 QQQ。這是公開基本面事件的研究假說，不是盈利承諾。

- universe 固定為 `us_large_cap_watchlist_v1.csv` 的 2026-07-30 快照；同一 CIK 的
  多個股份類別只保留檔案中較先出現的 ticker。它不是歷史成分股，不能支持 20 年無
  倖存者偏差宣稱。
- 每個 CIK 只從 SEC `data.sec.gov/api/xbrl/companyfacts/` 取得 facts；所有觀察只准
  使用 `filed <= 2026-06-30` 的資料，之後才出現的修訂或申報不能回填本輪。
- 因本輪凍結價格快照由 2023-01-03 開始，事件 filing date 固定限制在
  2023-01-01 至 2026-06-30；更早的 facts 只作同比配對，不進入交易事件。
- 收據保留 API URL、下載時間、User-Agent 描述及 SHA-256；缺資料不補值、不用 Yahoo
  估算值代替。

## 固定 fact 及事件規則

- 只納入 `form=10-Q`、`fp=Q1/Q2/Q3`、期間長度 70–120 日的季度觀察；排除 10-K、
  10-Q/A、8-K 及自訂 taxonomy。
- diluted EPS 只用 `us-gaap:EarningsPerShareDiluted` 的 `USD/shares` unit；營收按每個
  accession 的固定優先次序使用 `us-gaap:Revenues`，若該 accession 沒有合資格的
  `Revenues` observation 才用 `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`
  的 `USD` unit。
- 同一公司／財政年度／`fp` 只取最早的原始 10-Q accession；修訂列拒收。當期必須同一
  accession 同時有 EPS 及營收，並能找到相同 `fp` 的上年同期，兩者 prior 值均為正。
- 事件只有在 `eps_current > eps_prior` 且 `revenue_current > revenue_prior` 時成立；
  不按增幅排序、不設 Top-K、不用事後價格挑選。
- 以價格 CSV 的 QQQ session 找出 filing date 後第一個 XNYS session 作 available session；
  只使用 filing date 已公開的 facts。

## 組合、成本及基準

- 入場前 20 個 XNYS sessions 的 median dollar volume 至少 US$20m，前一日收市價至少
  US$5；只使用入場日前成交額及價格。
- 每個 ticker 第一個未重疊事件，持有 20 個 XNYS sessions；active ticker 等權，入場日
  adjusted open，之後 close-to-close，到期日收市後離場。
- 成本固定為單邊 10／25／50 bps；QQQ、SPY、IWM 用同一 evaluation period、同一
  時計及同一成本情境（20／50／100 bps round-trip）。
- 事前固定前半段為 filing date `2023-01-01` 至 `2024-12-31`，後半段為
  `2025-01-01` 至 `2026-06-30`；報告全期及這兩段的 CAGR、total return、Sharpe、
  最大回撤、平均持倉及年化 turnover，不依結果改變 fact、持有期、成本或 universe。

## 升格邊界

即使事件結果為正，本輪仍是現時 watchlist＋exploratory Yahoo 價格，缺少歷史逐期成分、
退市／收購回報、完整公司行動及正式 risk-free package。因此所有結果維持
`research_candidate_only`；失敗與 skip reason 只保留在機器收據／研究 log，不能建立
Paper、個股買入名單或 success-only 網頁策略。
