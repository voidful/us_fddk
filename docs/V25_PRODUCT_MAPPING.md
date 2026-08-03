# v25 美國大型成長＋黃金產品映射（首次聯合日線下載前凍結）

凍結時間以 `artifacts/v25_protocol_receipt.json` 為準。凍結前已閱讀產品官方
摘要與部分公開的長期績效，因此本輪不是完全盲測；但尚未下載或計算 v25 三條
80/20 聯合日線路徑。

## 唯一候選

| 路徑 | 成長袖套 80% | 黃金袖套 20% | 公平曝險控制 | 市場基準 |
|---|---|---|---|---|
| Vanguard | `VUG` | `GLD` | 80% `VUG`／20% `SHY` | `SPY` |
| iShares | `IWF` | `IAU` | 80% `IWF`／20% `SHY` | `SPY` |
| State Street | `SPYG` | `GLD` | 80% `SPYG`／20% `SHY` | `SPY` |

- `VUG`：Vanguard Growth ETF，2004-01-26 成立，屬美國大型成長指數產品。
  Vanguard 已公告 2026-04-21 生效 6:1 拆股，因此資料契約必須確認調整後序列
  沒有把拆股誤認成約 −83% 的投資損失。
- `IWF`：iShares Russell 1000 Growth ETF，2000-05-22 成立，追蹤 Russell
  1000 Growth Index。v13 曾使用 IWF 作成長袖套，因此這條路徑屬已見產品定義；
  新證據只來自凍結後的 IWF／IAU 聯合 80/20 路徑，不能稱完全外部。
- `SPYG`：State Street SPDR Portfolio S&P 500 Growth ETF，2000-09-25
  成立。目前追蹤 S&P 500 Growth Index；發行人揭露成立至 2010-12-17 前的
  歷史基準為 Dow Jones U.S. Large Cap Growth Total Stock Market Index，之後
  才是 S&P 500 Growth Index，因此 20 年產品報酬包含指數拼接。
- `GLD`：SPDR Gold Shares，2004-11-18 成立，目標反映金條價格扣除費用；
  不生息，且為支付費用每股代表的黃金量會逐步下降。
- `IAU`：iShares Gold Trust，2005-01-21 成立，同樣以持有實物黃金反映金價；
  用來檢查結果是否依賴單一黃金載具。
- `SHY`：iShares 1–3 Year Treasury Bond ETF，作為相同 80% 成長股曝險、20%
  低波動美元資產的公平控制。它有利率與信用利差以外的產品風險，不等於現金。
- `SPY`：廣泛美國大型股市場門檻。跑贏 SPY 不足以證明 alpha；候選還必須跨過
  相同成長曝險控制，並改善純成長 ETF 的風險路徑。

## 正式期間與資料契約

- 三份首次快照都下載 2006-07-01 至 2026-08-01（exclusive），正式月報酬
  2006-08 至 2026-07，恰 240 個月。
- Vanguard 快照：`GLD`、`SHY`、`SPY`、`VUG`。
- iShares 快照：`IAU`、`IWF`、`SHY`、`SPY`。
- State Street 快照：`GLD`、`SHY`、`SPY`、`SPYG`。
- 使用調整後 OHLC 與成交量，保留單次首次下載 ZIP。若欄位、完整月份、拆股
  處理或日期唯一性失敗，只能封存本輪，不能換供應商後挑較漂亮版本。

## 不得事後改寫的界線

- 80/20 是本輪唯一權重；不因某一路徑落後改成 70/30、90/10 或純成長。
- 不把三家成長指數當成完全相同；它們是產品定義敏感度，全部都要保留。
- 黃金可能數年落後、沒有收益，且股票與黃金可以同跌；不得把歷史分散效果說成
  保本或未來保證。
- 若 v25 通過歷史入口，也只能啟動隔離 Paper；不得直接把回測百分比升格為實金
  指令。
