# 美股短線落後反轉無市場濾網控制報告（Round 59）

版本：1.0
研究快照截至：2026-07-31
狀態：**post-hoc 正面控制診斷；不建立策略、不建立 Paper；實金動作 US$0；今天不下單。**

## 結論

本輪移除 Round 57 的 SPY 急跌條件，保留同一個現時 30 檔大型股觀察池、五日跌幅不高於
-5%、最弱 Top-5、20 bps 成本及 5／10／20-session 持有期。無市場濾網的 20-session 配對差
為 **+1.127 個百分點**，Newey–West t=**3.62**，bootstrap 95% 下界 **+0.525 個百分點**，
勝率 **55.2%**，六項 gate 全部通過。

這不是好消息的交易授權：Round 59 是看到 Round 57／58 後才加入的 post-hoc robustness
control，並非獨立首次證據；它顯示表面上的落後反轉未必需要市場急跌條件，故不能把 Round57
的 SPY 濾網宣稱為增量 alpha。現時觀察池的 survivorship bias 及缺少 point-in-time／退市
經濟數據仍完全阻止 Paper 或實金升格。

| 指標 | 5-session | 10-session | 20-session 主要 |
| --- | ---: | ---: | ---: |
| 完整事件數 | 755 | 751 | 747 |
| 落後 Top-5 平均回報（扣 20 bps） | 0.883% | 1.501% | 3.027% |
| 合資格池等權平均回報 | 0.435% | 0.846% | 1.900% |
| 配對差 | +0.447 個百分點 | +0.655 個百分點 | **+1.127 個百分點** |
| SPY／QQQ 同期平均回報 | 0.235%／0.357% | 0.450%／0.669% | 1.186%／1.547% |
| Newey–West t | 2.98 | 3.09 | **3.62** |
| bootstrap 95% 下界 | +0.075 個百分點 | +0.154 個百分點 | **+0.525 個百分點** |
| 配對勝率 | 52.5% | 55.8% | 55.2% |

20-session 前／後固定期間配對差為 +0.438／+1.667 個百分點；全部六項主要 gate 通過。這些
是事件平均數，不是可實現資金曲線：事件會重疊，且沒有 raw execution、滑點、停牌、退市／
收購完整賬本。

## Round57／58 的含義

- Round57「SPY 單日跌至少 1.5%」：204 宗、20-session +1.355 個百分點，survivorship-biased。
- Round58「SPY 單日升至少 1.5%」placebo：54 宗、20-session +1.379 個百分點，但 t=1.74
  未過門檻。
- Round59 無市場濾網：747 宗、20-session +1.127 個百分點，六項 gate 通過，但屬 post-hoc
  control。

三者不能當作三個可選策略；Round59 只令「市場急跌濾網有額外價值」這個說法更不可信，並
提高全域試驗下限至 6311。下一道真正可升格證據仍是合法 point-in-time security master、
退市／收購結果、raw execution 與獨立 forward Paper。

結果只寫入研究 log 和機器收據；公開頁面只接受已驗證可行策略，目前仍顯示「今天不下單」。

機器收據：

- protocol：`artifacts/short_term_laggard_reversal_unconditional_protocol_receipt.json`；
- validation：`artifacts/short_term_laggard_reversal_unconditional_validation.json`；
- multiplicity：Round59 family，全域下限 6311。

本報告只作研究及教育用途，不構成投資建議、Paper 成交或實金落盤指令。
