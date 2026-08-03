# 每日動量環境共振：schema-informed 工程診斷協議 v1

凍結日期：2026-08-04

證據等級：**已知 schema 的工程診斷，不是獨立首次外部驗證。**

## 不可改寫的第十輪失敗

第十輪原協議在提交 `1c1310fba545c1ac53d7d3419985755ffe8f0bf2` 後才首次下載
French 日檔。URL、ZIP 及 member 正確，但原映射要求精確 marker
`Value Weight Returns -- Daily`，官方實檔為
`Average Value Weighted Returns -- Daily`。首次運行按設計在策略計算前停止，原始 ZIP
及 4/9 收據已提交為 `0adf141`；不得修改或刪除該失敗。

為確認差異，工程檢視顯示：

- member：`10_Portfolios_Prior_12_2_Daily.csv`；
- 精確 marker 多一個 `Average ` 前綴；
- header 仍是凍結的十個 Prior 欄；
- 標題檢視同時顯示了 1926-11-03 起首批原始日列，但沒有解析、彙總、計算策略、
  查看任何正式期績效或改動策略規則。

因此本診斷固定 `independent_first_seen_evidence=false`。它只能回答「原策略在已封存
官方日檔上會得到甚麼工程結果」，不能把 schema 修正後的數字包裝成第十輪首次證據。

## 唯一允許修正

只把 parser 精確 marker 改為：

`Average Value Weighted Returns -- Daily`

其餘全部沿用
[`SHORT_TERM_DAILY_MOMENTUM_REGIME_PROTOCOL.md`](SHORT_TERM_DAILY_MOMENTUM_REGIME_PROTOCOL.md)：

- 同一 `a19daa6c84ef6232f3f867159e2752c2a437d5990d6f3bf673fd91317eab6093` ZIP，
  不重新下載、不換 TXT、不格式化原檔；
- 同一十欄順序、value-weighted daily table、1963–2006／2006–2026 固定期；
- 同一 20／60 日市場趨勢、60% 廣度、5／10／15／20 日至少兩窗共振；
- 同一 0／50／100% `Hi PRIOR`／RF 曝險；
- 同一 5% 年度學術實作拖累、10／25／50 bps 曝險變動成本；
- 同一 QQQ、SPY、French 市場、十組等權、永久 Hi、相同曝險市場、固定平均曝險、
  60 日二元及無共振控制；
- 同一切片、危機、Newey-West、PSR、DSR、PBO 及 48 道門檻；
- 全域搜尋懲罰仍是 6,208；本修正沒有新增策略候選。

不得模糊搜尋 marker、接受多個可能表格、刪除異常日、補值、移動日期、改成本、降低
門檻，亦不得按結果換成二元／無共振消融。

## 入口與決策

工程計算前必須同時驗證：

1. 第十輪原協議及映射 SHA-256 仍分別為
   `aee1d081bcbfbd819d6c6a6a3362e241e0aab8585cb087e45fed2d1f30464cdc`、
   `7ee12c479383810cae133a39951a4b3b20ddee3dbeb7c1c38ec79e753578baa1`；
2. 原失敗收據狀態仍是 `daily_momentum_regime_first_download_contract_failed_before_strategy`；
3. 原 ZIP、French market／RF 及 QQQ／SPY 快照雜湊全部相符；
4. 本 repair 協議的 SHA-256 與另存收據一致，且收據早於首次彙總／策略計算。

即使工程診斷 48/48，仍固定：`paper_eligible=false`、`trade_ready=false`、
`paper_state_created=false`、`real_money_action_usd=0`。正式短線 Paper 仍只接受逐股
point-in-time 賬本 20/20 及既有 v1 全門檻；本診斷不授權持倉或實金。

