import publicDecision from "../data/public-decision.json";

type PublicStrategy = {
  verified: true;
  key: string;
  horizon: string;
  name: string;
  description: string;
  action: string;
  metrics: Array<{ label: string; value: string; comparison: string }>;
};

type PublicDecisionContract = {
  data_through: string;
  next_expected_session: string;
  refresh_due_at_utc: string;
  surface: "verified-strategy" | "hold-cash";
  today_action: string;
  lead: string;
  action_detail: string;
  policy: string;
  strategies: PublicStrategy[];
};

const decision = publicDecision as PublicDecisionContract;
const shortDate = (value: string) => value.replaceAll("-", "/");
const publicStrategyKeys = new Set(["long-term", "short-term"]);

const isPublicStrategy = (value: unknown): value is PublicStrategy => {
  if (!value || typeof value !== "object") return false;
  const strategy = value as Partial<PublicStrategy>;
  return strategy.verified === true
    && typeof strategy.key === "string"
    && publicStrategyKeys.has(strategy.key)
    && typeof strategy.horizon === "string"
    && typeof strategy.name === "string"
    && typeof strategy.description === "string"
    && typeof strategy.action === "string"
    && strategy.action.trim().length > 0
    && Array.isArray(strategy.metrics)
    && strategy.metrics.length > 0
    && strategy.metrics.every(
      (metric) => metric
        && typeof metric.label === "string"
        && typeof metric.value === "string"
        && typeof metric.comparison === "string",
    );
};

const publicStrategies = Array.isArray(decision.strategies)
  ? decision.strategies.filter(isPublicStrategy)
  : [];
const hasPromotedStrategy = publicStrategies.length > 0;
const todayAction = publicStrategies.length === 0
  ? "今天不下單"
  : publicStrategies.every((strategy) => strategy.action.startsWith("今天不下單"))
    ? "今天不下單"
    : "按已驗證策略執行";
const statusReason = hasPromotedStrategy
  ? "以下策略已通過完整驗證；請只按其公開的行動說明理解研究狀態。"
  : "現時沒有策略通過完整回測及前瞻驗證，維持現金，不建立新倉。";

export default function PublicDecisionPage() {
  return (
    <>
      <header className="site-header public-header">
        <div className="wrap nav-shell">
          <a className="brand" href="#top" aria-label="返回策略狀態頂部">
            <span>US FDDK</span>
            <b>美股策略狀態</b>
          </a>
          <span className="public-header-state">驗證後才公開</span>
        </div>
      </header>

      <main
        className="public-decision-main"
        id="top"
        data-public-strategy-count={publicStrategies.length}
        data-public-action={hasPromotedStrategy ? "verified-strategy" : "hold-cash"}
        data-promotion-gate="fail-closed"
        data-public-surface="success-only"
      >
        <section className="public-status-shell wrap" id="today-action">
          <div className="public-status-card">
            <span className="public-kicker">最新狀態</span>
            <h1>{todayAction}</h1>
            <p className="public-status-reason">{statusReason}</p>
            <dl className="public-status-meta">
              <div>
                <dt>資料截至</dt>
                <dd>{shortDate(decision.data_through)}</dd>
              </div>
            </dl>
            <p className="public-status-note">
              本頁只會在完整驗證通過後顯示策略；未通過時不顯示研究細節或投資金額。
            </p>
          </div>
        </section>

        {hasPromotedStrategy ? (
          <section className="public-approved-section wrap" id="promoted-strategies">
            <div className="public-approved-heading">
              <span>已完成驗證</span>
              <h2>公開策略</h2>
            </div>
            <div className="public-approved-grid">
              {publicStrategies.map((strategy) => (
                <article className="public-approved-card" data-promoted-strategy={strategy.key} key={strategy.key}>
                  <div className="public-approved-title">
                    <span>{strategy.horizon}</span>
                  </div>
                  <h3>{strategy.name}</h3>
                  <p>{strategy.description}</p>
                  <p className="public-approved-action">{strategy.action}</p>
                  <dl className="public-approved-metrics">
                    {strategy.metrics.map((metric) => (
                      <div key={metric.label}>
                        <dt>{metric.label}</dt>
                        <dd>{metric.value}</dd>
                        <small>{metric.comparison}</small>
                      </div>
                    ))}
                  </dl>
                </article>
              ))}
            </div>
          </section>
        ) : null}

      </main>

      <footer className="public-footer">
        <div className="wrap public-footer-inner">
          <span>資料每日檢查 · 研究用途，非投資建議</span>
        </div>
      </footer>
    </>
  );
}
