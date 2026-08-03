# 香港金融用語準則

本專案所有對外網站與研究報告使用香港金融市場常見的繁體中文。策略代號、JSON 欄位、統計公式及歷史數值不因用詞本地化而改動。

## 對外詞彙

| 概念 | 報告用詞 | 保留的業界縮寫 |
| --- | --- | --- |
| return / total return | 回報／總回報 | CAGR |
| annualized return | 年率化回報 | CAGR |
| volatility | 波幅 | — |
| maximum drawdown | 最大跌幅 | MDD |
| portfolio | 投資組合；Paper 模擬組合 | Paper Trading |
| position / allocation | 持倉／配置 | — |
| exposure | 持倉比率；名義持倉比率 | — |
| rebalance | 重新平衡 | — |
| buy / sell | 買入／沽出 | — |
| place an order | 落盤 | — |
| market close / open | 收市／開市 | — |
| data | 數據 | — |
| performance | 表現 | — |
| net asset value | 資產淨值 | NAV |
| stop loss | 止蝕 | — |
| profit and loss | 盈虧 | P&L |

首次出現 Paper 時寫作「Paper Trading（模擬交易）」或「Paper（模擬交易）」。其後可保留 Paper，以便對照程式、稽核收據及國際市場慣用名稱。

## 官方用語依據

- 香港投資者及理財教育委員會使用「回報的波幅」及「最大跌幅」說明基金表現指標：[監察表現](https://www.ifec.org.hk/web/tc/investment/investment-products/funds/hedge-funds/monitoring-performance.page)。
- 投委會使用「投資組合」及「重新調整／重新平衡」說明資產配置：[應否重新調整投資組合？](https://www.ifec.org.hk/web/tc/financial-products/fintech/robo-adviser/rebalancing-or-not.page)、[每日重新平衡](https://www.ifec.org.hk/web/tc/investment/investment-products/leveraged-and-inverse-products/know-daily-rebalancing.page)。
- 投委會及港交所使用「買入」、「沽出」與「持倉」：[期貨及期權投資](https://www.ifec.org.hk/web/tc/investment/investment-products/futures-and-options/index.page)、[港交所期權策略概覽](https://www.hkex.com.hk/chi/sorc/frontend/strategies_ratioputback_received_c.htm)。
- 證監會以「回報」、「波幅」及「基準指數」描述投資表現比較：[證監會 2023–24 年報](https://www.sfc.hk/-/media/TC/files/COM/Annual-Report/2023-24/22_.pdf)。

## 報告架構參考

- [appr1ciat1/tst_wocker](https://github.com/appr1ciat1/tst_wocker)：策略摘要、詳細研究與 Paper 分層。
- [appr1ciat1/tw-block-warrant](https://github.com/appr1ciat1/tw-block-warrant)：每日訊號、數據來源與更新狀態。
- [appr1ciat1/tst_wocker_filter_lab](https://github.com/appr1ciat1/tst_wocker_filter_lab)：獨立候選報告、前瞻紀錄、發布守門及負結果稽核。

以上只用作資訊架構參考。由於三個參考倉庫沒有標示可重用授權，本專案不複製其程式碼、文案、台股參數或歷史結果。
