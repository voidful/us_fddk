# v21 官方產品配對稽核

稽核狀態：本檔必須與 v21 協議一起完成雜湊收據，且早於任何 UMDD／URTY 日線
下載與任何 v21 策略績效計算。

## 結論

v21 的兩組外部產品在固定正式期 2011-07-29–2026-07-31 使用相同名稱與範圍的
底層指數：IJH／UMDD 對應 S&P MidCap 400，IWM／URTY 對應 Russell 2000。所查
產品成立文件、現行公開說明與 SEC 系列延續資料中，未發現類似 v19 的正式期內
指數範圍錯位。

因此產品配對資料門檻允許進入**首次日線下載**，不代表策略通過、產品低風險或
已可 Paper。兩個槓桿 ETF 都只追求單日三倍結果，長期持有不等於指數長期報酬
的三倍。

## 配對判定

| 市場 | 核心 ETF | 每日 3 倍 ETF | 官方定義 | 正式期判定 |
|---|---|---|---|---|
| 美國中型股 | `IJH` | `UMDD` | IJH：S&P MidCap 400；UMDD：S&P MidCap 400 每日 3 倍 | 名稱與範圍相符 |
| 美國小型股 | `IWM` | `URTY` | IWM：Russell 2000；URTY：Russell 2000 每日 3 倍 | 名稱與範圍相符 |

## 歷史一致性證據

- 2010-02-09 的 ProShares UltraPro 系列成立 prospectus 同日列出 UMDD 與 URTY，
  並將目標分別定義為 S&P MidCap 400、Russell 2000 的每日三倍；文件明確說明
  目標是單日，不適用於超過一天的期間。
- 現行 UMDD、URTY summary prospectus 仍使用同一底層指數名稱與每日三倍目標。
- 2017 年 SEC 系列資料仍列出相同基金名稱與代號，支持產品系列在正式期內延續。
- IJH、IWM 的發行人現行產品頁分別將基準列為 S&P MidCap 400、Russell 2000。

這項稽核確認的是可比較的市場範圍，不代表普通與槓桿 ETF 的長期報酬必須成固定
倍數。費用、持股方式、衍生品、現金、每日重設、稅務與追蹤誤差仍會造成差異。

## 污染與證據邊界

產品識別時已看見 ProShares 官方頁的摘要績效表，但未查看或下載 UMDD／URTY
日線，也未把摘要數字帶入規則、權重、日期或成功門檻。因摘要績效已見，v21 外部
結果只可稱「未看日線路徑的半獨立驗證」，不得稱完全盲測。

## 官方來源

- IJH：<https://www.ishares.com/us/products/239763/ishares-core-s-p-mid-cap-etf>
- IWM：<https://www.ishares.com/us/products/239710/ishares-russell-2000-etf>
- UMDD：<https://www.proshares.com/our-etfs/leveraged-and-inverse/umdd>
- URTY：<https://www.proshares.com/our-etfs/leveraged-and-inverse/urty>
- 2010-02-09 成立 prospectus：<https://www.sec.gov/Archives/edgar/data/1174610/000119312510023274/d485bpos.htm>
- UMDD 現行 summary prospectus：<https://www.proshares.com/globalassets/proshares/prospectuses/umdd_summary_prospectus.pdf>
- URTY 現行 summary prospectus：<https://www.proshares.com/globalassets/proshares/prospectuses/urty_summary_prospectus.pdf>
- 2017 SEC 系列資料：<https://www.sec.gov/Archives/edgar/data/1174610/000110465917027863/0001104659-17-027863-index.html>

