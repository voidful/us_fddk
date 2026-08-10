# 短線正式訊號引擎（研究橋接層）

`usfddk/formal_signal_engine.py` 是凍結短線 v1 規則與日後一次性資金會計之間的
point-in-time 橋接層。它只接受 provider ledger 的永久 `security_id`、逐期 S&P 500
成分、歷史分類、原始 OHLCV／總回報因子及 XNYS 日曆，按每個完整月末收市產生：

- 45% 12–1 月總回報動量；
- 25% 6–1 月總回報動量；
- 20% 相對 200-session wealth-index 平均線距離；
- 10% 較低 63-session 年率化波幅；
- 同公司股份類別按訊號日前 20 日中位美元成交額去重，同值以永久 `security_id`；
- 綜合排名首十隻，每個歷史 sector 最多三隻，不足槽位以 QQQ 補位。

訊號層固定使用 provider ledger 的 ICB classification，並把 membership `announced_at` 與 classification `known_at` 同 XNYS
`close_at` 比較；同日收市後才公布的資料會被排除。所有缺價、缺分類、歧義身份及
無法建立窗口的情況都 fail closed，不會以前視資料補值。

## 使用邊界

```python
from usfddk.formal_signal_engine import (
    build_monthly_target_weights,
    load_signal_inputs_from_ledger,
)

inputs = load_signal_inputs_from_ledger("/private/provider-package")
targets, audit = build_monthly_target_weights(inputs)
```

這段程式只返回內部 target table 與 feature audit，不會：

- 讀取現時 watchlist 或 ticker snapshot；
- 計算回報、Paper 交易或實金動作；
- 改寫正式回測 readiness、全域 trial ledger 或網站資料；
- 把合成控制或局部訊號結果升格為策略成功。

`usfddk/formal_execution_schedule.py` 會再把每個月末 target 映射到唯一的下一個
XNYS 開市日；最後一個 session、重複 execution、缺失 target 或權重不等於 100% 都會
拒收。這層仍不做估值，避免把「有 target」誤稱為「已完成回測」。

正式執行前仍必須先通過 Round 17 provider intake、point-in-time 20/20、execution
extension 16/16、RF 及 release firewall。資料包尚未到位時，網站維持成功-only
allow-list 與「今天不下單」。
