type AccountPoint = { date: string; equity: number; drawdown: number };
type ForwardAccount = {
  as_of: string;
  equity: number;
  return: number;
  max_drawdown: number;
  cash: number;
  total_costs: number;
  transactions: number;
  filled_rebalances: number;
  equity_curve: AccountPoint[];
};
type Transaction = {
  date: string;
  signal_date: string;
  ticker: string;
  side: string;
  shares: number;
  price: number;
  notional: number;
  cost: number;
};
type FilledOrder = {
  signal_date: string;
  status: string;
  filled_at?: string;
  turnover?: number;
  cost?: number;
};
type PendingOrder = {
  signal_date: string;
  execute_after: string;
  target_weights: Record<string, number>;
  status: string;
} | null;
type ForwardBenchmarkDiagnostic = {
  annualized_return_difference: number;
  persistence_available: boolean;
  first_half_annualized_difference: number | null;
  second_half_annualized_difference: number | null;
  active_newey_west: { t_stat: number };
};
type ForwardEvidence = {
  promotion_protocol: {
    schema_version: number;
    minimum_annualized_edge: number;
    minimum_active_newey_west_t: number;
  };
  promotion_protocol_sha256: string;
  forward_sessions: number;
  minimum_sessions: number;
  remaining_sessions: number;
  filled_orders_including_initial_allocation: number;
  initial_allocations: number;
  filled_rebalances: number;
  minimum_filled_rebalances: number;
  remaining_filled_rebalances: number;
  return_difference_vs_SPY: number;
  return_difference_vs_matched: number;
  forward_diagnostics: {
    SPY: ForwardBenchmarkDiagnostic;
    matched_80_VUG_20_SHY: ForwardBenchmarkDiagnostic;
  };
  gates: Record<string, boolean>;
  live_confirmed: boolean;
};
type PaperBundle = {
  started_at: string | null;
  as_of: string;
  initial_cash: number;
  cost_bps: number;
  total_costs: number;
  execution_clock: string | null;
  pending_order: PendingOrder;
  recent_transactions: Transaction[];
  recent_filled_orders: FilledOrder[];
  accounts: {
    candidate: ForwardAccount;
    SPY: ForwardAccount;
    matched_80_VUG_20_SHY: ForwardAccount;
  };
  forward_evidence: ForwardEvidence;
};

