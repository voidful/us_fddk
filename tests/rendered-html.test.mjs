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
  assert.match(html, /data-signal-freshness="checking"/);
  assert.match(html, /今天不用猜/);
  assert.match(html, /等待模擬成交/);
  assert.match(html, /QQQ 75\.5%/);
  assert.match(html, /SHY 24\.5%/);
  assert.match(html, /18% 目標波動/);
  assert.match(html, /固定 18% 目標波動政策/);
  assert.match(html, /統計尚未確認/);
  assert.match(html, /LIVE 累積中/);
  assert.match(html, /SPY 同期/);
  assert.match(html, /QQQ 同期/);
  assert.match(html, /同一天現金起跑/);
  assert.match(html, /資料已過期/);
  assert.match(html, /停止參考舊配置/);
  assert.match(html, /Paper trade 不回填漂亮歷史/);
  assert.match(html, /研究與教育用途，不構成投資建議/);
  assert.doesNotMatch(html, /固定 80\/20 政策/);
  assert.doesNotMatch(html, /Your site is taking shape|react-loading-skeleton/);
});

test("mobile controls keep safe touch targets and readable FAQ spacing", async () => {
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(css, /\.brand \{ min-height: 44px;/);
  assert.match(css, /\.quick-values button \{ min-height: 44px;/);
  assert.match(css, /\.faq-list details p \{[^}]*margin: 12px 0 24px;/);
  assert.doesNotMatch(css, /\.faq-list details p \{[^}]*margin: -/);
});
