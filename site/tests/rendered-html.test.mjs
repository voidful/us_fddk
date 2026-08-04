import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const publicSiteRoot = (
  process.env.PUBLIC_SITE_URL ?? "https://voidful.github.io/us_fddk"
).replace(/\/$/, "");
const escapedPublicSiteRoot = publicSiteRoot.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const ogImagePattern = new RegExp(
  `property="og:image" content="${escapedPublicSiteRoot}/og\\.png"`,
);

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("latest report exposes expanded baselines and stock diagnostics", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /更多 baseline，不迴避輸贏/);
  assert.match(html, /九組同口徑配置矩陣/);
  assert.match(html, /12 隻現時大型股的完整 20 年比較/);
  assert.match(html, /倖存者偏差診斷/);
  assert.match(html, /60% SPY／40% IEF/);
  assert.match(html, /80% SPY／20% GLD/);
  assert.match(html, /80% VUG／20% GLD 漂移/);
  assert.match(html, /VUG／GLD 相關性/);
  assert.match(html, /NVDA/);
  assert.match(html, /AMD/);
  assert.match(html, /Paper-only/);
  assert.match(html, /兩條策略，兩套目標與門檻/);
  assert.match(html, /長線穩定/);
  assert.match(html, /短線高回報/);
  assert.match(html, /真實與合成分開/);
  assert.match(html, /FORMAL BACKTEST READINESS · ROUND 18/);
  assert.match(html, /合成就緒 18\/18、攻擊 18\/18；真實正式就緒仍只有 1\/18/);
  assert.match(html, /QQQ／SPY 不等於風險免費；超額統計不能再用 0 或 SHY 偷代/);
  assert.match(html, /四個比較對手在正式結果前定義清楚/);
  assert.match(html, /首輪 Top-10 等權後漂移/);
  assert.match(html, /US 1M T-bill daily RF/);
  assert.match(html, /6,208 trials/);
  assert.match(html, /十八道事前控制逐項呈列/);
  assert.match(html, /十八項 RF、run ID、baseline、成本及決策錯誤全數拒收/);
  assert.match(html, /只在合法 provider package 與同步一個月國庫券 RF 都到位後/);
  assert.match(html, /LOCAL QUARANTINE INTAKE · ROUND 17/);
  assert.match(html, /合成匯入 16\/16、攻擊 16\/16；真實匯入仍只有 1\/16/);
  assert.match(html, /舊 bridge 的 synthetic 標示不能直接承接真實供應商包/);
  assert.match(html, /真實與合成 status 不可互換/);
  assert.match(html, /十六道匯入控制逐項呈列/);
  assert.match(html, /十六項路徑、來源、數據及權限錯誤全數拒收/);
  assert.match(html, /只在使用者明確提供四個外部絕對路徑後運行 provider mode/);
  assert.match(html, /AUTHORIZED DATA HANDOFF · ROUND 16/);
  assert.match(html, /合成文件 12\/12、攻擊 12\/12；真實文件只有 1\/12/);
  assert.match(html, /請求已準備好；供應商能力及授權仍未證實/);
  assert.match(html, /同一產品、時段、欄位與成交時鐘/);
  assert.match(html, /十二道文件控制逐項呈列/);
  assert.match(html, /十二項文件錯誤，全數以指定代碼拒收/);
  assert.match(html, /先取得使用者授權，再發送固定請求/);
  assert.match(html, /EXECUTION EXTENSION · ROUND 15/);
  assert.match(html, /合成 extension 16\/16、攻擊 16\/16；真實逐股數據仍是 1\/20/);
  assert.match(html, /四項 schema 缺口已封口；市場證據仍未到位/);
  assert.match(html, /每項都有可核對日期、計數或價格路徑/);
  assert.match(html, /272(?:<!-- -->)?／(?:<!-- -->)?252/);
  assert.match(html, /十六道 extension 閘門逐項呈列/);
  assert.match(html, /十六項單一錯誤，全數以指定代碼停止/);
  assert.match(html, /候選只有 251 個訊號前回報 session/);
  assert.match(html, /只索取合法細樣本，不以合成 16\/16 先跑策略/);
  assert.match(html, /EXECUTION ACCOUNTING · ROUND 14/);
  assert.match(html, /退出會計 8\/12；十項攻擊全拒收，四項正式輸入仍缺/);
  assert.match(html, /退市沒有雙計，但正式引擎仍不可運行/);
  assert.match(html, /100 → (?:<!-- -->)?50/);
  assert.match(html, /十二道閘門逐項呈列/);
  assert.match(html, /十項會計與成交攻擊，全數以指定代碼停止/);
  assert.match(html, /付款日前釋放派息現金/);
  assert.match(html, /四項 extension 已在合成控制封口；真實數據仍未通過/);
  assert.match(html, /CRSP CIZ MAPPING · ROUND 13/);
  assert.match(html, /映射 20\/20、攻擊 12\/12 拒收/);
  assert.match(html, /成分生效日不是公布時間；退市儲存日不是退出日/);
  assert.match(html, /十二種單一錯誤，全數在指定閘門被擋下/);
  assert.match(html, /缺少成分公布時間 overlay/);
  assert.match(html, /換股 successor PERMNO 不在 master/);
  assert.match(html, /合法樣本 0、正式回測 0、Paper 0/);
  assert.match(html, /四條數據路徑：沒有一條可單獨通過/);
  assert.match(html, /CRSP／WRDS 只適合先索取正式樣本/);
  assert.match(html, /Norgate 不是現有合約的單一替代品|Norgate Data/);
  assert.match(html, /明確不等於通過/);
  assert.match(html, /危機減倉有效，但近期回報幾乎消失/);
  assert.match(html, /早期 (?:<!-- -->)?14\.59%(?:<!-- -->)?，近期只餘 (?:<!-- -->)?0\.58%/);
  assert.match(html, /QQQ、SPY、原始動量與相同持倉比率全部列出/);
  assert.match(html, /低成本假設亦救不到近期結果/);
  assert.match(html, /跌幅較淺，不等於值得犧牲二十年升幅/);
  assert.match(html, /原始數據合約/);
  assert.match(html, /4(?:<!-- -->)?\/(?:<!-- -->)?9/);
  assert.match(html, /非獨立 · (?:<!-- -->)?27(?:<!-- -->)?\/(?:<!-- -->)?48/);
  assert.match(html, /候選 (?:<!-- -->)?0\.58%(?:<!-- -->)?／QQQ (?:<!-- -->)?16\.81%/);
  assert.match(html, /NW t (?:<!-- -->)?-4\.21/);
  assert.match(html, /負 alpha 反駁/);
  assert.match(html, /逐股數據就緒度：1\/20，先堵住存活者偏差/);
  assert.match(html, /展開全部 20 道數據閘門/);
  assert.match(html, /十二種固定攻擊加一個完整控制包/);
  assert.match(html, /驗證器已能拒絕壞數據；真實供應商數據仍未到位/);
  assert.match(html, /幽靈價格/);
  assert.match(html, /全池動量傾斜：數據 10\/10，經濟只過 23\/48/);
  assert.match(html, /排名傾斜早期有效；近期仍輸市場、SPY 及 QQQ/);
  assert.match(html, /早期：分散傾斜勝市場與等權，仍輸集中組合/);
  assert.match(html, /近期：只輕微勝等權，市場及 QQQ 機會成本更高/);
  assert.match(html, /早期集中度有回報，近期則幾乎攤平/);
  assert.match(html, /排名訊號仍有殘餘，最高五分位已不再領先/);
  assert.match(html, /12\.36%/);
  assert.match(html, /8\.31%/);
  assert.match(html, /-1\.63%/);
  assert.match(html, /23\/48 負結果優先/);
  assert.match(html, /大型股短窗贏家：數據 10\/10，經濟只過 14\/44/);
  assert.match(html, /大型股隔離後仍跑輸市場；近期更大幅落後 QQQ/);
  assert.match(html, /first-seen 14\/44、schema-informed 11\/38/);
  assert.match(html, /短窗贏家策略：工程 8\/8，經濟只過 11\/38/);
  assert.match(html, /短窗贏家延續被市場、同池基準與長窗動量擊敗/);
  assert.match(html, /早期完整期：零成本也未能追上四個基準/);
  assert.match(html, /近期改善，但市場及 12–2 贏家仍更好/);
  assert.match(html, /成本容忍度很低，統計沒有確認/);
  assert.match(html, /六條路徑全部保留，不事後換冠軍/);
  assert.match(html, /2020 勝出，不能掩蓋五段較差尾部表現/);
  assert.match(html, /4\.61%/);
  assert.match(html, /9\.71%/);
  assert.match(html, /-0\.36%/);
  assert.match(html, /市場 .*3\.71.* · 大型股等權 .*15\.32.* bps/);
  assert.match(html, /最新全池動量傾斜驗證只過/);
  assert.match(html, /實金及 Paper 動作均為 US\$0/);
  assert.match(html, /美股一個月贏家延續測試：6\/8，計算前停止/);
  assert.match(html, /原檔標題不符凍結映射，沒有計算任何回報/);
  assert.match(html, /Aerage Value Weighted Returns -- Monthly/);
  assert.match(html, /Value Weight Returns -- Monthly/);
  assert.match(html, /French 30 行業逾 63 年驗證：早期有效，近期不足/);
  assert.match(html, /完整早期樣本：候選勝出，但仍未過全部門檻/);
  assert.match(html, /近期樣本：回報略高，證據強度大幅下降/);
  assert.match(html, /成本、分段、PBO 與因子解釋/);
  assert.match(html, /早期 5\/5，近期只 3\/5/);
  assert.match(html, /六段壓力期：上行較高，尾部風險仍大/);
  assert.match(html, /14\.11%/);
  assert.match(html, /12\.55%/);
  assert.match(html, /5\.81%/);
  assert.match(html, /98\.4%/);
  assert.match(html, /88\.1%/);
  assert.match(html, /1971-03-11/);
  assert.match(html, /較早大型股沙盒：表面跑贏也未證明輪選/);
  assert.match(html, /現時完整股池漂移/);
  assert.match(html, /21\.52%/);
  assert.match(html, /23\.04%/);
  assert.match(html, /PBO .*69\.0%/);
  assert.match(html, /台股短窗規則直譯：三版均未勝 QQQ/);
  assert.match(html, /拆走止賺止蝕後，20 日排序有正差/);
  assert.match(html, /5(?:<!-- -->)?\/(?:<!-- -->)?5(?:<!-- -->)? 表面通過/);
  assert.match(html, /NW t .*3\.03/);
  assert.match(html, /tst_wocker_filter_lab/);
  assert.match(html, /實金及 Paper 動作均為 US\$0/);
  assert.match(html, ogImagePattern);
  assert.match(html, /name="twitter:card" content="summary_large_image"/);
  assert.doesNotMatch(html, /IntersectionObserver|motion-reveal/);
});

