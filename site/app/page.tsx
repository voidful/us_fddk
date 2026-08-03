import type { Metadata } from "next";
import FreshnessGuard from "./FreshnessGuard";
import PaperAllocationLab from "./PaperAllocationLab";
import V25ForwardBoard from "./V25ForwardBoard";
import data from "../data/trading-data.json";

export const metadata: Metadata = {
  title: "美股成長＋黃金策略｜最新研究及 Paper 儀表板",
  description:
    "最新 v25 80% VUG／20% GLD 的 20 年回測、三產品路徑、成本與分段測試、統計診斷、市場狀況及 Paper Trading 進度。",
};

const readerCapital = 1_000;
const latest = data.research_pipeline.growth_gold_diversification;
const pooled = latest.pooled;
const diagnostics = pooled.post_entry_diagnostics_not_used_for_frozen_gate;
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

const shortDate = (value: string) => value.replaceAll("-", "/");

const comparisonRows = [
  { label: "最新策略", detail: "80% 大型成長股／20% 黃金", metrics: pooled.strategy_metrics },
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
            <a href="#market">市場狀況</a>
            <a href="#backtest">20 年回測</a>
            <a href="#tests">穩健測試</a>
            <a href="#paper">Paper</a>
          </nav>
          <FreshnessGuard
            dataThrough={data.data_through}
            refreshDueAtUtc={data.freshness.refresh_due_at_utc}
          />
        </div>
      </header>

      <main id="top">
        <section className="hero wrap">
          <div className="hero-copy">
            <div className="eyebrow-row">
              <span className="eyebrow">LATEST STRATEGY REPORT · v25</span>
              <span className="status-chip warning"><i /> PAPER ONLY</span>
            </div>
            <h1>80% 美國大型成長股<br />＋20% 黃金</h1>
            <p className="hero-lead">
              20 年歷史入口及三家實際 ETF 產品路徑全部通過。最新前瞻樣本仍是
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
              <span>投資決策摘要</span>
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
            <article><span>20 年年率化回報</span><strong>{pct(pooled.strategy_metrics.cagr, 2)}</strong><small>SPY {pct(pooled.spy_metrics.cagr, 2)}</small></article>
            <article><span>Sharpe 比率</span><strong>{pooled.strategy_metrics.sharpe.toFixed(2)}</strong><small>SPY {pooled.spy_metrics.sharpe.toFixed(2)}</small></article>
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
            <details open><summary>最新策略現在可以用實金嗎？</summary><p>不可以。歷史回測通過只准建立 Paper。前瞻仍是 {forward.forward_sessions}/{forward.minimum_sessions} 個新增交易日、{forward.filled_rebalances}/{forward.minimum_filled_rebalances} 次完成重新平衡，實金動作為 US$0。</p></details>
            <details><summary>為甚麼同時比較 SPY、純成長和公平持倉比率基準？</summary><p>SPY 回答是否勝過廣泛市場；純成長回答黃金是否犧牲上行；80% 成長／20% SHY 回答黃金是否只靠降低股票持倉比率製造較淺跌幅。三者缺一不可。</p></details>
            <details><summary>目前市場判讀是買入還是避險？</summary><p>此策略沒有短線看好或看淡訊號，只在每個完整月末把比例拉回 80/20。最新五年窗仍領先 SPY，但組合距歷史高位約 {pct(Math.abs(diagnostics.portfolio_underwater.current_drawdown), 1)}，不能解讀為保證反彈。</p></details>
            <details><summary>US$1,000 應該如何理解？</summary><p>US$800 VUG／US$200 GLD 是瀏覽器內的 Paper 比例示例，不是落盤指令。正式前瞻比較仍以 US$100,000 同起點、相同成本及相同交易日序列運作。</p></details>
          </div>
        </section>
      </main>

      <footer>
        <div className="wrap footer-grid">
          <div><b>US FDDK</b><p>美股策略研究及前瞻 Paper 紀錄。</p></div>
          <div><span>最新數據</span><b>{data.data_through}</b></div>
          <div><span>公開狀態</span><b>Research + Paper-only</b></div>
          <div><span>免責聲明</span><p>歷史表現不保證未來結果；本頁不構成投資建議或實金落盤指令。</p></div>
        </div>
      </footer>
    </>
  );
}
