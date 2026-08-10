# 美股短線超賣反轉診斷協議（Round 55）

版本：1.0（事前固定、只作診斷）
固定日期：2026-08-10
狀態：`preregistered_oversold_reversal_diagnostic_only`

## 研究問題

在同一份 2006-08-01 至 2026-07-31 的美股 OHLCV 快照中，大型股出現短期極端下跌並觸及
近期低位後，下一個交易日進場、持有固定 5／10／20 個交易日，是否能在成本後穩健跑贏
同日合資格池？這是與突破動量不同的獨立反轉假說。

本輪只作現時 30 檔大型股倒推診斷，不是 point-in-time 成分回測，不得建立策略、Paper
或實金動作。

## 凍結訊號與執行

- 訊號只在每個已完成的 XNYS 星期最後一個交易日收市後計算。
- 基礎合資格條件：收市價 > US$5、20 日中位數美元成交額 >= US$20m。
- 反轉訊號必須同時符合：5 日收市回報 <= -8%，以及收市價 <= 前一個完整 20 日最低收市價。
- 以 5 日回報由低至高排序，取最弱 Top-5 等權；不足 1 檔則該事件不完整。
- 訊號日後一個完整 XNYS 交易日以 adjusted open 等權進場；第 5／10／20 個交易日以
  adjusted close 等權離場。
- 每宗事件扣固定 round-trip 20 bps；不使用盤中資料、停損、停利、槓桿、事後選股或
  動態調參。

## 基準與統計

每個事件同時計算：候選 Top-5、只套用價格／流動性條件的合資格池等權、有完整進出場價格的
現時股池等權，以及 SPY、QQQ。主要 horizon 固定為 20 個交易日；5／10 日為同一協議下的
次要 horizon。

主要 6 道 gate：至少 30 宗完整事件、相對合資格池平均差額 > 0、Newey–West t >= 1.96、
moving-block bootstrap 95% 下界 > 0、事件勝率 > 50%、固定前／後半段平均差額均 > 0。

全部 gate 通過才可標記為診斷陽性；即使通過，仍須另取 point-in-time 成分、退市／收購回報、
公司行動及 raw execution，才可進入正式 readiness。任何 gate 失敗都只保留研究 log，不建立
策略或 Paper。

## 不可升格邊界

本輪固定 `performance_authorized=false`、`paper_authorized=false`、
`real_money_authorized=false`，首頁行動固定「今天不下單」。結果只輸出 aggregate 指標，
不輸出個股、股票代號、逐筆事件、交易指令或持倉比例。

現時股池帶 survivorship bias；adjusted OHLCV 不是可成交 raw execution；低位及回報沒有盤中
公開 timestamp；事件可重疊；因此不能宣稱可賺錢或構成投資建議。
