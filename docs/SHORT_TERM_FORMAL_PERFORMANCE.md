# 短線正式帳本績效與 baseline 比較層

`usfddk/formal_performance.py` 只讀取 raw-accounting ledger，建立同一 session path 的
描述性統計與 candidate／baseline active-return diagnostics。它不會自行判定策略成功、
啟動 Paper 或寫入公開決策資料。

## 固定輸出

單一路徑報告：總回報、CAGR、年率化波幅、美元一個月國庫券超額 Sharpe／Sortino、最大
跌幅、Calmar、年率化單邊成交額、交易成本、交易筆數、期末 US$ 值及持倉比率。

相對比較固定在共同日期後計算：CAGR 差、最大跌幅差、正 active-return 比例、Newey–West
平均 active return、PSR 及以事前 global trial count 調整的 DSR。缺 RF session、缺
baseline、日期不一致或非有限數字會直接拒收。

候選只能與同一 raw open／raw close、公司行動、成本及 D+1 時鐘下的 QQQ、SPY、逐期
合資格池等權及首輪十股漂移比較。這些數字在正式 provider 20/20、execution 16/16、RF
及 release firewall 全通過前，只屬合成控制；失敗結果留在研究 log，不進網站。
