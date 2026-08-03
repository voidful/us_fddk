# 短線個股第十七輪：授權數據本地隔離匯入協議 v1.0

凍結時間：2026-08-03T23:27:33Z

狀態：`frozen_before_provider_mode_bridge_or_intake_implementation`

## 研究問題

第十六輪已把 CRSP／WRDS 文件回覆固定成機器可驗證格式，但仍未聯絡供應商、沒有
文件回覆或市場列。真實文件交接為 1/12、point-in-time／退市數據為 1/20、正式
20 年逐股回測為 0、短線 Paper 全現金、實金動作 US$0。

稽核現有程式時發現，第十五輪 execution extension 把輸出狀態固定為
`synthetic_execution_extension_built`，auditor 亦只接受這個狀態。這能驗證合成 bridge，
但不能把未來授權供應商數據誠實標成 provider mode。不得修改第十五輪檔案或收據，
否則會破壞既有 16/16 可重現證據。

本輪建立一條新的 provider-mode bridge 及本地隔離匯入編排。它只可在使用者明確提供
三個本地輸入及一個新輸出位置時運行；不得登入供應商、下載、購買、發送文件、掃描磁碟、
把原始列加入 Git、運行策略、建立 Paper 或作實金動作。

## 固定輸入與模式

正式模式只接受四個明確的絕對路徑：

1. 第十六輪回覆 envelope JSON；
2. 十份 CIZ／證據輸入及 `ciz_manifest.json`；
3. QQQ／SPY execution overlay 及 `execution_overlay_manifest.json`；
4. 一個尚不存在、位於專案外的輸出目錄。

任何輸入或輸出位於 repository 內、使用相對路徑、包含 symlink／socket／device／FIFO、
輸出已存在，均須在讀取市場列或寫出前停止。正式模式不接受
`synthetic_document_response_control`；合成模式只供固定測試 harness 使用，輸出及收據
必須明示 synthetic，不可冒充 provider。

## 固定 provider-mode 輸出

新 bridge 沿用第十三輪 adapter 的八份 ledger 及第十五輪四份 execution CSV，但另立
manifest status：

- 合成控制：`synthetic_local_quarantine_extension_built`；
- 真實授權模式：`authorized_provider_local_quarantine_extension_built`。

輸出根目錄只可有 `ledger/`、`execution/` 及 `intake_receipt.json`。收據只含版本、模式、
相對檔名、供應商／產品字串、上游 response hash、各 manifest hash、列數、閘門匯總及
政策狀態；不得含絕對路徑、憑證、合約、報價或市場原始列。輸出目錄設為 owner-only，
檔案設為 owner read/write。寫出必須在同一父目錄的臨時 staging 完成，再以 rename 原子化。

## 固定十六道匯入閘門

| # | 閘門 | 通過條件 |
|---|---|---|
| 01 | 事前凍結完整性 | 本協議、收據及十六份前置檔案雜湊完整 |
| 02 | 模式明確 | 只接受 `provider` 或內部 `synthetic_control`；輸出 status 必須一致 |
| 03 | 絕對外部路徑 | 四條路徑均為絕對路徑且 realpath 位於 repository 外 |
| 04 | 無連結或特殊檔 | 三個輸入樹沒有 symlink、socket、device 或 FIFO |
| 05 | 新輸出及原子寫入 | 目的地不存在；同父目錄 staging 後 rename，不覆寫 |
| 06 | 文件 envelope 對數 | 第十六輪 request ID、schema、協議及 response SHA-256 通過 |
| 07 | 正式／合成隔離 | provider mode 必須是真實文件狀態；synthetic 只可在 harness |
| 08 | 供應商及產品綁定 | response、CIZ manifest、overlay manifest 的 provider／product 完全一致 |
| 09 | 授權邊界綁定 | 三層本地研究授權為 true，再分發 boolean 及 reference 非空白 |
| 10 | 時間次序 | 文件／授權不遲於 export；export 不遲於 first import；全部帶 UTC offset |
| 11 | CIZ 精確輸入 | 十份檔案、欄位、列數及 SHA-256 對數，CIZ FF2 及固定政策不變 |
| 12 | Base ledger 20/20 | 正式模式用固定 2006-08-01–2026-07-31 要求；所有閘門通過 |
| 13 | Provider-mode 語義 | 新 manifest 明示來源模式，不接受第十五輪 synthetic status 冒充 |
| 14 | 公平 execution overlay | QQQ／SPY 同日 raw OHLCV、總回報、來源 ID、時鐘及成本完整 |
| 15 | Execution extension 16/16 | 派息、歷史、移除、基準、D+1 及成本全部通過 |
| 16 | 隔離及決策邊界 | owner-only 權限；不公開原始列、不運行策略／Paper、實金 US$0 |

