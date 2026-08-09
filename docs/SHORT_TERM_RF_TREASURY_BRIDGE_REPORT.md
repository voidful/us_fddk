# 短線個股第三十七輪：Treasury RF bridge 診斷報告

結果：**official_treasury_bridge_observed_formal_rf_still_blocked**
觀測時間（UTC）：`2026-08-09T02:10:43.773511Z`

## 結論

官方 Treasury Daily Treasury Bill Rates 的 4-week coupon-equivalent 可觀察到
**22/22** 個
2026-07 XNYS 缺日；這只證明官方來源有 rows，**不代表它等同 frozen French／ICE BofA
1-month RF**。本輪因此只作 proxy 差異診斷，不把 Treasury rows 寫入正式 RF manifest。

- source：`https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_bill_rates&field_tdr_date_value=2026`
- field：`ROUND_B1_YIELD_4WK_2`；HTTP：`200`；bytes：`586232`
- source SHA-256：`b35dd554d36e7735ea5aee84fffcb2042ae1bc49231594a2ba68fa37244dcaf6`；原始 XML 保存：**否**
- missing target sessions：`[]`
- error：沒有 probe error。

## 定義差異診斷

proxy daily simple 只按 `(1 + annual_percent / 100) ** (1 / 365) - 1` 轉換，不能取代
French data file 中「compounds to 1-month TBill return」且自 202406 使用 ICE BofA
US 1-Month Treasury Bill Index 的 RF。與 frozen RF 的重疊期只供量化差異：

| 指標 | 結果 |
|---|---:|
| overlap sessions | 123 |
| overlap range | 2026-01-02 → 2026-06-30 |
| mean diff | `-0.00003370` |
| mean absolute diff | `0.00003370` |
| max absolute diff | `0.00010283` |
| correlation | `-0.35236973` |
| formal equivalence | **False** |

## 22 日 derived rows

| date | annual 4-week CE % | proxy daily simple |
|---|---:|---:|
| 2026-07-01 | 3.63 | 0.0000976943 |
| 2026-07-02 | 3.67 | 0.0000987517 |
| 2026-07-06 | 3.67 | 0.0000987517 |
| 2026-07-07 | 3.65 | 0.0000982231 |
| 2026-07-08 | 3.63 | 0.0000976943 |
| 2026-07-09 | 3.69 | 0.0000992803 |
| 2026-07-10 | 3.69 | 0.0000992803 |
| 2026-07-13 | 3.70 | 0.0000995445 |
| 2026-07-14 | 3.70 | 0.0000995445 |
| 2026-07-15 | 3.70 | 0.0000995445 |
| 2026-07-16 | 3.73 | 0.0001003370 |
| 2026-07-17 | 3.71 | 0.0000998087 |
| 2026-07-20 | 3.70 | 0.0000995445 |
| 2026-07-21 | 3.70 | 0.0000995445 |
| 2026-07-22 | 3.71 | 0.0000998087 |
| 2026-07-23 | 3.79 | 0.0001019215 |
| 2026-07-24 | 3.77 | 0.0001013934 |
| 2026-07-27 | 3.75 | 0.0001008653 |
| 2026-07-28 | 3.70 | 0.0000995445 |
| 2026-07-29 | 3.67 | 0.0000987517 |
| 2026-07-30 | 3.70 | 0.0000995445 |
| 2026-07-31 | 3.69 | 0.0000992803 |

## 決策邊界

`formal_rf_substitute=false`、formal backtest 未授權、Paper `all_cash`、策略 run 0、
實金 US$0。不得以 Treasury proxy 回填 frozen French RF、改寫正式 readiness、重選參數
或建立交易建議。下一步仍是取得與正式定義一致、具授權及 row-level provenance 的完整 RF
manifest，並另外通過既有 18/18 formal、20/20 point-in-time 及 execution 閘門。

本報告只作研究及專業資訊參考，不構成投資建議、盈利證明或盈利保證。