test.skip("legacy public report assertions are retained as an archive", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<html[^>]*lang="zh-Hant-HK"/);
  assert.match(html, /成長守門員 v2｜收窄最大跌幅有效，不等於穩健超額/);
  assert.match(html, /property="og:image"/);
  assert.match(html, /data-signal-freshness="checking"/);
  assert.match(html, /今天不落盤/);
  assert.match(html, /Paper Trading（模擬交易）/);
  assert.match(html, /v25 先做 Paper/);
  assert.match(html, /US\$1,000 摘要/);
  assert.match(html, /US\$1,000 REPORT SNAPSHOT/);
  assert.match(html, /示例投資本金/);
  assert.match(html, /US\$800/);
  assert.match(html, /US\$200/);
  assert.match(html, /20 年歷史入口/);
  assert.match(html, /標準化 Paper 比較帳戶仍以 US\$100,000 同日起跑/);
  assert.match(html, /只把讀者試算本金改為 US\$1,000/);
  assert.match(html, /第一個跨三家產品通過的候選/);
  assert.match(html, /v25 PAPER 目標，不是實金指令/);
  assert.match(html, /VUG 大型成長股/);
  assert.match(html, /GLD 實物黃金/);
  assert.match(html, /真實資金動作仍是 0/);
  assert.match(html, /三個模擬組合一致性/);
  assert.match(html, /同步通過/);
  assert.match(html, /更新期限/);
  assert.match(html, /跑贏 SPY，不等於跑贏每一種 ETF/);
  assert.match(html, /相對純成長 ETF/);
  assert.match(html, /自己最久低於先前高點/);
  assert.match(html, /179(?:<!-- -->)? 個月/);
  assert.match(html, /12 月區塊重抽樣/);
  assert.match(html, /這不是未來勝率/);
  assert.match(html, /PAPER 模擬交易試算 · 不會落盤/);
  assert.match(html, /示例 Paper 本金/);
  assert.match(html, /以 US\$1,000 看懂固定 80\/20/);
  assert.match(html, /value="1000"/);
  assert.match(html, /未計碎股限制、佣金、買賣差價、匯率及稅項/);
  assert.match(html, /目前實金動作仍是 0/);
  assert.match(html, /LIVE PAPER · 同起點公平競賽/);
  assert.match(html, /不是看回測冠軍，是看三個真實等待中的組合/);
  assert.match(html, /升級合約 v(?:<!-- -->)?2(?:<!-- -->)? 已在第一筆成交前凍結/);
  assert.match(html, /相同股票持倉比率控制/);
  assert.match(html, /等待足夠樣本/);
  assert.match(html, /待成交不算完成/);
  assert.match(html, /首次建倉/);
  assert.match(html, /不算六次月度重新平衡/);
  assert.match(html, /不是只贏一點點/);
  assert.match(html, /前後兩半都要贏/);
  assert.match(html, /不是隨機雜訊/);
  assert.match(html, /尚無成交/);
  assert.match(html, /沒有把待成交委託偽裝成已成交/);
  assert.match(html, /前瞻累積財富/);
  assert.match(html, /尚無可畫的前瞻走勢/);
  assert.match(html, /不把 20 年回測接到 LIVE 圖上/);
  assert.match(html, /不建立實金持倉/);
  assert.match(html, /今日實金動作：0/);
  assert.match(html, /不顯示可照抄的實金落盤金額/);
  assert.match(html, /目前沒有實金配置/);
  assert.match(html, /實金配置鎖定中/);
  assert.doesNotMatch(html, /我的試算資金/);
  assert.match(html, /固定 18% 目標波幅政策/);
  assert.match(html, /統計尚未確認/);
  assert.match(html, /持倉比率控制未通過/);
  assert.match(html, /數據可安全發布/);
  assert.match(html, /實金參考未開放/);
  assert.match(html, /Paper 與實金都停止參考/);
  assert.match(html, /更新與完整性檢查完成前維持關閉/);
  assert.match(html, /不可回填的等待期/);
  assert.match(html, /維持 Paper-only/);
  assert.match(html, /為什麼數據檢查通過，還是不能落盤/);
  assert.match(html, /真正難的基準：不用預測的 90\/10/);
  assert.match(html, /5 年滾動勝率至少 75%/);
  assert.match(html, /保留 Paper 追蹤，不升級成實金參考策略/);
  assert.match(html, /v3 在 20 年贏 QQQ/);
  assert.match(html, /1986–2006 · 更早期代理/);
  assert.match(html, /1989–2006 · 五市場事前凍結/);
  assert.match(html, /完整期勝出，機制未能泛化/);
  assert.match(html, /不能拿單一成功掩蓋四個失敗市場/);
  assert.match(html, /德國/);
  assert.match(html, /DAX/);
  assert.match(html, /50 bps 仍勝出/);
  assert.match(html, /Newey–West t/);
  assert.match(html, /2006–2026 · v4 股權風格輪動/);
  assert.match(html, /14 道門檻只過/);
  assert.match(html, /不建立 Paper/);
  assert.match(html, /舊代理數據門檻失敗/);
  assert.match(html, /2002-09-30/);
  assert.match(html, /v4 最大跌幅較小，為什麼連 Paper 都不開/);
  assert.match(html, /1986–2026 · v5 三時鐘等權集成/);
  assert.match(html, /近期幾乎追平 QQQ，為何仍不開 Paper/);
  assert.match(html, /研究配置，不是主訊號/);
  assert.match(html, /最新研究權重為 QQQ/);
  assert.match(html, /91\.8%/);
  assert.match(html, /五市場完整期/);
  assert.match(html, /v5 幾乎追平 QQQ，為什麼還是不開 Paper/);
  assert.match(html, /36\.9%/);
  assert.match(html, /1927–2026 · v6 產業動能核心傾斜/);
  assert.match(html, /長期代理支持，為何可交易主期仍淘汰/);
  assert.match(html, /道 · 不建立 Paper/);
  assert.match(html, /ETF 主期 · 策略 \/ SPY 年率化/);
  assert.match(html, /10\.00%/);
  assert.match(html, /11\.27%/);
  assert.match(html, /相同總股票持倉比率下，選產業沒有增加淨回報/);
  assert.match(html, /負結果已封存/);
  assert.match(html, /不可照單、不提供金額試算/);
  assert.match(html, /v6 長期代理有效，為什麼還是淘汰/);
  assert.match(html, /1989–2026 · v7 相對成長衛星/);
  assert.match(html, /政策值得理解，不代表可以照單/);
  assert.match(html, /v7 最大跌幅比 SPY 淺，為什麼仍不建立 Paper/);
  assert.match(html, /1989–2026 · v8 永遠持股相對成長/);
  assert.match(html, /最接近目標，不等於通過/);
  assert.match(html, /v8 已經連續兩段都跑贏市場/);
  assert.match(html, /1973–2026 · v9 低換手＋下載前未見外部期/);
  assert.match(html, /政策狀態不等於今天的落盤建議/);
  assert.match(html, /v9 已減少交易，為什麼成本門檻還是失敗/);
  assert.match(html, /1973–2026 · v10–v12 階層式三態/);
  assert.match(html, /最大跌幅改善了，為什麼仍不能當成跑贏 ETF 策略/);
  assert.match(html, /Paper 指令鎖定/);
  assert.match(html, /v12 已把最大跌幅壓低，為什麼仍不值得 Paper/);
  assert.match(html, /2006–2026 · v13 規則先鎖定、再下載新 ETF/);
  assert.match(html, /已知年代看起來進步，真正的新數據答應了嗎/);
  assert.match(html, /道新數據經濟門檻/);
  assert.match(html, /少跌不等於有能力跑贏/);
  assert.match(html, /v13 交易更少、舊年代更好，為什麼還是淘汰/);
  assert.match(html, /2006–2026 · v14 先凍結、再下載實際槓桿 ETF/);
  assert.match(html, /小幅槓桿加趨勢，真的能兼顧回報與風險嗎/);
  assert.match(html, /槓桿不是免費回報，少跌也不能抵銷少賺/);
  assert.match(html, /v14 的 Nasdaq 結果贏 QQQ，為什麼仍不開 Paper/);
  assert.match(html, /2011–2026 · v15 先凍結、再首次查看實際 3 倍 ETF/);
  assert.match(html, /三市場都賺比較多，就能稱為穩健跑贏嗎/);
  assert.match(html, /回報放大了，虧損也放大了/);
  assert.match(html, /不能拼成「獨立 20 年」/);
  assert.match(html, /v15 三市場年率化都贏 ETF，為什麼還是不能 Paper/);
  assert.match(html, /2008–2026 · v16 中小型股週度趨勢／波幅煞車/);
  assert.match(html, /少跌一些，是否值得犧牲一半以上回報/);
  assert.match(html, /v16 已降低最大跌幅，為什麼連 Paper 都不開/);
  assert.match(html, /2006–2026 \/ 2008–2026 · v17 六市場股債資本效率/);
  assert.match(html, /年率化比較高，為什麼仍不是穩健策略/);
  assert.match(html, /更高 CAGR 不是免費午餐/);
  assert.match(html, /v17 六市場 CAGR 多數較高，為什麼仍不算跑贏/);
  assert.match(html, /2010–2026 · v18 規則先凍結、再下載 EFO／EET 日線/);
  assert.match(html, /六個美國市場都好看，海外還能重現嗎/);
  assert.match(html, /美國回測成功，不代表規則能泛化/);
  assert.match(html, /v18 在六個美國市場都改善，為什麼海外失敗更重要/);
  assert.match(html, /2016–2026 · v20 三組新區域 ETF 日線/);
  assert.match(html, /id="v20-research"/);
  assert.match(html, /每月挑較強的債券或黃金，真的比固定配置好嗎/);
  assert.match(html, /動態輪替沒有勝過更簡單的固定配置/);
  assert.match(html, /中國大型股/);
  assert.match(html, /v20 會挑較強的分散器，為什麼仍輸固定配置/);
  assert.match(html, /2006–2026.+2011–2026 · v21 常駐核心＋受控槓桿/);
  assert.match(html, /id="v21-research"/);
  assert.match(html, /不完全退場、也不永遠全數持股/);
  assert.match(html, /折衷持倉比率仍不是穩健超額/);
  assert.match(html, /v21 已在退場與全數持股之間折衷，為什麼還是失敗/);
  assert.match(html, /id="v22-research"/);
  assert.match(html, /九個產業完整期都贏，為什麼仍不能拿來交易/);
  assert.match(html, /單一起訖點跑贏，不等於可以穩健跑贏 ETF/);
  assert.match(html, /v22 九個產業完整期都跑贏，為什麼還不開 Paper/);
  assert.match(html, /不替換 v2；v3 留在隔離 Paper/);
  assert.match(html, /任何漂移都拒絕更新網站/);
  assert.match(html, /獨立 Paper 驗證/);
  assert.match(html, /252 個交易日/);
  assert.match(html, /v3 回測贏 QQQ，為什麼不用/);
  assert.match(html, /LIVE 累積中/);
  assert.match(html, /SPY 同期/);
  assert.match(html, /QQQ 同期/);
  assert.match(html, /被動 90\/10 同期/);
  assert.match(html, /同一天現金起跑/);
  assert.match(html, /數據已過期/);
  assert.match(html, /停止參考舊配置/);
  assert.match(html, /Paper trade 不回填漂亮歷史/);
  assert.match(html, /價格重基準/);
  assert.match(html, /不回寫既有盈虧/);
  assert.match(html, /為什麼除息後 Paper 單位數可能改變/);
  assert.match(html, /不是證券商實際股數/);
  assert.match(html, /研究與教育用途，不構成投資建議/);
  assert.match(html, /報告架構參考/);
  assert.match(html, /tst_wocker_filter_lab/);
  assert.match(html, /中文採香港金融市場慣用詞/);
  for (const discouragedTerm of [
    "報酬",
    "績效",
    "回撤",
    "買進",
    "賣出",
    "下單",
    "資料",
    "新手",
    "部位",
    "曝險",
    "再平衡",
    "年化",
    "波動率",
    "收盤",
    "開盤",
    "停損",
  ]) {
    assert.doesNotMatch(html, new RegExp(discouragedTerm));
  }
  assert.doesNotMatch(html, /固定 80\/20 政策/);
  assert.doesNotMatch(html, /Your site is taking shape|react-loading-skeleton/);
});

