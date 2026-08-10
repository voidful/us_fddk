import FreshnessGuard from "./FreshnessGuard";
import data from "../data/trading-data.json";
import formalBacktestReadiness from "../data/short-term-formal-backtest-readiness.json";
import qqqReplacementOverlay from "../data/short-term-qqq-replacement-overlay.json";

const readerCapital = 1_000;
const latest = data.research_pipeline.growth_gold_diversification;
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

const shortDate = (value: string) => value.replaceAll("-", "/");

const accountIntegrityGateNames = [
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

const rootGateValues = Object.values(data.readiness.gates);
const selectedStrategyKey = (
  data.readiness as typeof data.readiness & { selected_strategy_key?: string }
).selected_strategy_key;
const rootReadinessComplete =
  data.readiness.required_gate_count === 11
  && data.readiness.passed_gate_count === data.readiness.required_gate_count
  && rootGateValues.length === data.readiness.required_gate_count
  && rootGateValues.every((passed) => passed === true)
  && data.readiness.trade_ready === true
  && data.readiness.allocation_visible === true;

const longTermIntegrityComplete =
  paper.as_of === data.data_through
  && forward.as_of === data.data_through
  && forward.integrity_violations === 0
  && accountIntegrityGateNames.every((gate) => forward.gates[gate] === true);

const longTermTradeReady =
  rootReadinessComplete
  && selectedStrategyKey === "growth_gold_diversification"
  && latest.trade_ready === true
  && latest.real_money_signal_display_allowed === true
  && forward.live_confirmed === true
  && longTermIntegrityComplete;

type ShortPublicDecision = typeof qqqReplacementOverlay.decision & {
  trade_ready?: boolean;
  public_action?: string;
  public_symbols?: string[];
};

const shortDecision = qqqReplacementOverlay.decision as ShortPublicDecision;
const shortTermTradeReady =
  formalBacktestReadiness.actual_formal_readiness.all_passed === true
  && formalBacktestReadiness.actual_formal_readiness.passed
    === formalBacktestReadiness.actual_formal_readiness.total
  && qqqReplacementOverlay.gate_summary.all_passed === true
  && qqqReplacementOverlay.gate_summary.passed === qqqReplacementOverlay.gate_summary.total
  && shortDecision.trade_ready === true
  && shortDecision.can_promote_from_this_round === true
  && shortDecision.new_strategy_created === true
  && shortDecision.formal_strategy_runs > 0
  && typeof shortDecision.public_action === "string"
  && shortDecision.public_action.trim().length > 0
  && Array.isArray(shortDecision.public_symbols)
  && shortDecision.public_symbols.length > 0;

type PublicStrategy = {
  key: string;
  horizon: string;
  name: string;
  description: string;
  action: string;
  allocation?: string;
  amountExample?: string;
  metrics: Array<{ label: string; value: string; comparison: string }>;
};

const publicStrategies: PublicStrategy[] = [
  ...(longTermTradeReady
    ? [{
        key: "long-term",
        horizon: "長線穩定",
        name: "大型成長股＋黃金",
        description: "固定規則、每月檢查；只在歷史、成本、風險及前瞻門檻全部通過後公開。",
        action: paper.pending_order
          ? "下一個完成交易日按已凍結指令調整持倉"
          : "今天不下單；維持現有持倉，等待下一個月末檢查",
        allocation: "VUG 80%／GLD 20%",
        amountExample: `${money(readerCapital * 0.8)}／${money(readerCapital * 0.2)}`,
        metrics: [
          {
            label: "20 年年率化回報",
            value: pct(latest.pooled.strategy_metrics.cagr, 2),
            comparison: `SPY ${pct(latest.pooled.spy_metrics.cagr, 2)}`,
          },
          {
            label: "最大跌幅",
            value: pct(latest.pooled.strategy_metrics.max_drawdown, 1),
            comparison: `SPY ${pct(latest.pooled.spy_metrics.max_drawdown, 1)}`,
          },
          {
            label: "前瞻交易日",
            value: String(forward.forward_sessions),
            comparison: `${forward.filled_rebalances} 次完成換倉`,
          },
        ],
      }]
    : []),
  ...(shortTermTradeReady
    ? [{
        key: "short-term",
        horizon: "短線高回報",
        name: "已驗證個股策略",
        description: "正式個股策略已通過凍結資料、成本、統計、壓力及前瞻門檻。",
        action: shortDecision.public_action!,
        allocation: shortDecision.public_symbols!.join("／"),
        metrics: [
          {
            label: "正式就緒",
            value: `${formalBacktestReadiness.actual_formal_readiness.passed}/${formalBacktestReadiness.actual_formal_readiness.total}`,
            comparison: "全部事前門檻通過",
          },
          {
            label: "策略運行",
            value: String(shortDecision.formal_strategy_runs),
            comparison: "正式、不可回填",
          },
        ],
      }]
    : []),
];

const todayAction = publicStrategies.length === 0
  ? "今天不下單"
  : publicStrategies.every((strategy) => strategy.action.startsWith("今天不下單"))
    ? "今天不下單"
    : "按已驗證策略執行";

export default function PublicDecisionPage() {
  const hasPromotedStrategy = publicStrategies.length > 0;

  return (
    <>
      <header className="site-header public-header">
        <div className="wrap nav-shell">
          <a className="brand" href="#top" aria-label="返回策略狀態頂部">
            <span>US FDDK</span>
            <b>美股交易參考</b>
          </a>
          <FreshnessGuard
            dataThrough={data.data_through}
            refreshDueAtUtc={data.freshness.refresh_due_at_utc}
          />
        </div>
      </header>

      <main
        className="public-decision-main"
        id="top"
        data-public-strategy-count={publicStrategies.length}
        data-public-action={hasPromotedStrategy ? "verified-strategy" : "hold-cash"}
        data-promotion-gate="fail-closed"
      >
        <section className="public-status-hero wrap" id="today-action">
          <div className="public-status-copy">
            <div className="eyebrow-row">
              <span className="eyebrow">今日交易參考</span>
              <span className={`status-chip ${hasPromotedStrategy ? "verified" : "warning"}`}>
                <i /> {hasPromotedStrategy ? "合格策略已上線" : "保持現金"}
              </span>
            </div>
            <h1>{todayAction}</h1>
            <p className="public-status-lead">
              {hasPromotedStrategy
                ? "以下是目前合格策略及對應行動。"
                : "暫時沒有合格交易訊號。不建立新倉，等待下一個完成交易日。"}
            </p>
            <div className="public-as-of">
              <span>資料截至</span>
              <strong>{shortDate(data.data_through)}</strong>
              <span>下一個檢查交易日</span>
              <strong>{shortDate(data.freshness.next_expected_session)}</strong>
            </div>
          </div>
        </section>

        {hasPromotedStrategy ? (
          <section className="public-strategy-section wrap" id="promoted-strategies">
            <div className="public-section-heading">
              <span>通過全部門檻</span>
              <h2>目前可行策略</h2>
            </div>
            <div className="public-strategy-grid">
              {publicStrategies.map((strategy) => (
                <article className="public-strategy-card" data-promoted-strategy={strategy.key} key={strategy.key}>
                  <div className="public-strategy-title">
                    <span>{strategy.horizon}</span>
                    <b>已驗證</b>
                  </div>
                  <h3>{strategy.name}</h3>
                  <p>{strategy.description}</p>
                  <dl>
                    <div><dt>今日行動</dt><dd>{strategy.action}</dd></div>
                    {strategy.allocation ? <div><dt>正式配置</dt><dd>{strategy.allocation}</dd></div> : null}
                    {strategy.amountExample ? <div><dt>{money(readerCapital)} 示例</dt><dd>{strategy.amountExample}</dd></div> : null}
                  </dl>
                  <div className="public-metric-grid">
                    {strategy.metrics.map((metric) => (
                      <div key={metric.label}>
                        <span>{metric.label}</span>
                        <strong>{metric.value}</strong>
                        <small>{metric.comparison}</small>
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </section>
        ) : null}

      </main>

      <footer className="public-footer">
        <div className="wrap public-footer-inner">
          <b>{todayAction}</b>
          <span>研究與教育參考，不構成個人投資建議。</span>
        </div>
      </footer>
    </>
  );
}
