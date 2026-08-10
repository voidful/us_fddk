import FreshnessGuard from "./FreshnessGuard";
import publicDecision from "../data/public-decision.json";

type PublicStrategy = {
  verified: true;
  key: string;
  horizon: string;
  name: string;
  description: string;
  action: string;
  allocation?: string;
  amount_example?: string;
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

const isPublicStrategy = (value: unknown): value is PublicStrategy => {
  if (!value || typeof value !== "object") return false;
  const strategy = value as Partial<PublicStrategy>;
  return strategy.verified === true
    && typeof strategy.key === "string"
    && typeof strategy.horizon === "string"
    && typeof strategy.name === "string"
    && typeof strategy.description === "string"
    && typeof strategy.action === "string"
    && Array.isArray(strategy.metrics)
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

export default function PublicDecisionPage() {
  return (
    <>
      <header className="site-header public-header">
        <div className="wrap nav-shell">
          <a className="brand" href="#top" aria-label="返回策略狀態頂部">
            <span>US FDDK</span>
            <b>美股交易參考</b>
          </a>
          <nav aria-label="公開頁面導覽">
            <a href="#today-action">今日行動</a>
            {hasPromotedStrategy ? <a href="#promoted-strategies">可行策略</a> : null}
          </nav>
          <FreshnessGuard
            dataThrough={decision.data_through}
            refreshDueAtUtc={decision.refresh_due_at_utc}
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
              <span className="eyebrow">VERIFIED STRATEGIES ONLY</span>
              <span className={`status-chip ${hasPromotedStrategy ? "verified" : "warning"}`}>
                <i /> {publicStrategies.length} 個策略獲准公開
              </span>
            </div>
            <h1>{todayAction}</h1>
            <p className="public-status-lead">{decision.lead}</p>
            <div className="public-as-of">
              <span>資料截至</span>
              <strong>{shortDate(decision.data_through)}</strong>
              <span>下一個檢查交易日</span>
              <strong>{shortDate(decision.next_expected_session)}</strong>
            </div>
          </div>

          <aside className="public-action-card" aria-label="今日行動建議">
            <span>今日行動</span>
            <strong>{todayAction}</strong>
            {hasPromotedStrategy ? (
              <p>{decision.action_detail}</p>
            ) : (
              <>
                <p>不建立新倉，保留現金並等待下一個完成交易日的正式驗證。</p>
                <ul>
                  <li>不把 Paper 持倉當成落盤訊號</li>
                  <li>不照抄歷史最後權重或單次回測</li>
                  <li>只有已驗證策略才會提供交易建議</li>
                </ul>
              </>
            )}
          </aside>
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
                    {strategy.amount_example ? <div><dt>US$1,000 示例</dt><dd>{strategy.amount_example}</dd></div> : null}
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

        <section className="public-policy-strip" aria-label="公開策略規則">
          <div className="wrap">
            <strong>公開原則</strong>
            <p>{decision.policy}</p>
          </div>
        </section>
      </main>

      <footer className="public-footer">
        <div className="wrap public-footer-inner">
          <div><span>狀態</span><b>{todayAction}</b></div>
          <div><span>已驗證策略</span><b>{publicStrategies.length}</b></div>
          <div><span>用途</span><b>研究與教育參考</b></div>
          <a href="https://github.com/voidful/us_fddk" target="_blank" rel="noreferrer">研究日誌與機器收據</a>
        </div>
      </footer>
    </>
  );
}