test("server-renders the latest-strategy investment report", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<html[^>]*lang="zh-Hant-HK"/);
  assert.match(html, ogImagePattern);
  assert.match(html, /data-signal-freshness="checking"/);
  assert.match(html, /LONG-TERM STABILITY · v25/);
  assert.match(html, /SHORT-TERM RETURN RESEARCH/);
  assert.match(html, /role="tablist"/);
  assert.match(html, /長線穩定/);
  assert.match(html, /短線高回報/);
  assert.match(html, /80% 美國大型成長股/);
  assert.match(html, /今日實金動作維持/);
  assert.match(html, /US\$0/);
  assert.match(html, /US\$1,000/);
  assert.match(html, /VUG.*US\$800/);
  assert.match(html, /GLD.*US\$200/);
  assert.match(html, /目前市場與策略狀況/);
  assert.match(html, /近期五年仍領先 SPY/);
  assert.match(html, /20 年歷史入口/);
  assert.match(html, /同期間、同成本口徑的核心比較/);
  assert.match(html, /12\.94%/);
  assert.match(html, /三家實際 ETF 產品路徑/);
  assert.match(html, /Vanguard/);
  assert.match(html, /iShares/);
  assert.match(html, /State Street/);
  assert.match(html, /不是只看漂亮 CAGR/);
  assert.match(html, /成本壓力/);
  assert.match(html, /固定十年分段/);
  assert.match(html, /181 個滾動五年窗/);
  assert.match(html, /對 SPY 未確認/);
  assert.match(html, /多重搜尋校正/);
  assert.match(html, /配對移動區塊重抽樣/);
  assert.match(html, /最差歷史壓力並不溫和/);
  assert.match(html, /歷史通過，前瞻證據由零開始/);
  assert.match(html, /LIVE PAPER · 同起點公平競賽/);
  assert.match(html, /PAPER 模擬交易試算 · 不會落盤/);
  assert.match(html, /專業判讀與限制/);
  assert.match(html, /Yahoo Finance／yfinance/);
  assert.doesNotMatch(html, /v3 在 20 年贏 QQQ/);
  assert.doesNotMatch(html, /v24 學術測試/);
  assert.doesNotMatch(html, /舊策略研究/);
  assert.doesNotMatch(html, /Your site is taking shape|react-loading-skeleton/);

  for (const discouragedTerm of [
    "報酬",
    "績效",
    "回撤",
    "買進",
    "賣出",
    "下單",
    "資料",
    "新手",
    "部位",
    "曝險",
    "再平衡",
    "年化",
    "波動率",
    "收盤",
    "開盤",
    "停損",
  ]) {
    assert.doesNotMatch(html, new RegExp(discouragedTerm));
  }
});

