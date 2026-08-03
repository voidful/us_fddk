# US FDDK — 美股資料與策略研究台

這不是一個報明牌程式，而是一套可重現的美股研究流程：同一份凍結行情同時產生訊號、模擬下一交易日成交、扣除成本、比較基準，並把不顯著或失敗的結果照實留下。

## 公開網站與每日更新

- GitHub Pages 顯示凍結的 20 年研究與 v25 LIVE Paper，清楚分開研究快照日與前瞻資料日。
- GitHub Actions 每天 04:30 UTC（台北 12:30）檢查最近完成的 XNYS session；週末與休市日不建立假版本。
- 日更只推進事前鎖定的 v25、SPY 與 80% VUG／20% SHY 三個同起點 Paper 帳戶，不用新資料重選歷史冠軍。
- 同日行情改寫、三帳戶不同步、前瞻收據鏈或網站契約不一致時會 fail closed，不推送也不部署。
- 公開頁與所有 Paper 結果只供研究教育；在 252 個新增交易日與完整升級合約通過前，實金訊號維持關閉。

專案參考了：

對外網站及研究報告的繁體中文遵守[香港金融用語準則](docs/HK_FINANCE_TERMINOLOGY.md)；策略代號、統計公式及機器數據欄位維持不變。

- [appr1ciat1/tst_wocker](https://github.com/appr1ciat1/tst_wocker) 的資料／策略／成交分層與 regime 思路。
- [appr1ciat1/tw-block-warrant](https://github.com/appr1ciat1/tw-block-warrant) 的「原始訊號不被研究層覆寫」、年度資料與證據分級。
- [appr1ciat1/tst_wocker_filter_lab](https://github.com/appr1ciat1/tst_wocker_filter_lab) 後期稽核得到的負面教訓：資料修訂、同日時序穿越、零成本、今天的成分股回填歷史、只看單點績效，以及少數持股造成的路徑雜訊。

## 現在有什麼

- 每日調整後 OHLCV、SPY、VIX、10 類跨資產 ETF 與 30 檔大型股觀察池。
- 資料契約：新鮮度、必要標的、覆蓋率、正價格、OHLC 關係、成交量與異常跳變。
- 可驗證 ZIP 快照：每個 CSV 都有 SHA-256；載入時拒絕未知檔案或遭竄改內容。
- 八個 ETF 主對照：SPY、QQQ、被動 90% QQQ／10% SHY、ETF 等權、分散式雙動量、成長守門員 v3／v2 與封存的 v1；另保留低回撤平衡趨勢衛星的負結果。
- 大型股當期排名，以及「廣泛持有後動量傾斜」的偏誤診斷。
- 下一交易日開盤成交、權重自然漂移、雙邊換手成本。
- 預設完整 20 年研究窗；Newey–West、區塊 bootstrap、前後十年、壓力期、滾動三年、成本／參數鄰域、CSCV-PBO、PSR、6,000 次搜尋懲罰 DSR，以及 2012 年起的展開式兩年 walk-forward。
- v3 另有下載前凍結的五市場機制驗證：美、英、德、日、港各自本地交易日，固定規則、10／50 bps 成本、五年滾動與等權 Newey–West；失敗市場與雜湊收據不刪除。
- v4 另有下載前凍結的股權風格輪動驗證：20 年可交易 ETF、固定前後十年、五年滾動、50 bps、SPY／QQQ／風格等權與舊代理資料門檻；14 道只過 2 道，因此不建立 Paper。
- v5 把固定持有、波動管理、趨勢確認各保留 1/3 袖套；近期 20 年幾乎追平 QQQ 且回撤較淺，但 1986–2006 滾動與五市場泛化失敗，22 道只過 10 道，不建立 Paper。
- v6 在下載新資料前固定 50% SPY 核心與三個產業動能槽位，另建每月完全相同總權益曝險的 matched control；1927–2005 代理期支持機制，但 2006–2026 ETF 主期落後 SPY 與 matched，22 道只過 11 道，不建立 Paper。
- v7 在第一次計算前固定 50% SPY 核心與相對成長開關；2006–2026 回撤較 SPY 淺但 CAGR 落後，1989–2006 舊代理也無法通過前後半期與統計門檻，19 道只過 6 道，不建立 Paper。
- v8 永遠維持 100% 股票曝險，只在相對強勢成立時用一半 QQQ 取代 SPY；近期與舊期全期都勝市場，但 50 bps 成本與舊期尾部風險失敗，Paper 入口 14/16，不建立帳戶。
- v9 把成長槽位降為 40%，而且只在相對強勢狀態改變時交易；另在下載前鎖定 1973–1988 Nasdaq Composite／S&P 500 外部期。三段全期 CAGR 都勝市場，但主期 50 bps、舊期回撤與外部期後半失敗，Paper 入口 20/23，不建立帳戶。
- v10/v11 的兩個 DJIA 來源都在策略計算前失敗並留下不可回改收據；v12 保留同一套 60% 核心＋40% growth/core/defense 三態，只用三段既有凍結資料首次計算。主期回撤改善約 14pp，但 CAGR 落後 SPY、50 bps 與後十年失敗，Paper 入口 16/23，不建立帳戶。
- v13 先在既有三年代探索出「兩月確認＋部分防守」，再於規則凍結後下載 IWF/IWB、IWO/IWM、EFG/EFA 三組新 ETF。Russell 1000 與 Russell 2000 都無法穩定跑贏核心 ETF，EAFE 在固定起點前暖機不足；新資料經濟門檻只過 9/30，不建立 Paper。
- v14 不再用理論倍數合成績效：先凍結 60% 實際 2 倍每日目標 ETF／40% SHY、兩月確認與 36 道門檻，再下載 SSO/QLD/DDM。三組資料都完整，但 S&P 500 與 Dow 30 明顯落後原始 ETF；Nasdaq-100 雖略勝 QQQ，仍輸給同產品固定 60/40。經濟門檻 13/36、統計 0/18，不建立 Paper。
- v15 保留原始核心，只在兩月趨勢確認時用 10% 實際 3 倍每日目標 ETF 把名目股票曝險提高到約 120%。協議凍結後才首次查看 UPRO/TQQQ/UDOW 的 15 年產品史；三市場 CAGR 都高於原始 ETF，但三組回撤都更深、Sharpe 都未嚴格勝出，經濟門檻 17/36、統計 4/18，不建立 Paper。v14 的 20 年設計期與 v15 的 15 年確認期不合併冒充「獨立 20 年」。
- v16 把中小型股的實際 2 倍 ETF 曝險限制在約 100%–150%，低於 200 日均線時全退 SHY；規則凍結後才下載 MVV/UWM/SAA 的 18 年樣本。三組只通過 6/48 經濟門檻、0/27 統計門檻：回撤縮小，但週度調整與踏空讓 CAGR 僅 2.8%–5.6%，不建立 Paper。
- v17 每月固定 60% 實際 2 倍股票 ETF／40% IEF，約為 120% 股票＋40% 7–10 年公債曝險。大型股三組使用完整 20 年，中小型股三組保留實際可得的 18 年；六組多數提高 CAGR，卻把最大回撤推到約 −58% 至 −63%，經濟門檻 48/84、統計 9/54，不建立 Paper。
- v18 把股票名目曝險降回約 100%，固定持有 50% 實際 2 倍股票 ETF／25% IEF／25% GLD。六個已見美國市場只用來選規則；協議凍結後才下載 EFO/EET 日線做 16 年海外驗證。已開發與新興市場都加深回撤，前半期與五年滾動也失敗，外部經濟門檻 5/18、統計 0/12，不建立 Paper。
- v19 原定把同一股票袖套搭配每月 12–1 相對強弱的 IEF／GLD／SHY，但在下載日線前先做產品映射稽核；VGK 與 UPV 在 2015-10-01–2016-08-31 的指數範圍不一致，因此整輪在策略計算前停止，不以換代號或移動日期補救。
- v20 只修正外部產品組合，保留 v19 原規則；美國 20／18 年設計資料與日本、中國大型股、巴西 10 年外部資料共 11 組全部完成。資料門檻 13/13，但動態輪替的 CAGR 在 11/11 組都低於固定 50% 實際 2 倍股票 ETF／25% IEF／25% GLD；經濟門檻 45/154、外部統計 0/27，不建立 Paper。
- v21 永久保留 60% 普通 ETF，兩月趨勢確認後才用實際 2／3 倍 ETF 把名目股票曝險提高到約 120%。大型股保留 20 年設計診斷，但凍結後的 MidCap 400／Russell 2000 兩組 15 年外部路徑同時落後普通 ETF且回撤更深；完整經濟 53/128、外部統計 0/18，不建立 Paper。
- v22 不修改 v18 的固定 50% 實際每日 2 倍美國股票 ETF／25% IEF／25% GLD，只把海外失敗後的新假說縮窄到美國。九組首次下載的產業日線在定義一致的 2007–2019 區間全部取得較高完整期 CAGR，個別門檻 51/63；但九個產業的五年滾動勝率全未達 60%，等權也只有 51.2%，經濟入口 13/15、統計 0/3，因此不建立 Paper、不顯示 50/25/25 配置。
- 短線高回報第一輪把凍結的 12–1／6–1 月綜合動量規則跑成 20 年現時股池沙盒，並直譯三個台股 20 日動量版本。沙盒 CAGR 21.52% 雖勝 QQQ 16.70%，卻輸同股池漂移 23.04%；NW t 1.83、全專案 DSR 2.51%、PBO 69.05%，且逐期成分及退市回報未齊，因此不建立短線 Paper。
- 短線第二輪在首次計算前另凍結[訊號層協議](docs/SHORT_TERM_SIGNAL_DIAGNOSTIC_PROTOCOL.md)：20 日 Top-7 固定持有事件相對同日合資格池平均 +0.32 個百分點、NW t 3.03，前後十年均為正；但仍屬現時股池倒推，故只保留為 CRSP／WRDS 或 Norgate 重測線索，不產生選股名單或 Paper。
- 短線第三輪先凍結[Vanguard 行業 ETF 外部協議](docs/SHORT_TERM_SECTOR_ETF_PROTOCOL.md)，才首次下載十行業共同面板。月度 Top-3 CAGR 5.28%，遠低於 QQQ 16.73%；固定 20 日事件配對差 -0.05 個百分點、NW t -0.77，訊號 0/5、總門檻 7/21、PBO 79.37%。完整[負結果報告](docs/SHORT_TERM_SECTOR_ETF_RESEARCH_REPORT.md)保留，沒有改參數救援或建立 Paper。
- 持久化 paper trade：LIVE 前瞻模式保存現金、總報酬單位、待成交委託、成交、成本與逐日權益；REPLAY 只作歷史流程驗證並明確標示。
- 調整價修訂防護：除息、拆股或供應商修訂讓舊調整價改變時，等比例重基準總報酬單位並保持當時市值，不製造假損益；每次重基準都留下舊／新價格、倍數、前後市值與快照雜湊收據。
- 曝險控制：另以每月末再平衡的被動 90% QQQ／10% SHY 檢查波動管理是否真的創造價值，避免把較高 QQQ 曝險誤認成勝過 SPY 的 alpha。
- 同起點 LIVE 基準：成長守門員 v2、SPY、QQQ 與被動 90/10 都從同一天現金起跑、用相同成本與下一開盤成交；不拿歷史 ETF 報酬冒充前瞻比較。
- 固定的 LIVE 門檻：至少 252 個前瞻交易日、6 次完成換倉、扣成本後為正、總報酬同時勝 SPY 與被動 90/10，且最大回撤不比兩者深，七項全過才顯示 LIVE 通過。
- 交易日感知的訊號鮮度：依 XNYS 下一個 session 的正式收盤時間加 6 小時緩衝；逾期網站自動隱藏配置與金額試算。
- 台灣／紐約時區安全：最新資料日以「當下已完成的 XNYS 收盤」判斷，不會在台灣隔日上午誤等尚未發生的美國當日行情。
- `reference-check` 同時核對網站、快照、v2 主帳戶、三個 LIVE 基準與 v3 隔離帳戶的日期、雜湊、模式、待成交狀態、標記市值、調整價重基準筆數及權重；任一漂移就拒絕部署。
- 實金 readiness 與資料完整性分離：`integrity_ok=true` 只表示可安全發布 Paper 狀態；`trade_ready=true` 必須另外通過歷史、公平曝險、統計與七項前瞻門檻，共 11 道全過。尚未累積 252 日與 6 次換倉前，前瞻報酬／回撤門檻一律鎖定為未通過。
- 前瞻證據雜湊鏈：每個新日期、快照或明示的 readiness 合約版本寫入 `live_evidence_ledger.jsonl`；相同日期與快照的績效資料若改變，會拒絕靜默回填，完全相同的重跑則不重複新增。
- 研究、候選 paper、雙動量 paper 靜態 HTML 儀表板，以及機器可讀 `signals.json`、`validation.json` 與各自獨立的 paper state。

## 快速使用

Python 3.11 以上：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

# 抓最新資料、凍結快照、跑最近完整 20 年、產生研究報表與 LIVE paper 帳戶
python -m usfddk build

# 正式更新入口：完整重建、LIVE 基準核對、網站渲染、套件稽核與跨檔一致性檢查
scripts/refresh_live_reference.sh

# 完全使用已凍結資料重算，不接觸網路
python -m usfddk build \
  --snapshot artifacts/snapshot_20260731_6a7ca6b8.zip \
  --output artifacts

# 重跑下載前已凍結的 v3 五市場驗證與獨立 HTML 研究報表
python -m usfddk cross-market

# 重跑下載前已凍結的 v4 股權風格輪動與舊代理資料門檻
python -m usfddk v4-style

# 重跑第一次集成計算前已凍結的 v5 三時鐘完整驗證
python -m usfddk v5-three-clock

# 重跑新資料下載前已凍結的 v6 產業動能與 French 長期代理驗證
python -m usfddk v6-industry

# 重跑第一次計算前已凍結的 v7 相對成長衛星與舊指數代理驗證
python -m usfddk v7-relative-growth

# 重跑第一次計算前已凍結的 v8 永遠持股相對成長驗證
python -m usfddk v8-always-invested

# v9 外部資料只需首次依下載前契約取得；快照已凍結時直接重跑三年代驗證
python -m usfddk v9-low-turnover

# v9 Paper 有研究守門：目前 20/23，這個命令會拒絕建帳戶
python -m usfddk paper update \
  --snapshot artifacts/snapshot_20260731_6a7ca6b8.zip \
  --strategy v9

# 重跑 v12 三樣本階層式規則；v10/v11 失敗收據也會一併驗證
python -m usfddk v12-hierarchical

# 重跑規則先凍結、再下載三組新 ETF 的 v13 驗證；目前 9/30，不建立 Paper
python -m usfddk v13-confirmed-growth

# v13 Paper 同樣有機器守門；新 ETF 驗證失敗時會拒絕建立帳戶
python -m usfddk paper update \
  --snapshot artifacts/snapshot_20260731_6a7ca6b8.zip \
  --strategy v13

# 重跑先凍結、再下載三組實際槓桿 ETF 的 v14 驗證
python -m usfddk v14-modest-leverage

# v14 經濟門檻只有 13/36；Paper 指令會先讀收據並拒絕建帳戶
python -m usfddk paper update \
  --snapshot artifacts/snapshot_v14_leveraged_20040102_20260731_d7dc527a.zip \
  --strategy v14

# 重跑 v15 規則凍結後首次查看三組 3 倍 ETF 的 15 年確認
python -m usfddk v15-modest-leverage-overlay

# v15 雖然三市場 CAGR 都較高，風險門檻只讓總經濟檢查通過 17/36；拒絕建帳戶
python -m usfddk paper update \
  --snapshot artifacts/snapshot_v15_3x_20080102_20260731_57527472_validated.zip \
  --strategy v15

# 重跑 v16 的 18 年中小型股週度趨勢／波動煞車；結果 6/48，不建立 Paper
python -m usfddk v16-trend-volatility-brake

# v16 Paper 入口會讀完整收據並拒絕失敗候選
python -m usfddk paper update \
  --snapshot artifacts/snapshot_v16_trend_vol_20050103_20260731_777302d4.zip \
  --strategy v16

# 重跑 v17 六市場資本效率組合；大型股 20 年、中小型股 18 年
python -m usfddk v17-capital-efficient

# v17 只有 48/84 經濟門檻；Paper 守門拒絕建帳戶
python -m usfddk paper update \
  --snapshot artifacts/snapshot_v17_capital_efficient_20040102_20260731_4c948bf6.zip \
  --strategy v17

# 重跑 v18 凍結後的 EFO/EET 16 年股債金外部驗證
python -m usfddk v18-equal-diversifier

# v18 外部經濟門檻只有 5/18；Paper 守門拒絕建帳戶
python -m usfddk paper update \
  --snapshot artifacts/snapshot_v18_equal_diversifier_20080602_20260731_dd920b90.zip \
  --strategy v18

# 重跑 v20：大型股保留 20 年，中小型股 18 年，三個新區域市場 10 年
python -m usfddk v20-diversifier-strength

# v20 只有 45/154 經濟門檻、0/27 外部統計門檻；Paper 守門拒絕建帳戶
python -m usfddk paper update \
  --snapshot artifacts/snapshot_v20_diversifier_strength_20060803_20260731_e30b4032.zip \
  --strategy v20

# 重跑 v21：大型股 2 倍實作保留 20 年，外部中小型股 3 倍實作為 15 年
python -m usfddk v21-hybrid-core

# v21 只有 53/128 經濟門檻、0/18 外部統計門檻；Paper 守門拒絕建帳戶
python -m usfddk paper update \
  --snapshot artifacts/snapshot_v17_capital_efficient_20040102_20260731_4c948bf6.zip \
  --strategy v21

# 重跑 v22：20 年美國廣泛市場只算設計；九組新產業日線使用 2007–2019 共同指數期
python -m usfddk v22-sector-capital-efficiency

# v22 個別 51/63，但五年一致性使經濟入口只有 13/15；守門拒絕建帳戶
python -m usfddk paper update \
  --snapshot artifacts/snapshot_20260731_6a7ca6b8.zip \
  --strategy v22

# 重跑 v23：20 年 SSO＋官方 KFA 指數代理，以及 KMLM／FMF 實際產品橋接
python -m usfddk v23-managed-futures-capital-efficiency

# v23 長期 6/10、KMLM 7/10、FMF 2/7；守門拒絕建立 50/50 Paper
python -m usfddk paper update \
  --snapshot artifacts/snapshot_v23_kmlm_20201201_20260731_a7826ecd.zip \
  --strategy v23

# 重跑 v24：20 年學術品質＋動能，以及 QUAL／MTUM、SPHQ／PDP 實際產品橋接
python -m usfddk v24-quality-momentum-factor

# v24 學術 10/10，但 iShares 5/10、Invesco 0/7；守門拒絕建立 50/50 Paper
python -m usfddk paper update \
  --snapshot artifacts/snapshot_v24_ishares_quality_momentum_20130701_20260731_11fc153f.zip \
  --strategy v24

# 重跑 v25：Vanguard／iShares／State Street 三條 20 年大型成長＋黃金產品路徑
python -m usfddk v25-growth-gold-diversification

# 重跑短線高回報第一輪：現時股池沙盒、QQQ／等權／漂移 baseline、台股規則直譯
# 結果只作偏誤診斷；程式固定不會建立 Paper state
python scripts/build_short_term_high_return.py

# 只用已凍結的首次 Vanguard 行業快照重建第三輪外部產品負結果
python scripts/build_short_term_sector_etf.py

# v25 三路徑 12/12、彙總 10/10、資料 8/8；同一快照同步推進候選、SPY
# 與 80% VUG／20% SHY 公平基準，只做隔離 Paper，實金仍關閉
python -m usfddk v25-paper-bundle \
  --snapshot artifacts/snapshot_v25_vanguard_20060701_20260731_6cf44e63.zip

# v12 Paper 守門目前 16/23，這個命令同樣會拒絕建帳戶
python -m usfddk paper update \
  --snapshot artifacts/snapshot_20260731_6a7ca6b8.zip \
  --strategy v12

# 單獨驗證快照與資料契約
python -m usfddk verify artifacts/snapshot_20260731_6a7ca6b8.zip

# 用下一份新快照推進同一個 LIVE 帳戶；只處理 state 日期之後的新 bars
python -m usfddk paper update \
  --snapshot artifacts/snapshot_YYYYMMDD_<hash8>.zip

# 同一份新快照也可單獨推進 v3 隔離帳戶
python -m usfddk paper update \
  --snapshot artifacts/snapshot_YYYYMMDD_<hash8>.zip \
  --strategy v3

# 查看帳戶；歷史回放要使用獨立 state，避免混成前瞻證據
python -m usfddk paper status
python -m usfddk reference-check

# 嚴格的實金部署閘門；資料雖一致但策略尚未通過時回傳狀態碼 4
python -m usfddk reference-check --require-trade-ready
python -m usfddk paper update \
  --snapshot artifacts/snapshot_20260731_6a7ca6b8.zip \
  --strategy candidate \
  --state artifacts/paper_replay_state.json \
  --report artifacts/paper_replay.html \
  --replay-from 2024-01-01

pytest
```

每日更新會另外原子寫入 `artifacts/live_refresh_status.json`。只有
`data_advanced=true` 才允許建立私人網站新版本；同一交易日重跑會明確標成冪等，
資料日期倒退或五個同起點帳戶任一不同步則直接失敗。

v25 也已納入同一條日更鏈。腳本會先以同一份 VUG／GLD／SPY／SHY 快照同步推進
候選、SPY 與 80% VUG／20% SHY 三帳戶，再重建網站並執行獨立交叉稽核。只有舊主
鏈與 v25 的 `private_deploy_allowed` 同時為 true 才能建立私人網站版本；同日行情
修訂、帳戶日期／快照／成本／交易日序列不一致或網站資料過期都會 fail closed。
相關收據為 `artifacts/v25_live_update_status.json`、
`artifacts/v25_reference_readiness.json`、`artifacts/v25_live_refresh_status.json`，
前瞻紀錄另寫入 `artifacts/v25_live_evidence_ledger.jsonl` 雜湊鏈。

主要輸出：

- `artifacts/report.html`：可直接用瀏覽器打開的研究台。
- `artifacts/paper_volatility.html`／`paper_volatility_state.json`：成長守門員 v2 的 LIVE 前瞻帳戶；網站主訊號只認這個 state。HTML 內含調整價重基準收據，JSON 的 `adjustment_rebases` 保存相同稽核事件。
- `artifacts/paper_v3.html`／`paper_v3_state.json`：趨勢確認 v3 的隔離研究帳戶。v3 雖在 2006–2026 通過 QQQ 與 96/4 曝險門檻，但較舊代理期的有效滾動勝率失敗，因此不會取代網站主訊號。
- `artifacts/paper_spy.html`／`paper_spy_state.json`、`paper_qqq.html`／`paper_qqq_state.json`：與 v2 同起點、同成本的 LIVE ETF 基準；日期、快照或模式不同步就拒絕發布。
- `artifacts/paper_passive90.html`／`paper_passive90_state.json`：被動 90% QQQ／10% SHY 的曝險控制 LIVE 基準；同樣只從 2026-07-31 後累積，不回填歷史成交。
- `artifacts/paper_growth.html`／`paper_growth_state.json`：v1 封存帳戶，不與 v2 前瞻證據合併。
- `artifacts/paper_candidate.html`／`paper_candidate_state.json`：低回撤研究候選的 LIVE 模擬帳戶與稽核紀錄；不代表標準 Sharpe 已達 1。
- `artifacts/paper.html`／`paper_state.json`：原雙動量的獨立 LIVE 模擬帳戶與稽核紀錄。
- `artifacts/signals.json`：最新 ETF 目標配置與個股觀察排名。
- `artifacts/validation.json`：成對檢驗、bootstrap、子期間與鄰域結果。
- `artifacts/reference_readiness.json`：明確分開 `integrity_ok`、`safe_to_publish_paper_status` 與 `trade_ready` 的上線判定；目前決定為 `paper_only`。
- `artifacts/live_evidence_ledger.jsonl`：只向後追加的前瞻證據鏈；包含前一筆與本筆 SHA-256、資料日、快照、前瞻日數、換倉數及 readiness 門檻。
- `artifacts/snapshot_YYYYMMDD_<hash8>.zip`：可重算的資料收據；同日上游若修訂歷史，會留下不同內容雜湊，不會靜默覆蓋。
- `artifacts/snapshot_ndx_proxy_19851001_20060728_4814654a.zip`：v3 的較舊 Nasdaq-100 價格指數代理期收據；不與 QQQ 總報酬串接。
- `artifacts/cross_market_validation.json`／`cross_market_report.html`：v3 五市場事前凍結驗證的機器收據與新手可讀研究報表；結果為未通過。
- `artifacts/cross_market_*_19870101_20060728_*.zip`：美、英、德、日、港五份互相獨立的價格指數快照，各自綁定下載前協議雜湊。
- `artifacts/v4_style_validation.json`／`v4_style_report.html`：v4 風格輪動的機器收據與新手可讀報表；20 年主樣本與舊代理資料門檻均未通過。
- `artifacts/snapshot_v4_style_trade_20030701_20260731_e879c128.zip`／`snapshot_v4_style_proxy_19930701_20060728_a94ed540.zip`：v4 兩份不可互相串接的凍結快照。
- `artifacts/v5_three_clock_validation.json`／`v5_three_clock_report.html`：v5 三時鐘集成的 22 道完整機器收據與新手報表；近期樣本通過多數，但舊年代與五市場失敗。
- `artifacts/v6_industry_validation.json`／`v6_industry_report.html`：v6 產業動能的 22 道完整機器收據與新手報表；結果 11/22，不建立 Paper。
- `artifacts/v6_data_receipt.json`、`snapshot_v6_sector_etf_*.zip` 與兩份 `french_*.zip`：規格、ETF 面板及官方 French 原始檔的 SHA-256 資料收據。
- `artifacts/v7_relative_growth_validation.json`／`v7_relative_growth_report.html`：v7 相對成長衛星的 19 道完整機器收據與新手報表；結果 6/19，不建立 Paper。
- `artifacts/v7_data_receipt.json`：v7 凍結協議、主 ETF 快照與兩份舊指數快照的 SHA-256 收據。
- `artifacts/v8_always_invested_validation.json`／`v8_always_invested_report.html`：v8 的 16 道 Paper 入口與 20 道完整歷史收據；結果分別 14/16、14/20，不建立 Paper。
- `artifacts/v8_data_receipt.json`：v8 凍結協議、主 ETF 快照與兩份舊指數快照的 SHA-256 收據。
- `artifacts/v9_low_turnover_validation.json`／`v9_low_turnover_report.html`：v9 三個不重疊年代的 23 道 Paper 入口與 29 道完整歷史收據；結果 20/23、20/29，不建立 Paper。
- `artifacts/v9_external_data_receipt.json`、`snapshot_v9_ixic_19710205_19881230_76bc29b6.zip` 與 `snapshot_v9_gspc_19710205_19881230_414d7879.zip`：在首次下載前先鎖定代號、期間與資料契約的全新外部樣本收據。
- `artifacts/v10_dji_data_receipt.json`／`v11_official_dji_data_receipt.json`：兩個都在任何策略計算前封存的 DJIA 取數失敗；前者為 Yahoo 無歷史資料，後者為 S&P 官方 URL 回覆 403。
- `artifacts/v12_hierarchical_validation.json`／`v12_hierarchical_report.html`：v12 三態規則的 23 道 Paper 入口與 29 道完整歷史收據；結果 16/23、16/29，不建立 Paper。
- `artifacts/v13_confirmed_growth_validation.json`／`v13_confirmed_growth_report.html`：v13 的三組新 ETF 機器收據與新手報表；經濟門檻 9/30、資料門檻 3/4、統計門檻 0/9，不建立 Paper。
- `artifacts/snapshot_v13_validation_20040102_20260731_1301e2e1.zip`：在 v13 規則與淘汰門檻凍結後才下載的 IWF/IWB、IWO/IWM、EFG/EFA、SHY 調整後 OHLCV 收據。
- `artifacts/v15_modest_leverage_overlay_validation.json`／`v15_modest_leverage_overlay_report.html`：v15 的三組首次查看 3 倍 ETF 機器收據與新手報表；經濟門檻 17/36、資料 4/4、統計 4/18，不建立 Paper。
- `artifacts/v15_protocol_receipt.json`、`v15_data_receipt.json` 與 `snapshot_v15_3x_20080102_20260731_57527472_validated.zip`：證明規則早於首次下載、保留第一次時區式新鮮度契約失敗，並以未修改價格面板重新簽發有效契約的 v15 收據。
- `artifacts/v16_trend_volatility_brake_validation.json`／`v16_trend_volatility_brake_report.html`：v16 的三組 18 年中小型實際 2 倍 ETF 驗證；經濟 6/48、資料 4/4、統計 0/27，不建立 Paper。
- `artifacts/v16_protocol_receipt.json`、`v16_data_receipt.json` 與 `snapshot_v16_trend_vol_20050103_20260731_777302d4.zip`：證明規則早於第一次下載 MVV/UWM/SAA，並保存完整資料雜湊與日期契約。
- `artifacts/v17_capital_efficient_validation.json`／`v17_capital_efficient_report.html`：六市場固定股債組合的 20／18 年機器收據與新手報表；經濟 48/84、資料 7/7、統計 9/54，不建立 Paper。
- `artifacts/v17_protocol_receipt.json`、`v17_data_receipt.json` 與 `snapshot_v17_capital_efficient_20040102_20260731_4c948bf6.zip`：第一次 v17 組合計算前鎖定比例、基準、期間、成本與門檻；元件路徑曾被看過，因此不冒充完全獨立確認。
- `artifacts/v18_equal_diversifier_validation.json`／`v18_equal_diversifier_report.html`：v18 的 EFA/EFO 與 EEM/EET 16 年海外機器收據與新手報表；外部經濟 5/18、資料 3/3、統計 0/12，不建立 Paper。
- `artifacts/v18_protocol_receipt.json`、`v18_data_receipt.json` 與 `snapshot_v18_equal_diversifier_20080602_20260731_dd920b90.zip`：證明股債金規則早於第一次下載海外日線，並揭露官方摘要績效曾在凍結前看過，所以只稱半獨立驗證。
- `artifacts/v19_product_mapping_receipt.json` 與 `docs/V19_PRODUCT_MAPPING.md`：在外部日線下載及策略計算前封存歐洲 ETF 歷史指數範圍不一致；v19 沒有績效結果，也沒有 Paper。
- `artifacts/v20_diversifier_strength_validation.json`／`v20_diversifier_strength_report.html`：v20 十一組資料的完整機器收據與新手報表；設計經濟 38/112、外部經濟 7/42、資料 13/13、外部統計 0/27，不建立 Paper。
- `artifacts/v20_protocol_receipt.json`、`v20_product_mapping_receipt.json`、`v20_data_receipt.json` 與 `snapshot_v20_diversifier_strength_20060803_20260731_e30b4032.zip`：證明只修正外部產品契約，規則早於第一次下載日本、中國大型股與巴西的實際 ETF 日線。
- `artifacts/v21_hybrid_leverage_core_validation.json`／`v21_hybrid_leverage_core_report.html`：v21 八組資料的完整機器收據與新手報表；已見設計經濟 49/96、新外部經濟 4/32、資料 10/10、外部統計 0/18，不建立 Paper。
- `docs/V21_HYBRID_LEVERAGE_CORE_PROTOCOL.md`、`docs/V21_PRODUCT_MAPPING.md`、三份 v21 收據與 `snapshot_v21_hybrid_core_20080102_20260731_45f452a2.zip`：證明 60% 常駐核心、120%／60% 名目曝險、兩月確認與全部淘汰門檻早於首次下載 UMDD／URTY 日線。
- `artifacts/v22_us_sector_capital_efficiency_validation.json`／`v22_us_sector_capital_efficiency_report.html`：v22 九組美國產業半獨立日線驗證；個別經濟 51/63、完整入口經濟 13/15、資料 11/11、統計 0/3，五年一致性失敗，不建立 Paper。
- `docs/V22_US_SECTOR_CAPITAL_EFFICIENCY_PROTOCOL.md`、`docs/V22_PRODUCT_MAPPING.md`、四份 v22 收據與 `snapshot_v22_us_sectors_20030102_20190621_52450c12_validated.zip`：證明九組產品、共同指數區間、固定 50/25/25、成本與淘汰門檻早於首次下載；DIG 極端行情另以 ProShares 官方 NAV 稽核且未重新下載。

## 研究策略與基準

### v22 美國產業股債金資本效率（完整期勝出，五年一致性否決）

六個美國廣泛市場的 20／18 年紀錄只算 v18 設計來源；v22 在第一次下載本輪
產業日線前，另把九組普通／實際每日 2 倍產業 ETF、共同指數截止日、固定
50/25/25、10／50 bps、兩半期與五年滾動門檻全部鎖定。正式期只有
2007-07-31–2019-06-21，因 2019-06-24 起部分普通 ETF 的底層指數加入集中度
上限；不把後續定義不一致資料拼成較長的「獨立 20 年」。

九產業等權策略 CAGR 9.99%、Sharpe 0.619、最大回撤 −52.18%，普通 ETF
等權為 8.23%、0.505、−53.07%。完整期平均有改善，但 1,260 日滾動 CAGR
領先至少 10 bps 的勝率只有 51.2%，低於事前 60%；九個產業個別勝率也都只有
36.9%–56.0%。同資產不槓桿的最大回撤只有 −36.17%，多重搜尋後 DSR 機率
0.12%。所以經濟入口 13/15、資料 11/11、統計 0/3；不建立 v22 Paper，
50/25/25 仍是被淘汰研究比例，不是交易訊號。

### v20 分散器相對強弱（大型股 20 年；三個新區域市場 10 年否決）

每個完整月末以 12–1 月報酬排序 IEF、GLD、SHY，固定持有 50% 實際每日 2 倍
股票 ETF，再各配 25% 給排名前二的分散器；物理權重 100%，約 150% 總名目
曝險。規則不擇時股票，也不因市場更換回顧期、權重或停損。

大型股三組保留 2006–2026 的完整 20 年，中小型股三組為 2008–2026，另含
EFA／EEM 的既有 16 年診斷。凍結後第一次下載的日本、中國大型股、巴西正式期
為 2016-09-01–2026-07-31。十一組資料門檻全數通過，但動態策略的 CAGR 在
11/11 組都低於固定 50/25/25；日本／中國／巴西經濟門檻分別只過 3/14、0/14、
4/14，外部 NW、PSR、DSR 共 0/27。結論是不顯示最後配置、不建 Paper。

### v18 等權股／債／金資本效率（海外 16 年否決）

每個完整月末固定回到 50% 實際每日 2 倍股票 ETF／25% IEF／25% GLD，物理
權重 100%，約 100% 股票、25% 中期美債、25% 黃金，總名目曝險約 150%。
六個已見美國市場的完整期結果雖都勝原始 ETF，但只用來從七個固定候選中選定
中央、對稱的 50/25/25；不能當獨立證據。

凍結後的 2010-07-30–2026-07-31 海外日線顯示：已開發市場策略 CAGR 8.00%
對 EFA 7.70%，但 Sharpe 0.490 低於 0.504，最大回撤 −36.17% 深於 −34.19%，
前半期落後且五年滾動勝率只有 34.8%。新興市場 CAGR 5.12% 對 EEM 4.98%，
低於同資產不槓桿組合 5.38%；最大回撤 −46.68% 深於 −39.82%，五年勝率
31.1%。外部經濟 5/18、統計 0/12，不顯示美股 50/25/25 配置、不建 Paper。

### v17 資本效率股票／公債（大型股 20 年，中小型股 18 年）

每個完整月末固定回到 60% 實際每日 2 倍股票 ETF／40% IEF，物理權重 100%，
名目曝險約 160%。同時比較原始 1 倍 ETF、未槓桿 75% 股票／25% IEF，以及
相同約 120% 股票曝險但持有 40% SHY 的對照。S&P 500 組 CAGR 12.08% 對
SPY 11.25%，但最大回撤 −62.70% 對 −55.19%；Nasdaq-100 CAGR 18.43% 對
16.63%，最大回撤 −59.82% 對 −53.40%。其餘四組也未同時通過報酬、Sharpe、
Calmar、回撤、前後半與五年滾動門檻。總計 48/84，不顯示配置、不建 Paper。

### v16 週度趨勢與波動煞車（18 年實際中小型 2 倍 ETF）

核心高於 200 日均線時，依 21 日實現波動將股票名目曝險限制在 100%–150%；
轉弱時 100% SHY。三組最大回撤確實壓到約 −38% 至 −44%，但 CAGR 只有
2.79%–5.56%，原始 ETF 則約 9.61%–10.58%。三組各只過 2/16，統計 0/27；
這是「煞車降低部分跌幅，卻因交易與踏空犧牲太多報酬」的負結果。

### v13 兩月確認相對成長（既有三年代改善，新 ETF 直接否決）

確認成長連續兩個月成立時持有 40% 核心／60% 成長；成長關閉但核心仍在
200 日均線上時持有 100% 核心；兩者都弱時持有 70% 核心／30% SHY。只在
三態改變時交易。這套配置是在已知三段資料探索出來，因此先把全部參數、固定
20 年起點、50 bps 成本與 30 道淘汰門檻寫入協議，之後才下載三組新 ETF。

2006-07-31–2026-07-31，Russell 1000 組策略 CAGR 10.94%，低於 IWB 的
11.17%；50 bps 年化差為 −1.16pp，後十年與五年滾動也失敗，只過 6/10。
Russell 2000 組策略 CAGR 7.30%，低於 IWM 的 8.86%，只過 3/10。EAFE 組
在固定起點前只有 247 個共同有效交易日，少於凍結的 252 日暖機要求，不能事後
延後起點救援。新資料經濟門檻合計 9/30、資料門檻 3/4、統計門檻 0/9；結果
反駁跨股票母體的穩健超額，不建立 v13 Paper，也不顯示最後研究配置。

### v12 階層式 growth／core／defense（回撤改善，不等於穩健超額）

每個完整月末永久保留 60% 核心市場。剩餘 40% 先檢查成長的 12–1 相對動量
與 200 日趨勢；不成立時檢查核心自己的 200 日趨勢；兩者都不成立才放防守。
只在三態改變時成交。這套規則在 v10/v11 已事前寫定，但兩版都因 DJIA 取數
失敗而從未計算；v12 另行凍結三段既有資料後才首次跑績效。

2006-07-31–2026-07-31，策略 CAGR 11.10%、Sharpe 0.714、MDD −41.23%，
SPY 為 11.25%、0.647、−55.19%。回撤改善 13.96pp，但 CAGR 落後 0.15pp；
50 bps 後年化落後 1.19pp，後十年落後 1.13pp，五年滾動勝率只有 26.7%。
舊代理全期勝出，外部期全期略勝，但三段 NW t 與 PSR 全未達門檻，6,109 次
搜尋後 DSR 也全失敗。因此 Paper 入口 16/23、完整歷史 16/29；最後歷史政策
狀態雖為 60% SPY／40% QQQ，仍不是下單訊號。

### v9 低換手相對成長（全期勝出，三道 Paper 入口仍失敗）

每個完整月末仍用 12–1 相對動量與 200 日均線判斷，但只有布林狀態改變時才
成交。風險開啟配置 60% 核心市場／40% 成長市場，風險關閉為 100% 核心；
兩次切換間不把自然漂移的權重月月拉回 60/40。這是看到 v8 成本與回撤失敗後
提出的新研究，因此以 6,106 次搜尋懲罰揭露選擇偏誤，沒有把它包裝成獨立發現。

2006-07-31–2026-07-31、10 bps 下，策略 CAGR 12.10%、Sharpe 0.674、MDD
−56.47%，SPY 為 11.25%、0.647、−55.19%；241 個完整月末只完成 47 次狀態
切換成交。不過 50 bps 下策略 CAGR 11.257%，只比 SPY 11.253% 高約 0.004pp，
未達事前要求的 0.10pp。主期 NW t = 1.56、PSR = 92.27%，也未統計確認。

1989-01-03–2006-07-28 舊 Nasdaq-100 代理 CAGR 10.75%，高於 S&P 500 的
9.14%，但最大回撤 −57.08% 比市場 −49.15% 深 7.94pp，超過 5pp 上限。
下載前未見的 1973-01-03–1988-12-30 Nasdaq Composite 外部期，策略 CAGR
6.13% 高於市場 5.41%，50 bps 與五年滾動也通過；可是固定後半期落後市場
0.15pp／年，且 NW t 1.16、PSR 85.98% 均未達門檻。

所以 23 道 Paper 入口只過 20 道，29 道完整歷史門檻也只過 20 道；不建立
v9 Paper，CLI 會依機器收據拒絕繞過。最後研究狀態雖是 60% SPY／40% QQQ，
仍是淘汰研究的政策狀態，不是下單配置。

### v8 永遠持股相對成長（兩段全期勝出，但 Paper 入口仍失敗）

每個完整月末永久保留 50% SPY。QQQ 的 12–1 動量嚴格高於 SPY、且站在
200 日均線上時，另一半持有 QQQ；否則也持有 SPY。策略與 SPY 基準每一天都
是 100% 股票曝險，因此年化差異不再能由轉 SHY、少承擔市場風險解釋。

2006-07-31–2026-07-31、10 bps 下，策略 CAGR 12.32%、Sharpe 0.680、MDD
−56.81%；SPY 為 11.27%、0.648、−55.19%。策略前後十年都領先，五年滾動
有效勝率 80.0%；但 50 bps 下策略 CAGR 11.23%，略低於 SPY 11.25%。主動報酬
NW t = 1.60、PSR = 92.82%，未達統計確認。

1989-01-03–2006-07-28 舊代理 CAGR 10.98%，高於 S&P 500 的 9.14%，前後
兩半與五年滾動也通過；但 MDD −56.12% 比市場 −49.15% 深 6.97pp，超過事前
容許的 5pp。代理 NW t = 1.48、PSR = 91.30%。因此 16 道 Paper 經濟／跨期
入口只過 14 道，20 道完整歷史門檻也只過 14 道；不建帳戶、不事後放寬成本或
回撤門檻。6,105 次搜尋懲罰後主期／代理 DSR 僅 1.14%／0.87%。

### v7 相對成長衛星（政策可解釋，但 19 道只過 6 道）

每個完整月末永久保留 50% SPY。只有 QQQ 的 `t-252` 至 `t-21` 動量嚴格
高於 SPY、且 QQQ 嚴格站在 200 日均線上時，另一半持有 QQQ；否則持有 SHY。
selection-matched control 每月使用相同股票曝險：開啟時 100% SPY，關閉時
50% SPY／50% SHY，因此可以分開「降低市場曝險」與「選 QQQ」的效果。

2006-07-31–2026-07-31、10 bps 下，策略 CAGR 10.59%、Sharpe 0.717、MDD
−40.33%；SPY 為 11.27%、0.648、−55.19%，matched 為 9.30%、0.671、
−38.28%。策略回撤比 SPY 淺、年化高於 matched，但仍落後 SPY，而且回撤比
matched 深；相對 SPY 的五年滾動有效勝率 45.6%、NW t = −0.82。50 bps 與
固定前後兩半也無法同勝兩基準。

1989-01-03–2006-07-28 的不重疊價格指數代理，把 QQQ／SPY／SHY 唯一翻譯成
Nasdaq-100／S&P 500／零報酬 CASH。全期策略 CAGR 9.40%，略高於市場 9.14%
與 matched 7.33%，但前半期落後市場 1.96pp、回撤比 matched 深，NW 與 PSR
也未同時通過。19 道事前門檻只過 6 道，因此封存負結果、不調參、不建立 Paper。

### v6 產業動能核心傾斜（可交易主期失敗，不建立 Paper）

每個完整月末永久保留 50% SPY；其餘三個各占總資產 1/6 的槽位，選出 12–1
動量勝 SHY、且在 200 日均線上的前三個原始 Select Sector SPDR，空槽放 SHY。
公平對照每月使用完全相同的產業槽位數，卻把產業權重平均分配九檔，因此能把
「少持股票」與「選對產業」分開。

2006-07-31–2026-07-31、10 bps 下，策略 CAGR 10.00%、Sharpe 0.694、MDD
−33.35%；SPY 為 11.27%、0.648、−55.19%，同曝險對照為 10.20%、0.718、
−34.10%。策略雖降低 SPY 回撤，卻同時落後 SPY 與公平對照，50 bps、前後半期、
五年滾動和統計門檻也未全過。

1927–2005 的官方 French value-weighted 10 Industry 代理期，策略 CAGR 11.40%，
高於市場 9.80% 與 matched 10.09%；但代理資料不能凌駕可交易主期。22 道事前
門檻只通過 11 道，故封存負結果、不調參、不顯示研究配置作下單用途。協議見
[`docs/V6_INDUSTRY_TILT_PROTOCOL.md`](docs/V6_INDUSTRY_TILT_PROTOCOL.md)。

### v5 三時鐘等權集成（外部失敗，不建立 Paper）

每個完整月末固定平均三個獨立袖套：1/3 永久持有 QQQ、1/3 使用 v2 的
18%／21 日波動管理、1/3 使用 v3 的 252 日趨勢兩月確認。剩餘部位放 SHY，不搜尋
袖套比例、不槓桿，下一交易日開盤成交。

2006–2026 的結果很接近表面目標：CAGR 16.69% 對 QQQ 16.68%，MDD −42.10%
對 −53.40%；也以 16.69% 對 16.00% 勝固定 95% QQQ／5% SHY。但相對 95/5 的
NW t 只有 0.41、6,102 次懲罰 DSR 只有 0.032%。1986–2006 的五年滾動勝率相對
NDX／95/5 只有 36.9%／37.4%；五市場完整期同勝兩基準只有 1/5。22 道只過 10 道，
不能以近期成功取代泛化失敗。協議見
[`docs/V5_THREE_CLOCK_PROTOCOL.md`](docs/V5_THREE_CLOCK_PROTOCOL.md)。

### v4 股權風格輪動（歷史失敗，不建立 Paper）

每個完整月末計算 IWF、IWD、IJR 的 12–1 月動量，只選正分數前兩名，各固定
50%；不足的槽位放 SHY，下一交易日開盤成交。這是下載前只允許一組規則的文獻型
假說，不跑參數鄰域。

2006-07-31 至 2026-07-31，策略 CAGR 10.85%、Sharpe 0.726、MDD −34.96%；
SPY 為 11.27%、0.648、−55.19%。回撤改善 20.23pp，但 CAGR 落後 0.42pp，後十年
落後 SPY 3.61pp，五年滾動有效勝率只有 17.8%，相對 SPY NW t = −0.41；50 bps
下也落後 SPY 2.07pp。固定舊代理 `^RLG`／`^RLV` 在 Yahoo 只有 2002 年後資料，
無法支援 1996 起算，且協議禁止事後換代號。14 道硬門檻只通過 2 道，故不建立
Paper、不升級網站訊號。協議見 [`docs/V4_STYLE_ROTATION_PROTOCOL.md`](docs/V4_STYLE_ROTATION_PROTOCOL.md)。

### 0. 成長守門員 v3（代理期未過，隔離研究）

每月末看 QQQ 過去 252 日總報酬；連續兩個月為正才確認成長 regime，連續兩個月不為正才確認防守 regime。成長時持有 100% QQQ；防守時沿用 v2 的 `18% / 21 日實現波動` 配置，其餘放 SHY，不使用槓桿，下一交易日開盤成交。

2006-07-31 至 2026-07-31：CAGR 17.61% 對 QQQ 16.68%，Sharpe 0.915 對 0.810，MDD −36.19% 對 −53.40%；前後十年、25 bps 與一／二／三個月確認鄰域都勝過 QQQ。固定 96% QQQ／4% SHY 公平基準 CAGR 16.13%、MDD −51.62%，曝險控制門檻全過。

但 1986-10-01 至 2006-07-28 的 `^NDX` 價格指數代理期雖以 15.01% 對 12.81% 勝過 buy-and-hold，五年視窗必須至少領先 10 bps 才算勝後，勝率只有 36.9%，代理期前十年也落後 0.74 個百分點。改用 FRED 官方 DGS3MO／DTB3 短債利率累積現金報酬後，全期優勢略增至約 2.43 個百分點，但五年勝率仍是 36.9%、前十年仍落後約 0.67 個百分點；失敗不是零利率現金造成。相對 QQQ 的 NW t 只有 0.31，6,100 次搜尋懲罰 DSR 只有 0.024%。

更嚴格的下載前凍結五市場測試也失敗：只有 DAX 的完整期 CAGR 勝出，合計 1/5；50 bps 後仍勝出 1/5、五年滾動勝率達 60% 為 0/5，五市場等權主動報酬 NW t 為 −1.20，6,100 次搜尋懲罰後 DSR 機率約 0.000056%。這表示 v3 並非可跨市場泛化的穩健機制，因此只保留研究 Paper，不升級主網站。完整協議見 [`docs/V3_RESEARCH_PROTOCOL.md`](docs/V3_RESEARCH_PROTOCOL.md) 與 [`docs/V3_CROSS_MARKET_PROTOCOL.md`](docs/V3_CROSS_MARKET_PROTOCOL.md)。

### 0a. 成長守門員 v2（Paper-only 風險管理候選）

每月末以 QQQ 最近 21 個交易日的實現波動估計下個月權重：`QQQ 權重 = 18% / 年化實現波動`，限制在 0%–100%，不使用槓桿；其餘放 SHY，下一交易日開盤成交。18% 是 14%／18%／22% 三個先驗風險目標的中間值；22% 報酬更高、14% 回撤更低，因此 18% 不是端點贏家。

在 2006-07-31 至 2026-07-31 的凍結回測中，CAGR 15.61% 對 SPY 11.27%，最大回撤 −35.96% 對 −55.19%；但 QQQ CAGR 16.68% 仍較高。五年滾動視窗勝過 SPY 的比例為 96.7%，最近一個五年視窗領先 1.80 個百分點。即使成交成本提高到 100 bps，CAGR 仍為 13.25%，相對同成本 SPY 領先 2.03 個百分點。

只對 SPY 設計的歷史門檻全部通過，但相對 SPY 的 Newey–West t 值只有 1.69，6,014 次搜尋懲罰後 DSR 只有 1.01%。更重要的是，新增曝險控制後，被動 90% QQQ／10% SHY 的 CAGR 為 15.31%、MDD −48.86%；v2 全期 CAGR 只領先 0.31 個百分點，後十年反而落後 1.02 個百分點；以至少 10 bps 年化才算有效勝出的口徑，5 年滾動勝率只有 47.8%；25 bps 成本下也轉為落後。相對被動 90/10 的平均每日主動報酬年化為 −0.24%、NW t 為 −0.19。

90/10 稽核是在 v2 選定後補上，不能冒充預先註冊；但它是直接反證，所以部署介面會把 `reference_trade_candidate` 設為 `false`。目前定位是「降回撤效果值得 Paper 追蹤，但沒有穩健 alpha 證據」，不可升級成實金照單策略。v1 的 CAGR 14.54%、MDD −44.44% 與 paper state 全部保留，但不再作網站主訊號。

### 0b. 被動 90% QQQ／10% SHY（月末再平衡）

這不是另一個待優化策略，而是透明的曝險控制：固定 90% QQQ、10% SHY，每個完整月末恢復原權重，使用同一個下一開盤成交時鐘與成本。90% 是既有 v2 歷史平均 QQQ 權重上限的整數政策基準；它不看波動、不預測市場，也不使用未來資訊產生訊號。

### 1. SPY 買進持有

不可省略的機會成本基準。策略若只因分散而降低報酬，報表會直接顯示，不會只拿現金或零報酬比較。

### 2. 十資產 ETF 等權

SPY、QQQ、IWM、EFA、EEM、VNQ、TLT、IEF、GLD、DBC 每月等權。它回答「不用預測、只做跨資產分散」能得到什麼。

### 3. 分散式雙動量（正式設定：252 日、跳過最近 21 日、Top 4）

每月末：

1. 計算 `t-252 → t-21` 的總報酬。
2. 只保留價格在 200 日均線上、且動量勝過 SHY 的資產。
3. 取前四名，每名 25%；不足的部位放入 SHY。
4. 下一交易日開盤成交。

Top 4 不是回測最高點：189／252／315 日三種回顧長度下，Top 4 都落在相近 CAGR、較高 Sharpe、較淺回撤的平坦區。這比挑一個尖峰參數更值得保留。

SHY 取代原先的 BIL，是因 [iShares 官方頁](https://www.ishares.com/us/products/239452/ishares-13-year-treasury-bond-etf)記載 SHY 成立於 2002-07-22，能支援 2006 年開始的完整 20 年研究；BIL 歷史較短，會截斷樣本。

### 4. 平衡趨勢衛星（研究候選，不是已證實策略）

每月末用 SPY、QQQ、IWM、EFA、EEM、VNQ、TLT、IEF、GLD、DBC：

1. 平均 63／126／252 日總報酬，只保留正動量且在 200 日均線上的 ETF。
2. 依 63 日波動倒數分配，每個資產在主動部位內最多 35%。
3. 十資產站上 200 日線的比例依序把核心風險降為 100%／70%／30%／0%；核心本身最多只用 50% 承擔這些風險，其餘放 SHY。
4. 總組合固定 75% 給上述核心、25% 給 QQQ 衛星；下一交易日開盤成交。

75% 不是零利率 Sharpe 最高點。核心比例 65%–90% 的零利率 Sharpe 高於 1；再往 85%–90% 雖提高該數字，CAGR 卻降到約 6%–7%，所以未採用。扣除 SHY 後，各比例的超額 Sharpe 只有約 0.77–0.81。這是同一快照反覆研究後得到的候選，不能把 20 年績效稱為純樣本外。

## 20 年結果摘要

固定使用 2026-07-31 快照、2006-07-31 至 2026-07-31、10 bps 成交成本：

- 成長守門員 v2：CAGR 15.61%、Sharpe 0.94、最大回撤 −35.96%；前後十年都勝過 SPY，五年滾動勝率 96.7%，但統計與前瞻資料仍未確認。
- 成長守門員 v3：CAGR 17.61%、Sharpe 0.91、最大回撤 −36.19%；近期完整期勝過 QQQ，但較舊代理期與五市場機制驗證都失敗，僅保留隔離 Paper。
- 成長守門員 v1（封存）：CAGR 14.54%、Sharpe 0.85、最大回撤 −44.44%。
- v6 產業動能核心傾斜：CAGR 10.00%、Sharpe 0.69、最大回撤 −33.35%；低於 SPY 與同曝險 matched，不建立 Paper。
- SPY：CAGR 11.3%、Sharpe 0.65、最大回撤 −55.2%。
- 十資產等權：CAGR 8.1%、Sharpe 0.64、最大回撤 −40.2%。
- Top 4 雙動量：CAGR 9.1%、Sharpe 0.75、最大回撤 −16.0%。
- 平衡趨勢衛星候選：CAGR 8.15%、零利率 Sharpe 1.071、SHY 超額 Sharpe 0.799、最大回撤 −14.36%；前後十年的 1.003／1.135 也屬零利率口徑。
- 雙動量相對 SPY 的 Newey–West t = −0.97，不能宣稱顯著勝出或顯著落後；樣本證據較支持降低路徑風險。

候選的額外檢查：

- 25 bps 成本下零利率／超額 Sharpe 為 1.032／0.761；50 bps 時為 0.966／0.696。
- 2012 年起展開式兩年 walk-forward 串接：CAGR 9.51%、零利率／超額 Sharpe 1.143／0.985、MDD −14.45%；2022–2023 單段零利率 Sharpe 只有 0.08。
- 局部核心比例族以超額報酬計算的 CSCV-PBO 約 63.9%。
- 超額 Sharpe 高於 1 的 PSR 只有 18.7%；把完成、中止、作廢與規劃搜尋以 6,000 次懲罰後，超額 DSR 為 42.2%。
- 另以 33 檔長歷史產業／國家／債券／實體資產 ETF 測試 128 個限定組合，最佳超額 Sharpe 只有 0.759；增加標的沒有解決問題。

因此目前準確結論是「找到零利率口徑 Sharpe > 1 的低回撤候選，但未找到教科書定義下、扣除 SHY 後 Sharpe > 1 的策略」。LIVE paper 從建立日後開始累積，作為實作與前瞻對照，不用來改寫這個負結果。

## 個股策略為何不當主線

`us_large_cap_watchlist_v1.csv` 是 IVV 官方持股檔在 2026-07-30 的前 30 大股票快照（`BRKB` 依 Yahoo 代號慣例記為 `BRK-B`）。把它拿去回填 20 年會有生存者偏誤，也會漏掉後來下市或被替換的公司。因此：

- 當期動量／趨勢／波動排名可以用來「今天看什麼」。
- 等權與動量傾斜回測只作機制診斷，報表明確標示偏誤。
- 在取得逐期成分股、下市報酬與可用日正確的財報資料前，不發布個股策略的歷史優越性宣稱。

## 美國版沒有硬搬的台股訊號

FINRA 的 ATS／Non-ATS 公開資料是彙總且延遲發布；SEC 13F 也是季度申報且有時差。它們能做研究因子，不能被描述成即時「大戶同向買進」。這與台灣鉅額交易＋權證資料的時間粒度和揭露制度不同，所以本版先保留資料邊界，不製造假的精確方向。

更多細節見 [研究方法](docs/RESEARCH_METHOD.md)、[資料來源與授權邊界](docs/DATA_SOURCES.md)、[決策與負結果](docs/DECISIONS.md)。

## 重要限制

- Yahoo Finance／yfinance 是研究用便利來源，不是交易所官方行情；上游可能回溯修訂。
- 調整後價格適合總報酬研究，但不是實際可成交價；快照會記錄還原方式。Paper 持倉因此是連續總報酬單位、不是券商股數；歷史調整價修訂只改單位數以維持既有市值，不改寫既有損益。
- 回測未含稅務、融資、申購限制、市場衝擊與盤中點差。
- LIVE paper 不是券商帳戶，也不證明能以模型開盤價成交；REPLAY 更不能冒充前瞻績效。
- v2 雖明顯降低被動 90/10 的歷史回撤，但跨十年、滾動視窗與成本檢查未證明報酬優勢；介面顯示的配置僅供 Paper 觀察。
- v3 五市場凍結測試僅 1/5 完整期勝出；單一 DAX 成功不能支持跨市場或實金策略宣稱。
- Bootstrap 區間描述歷史路徑不確定性，不是未來保證。
- 所有內容僅供研究與教育，不構成投資建議。
