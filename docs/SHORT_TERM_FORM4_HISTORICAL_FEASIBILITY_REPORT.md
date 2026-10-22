# 美股短線 Form 4 歷史事件可行性報表（Round 49）

更新：`2026-08-10`　｜　狀態：**事件率診斷通過；尚未回測、尚未 Paper、尚未升格**

## 結論

三個事前固定、非連續季度的 SEC Form 4 樣本，按固定的「至少兩份 distinct filing、至少
兩個 reporting-owner CIK、每份不少於 US$10,000、cluster 合計不少於 US$100,000」規則，
共產生 **805 個 primary clusters**，高於事前設定的 30 個 feasibility gate。

這只證明事件量足以支持下一階段正式歷史回測的事前登記，不代表策略有 alpha、能跑贏 QQQ／SPY、
值得建立 Paper 倉或可以落盤。網站維持「今天不下單」。

## 固定樣本結果

| 季度 | Form 4 submissions | 合資格 purchase accessions | 合資格交易列 | primary clusters | 邊界排除 |
|---|---:|---:|---:|---:|---:|
| 2006Q1 | 68,520 | 4,927 | 11,718 | 267 | 46 |
| 2016Q3 | 35,714 | 3,245 | 6,096 | 239 | 23 |
| 2026Q2 | 49,832 | 2,998 | 4,818 | 299 | 33 |
| **合計** | **154,066** | **11,170** | **22,632** | **805** | **102** |

`邊界排除` 是每季起始 19 個 calendar days 的 left-truncated cluster；三季彼此不連續，
沒有跨季 window 或 cooldown，所以不能把 805 除以三季推算年化訊號率。

## 事件質量及控制

- 只納入 `DOCUMENT_TYPE=4`、`TRANS_FORM_TYPE=4`、`TRANS_CODE=P`、`A` 及可證明非 equity
  swap 的非衍生交易；`4/A`、非買入、swap unknown、非正或非 finite shares／price 均排除並
  以 aggregate reason 記錄。
- 同一 `(ACCESSION_NUMBER, NONDERIV_TRANS_SK)` 只計一次；同一 accession 有多位 reporting
  owners 時，purchase dollars 不會重複相乘。
- 20 calendar-day inclusive window、同日批次、D+20 cooldown、US$10k／US$100k 門檻全部
  在讀取事件前凍結；沒有因 805 這個結果重選參數。
- receipt 不含 ticker、issuer、姓名、CIK、accession、逐筆 filing date 或 exact notional；
  row-level data 只在 process memory 存在，未寫入 repository。

## 不能由本輪推論的事項

SEC 將資料描述為 quarterly、as-filed 的 Forms 3／4／5 flattened data，並提醒資料可能含有
申報或抽取錯誤，且不代替完整 EDGAR filing。資料頁目前涵蓋 January 2006 至 June 2026，
但本輪只使用三季固定樣本，沒有完整 filing denominator、PIT security master、退市／公司
行動、XNYS market clock 或 raw execution price。故本輪沒有任何 CAGR、Sharpe、最大跌幅、
win rate、QQQ／SPY relative return 或統計顯著性結論。

下一階段若要正式回測，必須另行凍結連續季度及 point-in-time market data，沿用 Round 46 的
D+1 raw-open、D+10 close、十槽、D+20 XNYS cooldown、10／25／50 bps 四腿成本，並以 QQQ、
SPY、PIT equal-weight、single-owner、price-volume matched 及 permutation controls 共同否決。
在該回測完成前，本診斷不得改寫 Round 46、不得建立 Paper、不在網站展示任何人物或股票。

資料來源：

- [SEC Insider Transactions Data Sets](https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets)
- [SEC Insider Transactions data dictionary](https://www.sec.gov/files/insider_transactions_readme.pdf)