test("data contract fails closed when the exposure-control benchmark is not robust", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  assert.equal(payload.evidence.historical_gate_passed, true);
  assert.equal(payload.evidence.exposure_control_passed, false);
  assert.equal(payload.evidence.reference_trade_candidate, false);
  assert.equal(payload.evidence.exposure_control_gates.both_ten_year_halves_beat_passive_90_10, false);
  assert.equal(payload.evidence.exposure_control_gates.still_beats_passive_90_10_at_25bps, false);
  assert.equal(payload.paper.forward_evidence.benchmarks.QQQ90_SHY10.return, 0);
  assert.equal(payload.paper.forward_evidence.live_confirmed, false);
  assert.equal(payload.paper.forward_evidence.remaining_sessions, 252);
  assert.equal(payload.paper.forward_evidence.remaining_filled_rebalances, 6);
  assert.equal(payload.readiness.contract_version, 3);
  assert.equal(payload.readiness.trade_ready, false);
  assert.equal(payload.readiness.decision, "paper_only");
  assert.equal(payload.readiness.ui_mode, "paper_only");
  assert.equal(payload.readiness.allocation_visible, false);
  assert.equal(payload.readiness.passed_gate_count, 2);
  assert.equal(payload.readiness.required_gate_count, 11);
  assert.equal(payload.readiness.gates.fresh_integrity, true);
  assert.equal(payload.readiness.gates.historical_gate_passed, true);
  assert.equal(payload.readiness.gates.exposure_control_passed, false);
  assert.equal(payload.readiness.gates.max_drawdown_no_worse_than_spy, false);
});

test("v3 challenger remains isolated when older proxy stability fails", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v3 = payload.research_pipeline.challengers.v3;
  assert.equal(v3.historical_gate_passed, true);
  assert.equal(v3.matched_control_passed, true);
  assert.equal(v3.proxy_validation.passed, false);
  assert.equal(v3.proxy_validation.gates.rolling_five_year_win_rate_at_least_60pct, false);
  assert.ok(v3.proxy_validation.rolling_five_year_win_fraction < 0.6);
  assert.equal(v3.reference_trade_candidate, false);
  assert.equal(v3.statistically_confirmed, false);
  assert.equal(v3.paper.forward_sessions, 0);
  assert.equal(v3.paper.transactions, 0);
  assert.ok(v3.paper.pending_order);
  assert.equal(v3.paper.snapshot_sha256, payload.snapshot_sha256);
  assert.deepEqual(v3.paper.pending_order.target_weights, { QQQ: 1 });
  assert.deepEqual(v3.current_target, { QQQ: 1, SHY: 0 });
  const cross = payload.research_pipeline.cross_market;
  assert.equal(cross.status, "cross_market_failed");
  assert.equal(cross.passed, false);
  assert.equal(cross.counts.full_cagr, 1);
  assert.equal(cross.counts.cost_50bps, 1);
  assert.equal(cross.counts.rolling_60pct, 0);
  assert.equal(cross.counts.both_halves, 1);
  assert.ok(Object.values(cross.aggregate_gates).every((passed) => passed === false));
  assert.ok(cross.pooled_active_return.annualized < 0);
  assert.ok(cross.pooled_active_return.newey_west_t < 0);
  assert.ok(cross.markets["^GDAXI"].cagr_difference > 0);
  for (const ticker of ["^GSPC", "^FTSE", "^N225", "^HSI"]) {
    assert.ok(cross.markets[ticker].cagr_difference < 0);
  }
});

test("v4 style rotation fails closed without creating a paper candidate", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v4 = payload.research_pipeline.style_rotation;
  assert.equal(v4.status, "historical_failed");
  assert.equal(v4.historical_gate_passed, false);
  assert.equal(v4.paper_eligible, false);
  assert.equal(v4.data_gate_passed, false);
  assert.equal(v4.passed_gate_count, 2);
  assert.equal(v4.required_gate_count, 14);
  assert.ok(v4.comparisons.market.cagr_difference < 0);
  assert.ok(v4.comparisons.market.drawdown_improvement > 0.2);
  assert.ok(v4.rolling_five_year.market.win_fraction < 0.2);
  assert.equal(v4.proxy.status, "data_gate_failed");
  assert.equal(v4.proxy.coverage["^RLG"].first_valid, "2002-09-30");
  assert.equal(v4.proxy.coverage["^RLV"].warmup_sessions_before_1996_07_31, 0);
  assert.deepEqual(v4.current_target, { IWD: 0.5, IJR: 0.5 });
});

test("v5 three-clock research fails closed across older and external evidence", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v5 = payload.research_pipeline.three_clock;
  assert.equal(v5.status, "historical_failed");
  assert.equal(v5.historical_gate_passed, false);
  assert.equal(v5.paper_eligible, false);
  assert.equal(v5.passed_gate_count, 10);
  assert.equal(v5.required_gate_count, 22);
  assert.ok(v5.main.strategy_metrics.cagr > v5.main.benchmark_metrics.opportunity.cagr);
  assert.ok(v5.main.comparisons.opportunity.drawdown_improvement > 0.1);
  assert.ok(v5.main.comparisons.matched_95_5.newey_west_t < 1.96);
  assert.deepEqual(v5.main.current_target, {
    QQQ: 0.9181810645199134,
    SHY: 0.08181893548008656,
  });
  assert.ok(v5.proxy.rolling_five_year.market.win_fraction < 0.4);
  assert.ok(v5.proxy.rolling_five_year.market.median_cagr_difference < 0);
  assert.equal(v5.cross_market.counts.full_cagr_beats_both, 1);
  assert.equal(v5.cross_market.counts.cost_50bps_beats_both, 0);
  assert.equal(v5.cross_market.counts.rolling_60pct_vs_both, 0);
  assert.ok(v5.cross_market.pooled_active_return.market.annualized < 0);
  assert.ok(v5.cross_market.pooled_active_return.market.newey_west_t < 0);
});

test("v6 industry tilt keeps the proxy success but rejects the tradeable rule", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v6 = payload.research_pipeline.industry_tilt;
  assert.equal(v6.status, "historical_failed");
  assert.equal(v6.historical_gate_passed, false);
  assert.equal(v6.paper_eligible, false);
  assert.equal(v6.passed_gate_count, 11);
  assert.equal(v6.required_gate_count, 22);
  assert.ok(v6.main.strategy_metrics.cagr < v6.main.benchmark_metrics.spy.cagr);
  assert.ok(v6.main.strategy_metrics.cagr < v6.main.benchmark_metrics.matched.cagr);
  assert.ok(v6.main.strategy_metrics.max_drawdown > v6.main.benchmark_metrics.spy.max_drawdown);
  assert.ok(v6.proxy.strategy_metrics.cagr > v6.proxy.benchmark_metrics.market.cagr);
  assert.ok(v6.proxy.strategy_metrics.cagr > v6.proxy.benchmark_metrics.matched.cagr);
  assert.equal(v6.proxy.decade_wins, 5);
  assert.deepEqual(v6.main.current_target, {
    SPY: 0.5,
    XLE: 1 / 6,
    XLI: 1 / 6,
    XLK: 1 / 6,
  });
  assert.ok(payload.limitations.some((item) => /v6 產業動能.*不可照單、不建立 Paper/.test(item)));
});

