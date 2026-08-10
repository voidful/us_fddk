import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("public-home", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

function assertPublicDecisionSurface(html) {
  assert.match(html, /<html[^>]*lang="zh-Hant-HK"/);
  assert.match(html, /data-public-strategy-count="0"/);
  assert.match(html, /data-public-action="hold-cash"/);
  assert.match(html, /data-promotion-gate="fail-closed"/);
  assert.match(html, /今天不下單/);
  assert.match(html, /0(?:<!-- -->)? 個策略獲准公開/);
  assert.match(html, /目前沒有可公開的已驗證策略；今日維持現金/);
  assert.match(html, /不建立新倉，保留現金/);
  assert.match(html, /不把 Paper 持倉當成落盤訊號/);
  assert.match(html, /只有已驗證策略才會提供交易建議/);
  assert.match(html, /研究日誌與機器收據/);
  assert.doesNotMatch(html, /失敗|淘汰|攻擊測試|負結果|未通過項目/);

  assert.doesNotMatch(html, /data-promoted-strategy=/);
  assert.doesNotMatch(html, /role="tablist"/);
  assert.doesNotMatch(html, /class="allocation-split"/);
  assert.doesNotMatch(html, /class="paper-allocation-lab"/);
  assert.doesNotMatch(html, /US\$(?:1,000|800|200)/);
  assert.doesNotMatch(html, /VUG 80%|GLD 20%|Paper 目標/);
  assert.doesNotMatch(html, /QQQ REPLACEMENT OVERLAY|ROUND 30|13\/20/);
  assert.doesNotMatch(html, /短窗贏家策略|攻擊全拒收|舊策略研究/);
}

test("public home renders only the fail-closed action when no strategy is promoted", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  assertPublicDecisionSurface(await response.text());
});

test("public page imports only the success-only decision contract", async () => {
  const source = await readFile(new URL("../app/PublicDecisionPage.tsx", import.meta.url), "utf8");
  const decision = JSON.parse(
    await readFile(new URL("../data/public-decision.json", import.meta.url), "utf8"),
  );
  assert.doesNotMatch(source, /trading-data|formal-backtest-readiness|qqq-replacement-overlay/);
  assert.equal(decision.surface, "hold-cash");
  assert.deepEqual(decision.strategies, []);
  const rendered = JSON.stringify(decision);
  assert.doesNotMatch(rendered, /失敗|淘汰|攻擊測試|負結果|未通過項目/);
});
