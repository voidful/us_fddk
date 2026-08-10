# 美股短線第 42 輪：SEC Form 4 准入可行性報告

## 結論先行

第 42 輪按事前凍結規則，在 **2006Q1／2016Q3／2026Q2** 三個固定季度取得
**12 份** Form 4／4-A 細樣本。Form 4 專屬准入只通過
**2/16**，結果為 **停止且不作准入聲稱**；不會因部分工程證據
改寫門檻、改抽樣本或產生選股。

收集程序精確停在 **5 個已完成 HTTP request** 之後的
**1 次 post-fetch 本地驗證失敗**；complete-submission
request 為 **0**，cold replay **未完成**。因此不能寫成
真實細樣本已成功重播。

停止原因是：

- `form4_feasibility_daily_index_missing_or_ambiguous`：SEC 每日 Form index 未能為全部固定樣本提供唯一、可重播的匹配列。

這 12 份固定細樣本不是 12 隻股票，也不是可交易事件或推薦名單。
本輪沒有建立 20 年 filing／known-at 完整分母，沒有計算任何回報、風險或基準比較數值。
候選選擇 **0**、策略運行 **0**、
回報結果 **0**。Paper Trading（模擬交易）未授權並維持**全現金**、持倉 0、不可回填，
實金動作 **US$0**。**今天不下單。**

## 一目了然

| 項目 | 已驗證狀態 | 不可推論 |
|---|---|---|
| 固定季度 | 2006Q1／2016Q3／2026Q2 | 不代表 2006–2026 完整覆蓋 |
| 固定細樣本 | 12 份 | 不代表股票名單、事件分母或選股勝率 |
| Form 4 准入 | 2/16 | 低於 16/16 不准建立候選或策略 |
| 收集／重播 | 5 個 HTTP request 完成；1 次本地驗證失敗；cold replay 未完成 | 不代表真實細樣本已成功重播 |
| complete submission | 0 次 request | 沒有 as-filed complete-submission 重播證據 |
| 20 年 known-at | 未驗證 | SEC accepted time 或 nightly index 日期不能冒充歷史已知時間 |
| 動態選擇 | 停用 | 不產生買入、沽出、持倉或落盤指示 |
| Paper／實金 | 全現金／US$0 | 沒有 Paper 成交或實金授權 |

## 十六項 Form 4 准入門檻

| # | Form 4 准入門檻 | 結果 | 公開判讀 |
|---:|---|---|---|
| 01 | 父協議、修訂及收據雜湊鏈一致 | **通過** | 凍結父鏈雜湊一致 |
| 02 | SEC 精確用途、存取及完整嘗試紀錄已驗證 | 未通過 | 尚未建立全專案精確用途及完整嘗試紀錄 |
| 03 | 加密私有隔離及獨立證據已驗證 | 未通過 | 尚未建立獨立加密隔離證據 |
| 04 | 來源只限 SEC Form 4／4-A | **通過** | 來源及表格類型精確 |
| 05 | 完整申報分母已重播 | 未通過 | 未重播完整申報分母 |
| 06 | 全部 as-filed 內容及收據齊全 | 未通過 | 未重播完整分母的 as-filed 內容 |
| 07 | 2005Q4 暖機至 2026Q2 固定期間完整 | 未通過 | 未重播完整固定期間 |
| 08 | 歷史 known-at 證據完整 | 未通過 | 欠缺外部歷史 known-at 證據 |
| 09 | 收市決策及下一開市時鐘已驗證 | 未通過 | 沒有執行決策及落盤時鐘映射 |
| 10 | 4/A 修訂鏈唯一且不可回填 | 未通過 | 未重播完整版本及修訂鏈 |
| 11 | Form 4 交易語意及註腳完整 | 未通過 | 未重播完整分母的交易語意 |
| 12 | 共同持有及同一經濟交易已去重 | 未通過 | 未重播經濟事件去重 |
| 13 | 當時可知證券與股份池已驗證 | 未通過 | 未重播當時可知證券與股份池 |
| 14 | 當時可知行情及公司行動已驗證 | 未通過 | 未重播當時可知行情及執行輸入 |
| 15 | 獨立單欄變異攻擊全部拒收 | 未通過 | 本地 fixture 攻擊不是完整獨立准入攻擊 |
| 16 | 獲授權真實細樣本已獨立重播 | 未通過 | 真實細樣本未獲准入接受 |

兩項通過只表示父協議雜湊鏈及 SEC Form 4／4-A 來源範圍精確。其餘十四項沒有以缺失
資料、推測時間或較寬規則補值；任何一項未通過，准入都必須停止。

## 停止原因與 known-at 邊界

本次固定樣本未能在 SEC 每日 Form index 中全部得到唯一匹配，因此不能把後來下載到的
季度資料或 complete submission 倒填成當時已知。nightly index 只屬日級 archive evidence，
不是精確公開時間；SEC accepted time 也不能單獨充當 known-at。本輪因此沒有映射收市決策
或下一開市落盤時鐘。

程序在第 5 個已完成 HTTP request 後才於本地驗證停止；這是一項 post-fetch validation
failure，不是網路 request 失敗。停止後 complete-submission request 為
0，cold replay 未完成；所有後續階段均維持 0。

`P` 在 SEC Form 4 的語意是「公開市場或私人購買」，並不等於已證實的公開市場買入。
「企業家」也不是 SEC 法定申報身份；只能按 Section 16 董事、高級人員及逾 10% 股東等
可驗證角色處理，不能按知名度、姓名或事後結果建立人物權重。

## 私隱、研究與交易邊界

公開收據只保留三個固定季度、總樣本數、十六項門檻、停止碼、狀態邊界及私有 manifest
的整體 SHA-256 承諾。它不包含人物、CIK、accession、公司、股票代號、文件位置、原文或
逐筆交易資料。私有樣本不會流入 Git、CI 或網站內容。

Congress PTR 仍是分離來源，未獲本專案精確用途書面准許前不收集、不選股。公開披露
Phase 1 仍為 2/20；Round 42 細樣本不能替它補成 20/20，也不授權策略、Paper 或實金。

本報告只作研究及專業資訊參考，不構成投資或法律建議，不保證盈利。

## 可重播公開檔案

- `artifacts/short_term_form4_admission_feasibility_validation.json`
- `site/data/short-term-form4-admission-feasibility.json`
- `docs/SHORT_TERM_FORM4_ADMISSION_FEASIBILITY_PROTOCOL.md`
- `docs/SHORT_TERM_FORM4_ADMISSION_FEASIBILITY_SCHEMA_AMENDMENT_V1_1.md`
