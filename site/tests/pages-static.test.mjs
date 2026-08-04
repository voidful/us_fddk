import assert from "node:assert/strict";
import { access, readdir, readFile } from "node:fs/promises";
import test from "node:test";

const publicSiteRoot = (
  process.env.PUBLIC_SITE_URL ?? "https://voidful.github.io/us_fddk"
).replace(/\/$/, "");
const escapedPublicSiteRoot = publicSiteRoot.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const ogImagePattern = new RegExp(
  `property="og:image" content="${escapedPublicSiteRoot}/og\\.png"`,
);

test("GitHub Pages output is self-contained under the repository base path", async () => {
  const html = await readFile(new URL("../pages-dist/index.html", import.meta.url), "utf8");
  assert.match(html, /<html[^>]*lang="zh-Hant-HK"/);
  assert.match(html, /LONG-TERM STABILITY · v25/);
  assert.match(html, /SHORT-TERM RETURN RESEARCH/);
  assert.match(html, /兩條策略，兩套目標與門檻/);
  assert.match(html, /長線穩定/);
  assert.match(html, /短線高回報/);
  assert.match(html, /今日實金動作維持/);
  assert.match(html, /US\$1,000/);
  assert.match(html, /US\$800/);
  assert.match(html, /US\$200/);
  assert.match(html, /目前市場與策略狀況/);
  assert.match(html, /三家實際 ETF 產品路徑/);
  assert.match(html, /更多 baseline，不迴避輸贏/);
  assert.match(html, /九組同口徑配置矩陣/);
  assert.match(html, /12 隻現時大型股的完整 20 年比較/);
  assert.match(html, /倖存者偏差診斷/);
  assert.match(html, /超額 Sharpe/);
  assert.match(html, /60% SPY／40% IEF/);
  assert.match(html, /80% VUG／20% GLD 漂移/);
  assert.match(html, /VUG／GLD 相關性/);
  assert.match(html, /NVDA/);
  assert.match(html, /AMD/);
  assert.match(html, /較早大型股沙盒：表面跑贏也未證明輪選/);
  assert.match(html, /美股一個月贏家延續測試：6\/8，計算前停止/);
  assert.match(html, /原檔標題不符凍結映射，沒有計算任何回報/);
  assert.match(html, /Aerage Value Weighted Returns -- Monthly/);
  assert.match(html, /Value Weight Returns -- Monthly/);
  assert.match(html, /真實與合成分開/);
  assert.match(html, /TEMPORAL &amp; TAIL ROBUSTNESS · ROUND 23/);
  assert.match(html, /八項反證只過 7\/8；最佳三年移除後統計門檻失效/);
  assert.match(html, /曆年 cluster t (?:<!-- -->)?3\.01/);
  assert.match(html, /52-event circular block bootstrap/);
  assert.match(html, /2025、2026、2009/);
  assert.match(html, /NW t (?:<!-- -->)?1\.95/);
  assert.match(html, /17(?:<!-- -->)?\/(?:<!-- -->)?21 年平均為正/);
  assert.match(html, /46 列佔全部正配對差 (?:<!-- -->)?30\.5%/);
  assert.match(html, /八項門檻逐項呈列；7\/8 不升格/);
  assert.match(html, /十五道輸入、時間、尾部、重抽及決策邊界控制/);
  assert.match(html, /robustness_decision_boundary_breached/);
  assert.match(html, /SURVIVORSHIP CONTAMINATION · ROUND 22/);
  assert.match(html, /主要合成格 5\/5；嚴重退出令統計證據先於平均值消失/);
  assert.match(html, /固定主要格 · -50% 退出／2% 污染/);
  assert.match(html, /NW t (?:<!-- -->)?1\.80/);
  assert.match(html, /NW t (?:<!-- -->)?1\.49/);
  assert.match(html, /四種退出回報 × 五種污染率，20 格全部呈列/);
  assert.match(html, /統計證據比平均差更早失效/);
  assert.match(html, /stress_baseline_not_adjusted/);
  assert.match(html, /最後訊號日手寫錯誤在計算前 fail closed/);
  assert.match(html, /PROVIDER GAP CLOSURE · ROUND 21/);
  assert.match(html, /五條路徑逐項對齊 14 項正式能力；0\/5 合格/);
  assert.match(html, /CRSP＋S&amp;P DJI 最接近完整；LSEG 是最完整的單一品牌候選/);
  assert.match(html, /5(?:<!-- -->)?\/(?:<!-- -->)?14 明確/);
  assert.match(html, /Point In Time: No/);
  assert.match(html, /第一封詢價只問九個可驗收問題/);
  assert.match(html, /十五道證據控制，全數通過/);
  assert.match(html, /十五項產品、時間、價格、退出及 RF 攻擊全拒收/);
  assert.match(html, /gap_decision_boundary_violation/);
  assert.match(html, /PROVIDER CONVERGENCE · ROUND 20/);
  assert.match(html, /Stock CIZ 直接支持 5\/10；其餘 5\/10 仍須逐列證據層/);
  assert.match(html, /同一 CRSP／WRDS 路徑最接近完整；時間證據及精確 RF 仍未封口/);
  assert.match(html, /十份正式輸入，不用相近欄位補洞/);
  assert.match(html, /兩份均與凍結版本一致/);
  assert.match(html, /十二道指南、欄位、年期、單位及決策控制/);
  assert.match(html, /十二項協議、版本、時間、退市及 RF 替代攻擊全拒收/);
  assert.match(html, /risk_free_tenor_substitution/);
  assert.match(html, /OFFICIAL RISK-FREE STAGING · ROUND 19/);
  assert.match(html, /官方 RF 已覆蓋 5,009\/5,031；仍欠最後 22 個 XNYS session/);
  assert.match(html, /99\.56%/);
  assert.match(html, /與凍結 snapshot 一致/);
  assert.match(html, /rf_decision_boundary_violation/);
  assert.match(html, /FORMAL BACKTEST READINESS · ROUND 18/);
  assert.match(html, /合成就緒 18\/18、攻擊 18\/18；真實正式就緒仍只有 1\/18/);
  assert.match(html, /QQQ／SPY 不等於風險免費/);
  assert.match(html, /首輪 Top-10 等權後漂移/);
  assert.match(html, /十八道事前控制逐項呈列/);
  assert.match(html, /十八項 RF、run ID、baseline、成本及決策錯誤全數拒收/);
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
  assert.match(html, /Norgate Data/);
  assert.match(html, /明確不等於通過/);
  assert.match(html, /危機減倉有效，但近期回報幾乎消失/);
  assert.match(html, /QQQ、SPY、原始動量與相同持倉比率全部列出/);
  assert.match(html, /低成本假設亦救不到近期結果/);
  assert.match(html, /跌幅較淺，不等於值得犧牲二十年升幅/);
  assert.match(html, /非獨立 · (?:<!-- -->)?27(?:<!-- -->)?\/(?:<!-- -->)?48/);
  assert.match(html, /逐股數據就緒度：1\/20，先堵住存活者偏差/);
  assert.match(html, /展開全部 20 道數據閘門/);
  assert.match(html, /十二種固定攻擊加一個完整控制包/);
  assert.match(html, /驗證器已能拒絕壞數據；真實供應商數據仍未到位/);
  assert.match(html, /幽靈價格/);
  assert.match(html, /全池動量傾斜：數據 10\/10，經濟只過 23\/48/);
  assert.match(html, /排名傾斜早期有效；近期仍輸市場、SPY 及 QQQ/);
  assert.match(html, /早期集中度有回報，近期則幾乎攤平/);
  assert.match(html, /12\.36%/);
  assert.match(html, /8\.31%/);
  assert.match(html, /-1\.63%/);
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
  assert.match(html, /現時完整股池漂移/);
  assert.match(html, /台股短窗規則直譯：三版均未勝 QQQ/);
  assert.match(html, /拆走止賺止蝕後，20 日排序有正差/);
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
  assert.match(html, /5(?:<!-- -->)?\/(?:<!-- -->)?5(?:<!-- -->)? 表面通過/);
  assert.match(html, /21\.52%/);
  assert.match(html, /23\.04%/);
  assert.match(html, /181 個滾動五年窗/);
  assert.match(html, /對 SPY 未確認/);
  assert.match(html, /歷史通過，前瞻證據由零開始/);
  assert.match(html, /\/us_fddk\/assets\//);
  assert.match(html, ogImagePattern);
  assert.match(html, /name="twitter:card" content="summary_large_image"/);
  assert.doesNotMatch(html, /(?:href|src)="\/assets\//);

  const script = html.match(/(?:src|href)="\/us_fddk\/(assets\/[^"]+\.js)"/);
  assert.ok(script, "expected a repository-prefixed client bundle");
  await access(new URL(`../pages-dist/${script[1]}`, import.meta.url));
  await access(new URL("../pages-dist/.nojekyll", import.meta.url));

  const assetsUrl = new URL("../pages-dist/assets/", import.meta.url);
  const assetNames = await readdir(assetsUrl);
  const javascript = (
    await Promise.all(
      assetNames
        .filter((name) => name.endsWith(".js"))
        .map((name) => readFile(new URL(name, assetsUrl), "utf8")),
    )
  ).join("\n");
  const styles = (
    await Promise.all(
      assetNames
        .filter((name) => name.endsWith(".css"))
        .map((name) => readFile(new URL(name, assetsUrl), "utf8")),
    )
  ).join("\n");
  assert.doesNotMatch(javascript, /IntersectionObserver/);
  assert.doesNotMatch(javascript, /motion-reveal/);
  assert.match(styles, /scroll-behavior:auto/);
  assert.match(styles, /status-chip i\{[^}]*animation:none/);
  assert.doesNotMatch(styles, /status-pulse|@keyframes/);
  assert.doesNotMatch(styles, /data-motion=ready|motion-reveal/);
});