test("v7 separates exposure policy from alpha and fails closed", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v7 = payload.research_pipeline.relative_growth;
  assert.equal(v7.status, "historical_failed");
  assert.equal(v7.historical_gate_passed, false);
  assert.equal(v7.paper_eligible, false);
  assert.equal(v7.passed_gate_count, 6);
  assert.equal(v7.required_gate_count, 19);
  assert.ok(v7.main.strategy_metrics.cagr < v7.main.benchmark_metrics.market.cagr);
  assert.ok(v7.main.strategy_metrics.cagr > v7.main.benchmark_metrics.matched.cagr);
  assert.ok(v7.main.strategy_metrics.max_drawdown > v7.main.benchmark_metrics.market.max_drawdown);
  assert.ok(v7.main.strategy_metrics.max_drawdown < v7.main.benchmark_metrics.matched.max_drawdown);
  assert.ok(v7.main.rolling_five_year.market.win_fraction < 0.6);
  assert.ok(v7.main.comparisons.market.newey_west_t < 0);
  assert.ok(v7.proxy.strategy_metrics.cagr > v7.proxy.benchmark_metrics.market.cagr);
  assert.deepEqual(v7.main.current_target, { SPY: 0.5, QQQ: 0.5 });
  assert.ok(payload.limitations.some((item) => /v7 永久 50% SPY.*19 道只過 6 道，不建立 Paper/.test(item)));
});

test("v8 beats SPY in both full periods but respects cost and drawdown rejection", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v8 = payload.research_pipeline.always_invested;
  assert.equal(v8.status, "historical_economic_failed");
  assert.equal(v8.paper_eligible, false);
  assert.equal(v8.historically_confirmed, false);
  assert.equal(v8.paper_entry_passed_gate_count, 14);
  assert.equal(v8.paper_entry_required_gate_count, 16);
  assert.equal(v8.passed_gate_count, 14);
  assert.equal(v8.required_gate_count, 20);
  assert.ok(v8.main.strategy_metrics.cagr > v8.main.benchmark_metrics.market.cagr);
  assert.ok(v8.proxy.strategy_metrics.cagr > v8.proxy.benchmark_metrics.market.cagr);
  assert.ok(v8.main.rolling_five_year.win_fraction >= 0.8);
  assert.ok(v8.main.cost_50bps_cagr_difference < 0);
  assert.ok(v8.proxy.comparison.drawdown_difference < -0.05);
  assert.ok(v8.main.comparison.newey_west_t < 1.96);
  assert.ok(v8.proxy.comparison.newey_west_t < 1.96);
  assert.equal(v8.global_dsr_promotion_sensitivity.passed, false);
  assert.deepEqual(v8.main.current_target, { SPY: 0.5, QQQ: 0.5 });
  assert.ok(payload.limitations.some((item) => /v8 永遠維持.*Paper 入口 14\/16/.test(item)));
});

test("v9 reduces signal frequency but fails cost, old drawdown, and external-half gates", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v9 = payload.research_pipeline.low_turnover;
  assert.equal(v9.status, "historical_economic_failed");
  assert.equal(v9.paper_eligible, false);
  assert.equal(v9.historically_confirmed, false);
  assert.equal(v9.paper_entry_passed_gate_count, 20);
  assert.equal(v9.paper_entry_required_gate_count, 23);
  assert.equal(v9.passed_gate_count, 20);
  assert.equal(v9.required_gate_count, 29);
  assert.ok(v9.main.strategy_metrics.cagr > v9.main.benchmark_metrics.market.cagr);
  assert.ok(v9.main.signals.completed_executions_in_formal_period < v9.main.signals.completed_month_ends_in_formal_period);
  assert.ok(v9.main.cost_50bps_cagr_difference > 0);
  assert.ok(v9.main.cost_50bps_cagr_difference < 0.001);
  assert.ok(v9.old_proxy.comparison.drawdown_difference < -0.05);
  assert.ok(v9.external.fixed_halves.second.cagr_difference < 0);
  assert.ok(v9.main.comparison.newey_west_t < 1.96);
  assert.ok(v9.old_proxy.comparison.newey_west_t < 1.96);
  assert.ok(v9.external.comparison.newey_west_t < 1.96);
  assert.equal(v9.global_dsr_promotion_sensitivity.passed, false);
  assert.deepEqual(v9.main.current_policy_allocation, { SPY: 0.6, QQQ: 0.4 });
  assert.ok(payload.limitations.some((item) => /v9 改為只在狀態切換時交易.*Paper 入口 20\/23/.test(item)));
});

test("v12 improves drawdown but rejects return, cost, persistence, and statistics", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v12 = payload.research_pipeline.hierarchical_defense;
  assert.equal(v12.status, "historical_economic_failed");
  assert.equal(v12.paper_eligible, false);
  assert.equal(v12.historically_confirmed, false);
  assert.equal(v12.paper_entry_passed_gate_count, 16);
  assert.equal(v12.paper_entry_required_gate_count, 23);
  assert.equal(v12.passed_gate_count, 16);
  assert.equal(v12.required_gate_count, 29);
  assert.ok(v12.main.strategy_metrics.cagr < v12.main.benchmark_metrics.market.cagr);
  assert.ok(v12.main.comparison.drawdown_improvement > 0.13);
  assert.ok(v12.main.cost_50bps_cagr_difference < -0.01);
  assert.ok(v12.main.fixed_halves.second.cagr_difference < 0);
  assert.ok(v12.external.fixed_halves.second.cagr_difference < 0);
  assert.ok(v12.main.rolling_five_year.win_fraction < 0.3);
  assert.ok(v12.main.comparison.newey_west_t < 0);
  assert.ok(v12.old_proxy.comparison.newey_west_t < 1.96);
  assert.ok(v12.external.comparison.newey_west_t < 1.96);
  assert.equal(v12.global_dsr_promotion_sensitivity.passed, false);
  assert.equal(v12.prior_data_failures.v10.status, "fetch_failed");
  assert.match(v12.prior_data_failures.v11.error, /403/);
  assert.deepEqual(v12.main.current_policy_allocation, { SPY: 0.6, QQQ: 0.4 });
  assert.ok(payload.limitations.some((item) => /v12 保留 60% 核心.*Paper 入口 16\/23/.test(item)));
});

test("v13 freezes the rule before new ETF pairs and rejects cross-universe claims", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v13 = payload.research_pipeline.confirmed_relative_growth;
  assert.equal(v13.status, "new_etf_validation_failed");
  assert.equal(v13.paper_eligible, false);
  assert.equal(v13.historically_confirmed, false);
  assert.equal(v13.economic_passed_gate_count, 9);
  assert.equal(v13.economic_required_gate_count, 30);
  assert.equal(v13.data_passed_gate_count, 3);
  assert.equal(v13.data_required_gate_count, 4);
  assert.equal(v13.statistical_passed_gate_count, 0);
  assert.equal(v13.statistical_required_gate_count, 9);
  assert.ok(v13.datasets.russell_1000.strategy_metrics.cagr < v13.datasets.russell_1000.benchmark_metrics.market.cagr);
  assert.ok(v13.datasets.russell_2000.strategy_metrics.cagr < v13.datasets.russell_2000.benchmark_metrics.market.cagr);
  assert.ok(v13.datasets.russell_1000.cost_50bps_cagr_difference < 0);
  assert.ok(v13.datasets.russell_2000.cost_50bps_cagr_difference < 0);
  assert.equal(v13.datasets.eafe.status, "insufficient_warmup");
  assert.equal(v13.datasets.eafe.warmup_common_sessions, 247);
  assert.equal(v13.datasets.eafe.required_warmup_sessions, 252);
  assert.equal(v13.paper_entry_decision, "do_not_create");
  assert.ok(payload.limitations.some((item) => /v13 先凍結兩月確認.*新數據經濟門檻 9\/30/.test(item)));
});

