# 短線正式 raw 資金會計橋接層

`usfddk/formal_raw_accounting.py` 是月末 point-in-time 訊號與日線回測之間的內部橋接層。
它只接收已建立的 `ExecutionInstruction`、raw open／raw close 及公司行動表，輸出一個
可重播的日線帳本與交易／公司行動 audit frame。它不會改寫 Paper、正式 readiness 或
`site/data/public-decision.json`。

## 固定邊界

- 成交只用下一個 XNYS session 的 `open_raw`；不接受 adjusted open、VWAP、同日成交或補值。
- 收市估值只用 `close_raw`。`total_return_factor` 即使存在，也只供訊號特徵層使用，不會
  再套入帳戶，避免派息或拆股雙重計算。
- 派息在 ex-date 依當時股數建立應收；pay-date 才轉成可交易現金。應收在付款前仍計入
  權益，但不計入下一開市可用買入資金，避免隱含借貸。
- 拆股只調整股數一次；分拆只增加 successor 股數；現金收購、DelRet 或換股只能選一條
  經濟結算路徑。
- 目標倉位使用「可用現金＋開市持倉市值」，並先預留凍結成本；沽出先於買入，買入不足
  時按同一比例縮放，絕不暫時製造槓桿。
- 研究期最後一天若仍有未到 pay-date 的應收，保留在終值的 `receivables` 欄；不把它提早
  變成現金，也不因研究窗口截斷而遺失經濟價值。
- 成本只接受事前登記的 10／25／50 bps；初始名義資金固定 US$1,000。

## 輸出與拒收

`RawAccountingResult` 只包含內部 `equity_curve`、`trades` 及 `action_audit`。每日必須通過
`cash + receivables + raw-close positions = equity` identity；以下情況會 fail closed 並
只留在測試／研究 log：價格缺失、非 observed 價格、早付派息、entitlement 對數失敗、
退出條款不唯一、successor 不一致、負股數、買入現金不足或未付款應收。

合成測試只證明會計控制能拒絕錯誤輸入，不代表正式 provider 已到、不代表 20 年策略回報、
不代表 Paper 通過，也不會產生公開個股名單或落盤建議。
