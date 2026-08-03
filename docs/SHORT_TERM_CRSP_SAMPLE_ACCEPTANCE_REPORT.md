# 美股短線高回報研究｜第十二輪 CRSP／WRDS 樣本驗收報告

研究日期：2026-08-04　｜　狀態：**驗收器通過；供應商及策略仍未通過**

## 一頁結論

本輪沒有再調策略，也沒有下載受限制數據。事前凍結的 12 個 manifest、時間、永久 ID、
退市及幽靈價格攻擊全部被指定閘門拒收；合成控制包則為 20/20。這證明驗收器現在能擋住
本輪固定的錯誤，**不證明 CRSP／WRDS 已合格**。

真實 point-in-time／退市數據仍為 **1/20**，合法供應商樣本 0，正式 20 年個股回測 0，
短線 Paper 維持全現金、0 成交、0 持倉，實金動作 **US$0**。

| 驗證層 | 結果 | 正確解讀 |
|---|---:|---|
| 合成控制包 | 20/20 | 只證明合約可接收結構完整的合成包 |
| 凍結攻擊 | 12/12 拒收 | 只證明十二類已知錯誤 fail closed |
| 真實供應商包 | 1/20 | 只有事前凍結通過；尚無合法原始包 |
| 正式短線回測 | 0 | 不可由合成測試推升 |
| Paper／實金 | 0／US$0 | 仍鎖定 |

## 本輪修正了甚麼

原驗證器會檢查 top-level manifest 及 20 道語義閘門，但沒有完整執行巢狀 schema；此外，
`known_at`／`announced_at` 曾先正規化成日期再比較，同日較遲才公布的數據有被誤收風險。
本輪依已凍結合約補上：

- `license_attestation` 必要／可選欄位及額外欄位拒收；
- 所有時間必須帶明確 UTC offset，匯出不得晚於首次匯入；
- identifier、membership、classification 以紐約生效日午夜作無前視邊界；
- manifest 截至日必須與交易日曆最後一日一致且覆蓋固定研究終點；
- 換股 successor 必須存在於永久主檔；
- `still_member` 不得夾帶退出欄位，永久退出日須與 membership 終止日一致；
- 退市回報缺失、退出條款缺失及最後交易日後幽靈行情維持硬拒收。

## 事前固定攻擊結果

每次只注入一種錯誤，並重新計算 CSV 列數與 SHA-256，避免由雜湊失敗掩蓋語義測試。

| # | 攻擊 | 指定失敗閘門 | 結果 |
|---|---|---|---:|
| 01 | 授權聲明缺必要欄位 | 02_manifest_and_file_set | 拒收 |
| 02 | 授權聲明含未授權欄位 | 02_manifest_and_file_set | 拒收 |
| 03 | 授權時間沒有 UTC offset | 01_authorized_provider、02_manifest_and_file_set | 拒收 |
| 04 | 匯出時間晚於首次匯入 | 02_manifest_and_file_set | 拒收 |
| 05 | 數據截至日早於固定終點 | 09_fixed_20_year_calendar | 拒收 |
| 06 | 歷史代號在生效後才可知 | 06_identifier_history | 拒收 |
| 07 | 指數成分在生效後才公布 | 07_membership_availability | 拒收 |
| 08 | 退市回報及代價全部缺失 | 16_permanent_exit_economics | 拒收 |
| 09 | 換股 successor 不在永久主檔 | 14_corporate_actions、16_permanent_exit_economics | 拒收 |
| 10 | 仍在籍結果混入退出欄位 | 16_permanent_exit_economics | 拒收 |
| 11 | 退出日與成分終止日不一致 | 16_permanent_exit_economics | 拒收 |
| 12 | 最後交易日後仍有行情 | 17_no_post_exit_prices | 拒收 |

十二個攻擊全部拒收才算本輪 harness 通過；這套結果不能計入策略回報、PSR、DSR、PBO
或 Paper 樣本。

## 為何 CRSP 仍未通過

[CRSP US Stock Databases](https://indexes.morningstar.com/research-data-products/crsp-us-stock-databases)
官方說明涵蓋超過 36,000 隻 active 及 inactive 證券；Flat File Format 2.0 guide 列出
PERMNO／PERMCO、歷史 security information、日線 OHLCV、公司行動、membership 及
DelRet／DelRetMissType。這些欄位令 CRSP 成為最合理的首個樣本對象。

但 CRSP 官方[退市回報方法](https://www.crsp.org/crsp_pdf/crsp-us-stock-indexes-databases-calculations-index-methodologies-guide-flat-file-format-2-0/)
亦明示：退出後數據不足時會回報 missing value。現時沒有真實樣本，不能知道固定
2006–2026 主期的缺失比例、能否用完整現金／換股付款對數，也沒有逐次 S&P 500
announcement timestamp 證據。因此品牌與文件只能支持查詢，不能把 1/20 改成 20/20。

WRDS 目錄中的 CRSP10 是 10 年月線，並非固定 20 年日線；即使將來合法取得，也只能
用作 schema／退市事件小樣本，不能替代正式包。

## 已凍結的最小樣本要求

供應商須先書面回答：

1. S&P 500 membership 的 start/end 是生效日還是數據庫可用日
2. 能否逐次提供 announcement timestamp；不能時須明示不可重建
3. 2006-08-01 至 2026-07-31 的 DelRetMissType 數量、比例及原因分布
4. 缺失 DelRet 能否由 DelAmt、DelDivAmt、successor PERMNO/PERMCO 或完整付款重建
5. 本地研究、衍生匯總、SHA-256 收據及禁止原始列再分發的授權邊界

樣本固定包含：代號或交易所變更、同公司多股份類別、S&P 500 加入及移除、有效退市回報、缺失退市回報、現金收購、換股收購、停牌、拆股及現金派息、歷史分類變更。樣本只驗證轉換與缺值政策；正式包仍須完整覆蓋
2006-08-01 至 2026-07-31、每日 495–510 隻成分、在籍價格覆蓋至少 99.5%，並通過
20/20。

## 下一步及升格邊界

下一個有效動作是把上述最小要求交給 CRSP／WRDS，取得合法 schema、細樣本及授權條款。
只有樣本通過同一驗收、正式 20 年包再通過 20/20，才可按既有 v1 規則運行一次回測。
其後仍須對照 QQQ、SPY、逐期成分等權及同股漂移，扣 10／25／50 bps，通過前後十年、
滾動窗口、危機段、NW／PSR／全專案 DSR／PBO；全部通過才可由全現金開始、不回填的
前瞻 Paper。這不構成投資建議、供應商背書或盈利保證。
