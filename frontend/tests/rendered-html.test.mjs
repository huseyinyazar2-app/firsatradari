import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

const projectRoot = new URL("../", import.meta.url);

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the research workspace shell", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<html lang="tr">/);
  assert.match(html, /<title>Araştırma Masası \| Fırsat Radarı<\/title>/);
  assert.match(html, /Fırsat Radarı/);
  assert.match(html, /Problem keşfi/);
  assert.match(html, /Kaynaklar/);
  assert.match(html, /Veriler yükleniyor/);
  assert.doesNotMatch(html, /Your site is taking shape|react-loading-skeleton/);
});

test("removes the disposable starter and keeps API integration local", async () => {
  const [dashboard, packageJson] = await Promise.all([
    readFile(new URL("../app/research-dashboard.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  assert.match(dashboard, /http:\/\/127\.0\.0\.1:8000/);
  assert.match(dashboard, /\/problem-clusters\?status=cross_entity_candidate/);
  assert.match(dashboard, /\/opportunity-score-runs/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
  await assert.rejects(access(new URL("app/_sites-preview/SkeletonPreview.tsx", projectRoot)));
});
