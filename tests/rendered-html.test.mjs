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
  assert.match(html, /先別急著照單/);
  assert.match(html, /只做 Paper，不照單/);
  assert.match(html, /QQQ 75\.5%/);
  assert.match(html, /SHY 24\.5%/);
  assert.match(html, /18% 目標波動/);
  assert.match(html, /固定 18% 目標波動政策/);
  assert.match(html, /統計尚未確認/);
  assert.match(html, /曝險控制未通過/);
  assert.match(html, /資料可安全發布/);
  assert.match(html, /實金參考未開放/);
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
  assert.equal(payload.readiness.contract_version, 2);
  assert.equal(payload.readiness.trade_ready, false);
  assert.equal(payload.readiness.decision, "paper_only");
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

test("mobile controls keep safe touch targets and readable FAQ spacing", async () => {
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(css, /\.brand \{ min-height: 44px;/);
  assert.match(css, /\.quick-values button \{ min-height: 44px;/);
  assert.match(css, /\.faq-list details p \{[^}]*margin: 12px 0 24px;/);
  assert.doesNotMatch(css, /\.faq-list details p \{[^}]*margin: -/);
});
