import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  exampleResponse,
  createClient,
  queryString,
  decimal,
  VERSION,
  matchingFilterOptions,
} from "../src/api/index.js";
const db = JSON.parse(
  fs.readFileSync(new URL("../public/reference-data.json", import.meta.url)),
);
test("filter suggestions are exact labels and support case-insensitive typing", () => {
  const options = exampleResponse(db, "/filter-options", {
    report_month: "2026-08",
    comparison_month: "2026-07",
  });
  assert.equal(options.meta.dataset_version, VERSION);
  for (const field of ["sector", "ministry", "state", "agency"]) {
    assert.ok(options.data[field].length > 0);
    assert.equal(options.data[field].length, new Set(options.data[field]).size);
    assert.deepEqual(
      options.data[field],
      [...options.data[field]].sort((a, b) => a.localeCompare(b)),
    );
  }
  const single = exampleResponse(db, "/filter-options", { report_month: "2026-08" });
  const before = exampleResponse(db, "/filter-options", { report_month: "2026-07" });
  for (const field of ["sector", "ministry", "state", "agency"]) {
    assert.deepEqual(
      new Set(options.data[field]),
      new Set([...single.data[field], ...before.data[field]]),
    );
  }
  const ministries = options.data.ministry;
  const needle = ministries[0].slice(0, 4).toUpperCase();
  assert.ok(matchingFilterOptions(ministries, needle).includes(ministries[0]));
  assert.deepEqual(matchingFilterOptions(["Railways", "Water Resources"], "wATeR"), ["Water Resources"]);
  assert.deepEqual(matchingFilterOptions(["Power", "Roads"], "no-match"), []);
  assert.throws(() => exampleResponse(db, "/filter-options", {
    report_month: "2026-08", comparison_month: "2026-06",
  }), { code: "VALIDATION_ERROR" });
});