const money = (value: number) =>
  new Intl.NumberFormat("zh-TW", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

const pct = (value: number, digits = 2) =>
  new Intl.NumberFormat("zh-TW", {
    style: "percent",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);

const gateState = (sampleReady: boolean, passed: boolean) =>
  sampleReady ? (passed ? "通過" : "未通過") : "等待足夠樣本";

const normalizedCurve = (curve: AccountPoint[]) => {
  const initial = curve[0]?.equity ?? 1;
  return curve.map((point) => ({
    date: point.date,
    value: (point.equity / initial) * 100,
  }));
};

export default function V25ForwardBoard({
  paper,
  integrity,
}: {
  paper: PaperBundle;
  integrity: boolean;
}) {
  const forward = paper.forward_evidence;
  const sampleReady =
    forward.gates.at_least_252_new_sessions === true &&
    forward.gates.at_least_6_filled_rebalances === true;
  const materialEdgePassed =
    forward.gates.candidate_annualized_edge_at_least_10bp_vs_SPY === true &&
    forward.gates.candidate_annualized_edge_at_least_10bp_vs_matched === true;
  const persistencePassed =
    forward.gates.candidate_outperforms_SPY_in_both_halves === true &&
    forward.gates.candidate_outperforms_matched_in_both_halves === true;
  const statisticsPassed =
    forward.gates.candidate_active_newey_west_t_at_least_1_96_vs_SPY === true &&
    forward.gates.candidate_active_newey_west_t_at_least_1_96_vs_matched === true;
  const sessionProgress = Math.min(
    (forward.forward_sessions / forward.minimum_sessions) * 100,
    100,
  );
  const rebalanceProgress = Math.min(
    (forward.filled_rebalances / forward.minimum_filled_rebalances) * 100,
    100,
  );
  const accounts: Array<{
    key: keyof PaperBundle["accounts"];
    name: string;
    note: string;
  }> = [
    { key: "candidate", name: "v25 80/20", note: "候選策略" },
    { key: "SPY", name: "SPY", note: "市場 ETF 基準" },
    {
      key: "matched_80_VUG_20_SHY",
      name: "80% VUG／20% SHY",
      note: "相同股票持倉比率控制",
    },
  ];
  const curves = accounts.map((account) => ({
    ...account,
    points: normalizedCurve(paper.accounts[account.key].equity_curve),
  }));
  const hasForwardCurve = curves.every((curve) => curve.points.length > 1);
  const allValues = curves.flatMap((curve) => curve.points.map((point) => point.value));
  const rawMinimum = Math.min(...allValues, 100);
  const rawMaximum = Math.max(...allValues, 100);
  const valuePadding = Math.max((rawMaximum - rawMinimum) * 0.12, 0.5);
  const chartMinimum = rawMinimum - valuePadding;
  const chartMaximum = rawMaximum + valuePadding;
  const chartWidth = 760;
  const chartHeight = 210;
  const chartX = (position: number, count: number) =>
    24 + (position / Math.max(count - 1, 1)) * (chartWidth - 48);
  const chartY = (value: number) =>
    18 +
    ((chartMaximum - value) / Math.max(chartMaximum - chartMinimum, 1e-9)) *
      (chartHeight - 42);
  const colors: Record<keyof PaperBundle["accounts"], string> = {
    candidate: "#173f33",
    SPY: "#b35c45",
    matched_80_VUG_20_SHY: "#b18a3b",
  };

  return (
    <section className="forward-paper-panel" aria-labelledby="v25-forward-title">
      <div className="paper-lab-heading">
        <div>
          <span>LIVE PAPER · 同起點公平競賽</span>
          <h3 id="v25-forward-title">不是看回測冠軍，是看三個真實等待中的組合</h3>
        </div>
        <p>
          三者都從 {paper.started_at} 的 {money(paper.initial_cash)} 現金開始，使用相同
          {paper.cost_bps.toFixed(0)} bps 成本、同一份快照與同一交易日序列。升級合約 v{forward.promotion_protocol.schema_version} 已在第一筆成交前凍結。
        </p>
      </div>

      <div className="forward-score-grid">
        {accounts.map(({ key, name, note }) => {
          const account = paper.accounts[key];
          return (
            <article className={key === "candidate" ? "candidate" : ""} key={key}>
              <div><span>{note}</span><b>{name}</b></div>
              <strong>{money(account.equity)}</strong>
              <dl>
                <div><dt>扣成本回報</dt><dd>{pct(account.return)}</dd></div>
                <div><dt>最大跌幅</dt><dd>{pct(account.max_drawdown, 1)}</dd></div>
                <div><dt>累積成本</dt><dd>{money(account.total_costs)}</dd></div>
                <div><dt>成交筆數</dt><dd>{account.transactions}</dd></div>
              </dl>
              <small>截至 {account.as_of}</small>
            </article>
          );
        })}
      </div>

      <div className="forward-chart" aria-label="v25 三個模擬組合同期市值走勢">
        <div className="forward-chart-head">
          <div><span>同一百美元起跑</span><strong>前瞻累積財富</strong></div>
          <div className="forward-chart-legend">{curves.map((curve) => <span key={curve.key}><i style={{ background: colors[curve.key] }} />{curve.name}</span>)}</div>
        </div>
        {hasForwardCurve ? (
          <>
            <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} role="img" aria-label="候選、SPY 與相同持倉比率控制的前瞻累積財富折線圖">
              <line x1="24" x2={chartWidth - 24} y1={chartY(100)} y2={chartY(100)} className="chart-baseline" />
              {curves.map((curve) => (
                <polyline
                  key={curve.key}
                  points={curve.points.map((point, position) => `${chartX(position, curve.points.length)},${chartY(point.value)}`).join(" ")}
                  fill="none"
                  stroke={colors[curve.key]}
                  strokeWidth={curve.key === "candidate" ? 4 : 2.5}
                  vectorEffect="non-scaling-stroke"
                />
              ))}
            </svg>
            <div className="forward-chart-axis"><span>{curves[0].points[0].date}</span><span>基準 100</span><span>{curves[0].points.at(-1)?.date}</span></div>
          </>
        ) : (
          <div className="forward-chart-empty"><strong>尚無可畫的前瞻走勢</strong><p>第一個真正新增交易日完成後才會出現折線；不把 20 年回測接到 LIVE 圖上。</p></div>
        )}
      </div>

      <div className="forward-progress-grid">
        <article>
          <div><span>新增交易日</span><strong>{forward.forward_sessions} / {forward.minimum_sessions}</strong></div>
          <div className="progress-track" aria-label={`新增交易日進度 ${sessionProgress.toFixed(1)}%`}><i style={{ width: `${sessionProgress}%` }} /></div>
          <p>還缺 {forward.remaining_sessions} 日；不能用回填市場數據縮短等待。</p>
        </article>
        <article>
          <div><span>完成重新平衡</span><strong>{forward.filled_rebalances} / {forward.minimum_filled_rebalances}</strong></div>
          <div className="progress-track" aria-label={`完成重新平衡進度 ${rebalanceProgress.toFixed(1)}%`}><i style={{ width: `${rebalanceProgress}%` }} /></div>
          <p>還缺 {forward.remaining_filled_rebalances} 次；待成交不算完成。首次建倉 {forward.initial_allocations ? "已完成" : "尚未完成"}，也不算六次月度重新平衡。</p>
        </article>
      </div>

      <div className="forward-decision-grid">
        <article className={integrity ? "passed" : "failed"}><span>{integrity ? "✓" : "!"}</span><div><b>三個模擬組合完整性</b><p>{integrity ? "日期、快照、成本與交易日序列同步" : "任一漂移就停止發布"}</p></div></article>
        <article className={!sampleReady ? "waiting" : forward.gates.candidate_return_above_SPY ? "passed" : "failed"}><span>{!sampleReady ? "…" : forward.gates.candidate_return_above_SPY ? "✓" : "!"}</span><div><b>扣成本回報勝 SPY</b><p>{gateState(sampleReady, forward.gates.candidate_return_above_SPY)} · 目前差 {pct(forward.return_difference_vs_SPY)}</p></div></article>
        <article className={!sampleReady ? "waiting" : forward.gates.candidate_return_above_matched ? "passed" : "failed"}><span>{!sampleReady ? "…" : forward.gates.candidate_return_above_matched ? "✓" : "!"}</span><div><b>勝相同持倉比率控制</b><p>{gateState(sampleReady, forward.gates.candidate_return_above_matched)} · 目前差 {pct(forward.return_difference_vs_matched)}</p></div></article>
        <article className={!sampleReady ? "waiting" : forward.gates.candidate_drawdown_not_worse_than_SPY && forward.gates.candidate_drawdown_not_worse_than_matched ? "passed" : "failed"}><span>{!sampleReady ? "…" : forward.gates.candidate_drawdown_not_worse_than_SPY && forward.gates.candidate_drawdown_not_worse_than_matched ? "✓" : "!"}</span><div><b>最大跌幅不比兩基準深</b><p>{gateState(sampleReady, forward.gates.candidate_drawdown_not_worse_than_SPY && forward.gates.candidate_drawdown_not_worse_than_matched)}</p></div></article>
        <article className={!sampleReady ? "waiting" : materialEdgePassed ? "passed" : "failed"}><span>{!sampleReady ? "…" : materialEdgePassed ? "✓" : "!"}</span><div><b>不是只贏一點點</b><p>{gateState(sampleReady, materialEdgePassed)} · 年率化至少多 0.10%；目前對 SPY {pct(forward.forward_diagnostics.SPY.annualized_return_difference)}、公平基準 {pct(forward.forward_diagnostics.matched_80_VUG_20_SHY.annualized_return_difference)}</p></div></article>
        <article className={!sampleReady ? "waiting" : persistencePassed ? "passed" : "failed"}><span>{!sampleReady ? "…" : persistencePassed ? "✓" : "!"}</span><div><b>前後兩半都要贏</b><p>{gateState(sampleReady, persistencePassed)} · 避免只靠一年中的單一事件</p></div></article>
        <article className={!sampleReady ? "waiting" : statisticsPassed ? "passed" : "failed"}><span>{!sampleReady ? "…" : statisticsPassed ? "✓" : "!"}</span><div><b>不是隨機雜訊</b><p>{gateState(sampleReady, statisticsPassed)} · NW t 對 SPY {forward.forward_diagnostics.SPY.active_newey_west.t_stat.toFixed(2)}、公平基準 {forward.forward_diagnostics.matched_80_VUG_20_SHY.active_newey_west.t_stat.toFixed(2)}，門檻 1.96</p></div></article>
      </div>

      <div className="forward-log-grid">
        <article>
          <span>下一筆 Paper 動作</span>
          {paper.pending_order ? (
            <><strong>等待下一個新增交易日開市</strong><p>訊號日 {paper.pending_order.signal_date}；目標 {Object.entries(paper.pending_order.target_weights).map(([ticker, weight]) => `${ticker} ${pct(weight, 0)}`).join("、")}。現在不算成交。</p></>
          ) : (
            <><strong>目前沒有待成交委託</strong><p>已持有的持倉會等到下一個完整月末再檢查。</p></>
          )}
        </article>
        <article>
          <span>不可回填成交紀錄</span>
          {paper.recent_transactions.length ? (
            <><strong>最近 {paper.recent_transactions.length} 筆</strong><p>{paper.recent_transactions.slice(-3).map((item) => `${item.date} ${item.side} ${item.ticker} ${money(item.notional)}`).join("；")}</p></>
          ) : (
            <><strong>尚無成交</strong><p>系統沒有把待成交委託偽裝成已成交，也沒有回填 20 年漂亮歷史。</p></>
          )}
        </article>
      </div>
      <p className="forward-final-decision"><b>目前決定：</b>{forward.live_confirmed ? "前瞻門檻已全數通過，才進入參考配置模式。" : sampleReady ? "一年樣本已滿，但仍有穩健門檻未過；繼續 Paper-only。" : "繼續 Paper-only；樣本未滿前，即使暫時領先也不開放實金參考。"}</p>
    </section>
  );
}
