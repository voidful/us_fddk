# 短線 Gap-down 反轉診斷協議（Round 56）

版本：1.0（事前固定、只作診斷）
固定日期：2026-08-12

## 研究問題

在同一份固定美股快照及大型股觀察池內，完成交易日出現「隔夜 gap-down 後收市反彈」的
個股，下一個交易日開市進場並持有 5、10、20 個交易日，是否相對只套用價格及流動性
條件的合資格池有可重複的超額回報？本輪測試的是 gap 反轉，與先前的趨勢突破、Form 4
事件及五日超賣反轉診斷不同，不把任何先前結果當作升格證據。

## 不可變資料及期間

- 資料：`snapshot_20260731_6a7ca6b8.zip`，只接受 archive SHA、panel fingerprint 及
  watchlist SHA 全部吻合。
- 期間：2006-08-01 至 2026-07-31；只使用已完成 XNYS session。
- 觀察池：固定 30 檔大型股 watchlist；此池有 survivorship bias，不能代表歷史可投資全集。
- 不作歷史回填、現時資料改寫、個別股票公開名單或參數重選。

## 固定訊號及執行

1. 每個完成交易日收市計算；價格必須高於 US$5，20-session median dollar volume 至少
   US$20m。
2. gap-down 定義為當日 adjusted open 相對前一個完成 session adjusted close 跌至少
   2%（`open / prior_close - 1 <= -2%`）。
3. 收市反彈定義為當日 adjusted close 相對 adjusted open 至少升 0.5%，且收市位於當日
   adjusted high-low range 的上四分位（close strength 至少 0.75）。
4. 在符合訊號的個股中按當日 intraday return 由高至低排序，取 Top-5；不足 5 檔即跳過。
5. 下一個交易日 adjusted open 進場，於第 5、10、20 個交易日 adjusted close 離場；每宗
   事件扣固定 round-trip 20 bps，不使用停損、槓桿、盤中 timestamp 或事後調參。

## 基準、gate 及邊界

- 合資格池只套用價格及流動性條件；另列完整現時股池、SPY 及 QQQ 作同期參考。
- 主要 20-session horizon 須同時通過六項 gate：至少 30 宗完整事件、相對合資格池平均
  差額為正、Newey–West t 至少 1.96、moving-block bootstrap 下界為正、配對勝率嚴格高於
  50%、前後固定期間平均差額均為正。
- 任何 gate 未通過即為負面診斷；即使全部通過，現時觀察池的 survivorship bias 仍阻止
  Paper 或實金升格，除非另有獨立的 point-in-time universe 及 forward contract。
- 本輪只產生 aggregate research log 及 append-only trial ledger。`paper_authorized=false`、
  `real_money_authorized=false`、`real_money_action_usd=0`，首頁行動維持「今天不下單」。

## 多重比較

本輪預先把 5、10、20-session 三個 horizon 視為一個新 family，global trial lower bound
由 6299 增加至少 3 至 6302；不聲稱精確增量。
