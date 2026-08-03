import type { Metadata } from "next";
import FreshnessGuard from "./FreshnessGuard";
import PaperAllocationLab from "./PaperAllocationLab";
import StrategyTabs from "./StrategyTabs";
import V25ForwardBoard from "./V25ForwardBoard";
import data from "../data/trading-data.json";
import shortResearch from "../data/short-term-research.json";
import frenchResearch from "../data/short-term-french-30-industry.json";
import priorReturnContract from "../data/short-term-french-prior-return-contract.json";
import priorReturnRepair from "../data/short-term-french-prior-return-schema-repair.json";
import sizePriorResearch from "../data/short-term-french-size-prior.json";

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
const frenchCandidate = frenchResearch.frozen_candidate;
const frenchPrimary = frenchResearch.primary_external_period;
const frenchRecent = frenchResearch.recent_confirmation_period;
const frenchPrimaryEvent = frenchPrimary.fixed_20_day_event;
const frenchRecentEvent = frenchRecent.fixed_20_day_event;
const frenchPrimaryMarket = frenchPrimary.comparisons.market;
const frenchPrimaryEqual = frenchPrimary.comparisons.industry_monthly_equal;
const frenchRecentMarket = frenchRecent.comparisons.market;
const frenchRecentEqual = frenchRecent.comparisons.industry_monthly_equal;
const frenchCostRows = ["10_bps", "25_bps", "50_bps"].map((key) => ({
  label: key.replace("_", " "),
  metrics: frenchCandidate.cost_sensitivity_full_history[key as keyof typeof frenchCandidate.cost_sensitivity_full_history],
}));
const frenchPrimaryRows = [
  { label: "6–1 行業動量 Top-3", detail: "唯一凍結候選 · 10 bps", metrics: frenchPrimary.candidate_metrics, featured: true },
  { label: "French 美國市場", detail: "Mkt-RF + RF", metrics: frenchPrimary.baseline_metrics.market },
  { label: "30 行業月度等權", detail: "不排序、每月回復等權", metrics: frenchPrimary.baseline_metrics.industry_monthly_equal },
  { label: "30 行業起點等權後漂移", detail: "不排序、不再輪替", metrics: frenchPrimary.baseline_metrics.industry_start_equal_then_drift },
];
const frenchRecentRows = [
  { label: "6–1 行業動量 Top-3", detail: "唯一凍結候選 · 10 bps", metrics: frenchRecent.candidate_metrics, featured: true },
  { label: "French 美國市場", detail: "Mkt-RF + RF", metrics: frenchRecent.baseline_metrics.market },
  { label: "30 行業月度等權", detail: "不排序、每月回復等權", metrics: frenchRecent.baseline_metrics.industry_monthly_equal },
  { label: "30 行業起點等權後漂移", detail: "不排序、不再輪替", metrics: frenchRecent.baseline_metrics.industry_start_equal_then_drift },
];
const frenchStressRows = [
  { label: "1973–1974 石油危機", result: frenchResearch.stress_periods["1973_1974"] },
  { label: "1987 股災", result: frenchResearch.stress_periods["1987_crash"] },
  { label: "2000–2002 科網泡沫", result: frenchResearch.stress_periods.dotcom },
  { label: "2008–2009 金融海嘯", result: frenchResearch.stress_periods.gfc },
  { label: "2020 新冠衝擊", result: frenchResearch.stress_periods.covid_2020 },
  { label: "2022 加息衝擊", result: frenchResearch.stress_periods.rate_shock_2022 },
];
const priorRepairCandidate = priorReturnRepair.frozen_candidate;
const priorRepairPrimary = priorReturnRepair.primary_external_period;
const priorRepairRecent = priorReturnRepair.recent_confirmation_period;
const priorRepairRecentMarket = priorRepairRecent.comparisons.market;
const priorRepairRecentEqual = priorRepairRecent.comparisons.decile_equal;
const priorRepairPrimaryRows = [
  { label: "VW Hi PRIOR 1–1", detail: "唯一凍結候選 · 每月完整換倉 · 10 bps", metrics: priorRepairPrimary.candidate_metrics, featured: true },
  { label: "French 美國市場", detail: "Mkt-RF + RF · 買入持有", metrics: priorRepairPrimary.baseline_metrics.market },
  { label: "VW 十分位等權", detail: "同一 short-term 母體 · 每月等權", metrics: priorRepairPrimary.baseline_metrics.decile_equal },
  { label: "VW Lo PRIOR 1–1", detail: "短期反轉對照 · 每月完整換倉", metrics: priorRepairPrimary.baseline_metrics.lo_prior_1_0 },
  { label: "VW Hi PRIOR 12–2", detail: "較慢橫斷面動量 · 每月完整換倉", metrics: priorRepairPrimary.baseline_metrics.long_momentum_hi_12_2 },
];
const priorRepairRecentRows = [
  { label: "VW Hi PRIOR 1–1", detail: "唯一凍結候選 · 每月完整換倉 · 10 bps", metrics: priorRepairRecent.candidate_metrics, featured: true },
  { label: "French 美國市場", detail: "Mkt-RF + RF · 買入持有", metrics: priorRepairRecent.baseline_metrics.market },
  { label: "VW 十分位等權", detail: "同一 short-term 母體 · 每月等權", metrics: priorRepairRecent.baseline_metrics.decile_equal },
  { label: "VW Lo PRIOR 1–1", detail: "短期反轉對照 · 每月完整換倉", metrics: priorRepairRecent.baseline_metrics.lo_prior_1_0 },
  { label: "VW Hi PRIOR 12–2", detail: "較慢橫斷面動量 · 每月完整換倉", metrics: priorRepairRecent.baseline_metrics.long_momentum_hi_12_2 },
];
const priorRepairSensitivityRows = [
  { label: "VW Hi PRIOR 1–1", metrics: priorReturnRepair.sensitivity_full_history_metrics_10bps.vw_hi_prior_1_0 },
  { label: "VW Top-2", metrics: priorReturnRepair.sensitivity_full_history_metrics_10bps.vw_top_2 },
  { label: "VW Top-3", metrics: priorReturnRepair.sensitivity_full_history_metrics_10bps.vw_top_3 },
  { label: "VW 線性全池傾斜", metrics: priorReturnRepair.sensitivity_full_history_metrics_10bps.vw_linear_tilt },
  { label: "VW 平方全池傾斜", metrics: priorReturnRepair.sensitivity_full_history_metrics_10bps.vw_square_tilt },
  { label: "EW Hi PRIOR 1–1", metrics: priorReturnRepair.sensitivity_full_history_metrics_10bps.ew_hi_prior_1_0 },
];
const priorRepairStressRows = [
  { label: "1973–1974 石油危機", result: priorReturnRepair.stress_periods["1973_1974"] },
  { label: "1987 股災", result: priorReturnRepair.stress_periods["1987_crash"] },
  { label: "2000–2002 科網泡沫", result: priorReturnRepair.stress_periods.dotcom },
  { label: "2008–2009 金融海嘯", result: priorReturnRepair.stress_periods.gfc },
  { label: "2020 新冠衝擊", result: priorReturnRepair.stress_periods.covid_2020 },
  { label: "2022 加息衝擊", result: priorReturnRepair.stress_periods.rate_shock_2022 },
];
const sizePriorPrimary = sizePriorResearch.primary_external_period;
const sizePriorRecent = sizePriorResearch.recent_confirmation_period;
const sizePriorRecentMarket = sizePriorRecent.comparisons.market;
const sizePriorRecentBigEqual = sizePriorRecent.comparisons.big_row_equal;
const sizePriorPrimaryRows = [
  { label: "Big Hi PRIOR 1–1", detail: "唯一凍結候選 · 大型股短窗贏家 · 10 bps", metrics: sizePriorPrimary.candidate_metrics, featured: true },
  { label: "French 美國市場", detail: "Mkt-RF + RF · 買入持有", metrics: sizePriorPrimary.baseline_metrics.market },
  { label: "大型股 prior 等權", detail: "同一 Size 5 母體 · 五組每月等權", metrics: sizePriorPrimary.baseline_metrics.big_row_equal },
  { label: "全 25 cells 等權", detail: "五個 size × 五個 prior", metrics: sizePriorPrimary.baseline_metrics.all_25_equal },
  { label: "Big Lo PRIOR", detail: "大型股短窗輸家 · 反方向控制", metrics: sizePriorPrimary.baseline_metrics.big_lo_prior },
  { label: "Hi PRIOR 12–2", detail: "長窗動量控制", metrics: sizePriorPrimary.baseline_metrics.long_momentum_hi_12_2 },
];
const sizePriorRecentRows = [
  { label: "Big Hi PRIOR 1–1", detail: "唯一凍結候選 · 大型股短窗贏家 · 10 bps", metrics: sizePriorRecent.candidate_metrics, featured: true },
  { label: "QQQ", detail: "實際產品機會成本 · 買入持有", metrics: sizePriorRecent.baseline_metrics.QQQ },
  { label: "French 美國市場", detail: "Mkt-RF + RF · 買入持有", metrics: sizePriorRecent.baseline_metrics.market },
  { label: "大型股 prior 等權", detail: "同一 Size 5 母體 · 五組每月等權", metrics: sizePriorRecent.baseline_metrics.big_row_equal },
  { label: "全 25 cells 等權", detail: "五個 size × 五個 prior", metrics: sizePriorRecent.baseline_metrics.all_25_equal },
  { label: "Big Lo PRIOR", detail: "大型股短窗輸家 · 反方向控制", metrics: sizePriorRecent.baseline_metrics.big_lo_prior },
  { label: "Hi PRIOR 12–2", detail: "長窗動量控制", metrics: sizePriorRecent.baseline_metrics.long_momentum_hi_12_2 },
];

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
                <span className="eyebrow">SHORT-TERM RETURN RESEARCH · SIZE-CONDITIONED FIRST-SEEN VALIDATION</span>
                <span className="status-chip research"><i /> 尚未啟動 PAPER</span>
              </div>
              <h1>短線高回報<br />短窗贏家壓力測試</h1>
              <p className="hero-lead">
                最新一輪在首次下載前凍結 `Big Hi PRIOR 1–1`，用 CRSP／Kenneth French 的 25 個 Size × Prior cells 檢查短窗贏家是否只是假象。
                數據合約通過 <strong>{sizePriorResearch.gate_breakdown.data}</strong>，但整體只有 <strong>{sizePriorResearch.passed_gate_count}/{sizePriorResearch.required_gate_count}</strong>：
                1963–2005 年率化回報 {pct(sizePriorPrimary.candidate_metrics.cagr, 2)}，2006–2026 為 {pct(sizePriorRecent.candidate_metrics.cagr, 2)}，近期更遠低於 QQQ 的 {pct(sizePriorRecent.baseline_metrics.QQQ.cagr, 2)}。
                <strong>這是首次未見機制驗證，但學術 cells 仍不可落盤；Paper、持倉及實金動作均為 US$0</strong>。
              </p>
              <div className="hero-actions">
                <a className="primary-button aggressive-button" href="#size-prior-diagnostic">查看最新 14/44 驗證</a>
                <a className="secondary-button" href="#prior-return-diagnostic">查看上一輪 11/38</a>
                <a className="secondary-button" href="#aggressive-evidence">查看 French 30 獨立結果</a>
                <a className="secondary-button" href="#aggressive-gates">查看啟動門檻</a>
              </div>
            </div>
            <aside className="decision-card aggressive-card" aria-label="短線高回報研究摘要">
              <div className="decision-head">
                <span>短線策略摘要</span>
                <b>{sizePriorResearch.passed_gate_count}/{sizePriorResearch.required_gate_count} · 經濟驗證失敗</b>
              </div>
              <div className="capital-number"><small>讀者示例本金</small><strong>{money(readerCapital)}</strong></div>
              <div className="research-lock" aria-label="短線策略尚未開放配置">
                <span>目前短線配置</span><strong>US$0</strong><small>{sizePriorResearch.gate_breakdown.primary} · {sizePriorResearch.gate_breakdown.recent}；Paper 保持關閉</small>
              </div>
              <dl className="decision-list">
                <div><dt>主要期 CAGR</dt><dd>{pct(sizePriorPrimary.candidate_metrics.cagr, 2)}／市場 {pct(sizePriorPrimary.baseline_metrics.market.cagr, 2)}</dd></div>
                <div><dt>近期 CAGR</dt><dd>{pct(sizePriorRecent.candidate_metrics.cagr, 2)}／QQQ {pct(sizePriorRecent.baseline_metrics.QQQ.cagr, 2)}</dd></div>
                <div><dt>硬傷</dt><dd>近期 50 bps {pct(sizePriorRecent.candidate_50bps_metrics.cagr, 2)}／PBO {pct(sizePriorResearch.pbo.recent.pbo, 1)}</dd></div>
                <div><dt>實金動作</dt><dd className="locked">US$0 · 不落盤</dd></div>
              </dl>
              <p>US$1,000 複利數字只解釋歷史尺度，不包括通脹、稅項及真實買賣差價，亦不是預測。</p>
            </aside>
          </section>

          <section className="truth-strip aggressive-truth">
            <div className="wrap truth-grid">
              <article><span>1963–2005 CAGR</span><strong>{pct(sizePriorPrimary.candidate_metrics.cagr, 2)}</strong><small>市場 {pct(sizePriorPrimary.baseline_metrics.market.cagr, 2)}</small></article>
              <article><span>2006–2026 CAGR</span><strong>{pct(sizePriorRecent.candidate_metrics.cagr, 2)}</strong><small>QQQ {pct(sizePriorRecent.baseline_metrics.QQQ.cagr, 2)}</small></article>
              <article><span>近期 50 bps CAGR</span><strong>{pct(sizePriorRecent.candidate_50bps_metrics.cagr, 2)}</strong><small>完整換倉成本後轉負</small></article>
              <article><span>近期勝市場 60 月窗</span><strong>{pct(sizePriorRecent.rolling_60m_vs_market.cagr_win_fraction, 1)}</strong><small>合格線 60%</small></article>
              <article><span>數據／經濟門檻</span><strong>{sizePriorResearch.gate_breakdown.data} · {sizePriorResearch.passed_gate_count}/{sizePriorResearch.required_gate_count}</strong><small>首次未見、仍判定失敗</small></article>
              <article><span>短線 Paper</span><strong>未啟動</strong><small>實金及 Paper 均為 0</small></article>
            </div>
          </section>

          <section className="section wrap" id="size-prior-diagnostic">
            <div className="section-heading">
              <div><span>FIRST-SEEN SIZE-CONDITIONED VALIDATION · ROUND 7</span><h2>大型股短窗贏家：數據 10/10，經濟只過 14/44</h2></div>
              <p>唯一候選、25 cells、成本、時期、QQQ／SPY 與同母體基準、17＋17 道門檻及 6,175 次搜尋校正在首次官方下載前已凍結。</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict">
                <span>最新研究判斷</span>
                <h3>大型股隔離後仍跑輸市場；近期更大幅落後 QQQ</h3>
                <p>主要期候選較市場低 {pp(sizePriorPrimary.candidate_metrics.cagr - sizePriorPrimary.baseline_metrics.market.cagr)}；近期較市場低 {pp(sizePriorRecent.candidate_metrics.cagr - sizePriorRecent.baseline_metrics.market.cagr)}，較 QQQ 低 {pp(sizePriorRecent.candidate_metrics.cagr - sizePriorRecent.baseline_metrics.QQQ.cagr)}。不是由小型股污染就能解釋或救援。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>門檻分解</span><strong>{sizePriorResearch.gate_breakdown.data} · {sizePriorResearch.gate_breakdown.primary} · {sizePriorResearch.gate_breakdown.recent}</strong><p>主要期只過 PBO；近期只過全池等權、Big Lo 及最大跌幅限制。</p></article>
                <article><span>證據與資金界線</span><strong>首次未見 · US$0</strong><p>數據合約有效，但 French cells 不是證券；Paper、選股名單及實金均維持關閉。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PRIMARY EXTERNAL PERIOD · 1963–2005</span><h3>長歷史：短窗贏家落後所有主要回報基準</h3></div>
              <p>所有每月重組路徑以相同 10 bps 單邊成本處理；French 市場只扣首次買入成本。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Calmar</th><th>US$1,000 期末值</th></tr></thead>
                <tbody>{sizePriorPrimaryRows.map((row) => (
                  <tr key={row.label} className={row.featured ? "featured-row" : undefined}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.excess_sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.calmar)}</td><td>{money(row.metrics.hypothetical_1000_usd_end)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>兩半一致失敗：</b><p>1963–1984 較市場低 {pp(sizePriorPrimary.fixed_splits["1963_to_1984"].edge_vs_market)}，1985–2005 低 {pp(sizePriorPrimary.fixed_splits["1985_to_2005"].edge_vs_market)}；60 月窗勝市場只有 {pct(sizePriorPrimary.rolling_60m_vs_market.cagr_win_fraction, 1)}。</p></div>

            <div className="subsection-heading stock-heading">
              <div><span>RECENT CONFIRMATION · 2006–2026</span><h3>近期：只勝弱基準，QQQ 明顯較好</h3></div>
              <p>QQQ／SPY 使用既有經調整產品價格快照，只作 2006 後機會成本；沒有用現時成份股回推歷史。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Calmar</th><th>US$1,000 期末值</th></tr></thead>
                <tbody>{sizePriorRecentRows.map((row) => (
                  <tr key={row.label} className={row.featured ? "featured-row" : undefined}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.excess_sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.calmar)}</td><td>{money(row.metrics.hypothetical_1000_usd_end)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>Regime 不穩定：</b><p>2006–2015 候選只得 {pct(sizePriorRecent.fixed_splits["2006_to_2015"].candidate_cagr, 2)}，較市場低 {pp(sizePriorRecent.fixed_splits["2006_to_2015"].edge_vs_market)}；2016 後才較市場高 {pp(sizePriorRecent.fixed_splits["2016_to_end"].edge_vs_market)}。後段反彈不能覆蓋固定前段。</p></div>

            <div className="subsection-heading stock-heading">
              <div><span>SIZE × DIRECTION</span><h3>早期五個 size 全部是反轉；近期才轉為部分延續</h3></div>
              <p>Hi−Lo 為同一 size 贏家 CAGR 減輸家 CAGR。這是機制拆解，不是事後改買最好的 size。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>Size 五分位</th><th>1963–2005 Hi−Lo</th><th>2006–2026 Hi−Lo</th><th>近期 Hi CAGR</th><th>近期 Hi 最大跌幅</th></tr></thead>
                <tbody>{sizePriorResearch.size_direction_diagnostic.recent.map((row, index) => (
                  <tr key={row.size_quintile}><th><b>Size {row.size_quintile}</b><span>{row.size_quintile === 5 ? "大型股" : "由小至大"}</span></th><td>{pp(sizePriorResearch.size_direction_diagnostic.primary[index].high_minus_low_cagr)}</td><td>{pp(row.high_minus_low_cagr)}</td><td>{pct(row.high_prior_cagr, 2)}</td><td>{pct(row.high_prior_max_drawdown, 1)}</td></tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>COST, WINDOWS &amp; STATISTICS</span><h3>成本容忍度不足，統計沒有確認</h3></div>
              <p>Newey–West 固定月度 lag 3；PSR／DSR 以每年 12 期計算；PBO family 包括全部 25 cells 及事前大型股傾斜。</p>
            </div>
            <div className="short-evidence-grid">
              <article><span>全歷史成本</span><dl><div><dt>10 bps</dt><dd>{pct(sizePriorResearch.frozen_candidate.cost_sensitivity_full_history["10_bps"].cagr, 2)}</dd></div><div><dt>25 bps</dt><dd>{pct(sizePriorResearch.frozen_candidate.cost_sensitivity_full_history["25_bps"].cagr, 2)}</dd></div><div><dt>50 bps</dt><dd>{pct(sizePriorResearch.frozen_candidate.cost_sensitivity_full_history["50_bps"].cagr, 2)}</dd></div></dl><p>年換手約 {multiple(sizePriorResearch.frozen_candidate.full_history_metrics_10bps.annual_turnover)}x；完整換倉成本是重要反證。</p></article>
              <article><span>近期成本 break-even</span><strong>市場 {sizePriorRecent.cost_break_even_vs_baselines.market.one_way_bps.toFixed(2)} · 大型股等權 {sizePriorRecent.cost_break_even_vs_baselines.big_row_equal.one_way_bps.toFixed(2)} bps</strong><p>凍結門檻為 50 bps；兩者都遠低於要求。</p></article>
              <article><span>近期 60 月勝率</span><strong>市場 {pct(sizePriorRecent.rolling_60m_vs_market.cagr_win_fraction, 1)} · 大型股等權 {pct(sizePriorRecent.rolling_60m_vs_big_row_equal.cagr_win_fraction, 1)}</strong><p>相對市場中位 CAGR 差 {pp(sizePriorRecent.rolling_60m_vs_market.median_cagr_difference)}。</p></article>
              <article><span>近期主動統計</span><strong>NW t {sizePriorRecentMarket.newey_west.t_stat.toFixed(2)}／{sizePriorRecentBigEqual.newey_west.t_stat.toFixed(2)}</strong><p>對市場／大型股等權；PSR {pct(sizePriorRecentMarket.active_probabilistic_sharpe.probability, 2)}／{pct(sizePriorRecentBigEqual.active_probabilistic_sharpe.probability, 2)}。</p></article>
              <article><span>DSR 與 PBO</span><strong>DSR {pct(sizePriorRecentMarket.active_global_deflated_sharpe.probability, 4)} · PBO {pct(sizePriorResearch.pbo.recent.pbo, 1)}</strong><p>6,175 次搜尋校正後不足；近期 PBO 高於 20% 上限。</p></article>
              <article><span>五因子解釋</span><strong>Alpha {pct(sizePriorResearch.factor_regression_full_history.annualized_alpha, 2)}</strong><p>市場 beta {multiple(sizePriorResearch.factor_regression_full_history.market_beta)}、ST_Rev beta {multiple(sizePriorResearch.factor_regression_full_history.short_term_reversal_beta)}、R² {pct(sizePriorResearch.factor_regression_full_history.r_squared, 1)}。</p></article>
            </div>

            <div className="data-source-decision">
              <div><span>DECISION BOUNDARY</span><b>首次數據 10/10，但經濟只有 14/44</b></div>
              <p>這輪比現時成份股倒推更可靠，仍只到機制層。沒有逐股 point-in-time 成分、退市／收購回報、公司行動、流動性及精確成交成本，所以不建立短線 Paper，不輸出股票名單。</p>
              <div className="data-source-links"><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_PRIOR_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">完整研究報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_PRIOR_PROTOCOL.md" target="_blank" rel="noreferrer">凍結協議</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_PRIOR_DATA_MAPPING.md" target="_blank" rel="noreferrer">數據映射</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_french_size_prior_validation.json" target="_blank" rel="noreferrer">完整 JSON</a><a href="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_25_port_form_sz_pr_1_0.html" target="_blank" rel="noreferrer">官方方法</a></div>
            </div>
          </section>

          <section className="section wrap" id="prior-return-contract">
            <div className="section-heading">
              <div><span>LATEST DATA-CONTRACT ATTEMPT · ROUND 6</span><h2>美股一個月贏家延續測試：6/8，計算前停止</h2></div>
              <p>主要候選、成本、短期反轉／同池等權／12–2 動量／市場 baseline，以及 38 道學術門檻已在五個新 ZIP 首次下載前凍結。</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict">
                <span>數據契約判斷</span>
                <h3>原檔標題不符凍結映射，沒有計算任何回報</h3>
                <p>short-term 原檔寫成 <code>{priorReturnContract.observed_monthly_markers.short_term_prior_1_0[0]}</code>；long-term 原檔則是 <code>{priorReturnContract.observed_monthly_markers.long_term_prior_12_2[0]}</code>。兩者都不等於事前固定的 <code>{priorReturnContract.expected_value_weighted_monthly_marker}</code>，所以沒有用寬鬆 parser 跨過。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>完整性檢查</span><strong>{priorReturnContract.passed_check_count}/{priorReturnContract.required_check_count}</strong><p>五個 SHA-256、CSV member、equal-weighted 表及因素 header 通過；兩個 value-weighted 表段標記失敗。</p></article>
                <article><span>策略與資金狀態</span><strong>未計算 · US$0</strong><p>沒有 CAGR、Sharpe、PBO、選股名單、Paper 或實金落盤；亦不重下載同一發布版。</p></article>
              </div>
            </div>
            <div className="comparison-caveat"><b>這不是策略負結果：</b><p>它只證明下載前映射與官方 CSV schema 不相容，不能據此說美股短窗動量有效或無效。修改 marker 後重用同一批已見原檔，也不能再聲稱獨立 first-seen 經濟驗證。</p></div>
            <div className="protocol-link"><span>第六輪凍結與失敗證據</span><div><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_PRIOR_RETURN_PROTOCOL.md" target="_blank" rel="noreferrer">事前協議</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_PRIOR_RETURN_DATA_MAPPING.md" target="_blank" rel="noreferrer">數據映射</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_PRIOR_RETURN_DATA_FAILURE.md" target="_blank" rel="noreferrer">完整失敗紀錄</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_french_prior_return_data_receipt.json" target="_blank" rel="noreferrer">機器收據</a><a href="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_10_port_form_pr_1_0.html" target="_blank" rel="noreferrer">官方方法</a></div></div>
          </section>

          <section className="section wrap" id="prior-return-diagnostic">
            <div className="section-heading">
              <div><span>SCHEMA-INFORMED ENGINEERING DIAGNOSTIC · ROUND 6B</span><h2>短窗贏家策略：工程 8/8，經濟只過 11/38</h2></div>
              <p>只使用原五份 SHA-256 快照；兩個精確 marker 的 repair 協議在任何策略數字前提交。經濟候選、四個 baseline、成本、時期及 6,150 次搜尋校正全部不變。</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict">
                <span>最新研究判斷</span>
                <h3>短窗贏家延續被市場、同池基準與長窗動量擊敗</h3>
                <p>主要期只過 {priorRepairPrimary.passed_gate_count}/15，近期只過 {priorRepairRecent.passed_gate_count}/15。近期候選雖較短窗輸家高 {pp(priorRepairRecent.candidate_metrics.cagr - priorRepairRecent.baseline_metrics.lo_prior_1_0.cagr)}，仍較市場低 {pp(priorRepairRecent.candidate_metrics.cagr - priorRepairRecent.baseline_metrics.market.cagr)}，最大跌幅達 {pct(priorRepairRecent.candidate_metrics.max_drawdown, 1)}。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>門檻分解</span><strong>{priorReturnRepair.gate_breakdown.data} · {priorReturnRepair.gate_breakdown.primary} · {priorReturnRepair.gate_breakdown.recent}</strong><p>數據工程全過；主要期只過 PBO，近期只過短窗輸家及最大跌幅兩項。</p></article>
                <article><span>證據與資金界線</span><strong>非獨立 · US$0</strong><p>原 6/8 收據不被覆蓋；`independent_first_seen_evidence=false`，Paper 及實金均維持關閉。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PRIMARY EXTERNAL PERIOD · 1963–2005</span><h3>早期完整期：零成本也未能追上四個基準</h3></div>
              <p>所有需每月輪替的投資組合使用相同 10 bps 單邊成本；每月假設完整沽出及買入。這是保守共同口徑，不是假裝知道逐股真實換手。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Calmar</th><th>US$1,000 期末值</th></tr></thead>
                <tbody>{priorRepairPrimaryRows.map((row) => (
                  <tr key={row.label} className={row.featured ? "featured-row" : undefined}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.excess_sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.calmar)}</td><td>{money(row.metrics.hypothetical_1000_usd_end)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>兩半都失敗：</b><p>1963–1984 候選 CAGR {pct(priorRepairPrimary.fixed_splits["1963_to_1984"].candidate_cagr, 2)}，較市場低 {pp(priorRepairPrimary.fixed_splits["1963_to_1984"].edge_vs_market)}；1985–2005 候選 CAGR {pct(priorRepairPrimary.fixed_splits["1985_to_2005"].candidate_cagr, 2)}，較市場低 {pp(priorRepairPrimary.fixed_splits["1985_to_2005"].edge_vs_market)}。候選在零交易成本下仍落後全部四個基準。</p></div>

            <div className="subsection-heading stock-heading">
              <div><span>RECENT CONFIRMATION · 2006–2026</span><h3>近期改善，但市場及 12–2 贏家仍更好</h3></div>
              <p>不能只展示 2016 後反彈；2006–2015 與 2016–2026 兩段固定結果同時列出。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Calmar</th><th>US$1,000 期末值</th></tr></thead>
                <tbody>{priorRepairRecentRows.map((row) => (
                  <tr key={row.label} className={row.featured ? "featured-row" : undefined}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.excess_sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.calmar)}</td><td>{money(row.metrics.hypothetical_1000_usd_end)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>分段不穩定：</b><p>2006–2015 候選 CAGR {pct(priorRepairRecent.fixed_splits["2006_to_2015"].candidate_cagr, 2)}，較市場低 {pp(priorRepairRecent.fixed_splits["2006_to_2015"].edge_vs_market)}；2016–2026 才較市場高 {pp(priorRepairRecent.fixed_splits["2016_to_end"].edge_vs_market)}。後段成功不能抵銷固定前段失敗。</p></div>

            <div className="subsection-heading stock-heading">
              <div><span>COST, WINDOWS &amp; STATISTICS</span><h3>成本容忍度很低，統計沒有確認</h3></div>
              <p>Newey–West 使用月度回報、固定三個月 lag；Sharpe／PSR／DSR 按每年 12 期，DSR 保留全專案 6,150 次搜尋懲罰。</p>
            </div>
            <div className="short-evidence-grid">
              <article><span>全歷史成本</span><dl><div><dt>10 bps</dt><dd>{pct(priorRepairCandidate.cost_sensitivity_full_history["10_bps"].cagr, 2)} CAGR</dd></div><div><dt>25 bps</dt><dd>{pct(priorRepairCandidate.cost_sensitivity_full_history["25_bps"].cagr, 2)} CAGR</dd></div><div><dt>50 bps</dt><dd>{pct(priorRepairCandidate.cost_sensitivity_full_history["50_bps"].cagr, 2)} CAGR</dd></div></dl><p>假設年換手 {multiple(priorRepairCandidate.full_history_metrics_10bps.annual_turnover)}x；50 bps 後 US$1,000 只餘 {money(priorRepairCandidate.cost_sensitivity_full_history["50_bps"].hypothetical_1000_usd_end)}。</p></article>
              <article><span>近期成本 break-even</span><strong>市場 {priorRepairRecent.cost_break_even_vs_baselines.market.one_way_bps.toFixed(2)} · 12–2 贏家 {priorRepairRecent.cost_break_even_vs_baselines.long_momentum_hi_12_2.one_way_bps.toFixed(2)} bps</strong><p>這是每月單邊上限；凍結主測 10 bps 已超出兩者。對十分位等權及短窗輸家則為 {priorRepairRecent.cost_break_even_vs_baselines.decile_equal.one_way_bps.toFixed(2)}／{priorRepairRecent.cost_break_even_vs_baselines.lo_prior_1_0.one_way_bps.toFixed(2)} bps。</p></article>
              <article><span>60 月滾動勝率</span><strong>市場 {pct(priorRepairRecent.rolling_60m_vs_market.cagr_win_fraction, 1)} · 等權 {pct(priorRepairRecent.rolling_60m_vs_decile_equal.cagr_win_fraction, 1)}</strong><p>合格線是 60%；中位 CAGR 差分別為 {pp(priorRepairRecent.rolling_60m_vs_market.median_cagr_difference)}／{pp(priorRepairRecent.rolling_60m_vs_decile_equal.median_cagr_difference)}。</p></article>
              <article><span>近期主動統計</span><strong>NW t {priorRepairRecentMarket.newey_west.t_stat.toFixed(2)}／{priorRepairRecentEqual.newey_west.t_stat.toFixed(2)}</strong><p>對市場／十分位等權；PSR {pct(priorRepairRecentMarket.active_probabilistic_sharpe.probability, 2)}／{pct(priorRepairRecentEqual.active_probabilistic_sharpe.probability, 2)}，均未達 95%。</p></article>
              <article><span>DSR 與 PBO</span><strong>DSR {pct(priorRepairRecentMarket.active_global_deflated_sharpe.probability, 3)} · PBO {pct(priorReturnRepair.pbo.recent.pbo, 1)}</strong><p>6,150 次搜尋校正後幾乎沒有證據；六路近期 PBO 高於 20% 上限。</p></article>
              <article><span>五因子解釋</span><strong>Alpha {pct(priorReturnRepair.factor_regression_full_history.annualized_alpha, 2)}</strong><p>市場 beta {multiple(priorReturnRepair.factor_regression_full_history.market_beta)}、ST_Rev beta {multiple(priorReturnRepair.factor_regression_full_history.short_term_reversal_beta)}、R² {pct(priorReturnRepair.factor_regression_full_history.r_squared, 1)}。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PREDECLARED SENSITIVITY SET</span><h3>六條路徑全部保留，不事後換冠軍</h3></div>
              <p>線性傾斜是事後看到的六路最高值，仍低於全歷史市場；它只能作敏感度，不能取代唯一主要候選。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>事前路徑</th><th>全歷史年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>US$1,000 期末值</th></tr></thead>
                <tbody>{priorRepairSensitivityRows.map((row, index) => (
                  <tr key={row.label} className={index === 0 ? "featured-row" : undefined}><th><b>{row.label}</b><span>{index === 0 ? "唯一主要候選" : "敏感度／PBO 路徑"}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.excess_sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{money(row.metrics.hypothetical_1000_usd_end)}</td></tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>CRISIS TESTS</span><h3>2020 勝出，不能掩蓋五段較差尾部表現</h3></div>
              <p>固定危機期全部展示；個別上升段不會取代完整期、成本、統計與最大跌幅門檻。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>壓力期</th><th>候選回報</th><th>市場回報</th><th>十分位等權</th><th>12–2 贏家</th><th>候選最大跌幅</th></tr></thead>
                <tbody>{priorRepairStressRows.map((row) => <tr key={row.label}><th><b>{row.label}</b><span>固定壓力窗口</span></th><td>{pct(row.result.candidate.return, 1)}</td><td>{pct(row.result.market.return, 1)}</td><td>{pct(row.result.decile_equal.return, 1)}</td><td>{pct(row.result.long_momentum_hi_12_2.return, 1)}</td><td>{pct(row.result.candidate.max_drawdown, 1)}</td></tr>)}</tbody>
              </table>
            </div>

            <div className="data-source-decision">
              <div><span>DECISION BOUNDARY</span><b>原 6/8 失敗與本次 11/38 工程診斷同時保留</b></div>
              <p>本次只證明精確 parser 可重現同一已見 schema 快照的負經濟結果。沒有逐股 point-in-time 成分、退市／收購回報、公司行動、精確換手及已授權供應商，所以不能產生股票名單、Paper 或落盤指令。</p>
              <div className="data-source-links"><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_PRIOR_RETURN_SCHEMA_REPAIR_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">完整研究報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_PRIOR_RETURN_SCHEMA_REPAIR_PROTOCOL.md" target="_blank" rel="noreferrer">repair 協議</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_PRIOR_RETURN_SCHEMA_REPAIR_MAPPING.md" target="_blank" rel="noreferrer">精確映射</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_french_prior_return_schema_repair_validation.json" target="_blank" rel="noreferrer">完整 JSON</a><a href="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_10_port_form_pr_1_0.html" target="_blank" rel="noreferrer">官方方法</a></div>
            </div>
          </section>

          <section className="section wrap" id="aggressive-evidence">
            <div className="section-heading">
              <div><span>PREVIOUS FIRST-SEEN EXTERNAL VALIDATION</span><h2>French 30 行業逾 63 年驗證：早期有效，近期不足</h2></div>
              <p>原始共同期 1926–2026；正式候選從 {shortDate(frenchPrimary.start)} 起計。規則、數據映射、成本及 33 道門檻在首次下載 30 行業 ZIP 前已凍結。</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict">
                <span>最新研究判斷</span>
                <h3>有歷史行業動量，不等於近期可穩健賺取超額</h3>
                <p>主要外部期較市場高 {pp(frenchPrimary.candidate_metrics.cagr - frenchPrimary.baseline_metrics.market.cagr)}，20 日事件亦 5/5；但近期只高 {pp(frenchRecent.candidate_metrics.cagr - frenchRecent.baseline_metrics.market.cagr)}，2006–2015 更落後市場，近期主動 NW t 只有 {frenchRecentMarket.newey_west.t_stat.toFixed(2)}。因此整體判定失敗。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>數據與凍結順序</span><strong>{frenchResearch.gate_breakdown.data}</strong><p>官方 ZIP、雜湊、30 欄、缺值及訊號 t／回報 t+1 全部通過。</p></article>
                <article><span>雙時期硬門檻</span><strong>{frenchResearch.gate_breakdown.primary} · {frenchResearch.gate_breakdown.recent}</strong><p>近期只過最大跌幅及對行業等權的五年滾動一致性。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PRIMARY EXTERNAL PERIOD · 1963–2005</span><h3>完整早期樣本：候選勝出，但仍未過全部門檻</h3></div>
              <p>同一官方快照、同一日期、10 bps 單邊成本；Sharpe 全部以每日回報減 RF 計算。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Calmar</th><th>每年換手</th></tr></thead>
                <tbody>{frenchPrimaryRows.map((row) => (
                  <tr key={row.label} className={row.featured ? "featured-row" : undefined}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.excess_sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.calmar)}</td><td>{multiple(row.metrics.annual_turnover)}x</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>US$1,000 歷史尺度：</b><p>1963 年投入候選的理論期末值為 {money(frenchPrimary.candidate_metrics.hypothetical_1000_usd_end)}，市場為 {money(frenchPrimary.baseline_metrics.market.hypothetical_1000_usd_end)}。這是 42 年名義複利、未計通脹與稅項；不能當成未來金額預測。</p></div>

            <div className="subsection-heading stock-heading">
              <div><span>RECENT CONFIRMATION · 2006–2026</span><h3>近期樣本：回報略高，證據強度大幅下降</h3></div>
              <p>不能用 1963–2005 的漂亮結果掩蓋近期失敗；近期獨立再用同一 13 道門檻。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Calmar</th><th>每年換手</th></tr></thead>
                <tbody>{frenchRecentRows.map((row) => (
                  <tr key={row.label} className={row.featured ? "featured-row" : undefined}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.excess_sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.calmar)}</td><td>{multiple(row.metrics.annual_turnover)}x</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>US$1,000 歷史尺度：</b><p>2006 年起候選的理論期末值為 {money(frenchRecent.candidate_metrics.hypothetical_1000_usd_end)}，市場為 {money(frenchRecent.baseline_metrics.market.hypothetical_1000_usd_end)}；候選最大跌幅 {pct(frenchRecent.candidate_metrics.max_drawdown, 1)}，並非低風險捷徑。</p></div>

            <div className="subsection-heading stock-heading">
              <div><span>COST, WINDOWS &amp; STATISTICS</span><h3>成本、分段、PBO 與因子解釋</h3></div>
              <p>Top-3 是唯一候選；Top-2／5 只作敏感度及 CSCV PBO，不因 Top-2 全期回報較高便換冠軍。</p>
            </div>
            <div className="short-evidence-grid">
              <article><span>全歷史成本敏感度</span><dl>{frenchCostRows.map((row) => <div key={row.label}><dt>{row.label}</dt><dd>{pct(row.metrics.cagr, 2)} CAGR</dd></div>)}</dl><p>每年雙邊換手約 {multiple(frenchCandidate.full_history_metrics.annual_turnover)}x；50 bps 把全期 CAGR 壓至 {pct(frenchCandidate.cost_sensitivity_full_history["50_bps"].cagr, 2)}。</p></article>
              <article><span>固定近期分段</span><strong>{pp(frenchRecent.fixed_splits["2006_to_2015"].edge_vs_market)}／{pp(frenchRecent.fixed_splits["2016_to_end"].edge_vs_market)}</strong><p>2006–2015／2016–2026 對市場；第一段落後，不能用第二段反彈掩蓋。</p></article>
              <article><span>五年滾動勝率</span><strong>市場 {pct(frenchRecent.rolling_five_year_vs_market.cagr_win_fraction, 1)} · 等權 {pct(frenchRecent.rolling_five_year_vs_industry_monthly_equal.cagr_win_fraction, 1)}</strong><p>近期 185 個窗口；對市場未達 60%，最差落後 {pp(frenchRecent.rolling_five_year_vs_market.worst_cagr_difference)}。</p></article>
              <article><span>主動統計</span><strong>早期 t {frenchPrimaryMarket.newey_west.t_stat.toFixed(2)}／{frenchPrimaryEqual.newey_west.t_stat.toFixed(2)}</strong><p>對市場／行業等權；近期跌至 {frenchRecentMarket.newey_west.t_stat.toFixed(2)}／{frenchRecentEqual.newey_west.t_stat.toFixed(2)}。近期對市場 DSR 只有 {pct(frenchRecentMarket.active_global_deflated_sharpe.probability, 2)}。</p></article>
              <article><span>CSCV 過度配適</span><strong>{pct(frenchResearch.pbo.primary.pbo, 1)}／{pct(frenchResearch.pbo.recent.pbo, 1)}</strong><p>主要／近期 PBO，遠高於 20% 上限；Top-2、3、5 的相對排序不穩定。</p></article>
              <article><span>四因子解釋</span><strong>Alpha {pct(frenchResearch.factor_regression_full_history.annualized_alpha, 2)}</strong><p>市場 beta {multiple(frenchResearch.factor_regression_full_history.market_beta)}、Mom beta {multiple(frenchResearch.factor_regression_full_history.mom_beta)}、R² {pct(frenchResearch.factor_regression_full_history.r_squared, 1)}；全歷史 alpha 為負。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FIXED 20-DAY SIGNAL</span><h3>早期 5/5，近期只 3/5</h3></div>
              <p>每週以同一 6–1 排名選 Top-3，下一交易日開始持有 20 日，每個事件扣來回 20 bps；重疊事件用 NW lag 4 及固定區塊重抽樣。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table signal-diagnostic-table">
                <thead><tr><th>時期</th><th>事件</th><th>Top-3 平均淨回報</th><th>30 行業等權</th><th>配對差</th><th>勝出率</th><th>NW t</th><th>Bootstrap 95% 區間</th></tr></thead>
                <tbody>
                  <tr className="featured-row"><th><b>1963–2005</b><span>主要外部期 · 5/5</span></th><td>{frenchPrimaryEvent.events}</td><td>{pct(frenchPrimaryEvent.selected_mean_return, 2)}</td><td>{pct(frenchPrimaryEvent.industry_equal_mean_return, 2)}</td><td>{pp(frenchPrimaryEvent.mean_difference_vs_industry_equal)}</td><td>{pct(frenchPrimaryEvent.paired_win_fraction, 1)}</td><td>{frenchPrimaryEvent.newey_west.t_stat.toFixed(2)}</td><td>{pp(frenchPrimaryEvent.moving_block_bootstrap.low)} 至 {pp(frenchPrimaryEvent.moving_block_bootstrap.high)}</td></tr>
                  <tr><th><b>2006–2026</b><span>近期確認期 · 3/5</span></th><td>{frenchRecentEvent.events}</td><td>{pct(frenchRecentEvent.selected_mean_return, 2)}</td><td>{pct(frenchRecentEvent.industry_equal_mean_return, 2)}</td><td>{pp(frenchRecentEvent.mean_difference_vs_industry_equal)}</td><td>{pct(frenchRecentEvent.paired_win_fraction, 1)}</td><td>{frenchRecentEvent.newey_west.t_stat.toFixed(2)}</td><td>{pp(frenchRecentEvent.moving_block_bootstrap.low)} 至 {pp(frenchRecentEvent.moving_block_bootstrap.high)}</td></tr>
                </tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>CRISIS TESTS</span><h3>六段壓力期：上行較高，尾部風險仍大</h3></div>
              <p>危機表只描述固定規則的實際歷史表現，不用個別危機勝出代替全套門檻。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>壓力期</th><th>候選回報</th><th>市場回報</th><th>行業等權回報</th><th>候選最大跌幅</th><th>候選最差單日</th></tr></thead>
                <tbody>{frenchStressRows.map((row) => <tr key={row.label}><th><b>{row.label}</b><span>固定歷史窗口</span></th><td>{pct(row.result.candidate.return, 1)}</td><td>{pct(row.result.market.return, 1)}</td><td>{pct(row.result.industry_monthly_equal.return, 1)}</td><td>{pct(row.result.candidate.max_drawdown, 1)}</td><td>{pct(row.result.candidate.worst_day, 1)}</td></tr>)}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>最新決策：</b><p>保留早期正面與近期負面證據，不改 6–1、Top-3、20 日、成本或起訖日救援。French 組合不是可買賣產品，短線 Paper 仍等候合格逐股 point-in-time 成分與退市回報；實金及 Paper 動作均為 US$0。</p></div>
            <div className="protocol-link"><span>最新研究協議、數據映射與失敗證據</span><div><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_30_INDUSTRY_MOMENTUM_PROTOCOL.md" target="_blank" rel="noreferrer">凍結協議</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_30_INDUSTRY_DATA_MAPPING.md" target="_blank" rel="noreferrer">數據映射</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_30_INDUSTRY_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">完整報告</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_french_30_industry_validation.json" target="_blank" rel="noreferrer">完整 JSON</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_INDUSTRY_DATA_FAILURE.md" target="_blank" rel="noreferrer">49 行業數據失敗</a></div></div>
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
                <div><span>GATE-BY-GATE DECISION</span><h2>最新大型股短窗贏家驗證只過 {sizePriorResearch.passed_gate_count} / {sizePriorResearch.required_gate_count} 道</h2></div>
                <p>首次數據 10/10，主要外部期 1/17，近期確認期 3/17。上一輪 schema-informed 11/38及 French 30 的 17/33 仍完整保留。</p>
              </div>
              <div className="signal-formula" aria-label="最新外部驗證凍結規格">
                <article><span>5 × 5</span><b>Size 與 prior 交叉</b><p>隔離大型股，避免只看未分 size 的贏家組。</p></article>
                <article><span>BIG HI</span><b>唯一主要候選</b><p>25 cells 及傾斜只作敏感度，不事後改選冠軍。</p></article>
                <article><span>MONTHLY</span><b>完整重新平衡</b><p>缺乏逐股換手，保守假設每月完整沽出再買入。</p></article>
                <article><span>10 bps</span><b>主要單邊成本</b><p>另測 25／50 bps；成本不能在看到負結果後刪除。</p></article>
              </div>

              <div className="short-gate-grid">
                <article className="waiting"><span>01</span><div><b>首次數據契約</b><strong>{sizePriorResearch.gate_breakdown.data} 通過</strong><p>官方 ZIP、SHA-256、兩個 25 欄月表、1963–2026 完整月份及形成時序全部通過。</p></div></article>
                <article className="failed"><span>02</span><div><b>主要外部期</b><strong>{sizePriorResearch.gate_breakdown.primary}</strong><p>候選 CAGR {pct(sizePriorPrimary.candidate_metrics.cagr, 2)}，市場 {pct(sizePriorPrimary.baseline_metrics.market.cagr, 2)}；只過 PBO。</p></div></article>
                <article className="failed"><span>03</span><div><b>近期確認期</b><strong>{sizePriorResearch.gate_breakdown.recent}</strong><p>候選 {pct(sizePriorRecent.candidate_metrics.cagr, 2)}，QQQ {pct(sizePriorRecent.baseline_metrics.QQQ.cagr, 2)}；只勝兩個弱基準並守住跌幅限制。</p></div></article>
                <article className="failed"><span>04</span><div><b>成本與固定分段</b><strong>失敗</strong><p>近期 50 bps CAGR {pct(sizePriorRecent.candidate_50bps_metrics.cagr, 2)}；2006–2015 較市場低 {pp(Math.abs(sizePriorRecent.fixed_splits["2006_to_2015"].edge_vs_market))}。</p></div></article>
                <article className="failed"><span>05</span><div><b>NW、DSR 與 PBO</b><strong>失敗</strong><p>近期市場 NW t {sizePriorRecentMarket.newey_west.t_stat.toFixed(2)}；DSR {pct(sizePriorRecentMarket.active_global_deflated_sharpe.probability, 4)}；PBO {pct(sizePriorResearch.pbo.recent.pbo, 1)}。</p></div></article>
                <article className="failed"><span>06</span><div><b>逐股數據與前瞻 Paper</b><strong>未啟動</strong><p>French cells 不是證券，亦沒有逐股 point-in-time／退市賬本；即使 44/44 亦不能直接落盤。</p></div></article>
              </div>
              <div className="data-source-decision">
                <div><span>EVIDENCE LADDER</span><b>first-seen 14/44、schema-informed 11/38、French 30 的 17/33 及原始失敗同時保留</b></div>
                <p>最新 25 cells 是首次未見，仍未通過；上一輪 repair 不是獨立證據；French 30 只有早期優勢；49 行業則在 1971-03-11 的數據缺值停止。沒有一條可取代逐股 point-in-time 賬本。</p>
                <div className="data-source-links"><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_PRIOR_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">最新 14/44 報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_PRIOR_RETURN_SCHEMA_REPAIR_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">上一輪 11/38</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_30_INDUSTRY_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">French 30 的 17/33</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_INDUSTRY_DATA_FAILURE.md" target="_blank" rel="noreferrer">49 行業失敗</a></div>
              </div>
              <p className="aggressive-final-decision"><b>目前決策：</b>短窗贏家在 size 隔離、早期、近期、成本、滾動窗口及統計上仍未通過，QQQ 亦明顯較好。不開短線 Paper。下一步只接受已授權逐股 point-in-time 成分、退市／收購、公司行動、流動性及精確成本，另立協議後由全現金開始。實金及 Paper 動作均為 US$0。</p>
              <div className="protocol-link"><span>最新證據完整保留 · 14/44 負結果優先</span><div><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_PRIOR_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">最新報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_PRIOR_PROTOCOL.md" target="_blank" rel="noreferrer">凍結協議</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_PRIOR_DATA_MAPPING.md" target="_blank" rel="noreferrer">數據映射</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_french_size_prior_validation.json" target="_blank" rel="noreferrer">完整結果</a></div></div>
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
