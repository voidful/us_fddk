import { cp, mkdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";

const projectRoot = process.cwd();
const output = path.join(projectRoot, "pages-dist");
const configuredBase = process.env.PAGES_BASE_PATH ?? "/us_fddk";
const basePath = `/${configuredBase.split("/").filter(Boolean).join("/")}`;

await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
await cp(path.join(projectRoot, "dist/client"), output, { recursive: true });

const workerUrl = new URL("../dist/server/index.js", import.meta.url);
workerUrl.searchParams.set("pages", `${process.pid}-${Date.now()}`);
const { default: worker } = await import(workerUrl.href);
const response = await worker.fetch(
  new Request("http://localhost/", { headers: { accept: "text/html" } }),
  { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
  { waitUntil() {}, passThroughOnException() {} },
);
if (!response.ok) {
  throw new Error(`Static render failed with HTTP ${response.status}`);
}

const rendered = await response.text();
const html = rendered.replaceAll("/assets/", `${basePath}/assets/`);
if (html.includes('href="/assets/') || html.includes('src="/assets/')) {
  throw new Error("Static HTML still contains a root-relative build asset");
}
await writeFile(path.join(output, "index.html"), html, "utf8");
await writeFile(path.join(output, "404.html"), html, "utf8");
await writeFile(path.join(output, ".nojekyll"), "", "utf8");

console.log(`GitHub Pages artifact: ${output} (base ${basePath})`);
