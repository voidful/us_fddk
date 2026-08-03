# 短線行業動量：French 30 日資料映射 v1.0

凍結日期：2026-08-03

用途：49 行業首次下載只因正式期內一格 `Softw` 缺值而按協議停止，未曾計算任何
候選回報。本輪用首次未見的 Kenneth R. French 30 行業日回報，驗證較粗、較持續的
行業分類能否通過同一 6–1 動量機制。映射與研究協議提交前，不得下載 30 行業 ZIP、
計算回報或查看其數值。

## 唯一新增官方來源

| 角色 | 官方檔案 | 固定 URL | 首次下載前狀態 |
|---|---|---|---|
| 30 行業日回報 | `30_Industry_Portfolios_Daily_CSV.zip` | https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/30_Industry_Portfolios_Daily_CSV.zip | 未下載、未查看 |

來源只接受 Kenneth R. French Data Library 官方網域，不使用鏡像、第三方整理檔或手工
複製表格。新增 ZIP 只下載一次，保存 SHA-256、ZIP member、檔案大小及首次下載時間。

## 已封存、不得重抓的共同因素

| 角色 | 封存檔 | SHA-256 |
|---|---|---|
| 市場及 RF | `artifacts/french_ff_factors_daily_af8aec07.zip` | `af8aec07d55c98caa15045a77b87455be68cb8847b2ee5bd03bf5c2c8a3f96e2` |
| 日動量因子 | `artifacts/french_momentum_daily_f4237e2e.zip` | `f4237e2e36dffa13fd7823f55376316a94b5ac663af951dd9eaca8ed2c678bcf` |

這兩檔在 49 行業資料準備時首次封存；本輪只讀相同 bytes，不重新下載或更新。

## 官方建構與證據邊界

[30 行業官方說明](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_30_ind_port.html)
指出，每年六月按當時四位 SIC code，把 NYSE、AMEX、NASDAQ 股票分配到行業，並計算
其後七月至翌年六月的回報。這降低用今日存活公司回填歷史的問題，但仍不是逐股
point-in-time 成分、退市事件及公司行動原始賬本。

[官方 Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library.html)
明示歷史會因 CRSP 修訂而改變，缺值碼為 `-99.99` 或 `-999`，並記錄日檔對退市日期
處理的修訂。因此本輪只可引用本次封存 ZIP 及既有兩個因素 ZIP。

## 不可交易限制

- 30 行業日檔只有組合收市至收市回報，沒有開市價、買賣差價、基金費用或容量資料。
- 缺值碼只記為不可用，不得補值；正式研究期起點只按資料完整性規則決定，不看回報。
- 訊號只可由收市日 `t` 套用至 `t+1` 回報，不能聲稱下一開市可按收市價成交。
- 30 行業組合不是 30 隻可直接買賣 ETF，不建立 ticker 或持倉金額。
- 不論結果，本輪固定 `paper_eligible=false`、`trade_ready=false`、實金動作 US$0。
