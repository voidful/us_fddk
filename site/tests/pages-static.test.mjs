import assert from "node:assert/strict";
import { access, readdir, readFile } from "node:fs/promises";
import test from "node:test";

test("GitHub Pages output is self-contained under the repository base path", async () => {
  const html = await readFile(new URL("../pages-dist/index.html", import.meta.url), "utf8");
  const publicSiteRoot = (process.env.PUBLIC_SITE_URL ?? "https://voidful.github.io/us_fddk").replace(
    /\/$/,
    "",
  );
  assert.match(html, /<html[^>]*lang="zh-Hant-HK"/);
  assert.match(html, /LATEST STRATEGY REPORT · v25/);
  assert.match(html, /今日實金動作維持/);
  assert.match(html, /US\$1,000/);
  assert.match(html, /US\$800/);
  assert.match(html, /US\$200/);
  assert.match(html, /目前市場與策略狀況/);
  assert.match(html, /三家實際 ETF 產品路徑/);
  assert.match(html, /181 個滾動五年窗/);
  assert.match(html, /對 SPY 未確認/);
  assert.match(html, /歷史通過，前瞻證據由零開始/);
  assert.match(html, /\/us_fddk\/assets\//);
  assert.ok(html.includes(`${publicSiteRoot}/og.png`));
  assert.doesNotMatch(html, /(?:href|src)="\/assets\//);

  const script = html.match(/(?:src|href)="\/us_fddk\/(assets\/[^"]+\.js)"/);
  assert.ok(script, "expected a repository-prefixed client bundle");
  await access(new URL(`../pages-dist/${script[1]}`, import.meta.url));
  await access(new URL("../pages-dist/.nojekyll", import.meta.url));

  const assetsUrl = new URL("../pages-dist/assets/", import.meta.url);
  const assetNames = await readdir(assetsUrl);
  const javascript = (
    await Promise.all(
      assetNames
        .filter((name) => name.endsWith(".js"))
        .map((name) => readFile(new URL(name, assetsUrl), "utf8")),
    )
  ).join("\n");
  const styles = (
    await Promise.all(
      assetNames
        .filter((name) => name.endsWith(".css"))
        .map((name) => readFile(new URL(name, assetsUrl), "utf8")),
    )
  ).join("\n");
  assert.doesNotMatch(javascript, /IntersectionObserver/);
  assert.doesNotMatch(javascript, /motion-reveal/);
  assert.match(styles, /status-pulse/);
  assert.doesNotMatch(styles, /data-motion=ready|motion-reveal/);
});