test("v14 uses real leveraged ETFs but rejects cherry-picking Nasdaq", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v14 = payload.research_pipeline.modest_leverage;
  assert.equal(v14.status, "new_leveraged_etf_validation_failed");
  assert.equal(v14.paper_eligible, false);
  assert.equal(v14.statistically_confirmed, false);
  assert.equal(v14.economic_passed_gate_count, 13);
  assert.equal(v14.economic_required_gate_count, 36);
  assert.equal(v14.data_passed_gate_count, 4);
  assert.equal(v14.data_required_gate_count, 4);
  assert.equal(v14.statistical_passed_gate_count, 0);
  assert.equal(v14.statistical_required_gate_count, 18);
  assert.equal(v14.maximum_equity_notional, 1.2);
  assert.ok(v14.datasets.sp500.strategy_metrics.cagr < v14.datasets.sp500.benchmark_metrics.core.cagr);
  assert.ok(v14.datasets.nasdaq100.strategy_metrics.cagr > v14.datasets.nasdaq100.benchmark_metrics.core.cagr);
  assert.ok(v14.datasets.nasdaq100.strategy_metrics.cagr < v14.datasets.nasdaq100.benchmark_metrics.fixed_60_40.cagr);
  assert.ok(v14.datasets.dow30.strategy_metrics.cagr < v14.datasets.dow30.benchmark_metrics.core.cagr);
  assert.ok(payload.limitations.some((item) => /v14 先凍結.*不建 Paper/.test(item)));
});

test("v15 beats each core CAGR but rejects deeper drawdown and weaker Sharpe", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v15 = payload.research_pipeline.modest_leverage_overlay;
  assert.equal(v15.status, "new_3x_etf_validation_failed");
  assert.equal(v15.paper_eligible, false);
  assert.equal(v15.statistically_confirmed, false);
  assert.equal(v15.economic_passed_gate_count, 17);
  assert.equal(v15.economic_required_gate_count, 36);
  assert.equal(v15.data_passed_gate_count, 4);
  assert.equal(v15.data_required_gate_count, 4);
  assert.equal(v15.statistical_passed_gate_count, 4);
  assert.equal(v15.statistical_required_gate_count, 18);
  assert.equal(v15.risk_on_equity_notional, 1.2);
  assert.equal(v15.independent_confirmation_years, 15);
  assert.equal(v15.cannot_claim_independent_twenty_year_v15, true);
  for (const data of Object.values(v15.datasets)) {
    assert.ok(data.strategy_metrics.cagr > data.benchmark_metrics.core.cagr);
    assert.ok(data.strategy_metrics.sharpe < data.benchmark_metrics.core.sharpe);
    assert.ok(data.strategy_metrics.max_drawdown < data.benchmark_metrics.core.max_drawdown);
  }
  assert.ok(v15.datasets.sp500.strategy_metrics.cagr < v15.datasets.sp500.benchmark_metrics.fixed_90_10.cagr);
  assert.ok(v15.datasets.dow30.strategy_metrics.cagr < v15.datasets.dow30.benchmark_metrics.fixed_90_10.cagr);
  assert.ok(payload.limitations.some((item) => /v15 先凍結.*不建 Paper/.test(item)));
});

test("v16 lowers drawdown but fails return and all statistical gates", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v16 = payload.research_pipeline.trend_volatility_brake;
  assert.equal(v16.status, "new_mid_small_cap_leveraged_etf_validation_failed");
  assert.equal(v16.paper_eligible, false);
  assert.equal(v16.economic_passed_gate_count, 6);
  assert.equal(v16.economic_required_gate_count, 48);
  assert.equal(v16.data_passed_gate_count, 4);
  assert.equal(v16.data_required_gate_count, 4);
  assert.equal(v16.statistical_passed_gate_count, 0);
  assert.equal(v16.statistical_required_gate_count, 27);
  assert.equal(v16.independent_confirmation_years, 18);
  for (const data of Object.values(v16.datasets)) {
    assert.equal(data.passed_gate_count, 2);
    assert.ok(data.strategy_metrics.cagr < data.benchmark_metrics.core.cagr);
  }
  assert.ok(payload.limitations.some((item) => /v16 先凍結.*不建 Paper/.test(item)));
});

test("v17 preserves twenty years where available but rejects deeper drawdowns", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v17 = payload.research_pipeline.capital_efficient;
  assert.equal(v17.status, "capital_efficient_equity_bond_validation_failed");
  assert.equal(v17.paper_eligible, false);
  assert.equal(v17.economic_passed_gate_count, 48);
  assert.equal(v17.economic_required_gate_count, 84);
  assert.equal(v17.data_passed_gate_count, 7);
  assert.equal(v17.data_required_gate_count, 7);
  assert.equal(v17.statistical_passed_gate_count, 9);
  assert.equal(v17.statistical_required_gate_count, 54);
  assert.equal(v17.large_cap_years, 20);
  assert.equal(v17.mid_small_cap_years, 18);
  for (const data of Object.values(v17.datasets)) {
    assert.ok(data.strategy_metrics.max_drawdown < data.benchmark_metrics.core.max_drawdown);
  }
  assert.ok(payload.limitations.some((item) => /v17 每月固定.*不建 Paper/.test(item)));
});

test("v18 external paths reject the US-selected stock bond gold structure", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v18 = payload.research_pipeline.equal_diversifier;
  assert.equal(v18.status, "equal_diversifier_external_validation_failed");
  assert.equal(v18.paper_eligible, false);
  assert.equal(v18.economic_passed_gate_count, 5);
  assert.equal(v18.economic_required_gate_count, 18);
  assert.equal(v18.data_passed_gate_count, 3);
  assert.equal(v18.data_required_gate_count, 3);
  assert.equal(v18.statistical_passed_gate_count, 0);
  assert.equal(v18.statistical_required_gate_count, 12);
  assert.equal(v18.external_years, 16);
  assert.equal(v18.evidence_classification, "semi_independent_external_validation_not_fully_blind");
  for (const data of Object.values(v18.datasets)) {
    assert.ok(data.strategy_metrics.max_drawdown < data.benchmark_metrics.core.max_drawdown);
  }
  assert.ok(payload.limitations.some((item) => /v18 在六個已見美國市場.*不建 Paper/.test(item)));
});

test("v20 diversifier strength rejects rotation across all eleven datasets", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v20 = payload.research_pipeline.diversifier_strength;
  assert.equal(v20.status, "diversifier_rotation_validation_failed");
  assert.equal(v20.paper_eligible, false);
  assert.equal(v20.design_economic_passed_gate_count, 38);
  assert.equal(v20.design_economic_required_gate_count, 112);
  assert.equal(v20.external_economic_passed_gate_count, 7);
  assert.equal(v20.external_economic_required_gate_count, 42);
  assert.equal(v20.economic_passed_gate_count, 45);
  assert.equal(v20.economic_required_gate_count, 154);
  assert.equal(v20.data_passed_gate_count, 13);
  assert.equal(v20.data_required_gate_count, 13);
  assert.equal(v20.statistical_passed_gate_count, 0);
  assert.equal(v20.statistical_required_gate_count, 27);
  assert.equal(v20.external_years, 10);
  assert.equal(v20.datasets.china_large_cap.passed_gate_count, 0);
  assert.equal(Object.keys(v20.datasets).length, 11);
  for (const data of Object.values(v20.datasets)) {
    assert.equal(data.data_gate_passed, true);
    assert.ok(data.strategy_metrics.cagr < data.benchmark_metrics.fixed_v18.cagr);
  }
  assert.ok(payload.limitations.some((item) => /v20 固定 50%.*不建 Paper/.test(item)));
});

