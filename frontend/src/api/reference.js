import { MONTHS, IDENTITY_FIELDS, VERSION } from "../constants.js";
import { matches } from "../utils/filters.js";
import { APIError } from "./errors.js";

export function qualityCounts(snapshots) {
  const flags = new Map(),
    missing = new Map();
  for (const s of snapshots) {
    for (const w of s.quality.snapshot_flags)
      for (const f of w.fields) {
        const k = w.code + "|" + f;
        flags.set(k, (flags.get(k) || 0) + 1);
      }
    for (const [f, v] of Object.entries(s.values))
      if (v.missing_reason) {
        const k = f + "|" + v.missing_reason;
        missing.set(k, (missing.get(k) || 0) + 1);
      }
  }
  return {
    snapshot_flags: [...flags].map(([k, count]) => {
      const [code, field] = k.split("|");
      return { code, field, count };
    }),
    missing_values: [...missing].map(([k, count]) => {
      const [field, missing_reason] = k.split("|");
      return { field, missing_reason, count };
    }),
  };
}
const counter = (a) => a.reduce((r, x) => ((r[x] = (r[x] || 0) + 1), r), {});
export function exampleResponse(db, path, params = {}) {
  if (params.dataset_version && params.dataset_version !== VERSION)
    throw new APIError(
      "DATASET_NOT_FOUND",
      "This reference revision is unavailable.",
    );
  const report = params.report_month;
  if (report && !MONTHS.includes(report))
    throw new APIError("REPORT_NOT_AVAILABLE", "Report month is unavailable.");
  const page = Number(params.page || 1),
    size = Number(params.page_size || 25);
  if (
    !Number.isInteger(page) ||
    page < 1 ||
    !Number.isInteger(size) ||
    size < 1 ||
    size > 100
  )
    throw new APIError("VALIDATION_ERROR", "Invalid pagination.");
  const meta = {
    contract_version: "1",
    dataset_version: VERSION,
    validation_status: "validated_history",
    filters: params,
    reference_sample: true,
    source_commit: db.source_commit,
  };
  const envelope = (data, warnings = []) => ({ data, meta, warnings });
  const paginate = (rows) => {
    meta.pagination = {
      page,
      page_size: size,
      total_items: rows.length,
      total_pages: Math.ceil(rows.length / size),
    };
    return rows.slice((page - 1) * size, page * size);
  };
  if (path === "/filter-options") {
    const other = params.comparison_month;
    if (other && MONTHS.indexOf(report) - MONTHS.indexOf(other) !== 1)
      throw new APIError("VALIDATION_ERROR", "Comparison must use the immediately preceding month.");
    const months = [report, ...(other ? [other] : [])];
    return envelope(Object.fromEntries(
      IDENTITY_FIELDS.map((field) => [field, [
        ...new Set(db.snapshots
          .filter((s) => months.includes(s.report_month))
          .map((s) => s.identity[field])
          .filter(Boolean)),
      ].sort((a, b) => a.localeCompare(b))]),
    ));
  }
  if (path === "/projects") {
    let rows = db.snapshots.filter(
      (s) => s.report_month === report && matches(s, params),
    );
    if (params.project_code?.length)
      rows = rows.filter((s) => params.project_code.includes(s.project_code));
    if (params.q)
      rows = rows.filter((s) =>
        s.identity.project_name.toLowerCase().includes(params.q.toLowerCase()),
      );
    return envelope(
      paginate(
        rows.sort((a, b) => a.project_code.localeCompare(b.project_code)),
      ),
    );
  }
  const match = path.match(/^\/projects\/([^/]+)(\/history)?$/);
  if (match) {
    const code = decodeURIComponent(match[1]),
      all = db.snapshots.filter((s) => s.project_code === code);
    if (!all.length)
      throw new APIError(
        "PROJECT_NOT_FOUND",
        "Project code is not included in the reference sample.",
      );
    if (!match[2]) {
      const s = all.find((s) => s.report_month === report);
      if (!s)
        throw new APIError(
          "REFERENCE_SNAPSHOT_UNAVAILABLE",
          "This month is not included in the reference sample. This does not establish report absence.",
        );
      return envelope(s);
    }
    const start = params.from_month || MONTHS[0],
      end = params.to_month || MONTHS.at(-1);
    if (!MONTHS.includes(start) || !MONTHS.includes(end))
      throw new APIError(
        "REPORT_NOT_AVAILABLE",
        "Report range is unavailable.",
      );
    if (start > end)
      throw new APIError(
        "VALIDATION_ERROR",
        "From month must not exceed to month.",
      );
    const rows = all
      .filter((s) => s.report_month >= start && s.report_month <= end)
      .sort((a, b) => a.report_month.localeCompare(b.report_month));
    meta.filters = { from_month: start, to_month: end };
    meta.comparisons = db.comparisons.filter(
      (p) =>
        p.project_code === code &&
        p.before_month >= start &&
        p.after_month <= end,
    );
    meta.not_observed_months = []; // Fixture omissions are not evidence of report absence.
    meta.sample_omitted_months = MONTHS.filter(
      (m) => m >= start && m <= end && !rows.some((s) => s.report_month === m),
    );
    const warnings =
      code === "400298" ? db.examples.monthly_history.response.warnings : [];
    return envelope(paginate(rows), warnings);
  }
  if (path === "/portfolio-summary") {
    const beforeMonth = params.comparison_month;
    if (
      beforeMonth &&
      MONTHS.indexOf(report) - MONTHS.indexOf(beforeMonth) !== 1
    )
      throw new APIError(
        "VALIDATION_ERROR",
        "Comparison must use the immediately preceding month.",
      );
    if (
      params.full_reference &&
      report === "2026-08" &&
      beforeMonth === "2026-07" &&
      IDENTITY_FIELDS.every((f) => !params[f]?.length)
    )
      return structuredClone(db.examples.portfolio_summary.response);
    const afterAll = db.snapshots.filter((s) => s.report_month === report),
      after = afterAll.filter((s) => matches(s, params));
    const data = {
      report_month: report,
      counts: {
        snapshot_records: after.length,
        distinct_project_codes: new Set(after.map((s) => s.project_code)).size,
        ministries: new Set(after.map((s) => s.identity.ministry)).size,
        sectors: new Set(after.map((s) => s.identity.sector)).size,
      },
      quality_counts: qualityCounts(after),
      comparison: null,
    };
    if (beforeMonth) {
      const beforeAll = db.snapshots.filter(
          (s) => s.report_month === beforeMonth,
        ),
        before = beforeAll.filter((s) => matches(s, params));
      const a = new Map(before.map((s) => [s.project_code, s])),
        b = new Map(after.map((s) => [s.project_code, s]));
      const shared = [...a.keys()].filter((c) => b.has(c));
      const pairs = db.comparisons.filter(
        (p) =>
          p.before_month === beforeMonth &&
          p.after_month === report &&
          shared.includes(p.project_code),
      );
      const presence = [];
      let unresolved = 0;
      for (const [rows, otherAll, otherScope, side] of [
        [before, afterAll, b, "before_only"],
        [after, beforeAll, a, "after_only"],
      ])
        for (const s of rows)
          if (!otherScope.has(s.project_code)) {
            if (otherAll.some((x) => x.project_code === s.project_code))
              presence.push({
                project_code: s.project_code,
                presence: side,
                reason: "not_in_filtered_scope",
              });
            else unresolved++;
          }
      meta.unresolved_sample_presence = unresolved;
      data.comparison = {
        before_month: beforeMonth,
        after_month: report,
        before_scope_count: before.length,
        after_scope_count: after.length,
        shared_scope_codes: shared.length,
        before_only: before.length - shared.length,
        after_only: after.length - shared.length,
        presence_scope: "filtered_report",
        presence,
        presence_breakdown: {
          before_only: counter(
            presence
              .filter((p) => p.presence === "before_only")
              .map((p) => p.reason),
          ),
          after_only: counter(
            presence
              .filter((p) => p.presence === "after_only")
              .map((p) => p.reason),
          ),
        },
        progress_changes: counter(
          pairs.map((p) => p.changes.physical_progress_pct_raw.status),
        ),
        expenditure_changes: counter(
          pairs.map(
            (p) => p.changes.cumulative_expenditure_rs_crore_raw.status,
          ),
        ),
        completion_date_changes: Object.fromEntries(
          ["original_target_doc_raw", "revised_doc_raw"].map((f) => [
            f,
            counter(pairs.map((p) => p.changes[f].status)),
          ]),
        ),
        missing_field_records: pairs.filter(
          (p) =>
            Object.keys(p.before_missing_values).length ||
            Object.keys(p.after_missing_values).length,
        ).length,
        missing_input_counts: Object.keys(
          after[0]?.values || before[0]?.values || {},
        ).map((field) => {
          const first = shared.filter(
              (c) => a.get(c).values[field].normalized === null,
            ).length,
            last = shared.filter(
              (c) => b.get(c).values[field].normalized === null,
            ).length,
            either = shared.filter(
              (c) =>
                a.get(c).values[field].normalized === null ||
                b.get(c).values[field].normalized === null,
            ).length;
          return {
            field,
            before_missing: first,
            after_missing: last,
            either_missing: either,
            both_known: shared.length - either,
          };
        }),
        before_quality_counts: qualityCounts(before),
        after_quality_counts: qualityCounts(after),
        screening_policy: "monthly-history-v1",
        trend_eligible: pairs.filter((p) => p.trend_eligible).length,
        trend_excluded: pairs.filter((p) => !p.trend_eligible).length,
        exclusion_reasons: counter(
          pairs.flatMap((p) => p.trend_review_reasons),
        ),
      };
    }
    return envelope(data);
  }
  throw new APIError("NOT_FOUND", "Unknown endpoint.");
}
