import assert from "node:assert/strict";
import { access, readdir, readFile } from "node:fs/promises";
import test from "node:test";

test("GitHub Pages artifact contains only the promoted-strategy decision surface", async () => {
  const html = await readFile(new URL("../pages-dist/index.html", import.meta.url), "utf8");

  assert.match(html, /<html[^>]*lang="zh-Hant-HK"/);
  assert.match(html, /data-public-strategy-count="0"/);
  assert.match(html, /data-public-action="hold-cash"/);
  assert.match(html, /data-promotion-gate="fail-closed"/);
  assert.match(html, /data-public-surface="success-only"/);
  assert.match(html, /今天不下單/);
  assert.match(html, /現時沒有策略通過完整回測及前瞻驗證，維持現金，不建立新倉/);
  assert.match(html, /資料截至/);
  assert.match(html, /本頁只會在完整驗證通過後顯示策略；未通過時不顯示研究細節或投資金額/);

  assert.doesNotMatch(html, /data-promoted-strategy=/);
  assert.doesNotMatch(html, /<nav/);
  assert.doesNotMatch(html, /role="tablist"/);
  assert.doesNotMatch(html, /class="allocation-split"/);
  assert.doesNotMatch(html, /class="paper-allocation-lab"/);
  assert.doesNotMatch(html, /US\$(?:1,000|800|200)/);
  assert.doesNotMatch(html, /VUG 80%|GLD 20%|Paper 目標/);
  assert.doesNotMatch(html, /QQQ REPLACEMENT OVERLAY|ROUND 30|13\/20/);
  assert.doesNotMatch(html, /失敗候選|研究中|淘汰/);
  assert.doesNotMatch(html, /個策略獲准公開|下一個檢查交易日|研究 log 與機器收據/);
  assert.doesNotMatch(html, /Paper/);
  assert.doesNotMatch(html, /property="og:image"|summary_large_image/);
  assert.match(html, /name="twitter:card" content="summary"/);
  assert.doesNotMatch(html, /href="\/assets\/|src="\/assets\//);

  const assets = await readdir(new URL("../pages-dist/assets/", import.meta.url));
  assert.equal(assets.some((name) => /PaperAllocationLab|StrategyTabs/.test(name)), false);
  await assert.rejects(
    access(new URL("../pages-dist/data", import.meta.url)),
    "research data must not be copied into the public Pages artifact",
  );
  await assert.rejects(access(new URL("../pages-dist/og.png", import.meta.url)));
});