test("v21 hybrid leverage core fails the new mid and small cap paths", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v21 = payload.research_pipeline.hybrid_leverage_core;
  assert.equal(v21.status, "hybrid_leverage_core_validation_failed");
  assert.equal(v21.paper_eligible, false);
  assert.equal(v21.trade_ready, false);
  assert.equal(v21.configuration_visible, false);
  assert.equal(v21.design_economic_passed_gate_count, 49);
  assert.equal(v21.design_economic_required_gate_count, 96);
  assert.equal(v21.external_economic_passed_gate_count, 4);
  assert.equal(v21.external_economic_required_gate_count, 32);
  assert.equal(v21.economic_passed_gate_count, 53);
  assert.equal(v21.economic_required_gate_count, 128);
  assert.equal(v21.data_passed_gate_count, 10);
  assert.equal(v21.data_required_gate_count, 10);
  assert.equal(v21.statistical_passed_gate_count, 0);
  assert.equal(v21.statistical_required_gate_count, 18);
  assert.equal(v21.design_20_year_markets, 3);
  assert.equal(v21.external_years, 15);
  assert.equal(Object.keys(v21.datasets).length, 8);
  assert.equal(v21.datasets.midcap400_3x.passed_gate_count, 2);
  assert.equal(v21.datasets.russell2000_3x.passed_gate_count, 2);
  for (const key of ["midcap400_3x", "russell2000_3x"]) {
    const dataset = v21.datasets[key];
    assert.equal(dataset.data_gate_passed, true);
    assert.ok(dataset.strategy_metrics.cagr < dataset.benchmark_metrics.core.cagr);
    assert.ok(dataset.strategy_metrics.max_drawdown < dataset.benchmark_metrics.core.max_drawdown);
  }
  assert.ok(payload.limitations.some((item) => /v21 永久保留 60% 核心.*不建 Paper/.test(item)));
});

test("v22 sector validation fails the preregistered five-year consistency gate", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v22 = payload.research_pipeline.sector_capital_efficiency;
  assert.equal(v22.status, "us_sector_capital_efficiency_validation_failed");
  assert.equal(v22.paper_eligible, false);
  assert.equal(v22.trade_ready, false);
  assert.equal(v22.configuration_visible, false);
  assert.equal(v22.individual_passed_gate_count, 51);
  assert.equal(v22.individual_required_gate_count, 63);
  assert.equal(v22.economic_passed_gate_count, 13);
  assert.equal(v22.economic_required_gate_count, 15);
  assert.equal(v22.data_passed_gate_count, 11);
  assert.equal(v22.data_required_gate_count, 11);
  assert.equal(v22.statistical_passed_gate_count, 0);
  assert.equal(v22.statistical_required_gate_count, 3);
  assert.equal(v22.individual_pass_count_by_gate.cagr_beats_core_25bp, 9);
  assert.equal(v22.individual_pass_count_by_gate.rolling_wins_60pct_and_positive_median, 0);
  assert.equal(v22.pooled.passed_gate_count, 8);
  assert.equal(v22.pooled.required_gate_count, 9);
  assert.ok(v22.pooled.strategy_metrics.cagr > v22.pooled.core_metrics.cagr);
  assert.ok(v22.pooled.rolling_five_year_vs_core.cagr_win_fraction < 0.60);
  assert.ok(v22.pooled.strategy_metrics.max_drawdown < -0.50);
  assert.equal(Object.keys(v22.datasets).length, 9);
  assert.ok(payload.limitations.some((item) => /v22 九產業完整期 CAGR.*不建 Paper/.test(item)));
});

test("v23 managed futures improves drawdown but fails persistence and product bridges", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v23 = payload.research_pipeline.managed_futures_capital_efficiency;
  assert.equal(v23.status, "managed_futures_capital_efficiency_validation_failed");
  assert.equal(v23.paper_eligible, false);
  assert.equal(v23.trade_ready, false);
  assert.equal(v23.signal_display_allowed, false);
  assert.equal(v23.long_passed_gate_count, 6);
  assert.equal(v23.long_required_gate_count, 10);
  assert.equal(v23.kmlm_bridge_passed_gate_count, 7);
  assert.equal(v23.kmlm_bridge_required_gate_count, 10);
  assert.equal(v23.fmf_passed_gate_count, 2);
  assert.equal(v23.fmf_required_pass_count, 5);
  assert.equal(v23.data_passed_gate_count, 7);
  assert.equal(v23.data_required_gate_count, 7);
  assert.equal(v23.long_horizon.period.months, 240);
  assert.ok(v23.long_horizon.strategy_metrics.cagr > v23.long_horizon.spy_metrics.cagr);
  assert.ok(
    v23.long_horizon.strategy_metrics.max_drawdown >
      v23.long_horizon.spy_metrics.max_drawdown,
  );
  assert.ok(v23.long_horizon.cost_50bps_cagr_difference < 0);
  assert.ok(v23.long_horizon.fixed_halves_vs_spy.second.cagr_difference < 0);
  assert.equal(v23.kmlm_actual_bridge.rolling_five_year_vs_spy.cagr_win_fraction, 0);
  assert.ok(v23.kmlm_actual_bridge.tracking.annualized_geometric_tracking_gap > 0.02);
  assert.ok(v23.fmf_cross_manager.strategy_metrics.cagr < v23.fmf_cross_manager.spy_metrics.cagr);
  assert.ok(payload.limitations.some((item) => /v23 50% SSO.*不建 Paper/.test(item)));
});

test("v24 separates academic factor success from failed investable ETF bridges", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v24 = payload.research_pipeline.quality_momentum_factor;
  assert.equal(v24.status, "quality_momentum_factor_validation_failed");
  assert.equal(v24.paper_eligible, false);
  assert.equal(v24.trade_ready, false);
  assert.equal(v24.signal_display_allowed, false);
  assert.equal(v24.academic_passed_gate_count, 10);
  assert.equal(v24.academic_required_gate_count, 10);
  assert.equal(v24.ishares_passed_gate_count, 5);
  assert.equal(v24.ishares_required_gate_count, 10);
  assert.equal(v24.invesco_passed_gate_count, 0);
  assert.equal(v24.invesco_required_gate_count, 7);
  assert.equal(v24.data_passed_gate_count, 8);
  assert.equal(v24.data_required_gate_count, 8);
  assert.equal(v24.academic_formal_20y.period.months, 240);
  assert.ok(
    v24.academic_formal_20y.strategy_metrics.cagr >
      v24.academic_formal_20y.market_metrics.cagr,
  );
  assert.ok(
    v24.academic_formal_20y.strategy_metrics.max_drawdown >
      v24.academic_formal_20y.market_metrics.max_drawdown,
  );
  assert.ok(v24.academic_formal_20y.rolling_five_year_vs_market.cagr_win_fraction > 0.60);
  assert.ok(v24.ishares_actual.fixed_halves_vs_market.second.cagr_difference < 0);
  assert.ok(v24.ishares_actual.rolling_five_year_vs_market.cagr_win_fraction < 0.50);
  assert.ok(
    v24.invesco_cross_manager.strategy_metrics.cagr <
      v24.invesco_cross_manager.market_metrics.cagr,
  );
  assert.ok(payload.limitations.some((item) => /v24 學術品質＋動能.*不建 Paper/.test(item)));
});

