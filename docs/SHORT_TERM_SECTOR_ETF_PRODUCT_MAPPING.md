# 短線行業 ETF 外部驗證：產品映射 v1.0

凍結日期：2026-08-03

用途：為短線 20 日動量訊號提供首次外部產品路徑。所有代號在本文件及協議提交後才可
首次下載共同日線；不得因結果、缺值或回報排名更換產品。

## Vanguard 行業投資範圍

| 行業 | ETF | 官方產品頁 | 官方成立日 |
|---|---|---|---|
| 基礎材料 | VAW | https://investor.vanguard.com/investment-products/etfs/profile/vaw | 2004-01-26 |
| 非必需消費 | VCR | https://investor.vanguard.com/investment-products/etfs/profile/vcr | 2004-01-26 |
| 必需消費 | VDC | https://investor.vanguard.com/investment-products/etfs/profile/vdc | 2004-01-26 |
| 能源 | VDE | https://investor.vanguard.com/investment-products/etfs/profile/vde | 2004-09-23 |
| 金融 | VFH | https://investor.vanguard.com/investment-products/etfs/profile/vfh | 2004-01-26 |
| 資訊科技 | VGT | https://investor.vanguard.com/investment-products/etfs/profile/vgt | 2004-01-26 |
| 醫療保健 | VHT | https://investor.vanguard.com/investment-products/etfs/profile/vht | 2004-01-26 |
| 工業 | VIS | https://investor.vanguard.com/investment-products/etfs/profile/vis | 2004-09-23 |
| 通訊服務 | VOX | https://investor.vanguard.com/investment-products/etfs/profile/vox | 2004-09-23 |
| 公用事業 | VPU | https://investor.vanguard.com/investment-products/etfs/profile/vpu | 2004-01-26 |

這十隻產品均為美國本土行業指數 ETF。VOX 及其指數分類在產品歷史中曾隨行業分類
演變；本研究保留真實產品路徑，不回填今日分類持股，也不把十隻 ETF 冒充固定不變的
公司層投資範圍。

## 固定基準及現金代理

| 角色 | ETF | 用途 |
|---|---|---|
| 高回報機會成本 | QQQ | 主要回報基準 |
| 美國大型股 | SPY | 廣泛市場基準 |
| 美國全市場 | VTI | 與 Vanguard 行業產品較接近的廣泛基準 |
| 現金／短債代理 | SHY | 不足三個合資格行業時的未用比例及超額回報基準 |

上述四隻不參與行業排名。任何單一 Vanguard 行業 ETF 的回報只列作事後診斷，不可把
全期最佳者反選為新基準或候選。

## 映射邊界

- 不加入成立較晚的房地產行業 ETF，以免縮短固定 20 年窗口。
- 不用槓桿、反向、主動管理或期權 ETF。
- 不聲稱 Vanguard 與既有 SPDR 行業產品逐日完全同質；本輪測試的是同一訊號在另一家
  實際產品家族能否保留方向，而不是把兩者價格拼接成更長歷史。
- 產品頁只證明代號、投資類別及成立日；實際回測一律使用凍結後單次下載並雜湊的經調整
  OHLCV，不抄用官方網頁顯示的期間回報。
