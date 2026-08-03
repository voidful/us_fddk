# v19 官方產品配對稽核

稽核時間：2026-08-02T18:58:39Z。這項稽核在 v19 協議凍結後、任何 v19 策略績效計算與外部日線下載前完成。

## 結論

v19 的官方產品配對資料門檻 **失敗**，因此不得下載凍結的外部日線、不得計算 v19 績效，也不得建立 v19 Paper。

日本與中國大型股目前的產品定義相符；歐洲配對在正式驗證期內有約十一個月追蹤範圍不一致：VGK 自 2015-10-01 起使用 FTSE Developed Europe All Cap Index，UPV 的 SEC 文件則記載到 2016-08-31 仍使用 FTSE Developed Europe Index，2016-09-01 才改為 All Cap。前者包含 small cap，後者不包含。

## 三組配對

| 市場 | 核心 ETF | 每日 2 倍 ETF | 官方定義 | 判定 |
|---|---|---|---|---|
| 日本 | EWJ | EZJ | EWJ：MSCI Developed - Japan Net Dividends (USD)；EZJ：MSCI Japan Index 每日 2 倍 | 同市場、同範圍，目前定義相符 |
| 歐洲 | VGK | UPV | 兩者目前皆為 FTSE Developed Europe All Cap；但歷史轉換到 All Cap 的日期不同 | **全期不相符** |
| 中國大型股 | FXI | XPP | FXI：FTSE China 50 Index (Net)；XPP：FTSE China 50 Index 每日 2 倍 | 同市場、同範圍，目前定義相符 |

「Net」代表扣除適用股息預扣稅後的指數報酬版本；每日 2 倍產品的目標是單日結果，不代表長期兩倍。這些差異仍須在後續風險揭露中保留。

## 歐洲歷史斷點證據

- Vanguard 官方頁面記載 VGK 的拼接基準：MSCI Europe 至 2013-03-26、FTSE Developed Europe 至 2015-09-30、其後為 FTSE Developed Europe All Cap。
- ProShares 的 SEC 申報記載 UPV：MSCI Europe 至 2013-04-22、FTSE Developed Europe 自 2013-04-23 至 2016-08-31、FTSE Developed Europe All Cap 自 2016-09-01 起。
- 兩檔在 2015-10-01 至 2016-08-31 的底層範圍不同，違反凍結協議「同名、同範圍」要求。這不是報酬表現問題，而是資料識別問題，所以在首次下載前即停止。

## 官方來源

- EWJ：<https://www.ishares.com/us/products/239665/ishares-msci-japan-etf>
- EZJ：<https://www.proshares.com/our-etfs/leveraged-and-inverse/ezj>
- VGK：<https://investor.vanguard.com/investment-products/etfs/profile/vgk>
- UPV：<https://www.proshares.com/our-etfs/leveraged-and-inverse/upv>
- UPV 歷史基準（SEC）：<https://www.sec.gov/Archives/edgar/data/1174610/000168386324005553/f39402d1.htm>
- FXI：<https://www.ishares.com/us/products/239536/ishares-china-largecap-etf>
- XPP：<https://www.proshares.com/our-etfs/leveraged-and-inverse/xpp>