test("documented list and detail values remain exact, including zeros, nulls and source cells", () => {
  const examples = db.examples;
  assert.deepEqual(
    exampleResponse(db, "/projects", {
      report_month: "2026-08",
      project_code: ["701530"],
    }).data,
    examples.project_list.response.data,
  );
  assert.deepEqual(
    exampleResponse(db, "/projects/701530", { report_month: "2026-07" }).data,
    examples.project_detail.response.data,
  );
  assert.equal(
    examples.project_detail.response.data.values.physical_progress_pct
      .normalized,
    "0",
  );
  assert.equal(
    examples.project_detail.response.data.values.revised_doc.normalized,
    null,
  );
  assert.equal(
    examples.project_detail.response.data.values.revised_doc.raw,
    "(-)",
  );
  assert.deepEqual(
    examples.project_detail.response.data.provenance.physical_cells,
    exampleResponse(db, "/projects/701530", { report_month: "2026-07" }).data
      .provenance.physical_cells,
  );
});
test("history preserves documented changes and comparison metadata beyond snapshot pagination", () => {
  const r = exampleResponse(db, "/projects/400298/history", {
    from_month: "2026-06",
    to_month: "2026-07",
    page_size: 1,
    page: 2,
  });
  assert.equal(r.data.length, 1);
  assert.equal(r.meta.pagination.total_items, 2);
  assert.deepEqual(
    r.meta.comparisons,
    db.examples.monthly_history.response.meta.comparisons,
  );
  assert.equal(
    r.meta.comparisons[0].changes.physical_progress_pct_raw.delta,
    "-53.02",
  );
  const empty = exampleResponse(db, "/projects/400298/history", {
    from_month: "2026-06",
    to_month: "2026-07",
    page_size: 1,
    page: 9,
  });
  assert.equal(empty.data.length, 0);
  assert.equal(empty.meta.comparisons.length, 1);
});
test("sample omissions never become fabricated report gaps or bridged comparison pairs", () => {
  const r = exampleResponse(db, "/projects/400298/history", {});
  assert.deepEqual(r.meta.not_observed_months, []);
  assert.ok(r.meta.sample_omitted_months.includes("2026-08"));
  for (const p of db.comparisons)
    assert.equal(
      Number(p.after_month.slice(5)) - Number(p.before_month.slice(5)),
      1,
    );
});
test("search is a case-insensitive literal name substring and source-code sorting is stable", () => {
  const r = exampleResponse(db, "/projects", {
    report_month: "2026-08",
    q: "AIRPORT",
    page_size: 100,
  });
  assert.ok(r.data.length >= 3);
  assert.ok(
    r.data.every((s) =>
      s.identity.project_name.toLowerCase().includes("airport"),
    ),
  );
  assert.equal(
    exampleResponse(db, "/projects", { report_month: "2026-08", q: "%" }).data
      .length,
    0,
  );
  const codes = r.data.map((s) => s.project_code);
  assert.deepEqual(codes, [...codes].sort());
});
test("repeated exact identity filters use OR within a field and AND across fields", () => {
  const r = exampleResponse(db, "/projects", {
    report_month: "2026-08",
    sector: ["Railways", "Water Resources"],
    state: ["Karnataka"],
    page_size: 100,
  });
  assert.ok(
    r.data.every(
      (s) =>
        ["Railways", "Water Resources"].includes(s.identity.sector) &&
        s.identity.state === "Karnataka",
    ),
  );
  assert.equal(
    exampleResponse(db, "/projects", {
      report_month: "2026-08",
      sector: ["railways"],
    }).data.length,
    0,
  );
  assert.match(
    queryString({ sector: ["Railways", "Water Resources"] }),
    /sector=Railways&sector=Water\+Resources/,
  );
});
test("portfolio full reference is verbatim and counts reconcile without fabricated missing inputs", () => {
  const r = exampleResponse(db, "/portfolio-summary", {
    report_month: "2026-08",
    comparison_month: "2026-07",
    full_reference: true,
  });
  assert.deepEqual(r, db.examples.portfolio_summary.response);
  const c = r.data.comparison;
  assert.equal(c.shared_scope_codes + c.before_only, c.before_scope_count);
  assert.equal(c.shared_scope_codes + c.after_only, c.after_scope_count);
  assert.equal(c.trend_eligible, 0);
  assert.equal(c.exclusion_reasons.baseline_revised_cost_rs_crore_raw, 1694);
});
test("independent month filters distinguish a demonstrated agency scope change", () => {
  const agency = db.examples.monthly_history.response.data[0].identity.agency;
  const r = exampleResponse(db, "/portfolio-summary", {
    report_month: "2026-07",
    comparison_month: "2026-06",
    agency: [agency],
  });
  assert.ok(
    r.data.comparison.presence.some(
      (p) =>
        p.project_code === "400298" &&
        p.reason === "not_in_filtered_scope" &&
        p.presence === "before_only",
    ),
  );
  assert.ok(
    !r.data.comparison.presence.some(
      (p) => p.reason === "not_observed_in_report",
    ),
  );
});
test("exact decimal display preserves large and fractional strings without rounding", () => {
  assert.equal(
    decimal("9007199254740993.012300"),
    "9,007,199,254,740,993.012300",
  );
  assert.equal(decimal("0"), "0");
  assert.equal(decimal(null), "Unknown");
});
test("invalid range, comparison and revisions return explicit errors", () => {
  assert.throws(
    () =>
      exampleResponse(db, "/projects/701530/history", {
        from_month: "2026-08",
        to_month: "2026-04",
      }),
    { code: "VALIDATION_ERROR" },
  );
  assert.throws(
    () =>
      exampleResponse(db, "/portfolio-summary", {
        report_month: "2026-08",
        comparison_month: "2026-06",
      }),
    { code: "VALIDATION_ERROR" },
  );
  assert.throws(
    () =>
      exampleResponse(db, "/projects", {
        report_month: "2026-08",
        dataset_version: "bad",
      }),
    { code: "DATASET_NOT_FOUND" },
  );
});
test("live client pins the dataset, handles error envelopes and refuses mixed revisions", async () => {
  const previous = globalThis.fetch;
  const urls = [];
  let n = 0;
  globalThis.fetch = async (url) => {
    urls.push(url);
    return {
      ok: true,
      json: async () => ({
        ...db.examples.project_list.response,
        meta: {
          ...db.examples.project_list.response.meta,
          dataset_version: n++ < 2 ? VERSION : "f".repeat(64),
        },
      }),
    };
  };
  try {
    const c = createClient(db, {
      mode: "live",
      base: "https://test.example/api/v1",
    });
    await c.get("/projects", { report_month: "2026-08" });
    await c.get("/projects", { report_month: "2026-08", page: 2 });
    assert.ok(urls[1].includes(`dataset_version=${VERSION}`));
    await assert.rejects(
      () => c.get("/projects", { report_month: "2026-08" }),
      { code: "DATASET_CHANGED" },
    );
    globalThis.fetch = async () => ({
      ok: false,
      json: async () => db.examples.validation_error.response,
    });
    await assert.rejects(
      () =>
        createClient(db, {
          mode: "live",
          base: "https://test.example/api/v1",
        }).get("/projects", {}),
      { code: "VALIDATION_ERROR" },
    );
  } finally {
    globalThis.fetch = previous;
  }
});
