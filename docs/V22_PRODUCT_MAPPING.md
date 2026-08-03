# v22 九組美國產業產品對應稽核

狀態：在任何 v22 日線下載與組合計算前完成。目的只是在凍結正式期內確認普通與
2 倍 ETF 的底層指數一致；官方摘要績效不是策略績效證據。

## 官方申報證據

1. iShares 2021 年 SEC SAI 列出 IYM、IYK、IYC、IYF、IYH、IYJ、IYE、IYW、
   IDU，並把其當時底層列為相應 Dow Jones U.S. 產業指數。
2. iShares 年報說明 IYF 與 IYW 的原始 Dow Jones 指數績效只計到
   2019-06-23；自 2019-06-24 起改用帶集中度上限版本。因此正式終點固定為
   2019-06-21，不納入第一個定義變更交易日。
3. ProShares 2023-01-05 通過、預計 2023-03-17 生效的 SEC 補充文件，逐項記錄
   UYM、UGE、UCC、UYG、RXL、UXI、DIG、ROM、UPW 的舊 Dow Jones U.S. 產業
   指數改為相應 S&P Select Sector 指數。這反向確認九檔在本輪 2019 截止日前仍
   使用表列舊指數。
4. ProShares 現行頁與文件再次說明各基金只追求底層指數**單日**兩倍結果；持有
   多日可能顯著偏離簡單兩倍。

主要來源：

- iShares 2021 SAI：<https://www.sec.gov/Archives/edgar/data/1100663/000119312521034573/d56500d497.htm>
- iShares IYF/IYW 歷史指數說明：<https://www.sec.gov/Archives/edgar/data/1100663/000100472625000082/primary-document.htm>
- ProShares 2023 產業指數變更：<https://www.sec.gov/Archives/edgar/data/1039803/000168386323000056/f23854d0.htm>
- ProShares 槓桿 ETF 清單：<https://www.proshares.com/our-etfs/find-leveraged-and-inverse-etfs>

## 凍結配對與共同定義

| 產業 | 普通 ETF | 2 倍 ETF | 2007-07-31–2019-06-21 共同底層 | 判定 |
|---|---|---|---|---|
| 基礎材料 | IYM | UYM | Dow Jones U.S. Basic Materials | 通過 |
| 民生消費 | IYK | UGE | Dow Jones U.S. Consumer Goods | 通過 |
| 非必需消費 | IYC | UCC | Dow Jones U.S. Consumer Services | 通過 |
| 金融 | IYF | UYG | Dow Jones U.S. Financials | 通過 |
| 醫療 | IYH | RXL | Dow Jones U.S. Health Care | 通過 |
| 工業 | IYJ | UXI | Dow Jones U.S. Industrials | 通過 |
| 能源 | IYE | DIG | Dow Jones U.S. Oil & Gas | 通過 |
| 科技 | IYW | ROM | Dow Jones U.S. Technology | 通過 |
| 公用事業 | IDU | UPW | Dow Jones U.S. Utilities | 通過 |

## 邊界與停止規則

- 九組都只在 2019-06-21 以前視為定義一致；不得把 2019-06-24 以後的普通 ETF
  capped／Russell 路徑與 2023 年以前 ProShares 舊路徑硬稱同一指數。
- 不用現行 S&P Select Sector 配對回填舊期，也不以名稱相似取代正式指數稽核。
- 產品配對通過只證明研究問題可執行，不代表流動性、報酬或風險門檻會通過。
- 任一首次日線的成立日、缺值或成交資料不符凍結契約，保留失敗收據並停止該組，
  不換代號或移動起訖日。

