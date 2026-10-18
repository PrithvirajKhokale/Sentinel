// Browser-level smoke test for the built Sentinel frontend.
//
// This uses a local mock API with a real, source-documented June–July 2026
// comparison. It never connects to the deployed API.
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { resolve, extname, sep } from "node:path";
import { once } from "node:events";
import { chromium as playwrightChromium } from "playwright-core";
import chromium from "@sparticuz/chromium";

const root = resolve(import.meta.dirname, "../dist");
const fixture = JSON.parse(
  await readFile(new URL("../public/reference-data.json", import.meta.url), "utf8"),
);
const history = fixture.examples.monthly_history.response;
const [before, after] = history.data;
const comparison = history.meta.comparisons[0];
const version = fixture.examples.project_list.response.meta.dataset_version;
const observed = [];

function reply(data, { month = "2026-07", total = 0 } = {}) {
  return {
    data,
    meta: {
      contract_version: "1",
      dataset_version: version,
      pagination: { page: 1, page_size: 20, total_items: total, total_pages: total ? 1 : 0 },
      filters: { report_month: month },
    },
    warnings: [],
  };
}
const riskSignal = {
  id: "400298:2026-06:2026-07:reported_progress_decrease",
  project_code: "400298",
  project_name: after.identity.project_name,
  identity: after.identity,
  before_month: "2026-06",
  after_month: "2026-07",
  type: "reported_progress_decrease",
  category: "progress",
  title: "Reported progress decreased",
  explanation: "The later report gives a lower physical-progress percentage. The cause is unknown.",
  evidence: [
    { field: "physical_progress_pct",
      before_raw: comparison.changes.physical_progress_pct_raw.before_raw,
      after_raw: comparison.changes.physical_progress_pct_raw.after_raw,
      status: "decreased",
      delta: comparison.changes.physical_progress_pct_raw.delta },
  ],
  source_files: { before: before.provenance.source_filename, after: after.provenance.source_filename },
  source_pdf_pages: { before: before.provenance.pdf_pages, after: after.provenance.pdf_pages },
  pair_wide_review_required: true,
  review_reasons: comparison.trend_review_reasons,
  identity_review_status: comparison.identity_review_status,
  policy: "reported-signals-v1",
};

const mime = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
};
const server = createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");
  if (url.pathname.startsWith("/api/v1/")) {
    observed.push({
      path: url.pathname,
      query: Object.fromEntries([...url.searchParams.keys()].map(k => [k, url.searchParams.getAll(k)])),
      authorization: req.headers.authorization,
      cookie: req.headers.cookie,
    });
    let payload;
    if (url.pathname === "/api/v1/projects") {
      payload = fixture.examples.project_list.response;
    } else if (url.pathname === "/api/v1/filter-options") {
      payload = reply({ ministry: [after.identity.ministry], sector: [after.identity.sector], state: [after.identity.state], agency: [after.identity.agency] });
    } else if (url.pathname === "/api/v1/risk-signals") {
      const code = url.searchParams.get("project_code");
      const q = url.searchParams.get("q");
      const type = url.searchParams.get("signal_type");
      const month = url.searchParams.get("report_month");
      const allowed = month === "2026-07" &&
        (!code || code === "400298") &&
        (!q || after.identity.project_name.toLowerCase().includes(q.toLowerCase())) &&
        (!type || type === riskSignal.type) &&
        (!url.searchParams.has("sector") || url.searchParams.getAll("sector").includes(after.identity.sector));
      const signals = allowed ? [riskSignal] : [];
      payload = reply({
        report_month: month,
        comparison_month: month === "2026-04" ? null : "2026-06",
        scope: "shared_observed_projects",
        summary: {
          shared_pairs_in_scope: month === "2026-04" ? 0 : 1,
          projects_with_signals: signals.length,
          total_signals: signals.length,
          signal_counts: signals.length ? { reported_progress_decrease: 1 } : {},
          signaled_projects_requiring_pair_review: signals.length,
        },
        signals,
      }, { month, total: signals.length });
    } else if (url.pathname === "/api/v1/projects/400298/history") {
      payload = history;
    } else if (url.pathname === "/api/v1/projects/400298") {
      payload = reply(after);
    } else {
      res.writeHead(404, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: { code: "NOT_FOUND", message: "Mock endpoint unavailable" } }));
      return;
    }
    res.writeHead(200, { "content-type": "application/json", "access-control-allow-origin": "*" });
    res.end(JSON.stringify(payload));
    return;
  }
  const target = resolve(root, "." + (url.pathname === "/" ? "/index.html" : decodeURIComponent(url.pathname)));
  if (!(target === root || target.startsWith(root + sep))) {
    res.writeHead(403); res.end("Forbidden"); return;
  }
  try {
    if (!(await stat(target)).isFile()) throw Error("Not a file");
    res.writeHead(200, { "content-type": mime[extname(target)] || "application/octet-stream" });
    res.end(await readFile(target));
  } catch {
    res.writeHead(404); res.end("Not found");
  }
});

