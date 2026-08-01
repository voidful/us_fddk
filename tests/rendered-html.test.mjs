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
  assert.match(html, /真正難的基準：不用預測的 90\/10/);
  assert.match(html, /5 年滾動勝率至少 75%/);
  assert.match(html, /保留 Paper 追蹤，不升級成實金參考策略/);
  assert.match(html, /v3 在 20 年贏 QQQ/);
  assert.match(html, /1986–2006 · 更早期代理/);
  assert.match(html, /36\.9%/);
  assert.match(html, /不替換 v2；v3 留在隔離 Paper/);
  assert.match(html, /任何漂移都拒絕更新網站/);
  assert.match(html, /獨立 Paper 驗證/);
  assert.match(html, /252 日/);
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
});

test("mobile controls keep safe touch targets and readable FAQ spacing", async () => {
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(css, /\.brand \{ min-height: 44px;/);
  assert.match(css, /\.quick-values button \{ min-height: 44px;/);
  assert.match(css, /\.faq-list details p \{[^}]*margin: 12px 0 24px;/);
  assert.doesNotMatch(css, /\.faq-list details p \{[^}]*margin: -/);
});