test("v25 passes three frozen product paths but remains gated by forward Paper evidence", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../data/trading-data.json", import.meta.url), "utf8"),
  );
  const v25 = payload.research_pipeline.growth_gold_diversification;
  assert.equal(v25.status, "growth_gold_diversification_passed_for_isolated_paper");
  assert.equal(v25.paper_eligible, true);
  assert.equal(v25.paper_state_created, true);
  assert.equal(v25.trade_ready, false);
  assert.equal(v25.paper_signal_display_allowed, true);
  assert.equal(v25.real_money_signal_display_allowed, false);
  assert.equal(v25.all_paths_passed, true);
  for (const path of Object.values(v25.paths)) {
    assert.equal(path.period.months, 240);
    assert.equal(path.passed_gate_count, 12);
    assert.equal(path.required_gate_count, 12);
    assert.ok(path.strategy_metrics.cagr > path.spy_metrics.cagr);
    assert.ok(path.strategy_metrics.max_drawdown > path.spy_metrics.max_drawdown);
  }
  assert.equal(v25.pooled.passed_gate_count, 10);
  assert.equal(v25.pooled.required_gate_count, 10);
  assert.ok(v25.pooled.strategy_metrics.cagr > v25.pooled.spy_metrics.cagr);
  assert.ok(v25.pooled.strategy_metrics.cagr > v25.pooled.matched_metrics.cagr);
  assert.ok(v25.pooled.strategy_metrics.cagr < v25.pooled.growth_metrics.cagr);
  assert.ok(v25.pooled.tradeoff_vs_growth.cagr_difference < 0);
  assert.ok(v25.pooled.tradeoff_vs_growth.sharpe_difference > 0);
  assert.ok(v25.pooled.tradeoff_vs_growth.drawdown_improvement > 0.10);
  assert.ok(v25.pooled.rolling_five_year_vs_spy.cagr_win_fraction > 0.60);
  assert.ok(v25.pooled.rolling_five_year_vs_growth.cagr_win_fraction < 0.20);
  const diagnostics = v25.pooled.post_entry_diagnostics_not_used_for_frozen_gate;
  assert.equal(diagnostics.used_for_frozen_entry_gate, false);
  assert.equal(diagnostics.portfolio_underwater.max_underwater_months, 35);
  assert.equal(diagnostics.relative_wealth_underwater.growth.max_underwater_months, 179);
  assert.equal(diagnostics.relative_wealth_underwater.growth.longest_episode.recovered, false);
  const bootstrap = diagnostics.paired_moving_block_bootstrap;
  assert.equal(bootstrap.used_for_frozen_entry_gate, false);
  const spy12 = bootstrap.benchmarks.SPY["12"];
  const growth12 = bootstrap.benchmarks.growth["12"];
  const matched12 = bootstrap.benchmarks.matched["12"];
  assert.ok(spy12.probability_cagr_above > 0.84);
  assert.ok(spy12.probability_cagr_above < 0.86);
  assert.ok(spy12.cagr_difference_percentiles.p05 < 0);
  assert.ok(spy12.probability_cagr_above_and_drawdown_not_worse > 0.72);
  assert.ok(spy12.probability_cagr_above_and_drawdown_not_worse < 0.75);
  assert.ok(growth12.probability_cagr_above < 0.40);
  assert.ok(matched12.probability_cagr_above > 0.98);
  assert.ok(matched12.probability_cagr_above_and_drawdown_not_worse > 0.58);
  assert.ok(matched12.probability_cagr_above_and_drawdown_not_worse < 0.62);
  assert.ok(v25.pooled.statistics_vs_spy.newey_west_t < 1.96);
  assert.equal(v25.paper.mode, "live");
  assert.equal(payload.research_snapshot_data_through, "2026-07-31");
  assert.equal(v25.paper.as_of, payload.data_through);
  assert.ok(["awaiting_fill", "invested", "cash"].includes(v25.paper.status));
  assert.ok(Number.isInteger(v25.paper.transactions));
  assert.ok(v25.paper.transactions >= 0);
  assert.equal(v25.paper.initial_cash, 100000);
  assert.equal(v25.paper.cost_bps, 10);
  assert.ok(v25.paper.total_costs >= 0);
  assert.ok(v25.paper.recent_transactions.length <= v25.paper.transactions);
  assert.ok(v25.paper.recent_filled_orders.length <= 12);
  assert.deepEqual(Object.keys(v25.paper.accounts).sort(), [
    "SPY",
    "candidate",
    "matched_80_VUG_20_SHY",
  ]);
  for (const account of Object.values(v25.paper.accounts)) {
    assert.equal(account.as_of, v25.paper.as_of);
    assert.ok(Number.isFinite(account.equity));
    assert.ok(account.equity > 0);
    assert.ok(Number.isFinite(account.return));
    assert.ok(account.max_drawdown <= 0);
    assert.ok(Number.isInteger(account.transactions));
    assert.ok(account.transactions >= 0);
    assert.ok(Number.isInteger(account.filled_rebalances));
    assert.ok(account.filled_rebalances >= 0);
    assert.equal(
      account.equity_curve.length,
      v25.paper.forward_evidence.forward_sessions + 1,
    );
    assert.equal(account.equity_curve[0].date, v25.paper.started_at);
  }
  if (v25.paper.status === "awaiting_fill") {
    assert.deepEqual(v25.paper.pending_order.target_weights, { GLD: 0.2, VUG: 0.8 });
  } else if (v25.paper.status === "invested") {
    assert.equal(v25.paper.pending_order, null);
    assert.ok(Object.keys(v25.paper.holdings).length > 0);
  }
  assert.ok(v25.paper.forward_evidence.forward_sessions >= 0);
  assert.equal(v25.paper.forward_evidence.minimum_sessions, 252);
  assert.equal(v25.paper.forward_evidence.promotion_protocol.schema_version, 2);
  assert.equal(
    v25.paper.forward_evidence.promotion_protocol.frozen_before_first_forward_fill,
    true,
  );
  assert.equal(v25.paper.forward_evidence.promotion_protocol.minimum_annualized_edge, 0.001);
  assert.equal(v25.paper.forward_evidence.promotion_protocol.minimum_active_newey_west_t, 1.96);
  assert.equal(v25.paper.forward_evidence.promotion_protocol_sha256.length, 64);
  assert.ok(v25.paper.forward_evidence.filled_orders_including_initial_allocation >= 0);
  assert.ok([0, 1].includes(v25.paper.forward_evidence.initial_allocations));
  assert.ok(v25.paper.forward_evidence.filled_rebalances >= 0);
  assert.equal(v25.paper.forward_evidence.gates.all_accounts_same_execution_clock, true);
  assert.equal(v25.paper.forward_evidence.gates.all_accounts_same_order_path, true);
  assert.equal(v25.paper.forward_evidence.gates.all_accounts_same_fill_counts, true);
  const forwardSampleReady =
    v25.paper.forward_evidence.forward_sessions >= v25.paper.forward_evidence.minimum_sessions
    && v25.paper.forward_evidence.filled_rebalances
      >= v25.paper.forward_evidence.minimum_filled_rebalances;
  assert.equal(
    v25.paper.forward_evidence.gates.all_accounts_exactly_one_initial_allocation,
    forwardSampleReady && v25.paper.forward_evidence.initial_allocations === 1,
  );
  for (const counts of Object.values(v25.paper.forward_evidence.account_fill_counts)) {
    assert.equal(
      counts.filled_orders,
      v25.paper.forward_evidence.filled_orders_including_initial_allocation,
    );
    assert.equal(counts.initial_allocations, v25.paper.forward_evidence.initial_allocations);
    assert.equal(counts.completed_rebalances, v25.paper.forward_evidence.filled_rebalances);
  }
  assert.equal(v25.paper.forward_evidence.live_confirmed, false);
  assert.equal(
    v25.paper.forward_evidence.gates.candidate_annualized_edge_at_least_10bp_vs_SPY,
    false,
  );
  assert.equal(
    v25.paper.forward_evidence.gates.candidate_outperforms_SPY_in_both_halves,
    false,
  );
  assert.equal(
    v25.paper.forward_evidence.gates.candidate_active_newey_west_t_at_least_1_96_vs_SPY,
    false,
  );
  assert.equal(v25.paper.forward_evidence.forward_diagnostics.SPY.active_newey_west.t_stat, 0);
  assert.equal(typeof v25.paper.snapshot_sha256, "string");
  assert.equal(v25.paper.snapshot_sha256.length, 64);
  assert.equal(v25.paper.forward_evidence.gates.all_accounts_same_snapshot, true);
  assert.equal(v25.paper.forward_evidence.gates.all_accounts_same_cost_and_cash, true);
  assert.equal(v25.paper.forward_evidence.gates.all_accounts_same_session_path, true);
  assert.ok(payload.limitations.some((item) => /v25 三條實際 20 年.*只顯示 Paper 80\/20/.test(item)));
});

test("mobile controls keep safe touch targets and readable FAQ spacing", async () => {
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(css, /\.brand \{ min-height: 48px;/);
  assert.match(css, /\.primary-button, \.secondary-button \{[^}]*min-height: 48px;/);
  assert.match(css, /\.quick-values button \{ min-height: 44px;/);
  assert.match(css, /\.market-status-list, \.context-grid, \.baseline-findings, \.test-matrix, \.robust-grid, \.tradeoff-grid, \.forward-score-grid,[^}]*grid-template-columns: 1fr;/);
  assert.match(css, /\.forward-decision-grid \{ grid-template-columns: 1fr;/);
  assert.match(css, /\.forward-decision-grid article:last-child:nth-child\(odd\) \{ grid-column: 1 \/ -1;/);
  assert.match(css, /\.faq-list details p \{[^}]*margin: 0 0 24px;/);
  assert.doesNotMatch(css, /\.faq-list details p \{[^}]*margin: -/);
});
