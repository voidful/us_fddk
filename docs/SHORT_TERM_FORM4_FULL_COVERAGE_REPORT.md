# 美股短線 Form 4 全季度覆蓋研究報告（Round 52）

## 結論

82/82 個 SEC 官方季度檔案（2006Q1–2026Q2）完成 bytes、SHA-256、ZIP、CRC、metadata
projection 及 aggregate replay。這證明資料入口可以供下一輪另行預註冊，但**沒有證明任何
短線 alpha、回報或可執行策略**。

因此本輪只保留研究 log；網站不顯示 Form 4 訊號、個股名單、持倉比例或行動建議，狀態維持
「今天不下單」。

## 覆蓋統計（aggregate-only）

| 指標 | 結果 |
| --- | ---: |
| SEC 季度檔案 | 82 / 82 |
| Form 4 submissions | 3,934,823 |
| 合資格 purchase transaction rows | 714,819 |
| 合資格 purchase accessions | 352,424 |
| current CIK exact 命中 | 643 |
| as-filed symbol exact 命中 | 651 |
| 兩條路徑 union 命中 | 664 |

current CIK 與 as-filed symbol 只作兩條分開的確定性對照；watchlist 是現時 30 檔大型股，並非
歷史 point-in-time 成分。報告不保存或呈現 ticker、CIK、accession、owner、filing date、issuer
name 或逐筆 notional。

## 不可解讀為投資訊號的原因

- 現時 CIK 對照不是歷史 security master，不能回溯當時上市代號、合併、拆股或除牌狀態。
- 現時 watchlist 帶有 survivorship bias，coverage 不能代表可投資全集。
- 本輪沒有定義 SEC 公開時間至可成交時間的 event clock，亦沒有交易價、滑點、佣金、baseline、
  out-of-sample 或 regime 分層回報。
- 沒有策略選股、收益計算、Paper 成交或 real-money authorization；不得以 coverage 數量替代
  可交易性及風險審核。

## 下一個準入條件

若要把 Form 4 研究提升為策略，必須另立協議並重新綁定 trial ledger：先固定 point-in-time
security master、披露可用時間、執行價格與成本，再作 walk-forward、ETF baseline、multiple-
testing、失敗結果及獨立 Paper forward test。任何一項未通過，失敗只寫入 validation／CI log，
網站維持 success-only。

本報告是資料工程及研究準入紀錄，不構成投資建議、Paper 成交或實金落盤指令。
