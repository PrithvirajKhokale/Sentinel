export const MONTHS = ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08"];
export const IDENTITY_FIELDS = ["sector", "ministry", "state", "agency"];
export const VERSION =
  "756d0304736b2f6a61a5fee7363a07e23c583611319fd4f17699ac6f4942d24a";
export const LABELS = {
  legacy_ocms_code: "Legacy OCMS code",
  pmgid: "PMG ID",
  approval_date: "Approval month",
  start_date: "Start month",
  original_target_doc: "Original target month",
  revised_doc: "Revised target month",
  original_cost_rs_crore: "Original cost",
  revised_cost_rs_crore: "Revised cost",
  cumulative_expenditure_rs_crore: "Cumulative expenditure",
  physical_progress_pct: "Physical progress",
};
export const pretty = (s) =>
  LABELS[s?.replace(/_raw$/, "")] ||
  (s || "").replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase());
export function monthLabel(m, short = false) {
  if (!m) return "Unknown";
  const [y, n] = m.split("-");
  return `${["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][Number(n) - 1]}${short ? "" : ` ${y}`}`;
}
// Decimal values remain strings. Formatting never rounds or converts money to floats.
export function decimal(s) {
  if (s === null || s === undefined) return "Unknown";
  const [whole, frac] = String(s).split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return grouped + (frac === undefined ? "" : "." + frac);
}
export function formatValue(v) {
  if (!v || v.normalized === null) return "Unknown";
  if (v.unit === "month") return monthLabel(v.normalized);
  return `${v.unit === "Rs. crore" ? "₹" : ""}${decimal(v.normalized)}${v.unit === "percent" ? "%" : ""}`;
}
export function queryString(params) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    for (const x of Array.isArray(v) ? v : [v]) q.append(k, String(x));
  }
  return q.toString();
}
export function matches(s, filters) {
  return IDENTITY_FIELDS.every(
    (f) => !filters[f]?.length || filters[f].includes(s.identity[f]),
  );
}
// Filter choices retain exact report labels while allowing case-insensitive discovery.
export function matchingFilterOptions(values, input) {
  const needle = input.trim().toLocaleLowerCase();
  return values.filter((v) => v.toLocaleLowerCase().includes(needle));
}

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
export class APIError extends Error {
  constructor(code, message, details = []) {
    super(message);
    this.code = code;
    this.details = details;
  }
}
export function exampleResponse(db, path, params = {}) {
  // Never synthesize reported warning signals from the partial reference fixtures.
  if (path === "/risk-signals")
    throw new APIError("LIVE_API_REQUIRED", "Risk Intelligence requires the authenticated Live API.");
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
export function createClient(db, config = { mode: "examples" }) {
  let pinned = null;
  return {
    get version() {
      return pinned;
    },
    async get(path, params = {}, signal) {
      let result;
      if (config.mode === "examples")
        result = exampleResponse(db, path, {
          ...params,
          dataset_version: params.dataset_version || pinned,
        });
      else {
        const base = config.base.replace(/\/$/, "");
        const q = {
          ...params,
          dataset_version: params.dataset_version || pinned,
        };
        delete q.full_reference;
        const timeout = AbortSignal.timeout(15000);
        const requestSignal = signal
          ? AbortSignal.any([signal, timeout])
          : timeout;
        let response;
        try {
          response = await fetch(`${base}${path}?${queryString(q)}`, {
            signal: requestSignal,
            credentials: "include",
            headers: config.token
              ? { Authorization: `Bearer ${config.token}` }
              : {},
          });
        } catch (e) {
          if (e.name === "AbortError") throw e;
          throw new APIError(
            "CONNECTION_FAILED",
            "Could not reach the API. Check its URL, authentication, and CORS settings.",
          );
        }
        try {
          result = await response.json();
        } catch {
          throw new APIError(
            "INVALID_RESPONSE",
            "API returned a non-JSON response.",
          );
        }
        if (!response.ok || result.error)
          throw new APIError(
            result.error?.code || `HTTP_${response.status}`,
            result.error?.message || "Request failed.",
            result.error?.details || [],
          );
      }
      if (
        result.meta?.contract_version !== "1" ||
        !Array.isArray(result.warnings) ||
        !result.meta?.dataset_version
      )
        throw new APIError(
          "INVALID_RESPONSE",
          "Response does not match Sentinel contract v1.",
        );
      if (pinned && result.meta.dataset_version !== pinned)
        throw new APIError(
          "DATASET_CHANGED",
          "Dataset revision changed. Reconnect to start a consistent session.",
        );
      pinned = result.meta.dataset_version;
      return result;
    },
  };
}
