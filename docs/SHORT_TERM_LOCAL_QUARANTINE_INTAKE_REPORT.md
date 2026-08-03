# 美股短線高回報研究｜第十七輪本地隔離匯入報告

研究日期：2026-08-04　｜　狀態：provider-mode bridge 已備；真實輸入尚未提供

## 一頁結論

第十五輪 execution extension 的輸出 status 固定為
`synthetic_execution_extension_built`，不能誠實標示未來的授權供應商包。本輪沒有改寫
第十五輪 bridge 或其 16/16 收據，而是另立 provider-mode bridge：

- 合成控制：`synthetic_local_quarantine_extension_built`；
- 正式授權模式：`authorized_provider_local_quarantine_extension_built`。

新的本地隔離匯入合成控制通過 **16/16**，事前固定的路徑、
symlink、文件 hash、模式、身份、授權、時間、CIZ 收據、前視成分、QQQ 缺日、status
冒充及檔案權限攻擊 **16/16 全數拒收**。

這不是真實數據通過。現時沒有四個明確外部路徑，provider-mode 運行 0 次；真實匯入只過
事前凍結 **1/16**，文件仍是
**1/12**，逐股數據仍是
**1/20**。正式 20 年逐股回測 0 次，短線 Paper
維持全現金、0 成交、0 持倉，實金動作 US$0。

## 為何不能直接沿用第十五輪

第十五輪的任務是證明合成 CIZ bridge 能否封閉派息 pay-date、252 日歷史、移除後成交及
QQQ／SPY 同步四項缺口，因此 synthetic status 是正確的測試標示。真實 provider package
若沿用同一 status，網站及下游程式便無法分辨「合成控制」與「授權市場列」。

本輪以新 manifest status 分開兩者，同時鎖定第十五輪 bridge 的 SHA-256；舊檔案、舊
manifest、舊報告及舊攻擊結果完全不改。

## 正式 CLI 邊界

只有使用者明確提供 repository 外四個絕對路徑時，才可運行：

```bash
python scripts/validate_short_term_local_quarantine_intake.py \
  --response /private/input/provider-response-envelope.json \
  --ciz-bundle /private/input/crsp-ciz-bundle \
  --execution-overlay /private/input/qqq-spy-overlay \
  --output /private/output/validated-local-package
```

CLI 不接受 synthetic mode，不掃描磁碟，不登入或下載，不覆寫目的地。輸出在同一父目錄
完成 staging 後才原子 rename；目錄權限為 0700、檔案為 0600。公開收據只含匯總，真正
response、合約、報價、原始列及衍生 package 不得加入 Git、網站或 Action artifact。

## 十六道合成匯入控制

| # | 閘門 | 結果 | 證據 |
|---|---|---|---|
| 01 | 事前凍結完整性 | 通過 | Round 17 協議及十六份前置雜湊完整 |
| 02 | 模式明確 | 通過 | source_mode=synthetic_control；status 一致 |
| 03 | 絕對外部路徑 | 通過 | 輸入及輸出均在 repository 外 |
| 04 | 無連結或特殊檔 | 通過 | 輸入樹只含正常檔案及目錄 |
| 05 | 新輸出及原子寫入 | 通過 | 新 staging 完成後才 rename |
| 06 | 文件 envelope 對數 | 通過 | Round 16 request、schema 及 response hash 通過 |
| 07 | 正式／合成隔離 | 通過 | provider 與 synthetic status 不可互換 |
| 08 | 供應商及產品綁定 | 通過 | response、CIZ 及 overlay 身份一致 |
| 09 | 授權邊界綁定 | 通過 | 三層本地研究授權及 reference 完整 |
| 10 | 時間次序 | 通過 | 文件／授權 ≤ export ≤ first import |
| 11 | CIZ 精確輸入 | 通過 | 十份輸入、欄位、列數及 SHA-256 對數 |
| 12 | Base ledger 20/20 | 通過 | 原 point-in-time auditor 全數通過 |
| 13 | Provider-mode 語義 | 通過 | 新 manifest 沒有沿用 synthetic 冒充 |
| 14 | 公平 execution overlay | 通過 | QQQ／SPY 同步 raw 行情及來源 ID |
| 15 | Execution extension 16/16 | 通過 | 派息、歷史、移除、D+1 及成本通過 |
| 16 | 隔離及決策邊界 | 通過 | owner-only；不運行策略、Paper 或實金 |

合成 fixture 只有 1 個完整月末訊號、
2 個候選資格、
1 個移除窗口及 46 列
QQQ／SPY 行情。這些數字只驗證工程，不會加入策略回報或 Paper 樣本。

## 十六項固定攻擊

| # | 單一錯誤 | 指定拒收代碼 | 結果 |
|---|---|---|---|
| 01 | response 使用相對路徑 | `intake_path_not_absolute` | 拒收 |
| 02 | 輸入位於 repository 內 | `intake_path_inside_repository` | 拒收 |
| 03 | CIZ 樹加入 symlink | `intake_symlink_or_special_file` | 拒收 |
| 04 | 輸出目錄已存在 | `intake_output_exists` | 拒收 |
| 05 | response hash 不符 | `response_receipt_mismatch` | 拒收 |
| 06 | provider mode 使用 synthetic response | `intake_source_mode_mismatch` | 拒收 |
| 07 | response 與 CIZ provider 不同 | `intake_provider_binding_mismatch` | 拒收 |
| 08 | response 與 CIZ product 不同 | `intake_product_binding_mismatch` | 拒收 |
| 09 | overlay provider 不同 | `intake_overlay_binding_mismatch` | 拒收 |
| 10 | overlay 本地研究授權 false | `intake_license_binding_invalid` | 拒收 |
| 11 | 文件時間遲於 export | `intake_timestamp_order_invalid` | 拒收 |
| 12 | CIZ CSV 改動但收據不改 | `source_receipt_invalid` | 拒收 |
| 13 | 成分公布時間晚於生效 | `membership_effective_date_substitution` | 拒收 |
| 14 | QQQ 缺一個必要 session | `benchmark_session_missing` | 拒收 |
| 15 | 輸出改成舊 synthetic status | `intake_source_mode_mismatch` | 拒收 |
| 16 | 輸出檔案變成 world-readable | `intake_private_permissions_invalid` | 拒收 |

第 12–14 項在任何實作前核對既有 bridge 後，以勘誤固定為程式實際錯誤代碼；攻擊內容、
門檻及停止規則沒有改變。每項攻擊只保留一個語義錯誤，不以 generic hash 失敗遮蓋。

## 通過後仍不可自動交易

真實 provider-mode 16/16 只會產生
`formal_stock_backtest_input_ready=true`，允許另一步運行一次凍結 v1 正式回測。它不會：

1. 自動運行或調整 12–1／6–1／3–1／1 個月訊號；
2. 改動 Top-10、30% 行業上限、US$5、US$20m 或 10／25／50 bps；
3. 刪除退市、收購、停牌或失敗公司；
4. 改用較弱 QQQ／SPY／等權／漂移 baseline；
5. 建立或回填 Paper；
6. 作任何實金動作。

正式策略仍須通過固定 20 年、前後十年、滾動窗、危機段、NW、PSR、全專案 DSR、PBO、
成本及最大跌幅。全部通過後，短線 Paper 仍須由全現金開始累積 252 個新增交易日及
12 次完成重新平衡，不能回填漂亮歷史。

## 決策

下一個有效行動仍是由使用者明確提供四個 repository 外路徑。沒有這些輸入時，不掃描、
不猜測、不運行 provider mode。合成 16/16 不構成供應商背書、投資建議或盈利保證。
