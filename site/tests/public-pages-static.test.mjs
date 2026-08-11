import assert from "node:assert/strict";
import { access, readdir, readFile } from "node:fs/promises";
import test from "node:test";

test("GitHub Pages artifact contains only the promoted-strategy decision surface", async () => {
  const html = await readFile(new URL("../pages-dist/index.html", import.meta.url), "utf8");

  assert.match(html, /<html[^>]*lang="zh-Hant-HK"/);
  assert.match(html, /data-public-strategy-count="0"/);
  assert.match(html, /data-public-action="hold-cash"/);
  assert.match(html, /data-promotion-gate="fail-closed"/);
  assert.match(html, /今天不下單/);
  assert.match(html, /0(?:<!-- -->)? 個策略獲准公開/);
  assert.match(html, /不建立新倉，保留現金/);
  assert.match(html, /只有已驗證策略才會提供交易建議/);

  assert.doesNotMatch(html, /data-promoted-strategy=/);
  assert.doesNotMatch(html, /role="tablist"/);
  assert.doesNotMatch(html, /class="allocation-split"/);
  assert.doesNotMatch(html, /class="paper-allocation-lab"/);
  assert.doesNotMatch(html, /US\$(?:1,000|800|200)/);
  assert.doesNotMatch(html, /VUG 80%|GLD 20%|Paper 目標/);
  assert.doesNotMatch(html, /QQQ REPLACEMENT OVERLAY|ROUND 30|13\/20/);
  assert.doesNotMatch(html, /href="\/assets\/|src="\/assets\//);

  const assets = await readdir(new URL("../pages-dist/assets/", import.meta.url));
  assert.equal(assets.some((name) => /PaperAllocationLab|StrategyTabs/.test(name)), false);
  await assert.rejects(
    access(new URL("../pages-dist/data", import.meta.url)),
    "research data must not be copied into the public Pages artifact",
  );
});
