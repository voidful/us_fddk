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
  assert.match(html, /先補真實數據/);
  assert.match(html, /供應商預審 (?:<!-- -->)?0(?:<!-- -->)?\/(?:<!-- -->)?4/);
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
  assert.match(styles, /status-pulse/);
  assert.doesNotMatch(styles, /data-motion=ready|motion-reveal/);
});
