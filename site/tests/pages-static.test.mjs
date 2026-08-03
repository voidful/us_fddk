import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

test("GitHub Pages output is self-contained under the repository base path", async () => {
  const html = await readFile(new URL("../pages-dist/index.html", import.meta.url), "utf8");
  const publicSiteRoot = (process.env.PUBLIC_SITE_URL ?? "https://voidful.github.io/us_fddk").replace(
    /\/$/,
    "",
  );
  assert.match(html, /<html[^>]*lang="zh-Hant"/);
  assert.match(html, /今天不下單/);
  assert.match(html, /v25 Paper 行情截止/);
  assert.match(html, /\/us_fddk\/assets\//);
  assert.ok(html.includes(`${publicSiteRoot}/og.png`));
  assert.doesNotMatch(html, /(?:href|src)="\/assets\//);

  const script = html.match(/(?:src|href)="\/us_fddk\/(assets\/[^"]+\.js)"/);
  assert.ok(script, "expected a repository-prefixed client bundle");
  await access(new URL(`../pages-dist/${script[1]}`, import.meta.url));
  await access(new URL("../pages-dist/.nojekyll", import.meta.url));
});
