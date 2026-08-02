import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

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

test("server-renders the beginner trading reference", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<html[^>]*lang="zh-Hant"/);
  assert.match(html, /成長守門員 v2｜降回撤有效，不等於穩健超額/);
  assert.match(html, /https:\/\/growth-guard-tw\.voidful819957\.chatgpt\.site\/og\.png/);
  assert.match(html, /data-signal-freshness="checking"/);
  assert.match(html, /今天不下單/);
  assert.match(html, /不建立實金部位/);
  assert.match(html, /今日實金動作：0/);
  assert.match(html, /不顯示可照抄的 ETF 百分比或金額/);
  assert.match(html, /目前沒有實金配置/);
  assert.match(html, /實金配置鎖定中/);
  assert.doesNotMatch(html, /我的試算資金/);
  assert.match(html, /固定 18% 目標波動政策/);
  assert.match(html, /統計尚未確認/);
  assert.match(html, /曝險控制未通過/);
  assert.match(html, /資料可安全發布/);
  assert.match(html, /實金參考未開放/);
  assert.match(html, /Paper 與實金都停止參考/);
  assert.match(html, /更新與完整性檢查完成前維持關閉/);
  assert.match(html, /不可回填的等待期/);
  assert.match(html, /維持 Paper-only/);
  assert.match(html, /為什麼資料檢查通過，還是不能下單/);
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
  assert.match(html, /舊代理資料門檻失敗/);
  assert.match(html, /2002-09-30/);
  assert.match(html, /v4 回撤較淺，為什麼連 Paper 都不開/);
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
  assert.match(html, /ETF 主期 · 策略 \/ SPY 年化/);
  assert.match(html, /10\.00%/);
  assert.match(html, /11\.27%/);
  assert.match(html, /同總權益曝險下，選產業沒有增加淨報酬/);
  assert.match(html, /負結果已封存/);
  assert.match(html, /不可照單、不提供金額試算/);
  assert.match(html, /v6 長期代理有效，為什麼還是淘汰/);
  assert.match(html, /1989–2026 · v7 相對成長衛星/);
  assert.match(html, /政策值得理解，不代表可以照單/);
  assert.match(html, /v7 回撤比 SPY 淺，為什麼仍不建立 Paper/);
  assert.match(html, /1989–2026 · v8 永遠持股相對成長/);
  assert.match(html, /最接近目標，不等於通過/);
  assert.match(html, /v8 已經連續兩段都跑贏市場/);
  assert.match(html, /1973–2026 · v9 低換手＋下載前未見外部期/);
  assert.match(html, /政策狀態不等於今天的下單建議/);
  assert.match(html, /v9 已減少交易，為什麼成本門檻還是失敗/);
  assert.match(html, /1973–2026 · v10–v12 階層式三態/);
  assert.match(html, /回撤改善了，為什麼仍不能當成跑贏 ETF 策略/);
  assert.match(html, /Paper 指令鎖定/);
  assert.match(html, /v12 已把回撤壓低，為什麼仍不值得 Paper/);
  assert.match(html, /2006–2026 · v13 規則先鎖定、再下載新 ETF/);
  assert.match(html, /已知年代看起來進步，真正的新資料答應了嗎/);
  assert.match(html, /道新資料經濟門檻/);
  assert.match(html, /少跌不等於有能力跑贏/);
  assert.match(html, /v13 交易更少、舊年代更好，為什麼還是淘汰/);
  assert.match(html, /2006–2026 · v14 先凍結、再下載實際槓桿 ETF/);
  assert.match(html, /小幅槓桿加趨勢，真的能兼顧報酬與風險嗎/);
  assert.match(html, /槓桿不是免費報酬，少跌也不能抵銷少賺/);
  assert.match(html, /v14 的 Nasdaq 結果贏 QQQ，為什麼仍不開 Paper/);
  assert.match(html, /2011–2026 · v15 先凍結、再首次查看實際 3 倍 ETF/);
  assert.match(html, /三市場都賺比較多，就能稱為穩健跑贏嗎/);
  assert.match(html, /報酬放大了，虧損也放大了/);
  assert.match(html, /不能拼成「獨立 20 年」/);
  assert.match(html, /v15 三市場年化都贏 ETF，為什麼還是不能 Paper/);
  assert.match(html, /2008–2026 · v16 中小型股週度趨勢／波動煞車/);
  assert.match(html, /少跌一些，是否值得犧牲一半以上報酬/);
  assert.match(html, /v16 已降低回撤，為什麼連 Paper 都不開/);
  assert.match(html, /2006–2026 \/ 2008–2026 · v17 六市場股債資本效率/);
  assert.match(html, /年化比較高，為什麼仍不是穩健策略/);
  assert.match(html, /更高 CAGR 不是免費午餐/);
  assert.match(html, /v17 六市場 CAGR 多數較高，為什麼仍不算跑贏/);
  assert.match(html, /2010–2026 · v18 規則先凍結、再下載 EFO／EET 日線/);
  assert.match(html, /六個美國市場都好看，海外還能重現嗎/);
  assert.match(html, /美國回測成功，不代表規則能泛化/);
  assert.match(html, /v18 在六個美國市場都改善，為什麼海外失敗更重要/);
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
  assert.match(html, /資料已過期/);
  assert.match(html, /停止參考舊配置/);
  assert.match(html, /Paper trade 不回填漂亮歷史/);
  assert.match(html, /價格重基準/);
  assert.match(html, /不回寫既有損益/);
  assert.match(html, /為什麼除息後 Paper 單位數可能改變/);
  assert.match(html, /不是券商實際股數/);
  assert.match(html, /研究與教育用途，不構成投資建議/);
  assert.doesNotMatch(html, /固定 80\/20 政策/);
  assert.doesNotMatch(html, /Your site is taking shape|react-loading-skeleton/);
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
  assert.ok(payload.limitations.some((item) => /v13 先凍結兩月確認.*新資料經濟門檻 9\/30/.test(item)));
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

test("mobile controls keep safe touch targets and readable FAQ spacing", async () => {
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(css, /\.brand \{ min-height: 44px;/);
  assert.match(css, /\.quick-values button \{ min-height: 44px;/);
  assert.match(css, /\.faq-list details p \{[^}]*margin: 12px 0 24px;/);
  assert.doesNotMatch(css, /\.faq-list details p \{[^}]*margin: -/);
});