合成 16/16 只證明新匯入器能分辨模式並關門。真實 provider 16/16 才表示「輸入可供一次
固定正式回測」，仍不代表策略、統計、Paper 或盈利通過。

## 固定十六項單一錯誤攻擊

| # | 單一攻擊 | 必須結果 |
|---|---|---|
| 01 | response 使用相對路徑 | 拒收 `intake_path_not_absolute` |
| 02 | 任一輸入 realpath 位於 repository 內 | 拒收 `intake_path_inside_repository` |
| 03 | CIZ 樹加入 symlink | 拒收 `intake_symlink_or_special_file` |
| 04 | 輸出目錄已存在 | 拒收 `intake_output_exists` |
| 05 | response hash 不符 | 拒收 `response_receipt_mismatch` |
| 06 | provider mode 使用 synthetic response | 拒收 `intake_source_mode_mismatch` |
| 07 | response 與 CIZ provider 不同 | 拒收 `intake_provider_binding_mismatch` |
| 08 | response 與 CIZ product 不同 | 拒收 `intake_product_binding_mismatch` |
| 09 | overlay provider／product 不同 | 拒收 `intake_overlay_binding_mismatch` |
| 10 | 任一層本地研究授權不是 true | 拒收 `intake_license_binding_invalid` |
| 11 | 文件時間遲於 export | 拒收 `intake_timestamp_order_invalid` |
| 12 | CIZ CSV 改動但收據不改 | 拒收既有 `source_receipt_mismatch` |
| 13 | 成分公布時間晚於生效 | 拒收既有 point-in-time 成分時間閘門 |
| 14 | QQQ 缺一個必要 session | 拒收 `benchmark_calendar_mismatch` |
| 15 | provider package 改成舊 synthetic status | 拒收 `intake_source_mode_mismatch` |
| 16 | 輸出檔案變成 group／world-readable | 拒收 `intake_private_permissions_invalid` |

每項攻擊須重算它應重算的上游收據，只保留指定語義錯誤；不得用 generic hash 失敗掩蓋
時間、模式或授權問題。fixture 只能是合成資料，不能仿造供應商品牌或真實市場列。

## 固定策略與決策界線

- 12–1／6–1／3–1／1 個月訊號權重 45/25/20/10、Top-10、30% 行業上限、US$5、
  US$20m、月末收市訊號／下一開市成交全部不變；
- baseline 維持 QQQ、SPY、逐期成分等權、同股漂移及相同執行時鐘；
- 成本維持單邊 10 bps 及 25／50 bps 壓力；
- 正式回測仍須固定 20 年、前後十年、滾動窗口、危機段、NW、PSR、全專案 DSR、
  PBO、成本及最大跌幅；
- 匯入 16/16 只允許另一步、一次性的正式回測。正式策略門檻通過後，仍須由全現金開始
  252 個新增交易日及 12 次完成重新平衡的不可回填 Paper；
- 本輪策略運行次數 0、Paper 新成交 0、實金動作 US$0。

## 固定公開輸出

1. 本協議及 freeze receipt；
2. provider-mode bridge 與本地 CLI；
3. 只含合成控制／攻擊及真實未就緒狀態的機器收據；
4. 香港金融用詞研究報告及網站摘要；
5. 測試及 GitHub Actions 重建步驟。

真正 response、憑證、合約、報價、CIZ／overlay、衍生 ledger／execution package 及本地
匯入收據一律不得加入 Git、網站、Action artifact 或公開測試 fixture。

## 停止規則

- 沒有使用者明確提供四個路徑：不掃描、不猜測、不匯入；
- 文件、路徑、授權、身份或時間任一失敗：不讀取或不繼續轉換市場列；
- 20/20 或 16/16 任一失敗：保留本地失敗收據，不運行策略；
- provider-mode bridge 不得改寫第十五輪檔案、manifest 或歷史結論；
- 不論合成 harness 多完整，真實數據未通過前仍是正式回測 0、短線 Paper 全現金、
  實金動作 US$0；
- 本輪不構成採購承諾、供應商背書、投資建議或盈利保證。
