# 短線行業動量長歷史驗證：數據映射 v1.0

凍結日期：2026-08-03

用途：以首次查看的 Kenneth R. French 49 行業日回報，驗證「較慢訊號、20 日固定持有」
是否能跨越現時個股池及 ETF 產品樣本。映射與研究協議提交前，不得下載下列三個 ZIP、
計算任何回報或查看其數值。

## 唯一官方來源

| 角色 | 官方檔案 | 固定 URL | 首次下載前狀態 |
|---|---|---|---|
| 49 行業日回報 | `49_Industry_Portfolios_Daily_CSV.zip` | https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/49_Industry_Portfolios_Daily_CSV.zip | 未下載 |
| 美國市場及無風險利率 | `F-F_Research_Data_Factors_daily_CSV.zip` | https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_daily_CSV.zip | 未下載日檔 |
| 美國日動量因子 | `F-F_Momentum_Factor_daily_CSV.zip` | https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_daily_CSV.zip | 未下載 |

來源只接受 Kenneth R. French Data Library 官方網域，不使用鏡像、第三方整理檔或手工
複製表格。三個 ZIP 必須在同一次資料準備運行下載並各自保存 SHA-256、ZIP member、
檔案大小及時間。

## 官方建構與證據邊界

[49 行業官方說明](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_49_ind_port.html)
指出，每年六月按當時四位 SIC code，把 NYSE、AMEX、NASDAQ 股票分配到行業，並計算
其後七月至翌年六月的回報。這降低用「今日仍存在公司」回填歷史的問題，但不等同持有
逐股 point-in-time 成分、退市事件或公司行動原始賬本。

[官方 Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library.html)
亦明示歷史會因 CRSP 修訂而改變，並記錄日檔在退市日後停止持有股票的計算修訂。因此
本輪只可引用本次封存 ZIP，不可把日後網站更新靜默當成同一數據。

[日動量因子官方說明](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_mom_factor_daily.html)
使用 prior 2–12 month return、每日重新組成的 size × momentum 六個 value-weighted
組合。它只作因子解釋與 benchmark，不參與 49 行業候選排名。

## 不可交易限制

- 行業日檔只有組合收市至收市回報，沒有開市價、買賣差價、基金費用或容量資料。
- 官方 `-99.99`／`-999` 缺值碼只記為不可用並封存稽核，不得填補；正式研究期只可
  從 1963-01-01 起第一個全部 49 行業已有連續 126 日有效回報的共同交易日開始，且
  起點不得遲於 1970-12-31。這個規則只看資料完整性，不看策略回報。
- 研究只能把收市日 `t` 的訊號套用到 `t+1` 日回報，不能聲稱下一開市真實成交。
- 49 行業組合不是 49 隻可直接買賣 ETF，也不建立 ticker 映射或持倉金額。
- 不論結果，這一輪固定 `paper_eligible=false`、`trade_ready=false`、實金動作 US$0。
- 只有合格個股 point-in-time 成分、退市回報及公司行動數據按既有協議通過，才可另行
  評估從全現金開始的短線 Paper。