let browser;
try {
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const port = server.address().port;
  browser = await playwrightChromium.launch({
    args: chromium.args,
    executablePath: await chromium.executablePath(),
    headless: true,
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  const errors = [];
  page.on("pageerror", e => errors.push(e.message));
  await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: "networkidle" });

  // Guard: reference-mode observations cannot be presented as the full dataset.
  await page.getByRole("button", { name: "Risk intelligence" }).click();
  await page.getByText("This view requires the validated live API").waitFor();

  await page.getByRole("button", { name: "Connect API" }).click();
  await page.getByRole("radio", { name: /Live Sentinel API/ }).check();
  await page.getByLabel("API base URL").fill(`http://127.0.0.1:${port}/api/v1`);
  await page.getByRole("button", { name: "Connect API" }).last().click();
  await page.getByText("LIVE API SESSION").waitFor();
  await page.getByLabel("Report month").selectOption("2026-07");
  await page.getByLabel("Filter risk signals by project code").fill("400298");
  await page.getByLabel("Search risk signals by project name").fill("NADIKUDE");
  await page.getByLabel("Reported signal type").selectOption("reported_progress_decrease");

  const card = page.locator(".signal-card");
  await card.getByText("Reported progress decreased").waitFor({ timeout: 10000 });
  const text = await card.textContent();
  assert.match(text, /55\.02/);
  assert.match(text, /53\.02/);
  assert.match(text, /Review required/);
  assert.match(text, /FlashReport_June_2026\.pdf/);
  assert.match(text, /FlashReport_July_2026\.pdf/);
  assert.match(text, /unreviewed_identity_change/);

  const expectedFilteredCall = x => x.path === "/api/v1/risk-signals"
    && x.query.report_month?.[0] === "2026-07"
    && x.query.project_code?.[0] === "400298"
    && x.query.q?.[0] === "NADIKUDE"
    && x.query.signal_type?.[0] === "reported_progress_decrease"
    && x.query.dataset_version?.[0] === version;
  const deadline = Date.now() + 10000;
  while (!observed.some(expectedFilteredCall) && Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert.ok(observed.some(expectedFilteredCall),
    "Expected revision-pinned, filtered API request: " +
    JSON.stringify(observed.filter(x => x.path === "/api/v1/risk-signals").slice(-5)));
  assert.ok(observed.every(x => !x.authorization && !x.cookie), "Public API requests must not send credentials");

  await card.getByRole("button", { name: /Inspect project history/ }).click();
  await page.getByText("Nadikude-Srikalahasti 308.7 km").first().waitFor();
  assert.deepEqual(errors, [], "Unexpected browser JavaScript errors");
  console.log("PASS: Risk Intelligence browser smoke — public connection, source evidence, exact filters and history drilldown");
} finally {
  await browser?.close();
  await new Promise(resolve => server.close(resolve));
}
