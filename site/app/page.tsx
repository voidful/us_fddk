import type { Metadata } from "next";
import FreshnessGuard from "./FreshnessGuard";
import PaperAllocationLab from "./PaperAllocationLab";
import StrategyTabs from "./StrategyTabs";
import V25ForwardBoard from "./V25ForwardBoard";
import data from "../data/trading-data.json";
import shortResearch from "../data/short-term-research.json";
import sectorResearch from "../data/short-term-sector-etf.json";

export const metadata: Metadata = {
  title: "美股雙策略研究｜長線穩定與短線高回報",
  description:
    "長線 ETF 分散策略與短線個股／行業動量研究分頁呈列，完整比較回報、最大跌幅、baseline、驗證門檻及 Paper 狀態。",
};

const readerCapital = 1_000;
const latest = data.research_pipeline.growth_gold_diversification;
const pooled = latest.pooled;
const diagnostics = pooled.post_entry_diagnostics_not_used_for_frozen_gate;
const expanded = latest.expanded_comparison_not_used_for_frozen_gate;
const marketContext = expanded.market_context;
const paper = latest.paper;
const forward = paper.forward_evidence;

const pct = (value: number, digits = 1) =>
  new Intl.NumberFormat("zh-HK", {
    style: "percent",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);

const money = (value: number) =>
  new Intl.NumberFormat("zh-HK", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

const pp = (value: number, digits = 2) =>
  `${value >= 0 ? "+" : ""}${(value * 100).toFixed(digits)} 個百分點`;

const multiple = (value: number, digits = 2) => value.toFixed(digits);

const shortDate = (value: string) => value.replaceAll("-", "/");

const comparisonRows = [
  { label: "長線穩定候選", detail: "80% 大型成長股／20% 黃金", metrics: pooled.strategy_metrics },
  { label: "SPY", detail: "美國大型股市場基準", metrics: pooled.spy_metrics },
  { label: "純成長 ETF", detail: "三路徑大型成長股彙總", metrics: pooled.growth_metrics },
  { label: "公平持倉比率基準", detail: "80% 成長股／20% SHY", metrics: pooled.matched_metrics },
];

const pathLabels: Record<string, string> = {
  vanguard: "Vanguard",
  ishares: "iShares",
  state_street: "State Street",
};

const productPaths = Object.entries(latest.paths).map(([key, value]) => ({
  key,
  provider: pathLabels[key] ?? key,
  pair: `${value.implementation.growth}／${value.implementation.gold}`,
  ...value,
}));

const bootstrap = diagnostics.paired_moving_block_bootstrap.benchmarks;
const expandedBaselines = expanded.formal_baselines;
const stockComparisons = expanded.individual_stock_diagnostics.stocks;
const baselineByKey = Object.fromEntries(expandedBaselines.map((row) => [row.key, row]));
const qqqBaseline = baselineByKey.QQQ;
const nvdaDiagnostic = stockComparisons.find((row) => row.symbol === "NVDA")!;
const amdDiagnostic = stockComparisons.find((row) => row.symbol === "AMD")!;
const sectorLabels: Record<string, string> = {
  "Information Technology": "資訊科技",
  "Consumer Discretionary": "非必需消費",
  Communication: "通訊服務",
  Financials: "金融",
  "Health Care": "醫療保健",
  Energy: "能源",
};
const identityGateNames = [
  "all_accounts_live_and_same_start",
  "all_accounts_same_as_of",
  "all_accounts_same_snapshot",
  "all_accounts_same_cost_and_cash",
  "all_accounts_same_session_path",
  "all_accounts_same_execution_clock",
  "all_accounts_same_order_path",
  "all_accounts_same_fill_counts",
  "zero_integrity_violations",
] as const;
const paperIntegrity = identityGateNames.every((key) => forward.gates[key] === true);
const realMoneyLocked = !latest.real_money_signal_display_allowed;
const shortCandidate = shortResearch.frozen_candidate;
const shortBaselines = shortResearch.baselines;
const shortComparison = shortResearch.comparison_vs_qqq;
const shortTranslation = shortResearch.taiwan_reference_translation_ablation.results;
const shortSignal = shortResearch.taiwan_reference_signal_layer_diagnostic;
const shortSignalPrimary = shortSignal.horizons["20"];
const shortCostRows = [
  { label: "10 bps", metrics: shortCandidate.cost_sensitivity["10_bps"] },
  { label: "25 bps", metrics: shortCandidate.cost_sensitivity["25_bps"] },
  { label: "50 bps", metrics: shortCandidate.cost_sensitivity["50_bps"] },
];
const shortTranslationRows = [
  { key: "tw_v85_weekly", label: "20 日動量＋60 日趨勢", metrics: shortTranslation.tw_v85_weekly },
  { key: "tw_v85_weekly_spy_regime", label: "再加 SPY 市場環境", metrics: shortTranslation.tw_v85_weekly_spy_regime },
  { key: "tw_v85_weekly_spy_regime_corr", label: "再加相關性濾網", metrics: shortTranslation.tw_v85_weekly_spy_regime_corr },
];
const shortSignalRows = [
  { label: "5 日", result: shortSignal.horizons["5"] },
  { label: "10 日", result: shortSignal.horizons["10"] },
  { label: "20 日（主要）", result: shortSignal.horizons["20"] },
];
const shortEconomicPassed = Object.values(shortResearch.economic_and_statistical_gates).filter(Boolean).length;
const shortDataPassed = Object.values(shortResearch.data_gates).filter(Boolean).length;
const sectorCandidate = sectorResearch.frozen_candidate;
const sectorBaselines = sectorResearch.baselines;
const sectorComparison = sectorResearch.comparison_vs_qqq;
const sectorSignal = sectorResearch.fixed_20_day_signal_external_diagnostic;
const sectorSignalComparison = sectorSignal.comparisons.eligible_equal;
const sectorBootstrap = sectorSignal.moving_block_bootstrap_mean_difference_vs_eligible_equal;
const sectorCostRows = [
  { label: "10 bps", metrics: sectorCandidate.cost_sensitivity["10_bps"] },
  { label: "25 bps", metrics: sectorCandidate.cost_sensitivity["25_bps"] },
  { label: "50 bps", metrics: sectorCandidate.cost_sensitivity["50_bps"] },
];
const sectorBaselineRows = [
  { label: "凍結月度 Top-3", detail: "20 日動量＋60 日趨勢", metrics: sectorCandidate.metrics, featured: true },
  { label: "QQQ 買入持有", detail: "高回報機會成本", metrics: sectorBaselines.QQQ },
  { label: "SPY 買入持有", detail: "美國大型股", metrics: sectorBaselines.SPY },
  { label: "VTI 買入持有", detail: "美國全市場", metrics: sectorBaselines.VTI },
  { label: "相同持倉比率行業等權", detail: "公平股票持倉比率控制", metrics: sectorBaselines.matched_equity_exposure_equal_sector },
  { label: "十行業月度等權", detail: "不排序、每月重設等權", metrics: sectorBaselines.sector_monthly_equal },
  { label: "十行業等權後漂移", detail: "起點等權、不再輪選", metrics: sectorBaselines.sector_start_equal_then_drift },
];
const sectorTickerOrder = ["VGT", "VCR", "VIS", "VHT", "VDC", "VAW", "VPU", "VOX", "VFH", "VDE"] as const;
const sectorIndividualRows = sectorTickerOrder.map((ticker) => ({
  ticker,
  ...sectorResearch.individual_sector_buy_and_hold_diagnostics[ticker],
}));
const sectorDataPassed = Object.values(sectorResearch.data_gates).filter(Boolean).length;
const sectorEconomicPassed = Object.values(sectorResearch.economic_and_statistical_gates).filter(Boolean).length;

export default function Home() {
  return (
    <>
      <header className="site-header">
        <div className="wrap nav-shell">
          <a className="brand" href="#top" aria-label="返回報告頂部">
            <span>US FDDK</span>
            <b>美股策略研究室</b>
          </a>
          <nav aria-label="報告導覽">
            <a href="#strategy-tabs">兩條策略</a>
            <a href="#strategy-evidence">研究證據</a>
            <a href="#paper">Paper 狀態</a>
          </nav>
          <FreshnessGuard
            dataThrough={data.data_through}
            refreshDueAtUtc={data.freshness.refresh_due_at_utc}
          />
        </div>
      </header>

      <main id="top">
        <StrategyTabs>
        <div id="long-term" data-strategy-panel="stable">
        <section className="hero wrap">
          <div className="hero-copy">
            <div className="eyebrow-row">
              <span className="eyebrow">LONG-TERM STABILITY · v25</span>
              <span className="status-chip warning"><i /> PAPER ONLY</span>
            </div>
            <h1>長線穩定<br />80% 美國大型成長股＋20% 黃金</h1>
            <p className="hero-lead">
              目標是保留增長、降低波幅與大型跌幅，不是追逐最高 CAGR。20 年歷史入口及三家實際 ETF 產品路徑全部通過；最新前瞻樣本仍是
              <strong> {forward.forward_sessions}/{forward.minimum_sessions} 個交易日</strong>，因此今日實金動作維持
              <strong> US$0</strong>。
            </p>
            <div className="hero-actions">
              <a className="primary-button" href="#backtest">查看完整回測</a>
              <a className="secondary-button" href="#paper">查看 Paper 進度</a>
            </div>
          </div>
          <aside className="decision-card" aria-label="最新策略決策摘要">
            <div className="decision-head">
              <span>長線策略摘要</span>
              <b>{realMoneyLocked ? "實金配置鎖定" : "參考配置開放"}</b>
            </div>
            <div className="capital-number"><small>讀者示例本金</small><strong>{money(readerCapital)}</strong></div>
            <div className="allocation-split" aria-label="Paper 目標配置">
              <div className="growth" style={{ width: "80%" }}><b>VUG</b><span>80% · {money(800)}</span></div>
              <div className="gold" style={{ width: "20%" }}><b>GLD</b><span>20%</span></div>
            </div>
            <dl className="decision-list">
              <div><dt>Paper 目標</dt><dd>VUG {money(800)}／GLD {money(200)}</dd></div>
              <div><dt>下一步</dt><dd>{paper.pending_order ? "等待下一交易日開市模擬成交" : "等待下次月末檢查"}</dd></div>
              <div><dt>實金動作</dt><dd className="locked">US$0 · 不落盤</dd></div>
            </dl>
            <p>US$1,000 只作比例示例；正式 Paper 三個模擬組合仍以 US$100,000 公平起跑。</p>
          </aside>
        </section>

        <section className="truth-strip">
          <div className="wrap truth-grid">
            <article><span>長線策略年率化回報</span><strong>{pct(pooled.strategy_metrics.cagr, 2)}</strong><small>SPY {pct(pooled.spy_metrics.cagr, 2)}</small></article>
            <article><span>QQQ 年率化回報</span><strong>{pct(qqqBaseline.metrics.cagr, 2)}</strong><small>高回報，但跌幅較深</small></article>
            <article><span>最大跌幅</span><strong>{pct(pooled.strategy_metrics.max_drawdown, 1)}</strong><small>SPY {pct(pooled.spy_metrics.max_drawdown, 1)}</small></article>
            <article><span>產品路徑</span><strong>3 / 3</strong><small>每條 12 / 12 門檻</small></article>
            <article><span>前瞻 Paper</span><strong>{forward.forward_sessions} / {forward.minimum_sessions}</strong><small>{paper.status === "awaiting_fill" ? "首筆仍待成交" : "已開始累積"}</small></article>
          </div>
        </section>

        <section className="section wrap" id="market">
          <div className="section-heading">
            <div><span>MARKET STATUS</span><h2>目前市場與策略狀況</h2></div>
            <p>只用最新凍結快照和前瞻狀態判讀，不把歷史回測當成今日即時訊號。</p>
          </div>
          <div className="market-grid">
            <article className="market-verdict">
              <span>截至 {shortDate(data.data_through)}</span>
              <h3>近期五年仍領先 SPY，組合距歷史高位約 {pct(Math.abs(diagnostics.portfolio_underwater.current_drawdown), 1)}</h3>
              <p>
                最新五年窗的年率化回報較 SPY 高 {pp(diagnostics.rolling_five_year_entry_timing_risk.SPY.latest_window.cagr_difference)}，
                較純成長高 {pp(diagnostics.rolling_five_year_entry_timing_risk.growth.latest_window.cagr_difference)}。
                但全 20 年純成長 CAGR 仍高 {pp(Math.abs(pooled.tradeoff_vs_growth.cagr_difference))}；這套配置追求的是較高 Sharpe 及較淺最大跌幅，不是每段市況都要成為最高回報組合。
              </p>
              <div className="market-badges">
                <span>固定 80/20</span><span>每月檢查</span><span>不預測升跌</span><span>不使用槓桿</span>
              </div>
            </article>
            <div className="market-status-list">
              <article><span>數據狀態</span><strong>{paperIntegrity ? "完整性通過" : "暫停參考"}</strong><p>最新交易日 {data.freshness.last_session}；下一預期交易日 {data.freshness.next_expected_session}。</p></article>
              <article><span>當前風險</span><strong>{pct(diagnostics.portfolio_underwater.current_drawdown, 1)}</strong><p>這是回測組合相對自身歷史高位的距離，不是未來跌幅預測。</p></article>
              <article><span>最長復原期</span><strong>{diagnostics.portfolio_underwater.max_underwater_months} 個月</strong><p>最深一段由 {diagnostics.portfolio_underwater.deepest_episode.peak} 高位開始，至 {diagnostics.portfolio_underwater.deepest_episode.recovery} 才復原。</p></article>
              <article><span>今日可執行狀態</span><strong className="danger-text">Paper-only</strong><p>待成交指令不等於成交；實金配置仍鎖定。</p></article>
            </div>
          </div>
        </section>

        <section className="section wrap" id="backtest">
          <div className="section-heading">
            <div><span>20-YEAR BACKTEST</span><h2>同期間、同成本口徑的核心比較</h2></div>
            <p>{pooled.period.start_equity_date} 至 {pooled.period.end}，共 {pooled.period.months} 個月；回報包含經調整價格，換手成本在策略中扣除。</p>
          </div>
          <div className="metric-table-wrap">
            <table className="metric-table">
              <thead><tr><th>組合</th><th>年率化回報</th><th>Sharpe</th><th>波幅</th><th>最大跌幅</th><th>平均月度換手</th></tr></thead>
              <tbody>
                {comparisonRows.map((row, index) => (
                  <tr className={index === 0 ? "featured-row" : ""} key={row.label}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th>
                    <td>{pct(row.metrics.cagr, 2)}</td>
                    <td>{row.metrics.sharpe.toFixed(2)}</td>
                    <td>{pct(row.metrics.volatility, 1)}</td>
                    <td>{pct(row.metrics.max_drawdown, 1)}</td>
                    <td>{pct(row.metrics.turnover, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="tradeoff-grid">
            <article><span>對 SPY</span><strong>{pp(pooled.strategy_metrics.cagr - pooled.spy_metrics.cagr)}</strong><p>年率化回報優勢；最大跌幅改善 {pp(Math.abs(pooled.spy_metrics.max_drawdown) - Math.abs(pooled.strategy_metrics.max_drawdown))}。</p></article>
            <article><span>對純成長</span><strong>{pp(pooled.tradeoff_vs_growth.cagr_difference)}</strong><p>放棄少量年率化回報，換取 Sharpe +{pooled.tradeoff_vs_growth.sharpe_difference.toFixed(2)}、最大跌幅改善 {pp(pooled.tradeoff_vs_growth.drawdown_improvement)}。</p></article>
            <article><span>對公平基準</span><strong>{pp(pooled.strategy_metrics.cagr - pooled.matched_metrics.cagr)}</strong><p>同樣 80% 股票持倉比率，以黃金取代 SHY 後的年率化差異。</p></article>
          </div>

          <div className="subsection-heading">
            <div><span>PRODUCT SENSITIVITY</span><h3>三家實際 ETF 產品路徑</h3></div>
            <p>不只測單一 VUG／GLD 組合；同一 80/20 定義跨 Vanguard、iShares、State Street 重跑。</p>
          </div>
          <div className="metric-table-wrap">
            <table className="metric-table compact-table">
              <thead><tr><th>產品路徑</th><th>實際 ETF</th><th>年率化回報</th><th>Sharpe</th><th>最大跌幅</th><th>50 bps 後對 SPY</th><th>5 年窗勝 SPY</th><th>入口</th></tr></thead>
              <tbody>
                {productPaths.map((path) => (
                  <tr key={path.key}>
                    <th><b>{path.provider}</b><span>{path.period.months} 個月</span></th>
                    <td>{path.pair}</td>
                    <td>{pct(path.strategy_metrics.cagr, 2)}</td>
                    <td>{path.strategy_metrics.sharpe.toFixed(2)}</td>
                    <td>{pct(path.strategy_metrics.max_drawdown, 1)}</td>
                    <td>{pp(path.cost_50bps_cagr_difference_vs_spy)}</td>
                    <td>{pct(path.rolling_five_year_vs_spy.cagr_win_fraction, 1)}</td>
                    <td><span className="pass-pill">{path.passed_gate_count}/{path.required_gate_count}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="section comparison-section" id="strategy-evidence">
          <div className="wrap">
            <div className="section-heading">
              <div><span>EXPANDED COMPARISON LAB</span><h2>更多 baseline，不迴避輸贏</h2></div>
              <p>同一 20 年、同一經調整價格及 10 bps 成本。這一層只作通過後診斷，不更改凍結策略或 Paper 門檻。</p>
            </div>

            <div className="context-grid" aria-label="研究快照市場狀況指標">
              <article>
                <span>大型股市場廣度</span>
                <strong>{pct(marketContext.current_watchlist_above_200d_fraction, 1)}</strong>
                <p>{marketContext.current_watchlist_count} 隻現時大型股高於 200 天平均線；高於 50 天為 {pct(marketContext.current_watchlist_above_50d_fraction, 1)}。</p>
              </article>
              <article>
                <span>SPY 12 個月</span>
                <strong>{pct(marketContext.spy_return_12m, 1)}</strong>
                <p>高於 200 天平均線 {pct(marketContext.spy_distance_from_200d_average, 1)}；只描述 {marketContext.as_of} 快照。</p>
              </article>
              <article>
                <span>21 天實現波幅</span>
                <strong>{pct(marketContext.spy_realized_volatility_21d, 1)}</strong>
                <p>位於近五年 {pct(marketContext.spy_realized_volatility_21d_five_year_percentile, 0)} 分位，並非波幅預測。</p>
              </article>
              <article>
                <span>VIX 收市</span>
                <strong>{marketContext.vix_close.toFixed(2)}</strong>
                <p>近五年 {pct(marketContext.vix_five_year_percentile, 0)} 分位；不參與 80/20 買賣規則。</p>
              </article>
              <article>
                <span>成長股相對 SPY</span>
                <strong className={marketContext.vug_relative_return_vs_spy_12m < 0 ? "negative-number" : ""}>{pp(marketContext.vug_relative_return_vs_spy_12m)}</strong>
                <p>12 個月 VUG {pct(marketContext.vug_return_12m, 1)}，SPY {pct(marketContext.spy_return_12m, 1)}。</p>
              </article>
              <article>
                <span>VUG／GLD 相關性</span>
                <strong>{marketContext.vug_gold_correlation_252d.toFixed(2)}</strong>
                <p>252 日相關性；近 63 日升至 {marketContext.vug_gold_correlation_63d.toFixed(2)}，短期分散效用有所減弱。</p>
              </article>
            </div>

            <div className="subsection-heading baseline-heading">
              <div><span>FORMAL BASELINES</span><h3>九組同口徑配置矩陣</h3></div>
              <p>超額 Sharpe 以 SHY 月回報作現金代理；「策略五年窗勝率」是最新策略在 181 個滾動窗口勝過該列的比例。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table expanded-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>超額 Sharpe</th><th>Sortino</th><th>最大跌幅</th><th>Beta</th><th>策略五年窗勝率</th><th>NW t</th></tr></thead>
                <tbody>
                  {expandedBaselines.map((row) => (
                    <tr className={row.key === "candidate" ? "featured-row" : ""} key={row.key}>
                      <th><b>{row.label}</b><span>{row.detail}</span></th>
                      <td>{pct(row.metrics.cagr, 2)}</td>
                      <td>{multiple(row.excess_sharpe_vs_shy)}</td>
                      <td>{multiple(row.metrics.sortino)}</td>
                      <td>{pct(row.metrics.max_drawdown, 1)}</td>
                      <td>{multiple(row.beta_to_spy)}</td>
                      <td>{row.candidate_rolling_five_year_win_fraction === null ? "—" : pct(row.candidate_rolling_five_year_win_fraction, 1)}</td>
                      <td>{row.candidate_active_newey_west_t === null ? "—" : row.candidate_active_newey_west_t.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="baseline-findings">
              <article><span>高回報 baseline</span><strong>{pp(baselineByKey.candidate.metrics.cagr - baselineByKey.QQQ.metrics.cagr)}</strong><p>長線策略的 CAGR 低於 QQQ，五年窗只有 {pct(baselineByKey.QQQ.candidate_rolling_five_year_win_fraction, 1)} 勝出。</p></article>
              <article><span>同黃金比重控制</span><strong>{pp(baselineByKey["80_SPY_20_GLD"].candidate_cagr_difference)}</strong><p>成長股選擇相對 80% SPY／20% GLD 的 NW t 只有 {baselineByKey["80_SPY_20_GLD"].candidate_active_newey_west_t.toFixed(2)}。</p></article>
              <article><span>重新平衡測試</span><strong>{pp(baselineByKey["80_VUG_20_GLD_DRIFT"].candidate_cagr_difference)}</strong><p>每月重新平衡 CAGR 略高，但最大跌幅反而深 {pp(Math.abs(baselineByKey.candidate.metrics.max_drawdown - baselineByKey["80_VUG_20_GLD_DRIFT"].metrics.max_drawdown))}。</p></article>
            </div>

            <div className="baseline-source-links" aria-label="ETF 官方產品定義">
              <span>官方產品定義</span>
              {Object.entries(expanded.official_product_sources).map(([ticker, href]) => (
                <a href={href} target="_blank" rel="noreferrer" key={ticker}>{ticker}</a>
              ))}
            </div>
          </div>
        </section>

        <section className="section wrap" id="tests">
          <div className="section-heading">
            <div><span>ROBUSTNESS &amp; STATISTICS</span><h2>不是只看漂亮 CAGR</h2></div>
            <p>成本、固定十年分段、181 個滾動五年窗、統計檢定及 30,000 次配對區塊重抽樣都完整呈列。</p>
          </div>
          <div className="test-matrix">
            <article className="test-card passed">
              <div><span>01 · 歷史入口</span><b>通過</b></div>
              <strong>{pooled.passed_gate_count}/{pooled.required_gate_count}</strong>
              <p>三條產品路徑各 12/12；數據契約 {latest.data_passed_gate_count}/{latest.data_required_gate_count}。</p>
            </article>
            <article className="test-card passed">
              <div><span>02 · 成本壓力</span><b>通過</b></div>
              <strong>{pp(pooled.cost_50bps_cagr_difference_vs_spy)}</strong>
              <p>把單邊成本假設提高至 50 bps 後，年率化回報仍領先 SPY。</p>
            </article>
            <article className="test-card passed">
              <div><span>03 · 固定十年分段</span><b>兩段皆正</b></div>
              <strong>{pp(pooled.fixed_halves_vs_spy.first.cagr_difference)}</strong>
              <p>前十年對 SPY；後十年仍有 {pp(pooled.fixed_halves_vs_spy.second.cagr_difference)}。</p>
            </article>
            <article className="test-card mixed">
              <div><span>04 · 滾動五年</span><b>有時序風險</b></div>
              <strong>{pct(pooled.rolling_five_year_vs_spy.cagr_win_fraction, 1)}</strong>
              <p>{pooled.rolling_five_year_vs_spy.windows} 個窗口勝 SPY 的比例；最差年率化落後 {pp(pooled.rolling_five_year_vs_spy.worst_cagr_difference)}。</p>
            </article>
            <article className="test-card mixed">
              <div><span>05 · 統計顯著</span><b>對 SPY 未確認</b></div>
              <strong>t = {pooled.statistics_vs_spy.newey_west_t.toFixed(2)}</strong>
              <p>對公平持倉比率基準 t = {pooled.statistics_vs_matched.newey_west_t.toFixed(2)}；不能把兩者混為一談。</p>
            </article>
            <article className="test-card failed">
              <div><span>06 · 多重搜尋校正</span><b>警示</b></div>
              <strong>{pct(pooled.statistics_vs_spy.global_deflated_sharpe_probability, 1)}</strong>
              <p>全專案 {latest.global_search_trials.toLocaleString("zh-HK")} 次搜尋後的 Deflated Sharpe 機率很低，故只准 Paper。</p>
            </article>
          </div>

          <div className="robust-grid">
            <article className="rolling-panel">
              <div className="panel-title"><span>181 個滾動五年窗</span><h3>進場時間會改變體驗</h3></div>
              <div className="rolling-rows">
                <div><span>勝 SPY</span><div><i style={{ width: `${pooled.rolling_five_year_vs_spy.cagr_win_fraction * 100}%` }} /></div><b>{pct(pooled.rolling_five_year_vs_spy.cagr_win_fraction, 1)}</b></div>
                <div><span>勝公平基準</span><div><i style={{ width: `${diagnostics.rolling_five_year_entry_timing_risk.matched.winning_window_fraction * 100}%` }} /></div><b>{pct(diagnostics.rolling_five_year_entry_timing_risk.matched.winning_window_fraction, 1)}</b></div>
                <div><span>勝純成長</span><div><i className="gold-bar" style={{ width: `${pooled.rolling_five_year_vs_growth.cagr_win_fraction * 100}%` }} /></div><b>{pct(pooled.rolling_five_year_vs_growth.cagr_win_fraction, 1)}</b></div>
              </div>
              <p>結論：策略相對 SPY 及公平基準較有一致性，但大多數五年窗不會跑贏 100% 純成長；黃金的角色是分散風險。</p>
            </article>
            <article className="bootstrap-panel">
              <div className="panel-title"><span>12 個月區塊 · 10,000 次</span><h3>配對移動區塊重抽樣</h3></div>
              <dl>
                <div><dt>回報高於 SPY</dt><dd>{pct(bootstrap.SPY["12"].probability_cagr_above, 1)}</dd></div>
                <div><dt>回報高於且最大跌幅不差於 SPY</dt><dd>{pct(bootstrap.SPY["12"].probability_cagr_above_and_drawdown_not_worse, 1)}</dd></div>
                <div><dt>回報高於公平基準</dt><dd>{pct(bootstrap.matched["12"].probability_cagr_above, 1)}</dd></div>
                <div><dt>回報高於純成長</dt><dd>{pct(bootstrap.growth["12"].probability_cagr_above, 1)}</dd></div>
              </dl>
              <p>這是對歷史月份順序的敏感度診斷，不是未來勝率，也沒有用來改寫凍結入口。</p>
            </article>
          </div>

          <div className="risk-panel">
            <div><span>HISTORICAL STRESS</span><h3>最差歷史壓力並不溫和</h3></div>
            <dl>
              <div><dt>最深跌幅</dt><dd>{pct(diagnostics.portfolio_underwater.deepest_episode.drawdown, 1)}</dd></div>
              <div><dt>高位</dt><dd>{diagnostics.portfolio_underwater.deepest_episode.peak}</dd></div>
              <div><dt>谷底</dt><dd>{diagnostics.portfolio_underwater.deepest_episode.trough}</dd></div>
              <div><dt>復原</dt><dd>{diagnostics.portfolio_underwater.deepest_episode.recovery}</dd></div>
              <div><dt>水底期</dt><dd>{diagnostics.portfolio_underwater.deepest_episode.underwater_months} 個月</dd></div>
            </dl>
            <p>即使歷史最大跌幅比 SPY 淺，投資者仍可能面對超過三成跌幅和接近三年的復原期。黃金不是本金保障。</p>
          </div>
        </section>

        <section className="section wrap" id="paper">
          <div className="section-heading">
            <div><span>FORWARD PAPER TRADING</span><h2>歷史通過，前瞻證據由零開始</h2></div>
            <p>候選、SPY 與公平持倉比率基準同日起跑；不把 20 年回測接到 LIVE 圖，也不回填成交。</p>
          </div>
          <V25ForwardBoard paper={paper} integrity={paperIntegrity} />
          <PaperAllocationLab paperOnly={!latest.trade_ready} />
        </section>

        <section className="section wrap report-notes" id="notes">
          <div className="section-heading">
            <div><span>READING NOTES</span><h2>專業判讀與限制</h2></div>
            <p>報告保留支持證據與反證，避免只挑勝出的欄位。</p>
          </div>
          <div className="note-grid">
            <article><span>結論</span><h3>歷史上合格，前瞻仍未確認</h3><p>20 年三產品路徑及 pooled 入口通過，足以建立隔離 Paper；0/252 個新增交易日不足以顯示實金參考。</p></article>
            <article><span>最重要反證</span><h3>對 SPY 的 NW t 只有 {pooled.statistics_vs_spy.newey_west_t.toFixed(2)}</h3><p>歷史年率化優勢存在，但統計證據未達常用 1.96 門檻；多重搜尋校正亦偏弱。</p></article>
            <article><span>數據邊界</span><h3>Yahoo Finance／yfinance 研究快照</h3><p>使用經調整 OHLCV 並保存 SHA-256 快照；上游不是交易所官方行情，可能回溯修訂。</p></article>
            <article><span>成本邊界</span><h3>回測不等於個人實際成交</h3><p>未涵蓋個人稅務、匯率、碎股限制、券商佣金差異、市場衝擊及即市買賣差價。</p></article>
          </div>
          <div className="source-line">
            <span>研究快照</span><code>{data.research_snapshot_sha256}</code>
            <span>v25 協議</span><code>{latest.protocol_sha256}</code>
            <a href="https://github.com/appr1ciat1/tst_wocker" target="_blank" rel="noreferrer">報告層次參考</a>
            <a href="https://github.com/voidful/us_fddk" target="_blank" rel="noreferrer">研究程式與完整證據</a>
          </div>
        </section>

        <section className="section wrap faq-section">
          <div className="section-heading">
            <div><span>QUICK ANSWERS</span><h2>四個關鍵問題</h2></div>
          </div>
          <div className="faq-list">
            <details open><summary>長線穩定策略現在可以用實金嗎？</summary><p>不可以。歷史回測通過只准建立 Paper。前瞻仍是 {forward.forward_sessions}/{forward.minimum_sessions} 個新增交易日、{forward.filled_rebalances}/{forward.minimum_filled_rebalances} 次完成重新平衡，實金動作為 US$0。</p></details>
            <details><summary>為甚麼同時比較 SPY、純成長和公平持倉比率基準？</summary><p>SPY 回答是否勝過廣泛市場；純成長回答黃金是否犧牲上行；80% 成長／20% SHY 回答黃金是否只靠降低股票持倉比率製造較淺跌幅。三者缺一不可。</p></details>
            <details><summary>目前市場判讀是買入還是避險？</summary><p>此策略沒有短線看好或看淡訊號，只在每個完整月末把比例拉回 80/20。最新五年窗仍領先 SPY，但組合距歷史高位約 {pct(Math.abs(diagnostics.portfolio_underwater.current_drawdown), 1)}，不能解讀為保證反彈。</p></details>
            <details><summary>US$1,000 應該如何理解？</summary><p>US$800 VUG／US$200 GLD 是瀏覽器內的 Paper 比例示例，不是落盤指令。正式前瞻比較仍以 US$100,000 同起點、相同成本及相同交易日序列運作。</p></details>
          </div>
        </section>
        </div>

        <div id="short-term" data-strategy-panel="aggressive">
          <section className="hero aggressive-hero wrap">
            <div className="hero-copy">
              <div className="eyebrow-row">
                <span className="eyebrow">SHORT-TERM RETURN RESEARCH</span>
                <span className="status-chip research"><i /> 尚未啟動 PAPER</span>
              </div>
              <h1>短線高回報<br />大型股動量輪選</h1>
              <p className="hero-lead">
                最新一輪先凍結規則，再首次下載 Vanguard 十行業 ETF 做 20 年外部驗證。
                月度 Top-3 只錄得 <strong>{pct(sectorCandidate.metrics.cagr, 2)}</strong>，遠低於 QQQ 的 {pct(sectorBaselines.QQQ.cagr, 2)}；
                固定 20 日訊號亦沒有跨產品重現。
                <strong> 沒有可執行持倉、沒有 Paper 成交、實金動作為 US$0</strong>。
              </p>
              <div className="hero-actions">
                <a className="primary-button aggressive-button" href="#aggressive-evidence">查看第一輪結果</a>
                <a className="secondary-button" href="#aggressive-gates">查看啟動門檻</a>
              </div>
            </div>
            <aside className="decision-card aggressive-card" aria-label="短線高回報研究摘要">
              <div className="decision-head">
                <span>短線策略摘要</span>
                <b>外部驗證失敗 · 不追認參數</b>
              </div>
              <div className="capital-number"><small>讀者示例本金</small><strong>{money(readerCapital)}</strong></div>
              <div className="research-lock" aria-label="短線策略尚未開放配置">
                <span>目前短線配置</span><strong>US$0</strong><small>{sectorResearch.passed_gate_count} / {sectorResearch.required_gate_count} 道門檻；Paper 保持關閉</small>
              </div>
              <dl className="decision-list">
                <div><dt>外部 CAGR</dt><dd>{pct(sectorCandidate.metrics.cagr, 2)}／QQQ {pct(sectorBaselines.QQQ.cagr, 2)}</dd></div>
                <div><dt>硬傷</dt><dd>訊號 0/5／PBO {pct(sectorResearch.pbo_across_top_k_2_3_4.pbo, 1)}</dd></div>
                <div><dt>實金動作</dt><dd className="locked">US$0 · 不落盤</dd></div>
              </dl>
              <p>VGT 是事後最佳行業，不是新候選；網頁不展示任何最新買入名單。</p>
            </aside>
          </section>

          <section className="truth-strip aggressive-truth">
            <div className="wrap truth-grid">
              <article><span>外部 Top-3 CAGR</span><strong>{pct(sectorCandidate.metrics.cagr, 2)}</strong><small>凍結後首次計算</small></article>
              <article><span>QQQ 20 年年率化回報</span><strong>{pct(sectorBaselines.QQQ.cagr, 2)}</strong><small>正式高回報 baseline</small></article>
              <article><span>50 bps 成本 CAGR</span><strong>{pct(sectorCandidate.cost_sensitivity["50_bps"].cagr, 2)}</strong><small>回報轉負</small></article>
              <article><span>訊號層 NW t</span><strong>{sectorSignalComparison.newey_west.t_stat.toFixed(2)}</strong><small>五項門檻 0/5</small></article>
              <article><span>短線 Paper</span><strong>未啟動</strong><small>實金及 Paper 均為 0</small></article>
            </div>
          </section>

          <section className="section wrap" id="aggressive-evidence">
            <div className="section-heading">
              <div><span>LATEST EXTERNAL VALIDATION</span><h2>首次 Vanguard 十行業驗證：沒有重現</h2></div>
              <p>{sectorResearch.period.start} 至 {sectorResearch.period.end}；產品、規則、成本及 21 道門檻在首次共同下載前已凍結。</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict">
                <span>最新研究判斷</span>
                <h3>Top-3 較 QQQ 每年落後 {pp(Math.abs(sectorComparison.cagr_difference))}</h3>
                <p>候選亦低於相同股票持倉比率行業等權 {pp(Math.abs(sectorResearch.comparison_vs_matched_control.cagr_difference))}。最大跌幅較淺，但不能抵銷回報、成本、分段、滾動窗口及統計失敗。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>凍結順序</span><strong>{sectorDataPassed}/6 數據門檻</strong><p>協議提交、首次下載、快照雜湊、完整 OHLCV 及下一開市時序全部通過。</p></article>
                <article><span>經濟／統計門檻</span><strong>{sectorEconomicPassed}/15</strong><p>只通過最大跌幅限制；總計 {sectorResearch.passed_gate_count}/{sectorResearch.required_gate_count}，外部驗證失敗。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FAIR BASELINES</span><h3>候選、三個市場 ETF 與三個行業控制</h3></div>
              <p>同一快照、同一起訖日；候選及會重新平衡的控制採相同 10 bps 單邊換手成本。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Calmar</th><th>每年換手</th></tr></thead>
                <tbody>{sectorBaselineRows.map((row) => (
                  <tr key={row.label} className={row.featured ? "featured-row" : undefined}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.calmar)}</td><td>{multiple(row.metrics.turnover)}x</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>COST, WINDOWS &amp; STATISTICS</span><h3>不是單一 baseline 造成的失敗</h3></div>
              <p>規則固定後不以 Top-2／Top-4、較低成本或事後最佳行業取代唯一候選。</p>
            </div>
            <div className="short-evidence-grid">
              <article><span>成本敏感度</span><dl>{sectorCostRows.map((row) => <div key={row.label}><dt>{row.label}</dt><dd>{pct(row.metrics.cagr, 2)} CAGR</dd></div>)}</dl><p>50 bps 後累計回報亦為 {pct(sectorCandidate.cost_sensitivity["50_bps"].total_return, 1)}。</p></article>
              <article><span>固定前後十年</span><strong>{pp(sectorResearch.fixed_halves_vs_qqq.first.cagr_difference)}／{pp(sectorResearch.fixed_halves_vs_qqq.second.cagr_difference)}</strong><p>兩段均輸 QQQ；不是由單一年代拖累。</p></article>
              <article><span>滾動三年／五年</span><strong>{pct(sectorResearch.rolling_three_year_vs_qqq.cagr_win_fraction, 1)}／{pct(sectorResearch.rolling_five_year_vs_qqq.cagr_win_fraction, 1)}</strong><p>204 個三年窗、180 個五年窗；五年最佳窗口仍落後 {pp(Math.abs(sectorResearch.rolling_five_year_vs_qqq.best_cagr_difference))}。</p></article>
              <article><span>統計與過度配適</span><strong>NW t {sectorComparison.active_newey_west.t_stat.toFixed(2)} · PBO {pct(sectorResearch.pbo_across_top_k_2_3_4.pbo, 1)}</strong><p>相對 QQQ PSR {pct(sectorComparison.active_probabilistic_sharpe.probability, 2)}；6,141 次搜尋校正 DSR 約為零。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FIXED 20-DAY SIGNAL</span><h3>大型股的正面線索沒有跨產品重現</h3></div>
              <p>874 個每週事件，下一開市入場、固定持有 20 個交易日、每個事件組合扣來回 20 bps。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table signal-diagnostic-table">
                <thead><tr><th>Top-3 平均淨回報</th><th>合資格行業等權</th><th>配對差</th><th>勝出率</th><th>NW t</th><th>Bootstrap 95% 區間</th></tr></thead>
                <tbody><tr className="featured-row"><td>{pct(sectorSignal.net_return_summary.top3_mean, 2)}</td><td>{pct(sectorSignal.net_return_summary.eligible_equal_mean, 2)}</td><td>{pp(sectorSignalComparison.mean_difference)}</td><td>{pct(sectorSignalComparison.win_fraction, 1)}</td><td>{sectorSignalComparison.newey_west.t_stat.toFixed(2)}</td><td>{pp(sectorBootstrap.low)} 至 {pp(sectorBootstrap.high)}</td></tr></tbody>
              </table>
            </div>
            <div className="signal-diagnostic-verdict">
              <div><span>外部訊號診斷</span><strong>{sectorSignal.passed_gate_count}/{sectorSignal.required_gate_count} 通過</strong></div>
              <p>前／後十年配對差為 {pp(sectorSignal.fixed_halves_vs_eligible_equal.first.mean_difference)}／{pp(sectorSignal.fixed_halves_vs_eligible_equal.second.mean_difference)}，方向均為負。這直接削弱現時大型股池 20 日 Top-7 的正面線索。</p>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>ALL TEN SECTORS</span><h3>單一行業只作事後診斷</h3></div>
              <p>VGT 全期略勝 QQQ，但不能由全期冠軍反選成新策略；其餘九個行業全部低於 QQQ。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>ETF</th><th>行業</th><th>年率化回報</th><th>Sharpe</th><th>波幅</th><th>最大跌幅</th></tr></thead>
                <tbody>{sectorIndividualRows.map((row) => <tr key={row.ticker}><th><b>{row.ticker}</b><span>買入持有診斷</span></th><td>{row.label}</td><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td></tr>)}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>最新決策：</b><p>保留這個負結果，不改窗口、Top-K 或現金規則救援。短線 Paper 仍等候合格 point-in-time 個股成分與退市回報原樣重測；實金及 Paper 動作均為 US$0。</p></div>
            <div className="protocol-link"><span>外部產品協議與首次結果</span><div><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_SECTOR_ETF_PROTOCOL.md" target="_blank" rel="noreferrer">凍結協議</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_SECTOR_ETF_PRODUCT_MAPPING.md" target="_blank" rel="noreferrer">產品映射</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_SECTOR_ETF_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">完整報告</a></div></div>
          </section>

          <section className="section wrap" id="aggressive-sandbox">
            <div className="section-heading">
              <div><span>PRIOR STOCK SANDBOX</span><h2>較早大型股沙盒：表面跑贏也未證明輪選</h2></div>
              <p>{shortResearch.period.start} 至 {shortResearch.period.end}；月末訊號、下一開市執行、主要單邊成本 10 bps。</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict">
                <span>目前研究判斷</span>
                <h3>較 QQQ 高 {pp(shortComparison.cagr_difference)}，但較同股池漂移低 {pp(shortCandidate.metrics.cagr - shortBaselines.current_cohort_start_equal_then_drift.cagr)}</h3>
                <p>候選只比「現時完整股池每月等權」高 {pp(shortCandidate.metrics.cagr - shortBaselines.current_cohort_monthly_equal_weight.cagr)}，卻輸給起點等權後不再選股。這表示漂亮回報很可能主要來自今日仍然成功的公司，而非輪選規則。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>候選最大跌幅</span><strong>{pct(shortCandidate.metrics.max_drawdown, 1)}</strong><p>新冠急跌段達 {pct(shortResearch.stress_periods.covid_crash.results.frozen_candidate.return, 1)}，比 QQQ 的 {pct(shortResearch.stress_periods.covid_crash.results.QQQ.return, 1)} 更差。</p></article>
                <article><span>數據／經濟門檻</span><strong>{shortDataPassed}/7 · {shortEconomicPassed}/13</strong><p>逐期成分、退市回報、歷史行業及公司行動賬本仍未完成。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>HARD BASELINES</span><h3>候選、QQQ、SPY 與同股池控制</h3></div>
              <p>同一凍結快照、同一起訖日及相同 10 bps 口徑；同股池兩列亦有偏差，但能檢查輪選是否勝過更簡單做法。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Calmar</th><th>每年換手</th></tr></thead>
                <tbody>
                  <tr className="featured-row"><th><b>綜合動量輪選沙盒</b><span>現時 2026 股池倒推 · 不可投資</span></th><td>{pct(shortCandidate.metrics.cagr, 2)}</td><td>{multiple(shortCandidate.metrics.sharpe)}</td><td>{pct(shortCandidate.metrics.volatility, 1)}</td><td>{pct(shortCandidate.metrics.max_drawdown, 1)}</td><td>{multiple(shortCandidate.metrics.calmar)}</td><td>{multiple(shortCandidate.metrics.turnover)}x</td></tr>
                  <tr><th><b>QQQ 買入持有</b><span>正式高回報機會成本</span></th><td>{pct(shortBaselines.QQQ.cagr, 2)}</td><td>{multiple(shortBaselines.QQQ.sharpe)}</td><td>{pct(shortBaselines.QQQ.volatility, 1)}</td><td>{pct(shortBaselines.QQQ.max_drawdown, 1)}</td><td>{multiple(shortBaselines.QQQ.calmar)}</td><td>{multiple(shortBaselines.QQQ.turnover)}x</td></tr>
                  <tr><th><b>SPY 買入持有</b><span>廣泛大型股市場</span></th><td>{pct(shortBaselines.SPY.cagr, 2)}</td><td>{multiple(shortBaselines.SPY.sharpe)}</td><td>{pct(shortBaselines.SPY.volatility, 1)}</td><td>{pct(shortBaselines.SPY.max_drawdown, 1)}</td><td>{multiple(shortBaselines.SPY.calmar)}</td><td>{multiple(shortBaselines.SPY.turnover)}x</td></tr>
                  <tr><th><b>現時完整股池等權</b><span>每月重新平衡 · 有偏差</span></th><td>{pct(shortBaselines.current_cohort_monthly_equal_weight.cagr, 2)}</td><td>{multiple(shortBaselines.current_cohort_monthly_equal_weight.sharpe)}</td><td>{pct(shortBaselines.current_cohort_monthly_equal_weight.volatility, 1)}</td><td>{pct(shortBaselines.current_cohort_monthly_equal_weight.max_drawdown, 1)}</td><td>{multiple(shortBaselines.current_cohort_monthly_equal_weight.calmar)}</td><td>{multiple(shortBaselines.current_cohort_monthly_equal_weight.turnover)}x</td></tr>
                  <tr><th><b>現時完整股池漂移</b><span>起點等權後不再選股 · 有偏差</span></th><td>{pct(shortBaselines.current_cohort_start_equal_then_drift.cagr, 2)}</td><td>{multiple(shortBaselines.current_cohort_start_equal_then_drift.sharpe)}</td><td>{pct(shortBaselines.current_cohort_start_equal_then_drift.volatility, 1)}</td><td>{pct(shortBaselines.current_cohort_start_equal_then_drift.max_drawdown, 1)}</td><td>{multiple(shortBaselines.current_cohort_start_equal_then_drift.calmar)}</td><td>{multiple(shortBaselines.current_cohort_start_equal_then_drift.turnover)}x</td></tr>
                </tbody>
              </table>
            </div>
            <div className="comparison-caveat">
              <b>為何 21.52% 仍不開 Paper：</b>
              <p>現時名單不知道 2006 年當時可買什麼，也漏掉退市、被收購及失敗公司；同股池漂移更達 {pct(shortBaselines.current_cohort_start_equal_then_drift.cagr, 2)}。這個沙盒只說明假說值得以合格數據重測，不代表可賺取相同回報。</p>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>COST, WINDOWS &amp; CRISES</span><h3>高成本、固定分段與壓力期</h3></div>
              <p>成本沒有立即消滅表面回報，但危機及統計檢驗顯示風險遠未解決。</p>
            </div>
            <div className="short-evidence-grid">
              <article>
                <span>成本敏感度</span>
                <dl>{shortCostRows.map((row) => <div key={row.label}><dt>{row.label}</dt><dd>{pct(row.metrics.cagr, 2)} CAGR</dd></div>)}</dl>
                <p>50 bps 後仍較 QQQ 高 {pp(shortCandidate.cost_sensitivity["50_bps"].cagr - shortBaselines.QQQ.cagr)}，但數據偏差沒有因成本測試而消失。</p>
              </article>
              <article>
                <span>固定十年分段</span>
                <strong>{pp(shortResearch.fixed_halves_vs_qqq.first.cagr_difference)}／{pp(shortResearch.fixed_halves_vs_qqq.second.cagr_difference)}</strong>
                <p>前十年／後十年對 QQQ；滾動三年 {pct(shortResearch.rolling_three_year_vs_qqq.cagr_win_fraction, 1)} 勝出，最差仍落後 {pp(shortResearch.rolling_three_year_vs_qqq.worst_cagr_difference)}。</p>
              </article>
              <article>
                <span>統計與搜尋校正</span>
                <strong>t {shortComparison.active_newey_west.t_stat.toFixed(2)} · DSR {pct(shortComparison.active_global_deflated_sharpe.probability, 1)}</strong>
                <p>未校正 PSR {pct(shortComparison.active_probabilistic_sharpe.probability, 1)}，但 {shortResearch.global_search_trials.toLocaleString("zh-HK")} 次搜尋後失效；四版本 PBO {pct(shortResearch.pbo_across_four_current_cohort_variants.pbo, 1)}。</p>
              </article>
              <article>
                <span>三段壓力期</span>
                <strong>{pct(shortResearch.stress_periods.global_financial_crisis.results.frozen_candidate.return, 1)} · {pct(shortResearch.stress_periods.covid_crash.results.frozen_candidate.return, 1)} · {pct(shortResearch.stress_periods.rate_hike_2022.results.frozen_candidate.return, 1)}</strong>
                <p>金融海嘯／新冠急跌／2022。2022 防守較佳，不能掩蓋新冠段比 QQQ 多跌逾 11 個百分點。</p>
              </article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>TAIWAN-TO-U.S. ABLATION</span><h3>台股短窗規則直譯：三版均未勝 QQQ</h3></div>
              <p>只逐層測 20 日動量、60 日趨勢、SPY 環境與相關性濾網；不搬用台股槓桿、止蝕、止賺或 headline 回報。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>直譯版本</th><th>年率化回報</th><th>Sharpe</th><th>最大跌幅</th><th>每年換手</th><th>對 QQQ</th></tr></thead>
                <tbody>{shortTranslationRows.map((row) => (
                  <tr key={row.key}><th><b>{row.label}</b><span>每週 Top-7 · 現時股池沙盒</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.sharpe)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.turnover)}x</td><td className="negative-number">{pp(row.metrics.cagr - shortBaselines.QQQ.cagr)}</td></tr>
                ))}</tbody>
              </table>
            </div>
            <div className="subsection-heading stock-heading">
              <div><span>SIGNAL-LAYER DIAGNOSTIC</span><h3>拆走止賺止蝕後，20 日排序有正差</h3></div>
              <p>協議在首次計算前提交；每週訊號於下一開市進場，固定持有，所有事件組合扣來回 20 bps。這只回答訊號層問題，不是可落盤策略。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table signal-diagnostic-table">
                <thead><tr><th>固定持有期</th><th>事件</th><th>Top-7 平均淨回報</th><th>合資格池等權</th><th>配對差</th><th>NW t</th><th>Bootstrap 95% 區間</th></tr></thead>
                <tbody>{shortSignalRows.map((row) => {
                  const comparison = row.result.comparisons.eligible_equal;
                  const bootstrapRange = row.result.moving_block_bootstrap_mean_difference_vs_eligible_equal;
                  return (
                    <tr key={row.label} className={row.result.holding_sessions === 20 ? "featured-row" : undefined}>
                      <th><b>{row.label}</b><span>每週 Top-7 · 固定離場</span></th>
                      <td>{row.result.events}</td>
                      <td>{pct(row.result.net_return_summary.top7_mean, 2)}</td>
                      <td>{pct(row.result.net_return_summary.eligible_equal_mean, 2)}</td>
                      <td>{pp(comparison.mean_difference)}</td>
                      <td>{comparison.newey_west.t_stat.toFixed(2)}</td>
                      <td>{pp(bootstrapRange.low)} 至 {pp(bootstrapRange.high)}</td>
                    </tr>
                  );
                })}</tbody>
              </table>
            </div>
            <div className="signal-diagnostic-verdict">
              <div><span>20 日主要診斷</span><strong>{shortSignal.passed_primary_gate_count}/{shortSignal.required_primary_gate_count} 表面通過</strong></div>
              <p>Top-7 每個 20 日事件平均較當日合資格池高 {pp(shortSignalPrimary.comparisons.eligible_equal.mean_difference)}，NW t {shortSignalPrimary.comparisons.eligible_equal.newey_west.t_stat.toFixed(2)}，配對勝率 {pct(shortSignalPrimary.comparisons.eligible_equal.win_fraction, 1)}；前後十年平均差為 {pp(shortSignalPrimary.fixed_halves_vs_eligible_equal.first.mean_difference)}／{pp(shortSignalPrimary.fixed_halves_vs_eligible_equal.second.mean_difference)}。但樣本仍用今日成功公司倒推，不能據此買入或開 Paper。</p>
            </div>
            <div className="reference-projects">
              <a href="https://github.com/appr1ciat1/tst_wocker" target="_blank" rel="noreferrer"><b>tst_wocker</b><span>橫斷面動量／市場環境</span></a>
              <a href="https://github.com/appr1ciat1/tw-block-warrant" target="_blank" rel="noreferrer"><b>tw-block-warrant</b><span>研究與每日訊號分層</span></a>
              <a href="https://github.com/appr1ciat1/tst_wocker_filter_lab" target="_blank" rel="noreferrer"><b>filter_lab</b><span>凍結快照／負結果／池 baseline</span></a>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>INDIVIDUAL STOCK RISK DIAGNOSTICS</span><h3>12 隻現時大型股的完整 20 年比較</h3></div>
              <p>這是倖存者偏差診斷，只量化個股上行及崩跌範圍；這些公司不能反推成 2006 年選股名單。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table stock-table">
                <thead><tr><th>個股</th><th>行業</th><th>年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Beta</th><th>長線策略五年窗勝率</th></tr></thead>
                <tbody>{stockComparisons.map((row) => (
                  <tr key={row.symbol}><th><b>{row.symbol}</b><span>{row.name}</span></th><td>{sectorLabels[row.sector] ?? row.sector}</td><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.excess_sharpe_vs_shy)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.beta_to_spy)}</td><td>{pct(row.candidate_rolling_five_year_win_fraction, 1)}</td></tr>
                ))}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>不能直接照表買入：</b><p>NVDA 年率化回報達 {pct(nvdaDiagnostic.metrics.cagr, 1)}，但最大跌幅亦達 {pct(nvdaDiagnostic.metrics.max_drawdown, 1)}；AMD 更曾達 {pct(amdDiagnostic.metrics.max_drawdown, 1)}。今日仍在大型股名單本身已包含未來資訊。</p></div>
          </section>

          <section className="section aggressive-method" id="aggressive-gates">
            <div className="wrap">
              <div className="section-heading">
                <div><span>GATE-BY-GATE DECISION</span><h2>最新外部驗證只過 {sectorResearch.passed_gate_count} / {sectorResearch.required_gate_count} 道</h2></div>
                <p>六項數據門檻全部通過，但十五項經濟及統計門檻只過一項；不以較淺跌幅掩蓋整體失敗。</p>
              </div>
              <div className="signal-formula" aria-label="最新外部驗證凍結規格">
                <article><span>20D</span><b>短期相對強勢</b><p>只按十個行業過去 20 日總回報排序。</p></article>
                <article><span>60D</span><b>趨勢資格</b><p>收市價須高於 60 日簡單平均線。</p></article>
                <article><span>TOP 3</span><b>固定三個槽位</b><p>每個槽位 1/3，不事後改 Top-K。</p></article>
                <article><span>SHY</span><b>未用比例</b><p>不足三個合資格行業時不放大持倉。</p></article>
              </div>

              <div className="short-gate-grid">
                <article className="waiting"><span>01</span><div><b>先凍結、後下載及完整 OHLCV</b><strong>6/6 通過</strong><p>數據時序、雜湊與下一開市成交時鐘均可重現。</p></div></article>
                <article className="failed"><span>02</span><div><b>QQQ 高回報 baseline</b><strong>失敗</strong><p>候選 {pct(sectorCandidate.metrics.cagr, 2)}，QQQ {pct(sectorBaselines.QQQ.cagr, 2)}。</p></div></article>
                <article className="failed"><span>03</span><div><b>三個行業控制 baseline</b><strong>全數失敗</strong><p>候選同時落後 matched、月度等權及起點等權後漂移。</p></div></article>
                <article className="failed"><span>04</span><div><b>成本、固定十年及滾動窗口</b><strong>失敗</strong><p>50 bps CAGR {pct(sectorCandidate.cost_sensitivity["50_bps"].cagr, 2)}；五年窗口勝率 0%。</p></div></article>
                <article className="failed"><span>05</span><div><b>NW、DSR、PBO 與訊號層</b><strong>失敗</strong><p>NW t {sectorComparison.active_newey_west.t_stat.toFixed(2)}；PBO {pct(sectorResearch.pbo_across_top_k_2_3_4.pbo, 1)}；訊號 0/5。</p></div></article>
                <article className="failed"><span>06</span><div><b>前瞻 Paper</b><strong>未啟動</strong><p>入口全過後才由全現金累積 252 日及 12 次月度輪選，不回填成交。</p></div></article>
              </div>
              <div className="data-source-decision">
                <div><span>DATA SOURCE AUDIT</span><b>免費歷史名單不等於無偏差價格</b></div>
                <p>公開成分名單沒有退市總回報；Yahoo 亦不能完整覆蓋退出及改名股票。正式下一輪只接受 CRSP／WRDS 或 Norgate 等可同時提供逐日成分與退市回報的來源，未取得權限前不拼湊假 20 年結果。</p>
                <div className="data-source-links"><a href="https://github.com/hanshof/sp500_constituents" target="_blank" rel="noreferrer">免費名單稽核</a><a href="https://norgatedata.com/data-content-tables.php" target="_blank" rel="noreferrer">Norgate 覆蓋</a><a href="https://www.crsp.org/crsp_pdf/crsp-historical-indexes-guide/" target="_blank" rel="noreferrer">CRSP 指南</a></div>
              </div>
              <p className="aggressive-final-decision"><b>目前決策：</b>外部產品驗證已推翻短期排序可直接泛化的假設，不開短線 Paper。下一步只補逐期 S&amp;P 500 成分、退市／收購回報、歷史行業及公司行動賬本，再按既有個股凍結規則重跑一次；實金及 Paper 動作均為 US$0。</p>
              <div className="protocol-link"><span>三輪證據完整保留 · 最新外部結果優先</span><div><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_SECTOR_ETF_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">最新外部報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_SECTOR_ETF_PROTOCOL.md" target="_blank" rel="noreferrer">外部協議</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_HIGH_RETURN_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">三輪總報告</a></div></div>
            </div>
          </section>
        </div>
        </StrategyTabs>
      </main>

      <footer>
        <div className="wrap footer-grid">
          <div><b>US FDDK</b><p>長線穩定與短線高回報兩條獨立研究線。</p></div>
          <div><span>最新數據</span><b>{data.data_through}</b></div>
          <div><span>公開狀態</span><b>Research + Paper-only</b></div>
          <div><span>免責聲明</span><p>歷史表現不保證未來結果；本頁不構成投資建議或實金落盤指令。</p></div>
        </div>
      </footer>
    </>
  );
}
