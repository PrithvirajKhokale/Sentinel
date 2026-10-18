import { useState, useEffect } from "react";
import { ArrowUpRight, Layers, ScanLine, GitCompareArrows, Building2, Info, Hash } from "lucide-react";
import { MONTHS, IDENTITY_FIELDS } from "../constants.js";
import { pretty, monthLabel, decimal } from "../utils/format.js";
import { useRequest } from "../hooks/useRequest.js";
import { ErrorBox } from "../components/common/ErrorBox.jsx";
import { Loading } from "../components/common/Loading.jsx";
import { Warnings } from "../components/common/Warnings.jsx";
import { MonthSelect } from "../components/common/MonthSelect.jsx";
import { Metric } from "../components/common/Metric.jsx";
import { Distribution } from "../components/common/Distribution.jsx";
import { Filters } from "../components/filters/Filters.jsx";
import { FilterChips } from "../components/filters/FilterChips.jsx";

export function Portfolio({
  db,
  client,
  mode,
  month,
  setMonth,
  filters,
  setFilters,
  onInspect,
}) {
  const [scope, setScope] = useState("full"),
    [compare, setCompare] = useState(
      MONTHS[Math.max(0, MONTHS.indexOf(month) - 1)],
    );
  useEffect(() => setCompare(MONTHS[MONTHS.indexOf(month) - 1] || ""), [month]);
  const hasFilters = IDENTITY_FIELDS.some((f) => filters[f]?.length);
  const full =
    mode === "examples" &&
    scope === "full" &&
    month === "2026-08" &&
    compare === "2026-07" &&
    !hasFilters;
  const { result, error, loading } = useRequest(client, "/portfolio-summary", {
    report_month: month,
    ...filters,
    ...(compare ? { comparison_month: compare } : {}),
    ...(full ? { full_reference: true } : {}),
  });
  const data = result?.data,
    c = data?.comparison;
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">COMPARE THE OBSERVATIONS</div>
          <h1>
            Portfolio comparisons<span className="heading-dot">.</span>
          </h1>
          <p>
            Reported changes, with the scope and caveats that give them meaning.
          </p>
        </div>
        <MonthSelect value={month} onChange={setMonth} />
      </div>
      <div className="portfolio-controls">
        <div>
          <span className="quiet">Compare with</span>
          <MonthSelect
            label="Comparison month"
            value={compare}
            onChange={setCompare}
            allowNone
            options={MONTHS.filter(
              (m) => MONTHS.indexOf(month) - MONTHS.indexOf(m) === 1,
            )}
          />
        </div>
        <div>
          {mode === "examples" && (
            <label className="scope-select">
              Scope{" "}
              <select
                aria-label="Portfolio data scope"
                value={scope}
                onChange={(e) => setScope(e.target.value)}
              >
                <option value="full">Full report example (Jul → Aug)</option>
                <option value="sample">Reference sample</option>
              </select>
            </label>
          )}
          <Filters
            db={db}
            client={client}
            comparisonMonth={compare}
            month={month}
            filters={filters}
            onChange={setFilters}
            mode={mode}
          />
        </div>
      </div>
      <FilterChips filters={filters} onChange={setFilters} />
      {mode === "examples" && (
        <div className="notice">
          <Info size={17} />
          <p>
            {full
              ? "This is the documented full-report July–August comparison. The example includes aggregate counts; project-level presence and missing-input breakdowns are not included."
              : "These counts describe only the checked reference sample. Filters apply independently to each month. Sample omissions are not treated as report absence."}
          </p>
        </div>
      )}
      {error ? (
        <ErrorBox error={error} />
      ) : loading ? (
        <Loading />
      ) : (
        <>
          <div className="metrics four">
            <Metric
              label="Observed records"
              value={decimal(String(data.counts.snapshot_records))}
              note={`${monthLabel(data.report_month)} · ${full ? "full report" : mode === "examples" ? "reference sample" : "selected scope"}`}
            />
            <Metric
              label="Distinct codes"
              value={decimal(String(data.counts.distinct_project_codes))}
              note="Published ongoing-table observations"
              icon={Hash}
            />
            <Metric
              label="Ministries"
              value={data.counts.ministries}
              note="Exact reported labels"
              icon={Building2}
            />
            <Metric
              label="Sectors"
              value={data.counts.sectors}
              note="Within the selected month"
              icon={Layers}
            />
          </div>
          {c && (
            <>
              <div className="comparison-flow">
                <div>
                  <span>{monthLabel(c.before_month)}</span>
                  <strong>{decimal(String(c.before_scope_count))}</strong>
                  <small>before scope</small>
                </div>
                <div className="flow-shared">
                  <GitCompareArrows size={24} />
                  <strong>{decimal(String(c.shared_scope_codes))}</strong>
                  <small>shared codes</small>
                </div>
                <div>
                  <span>{monthLabel(c.after_month)}</span>
                  <strong>{decimal(String(c.after_scope_count))}</strong>
                  <small>after scope</small>
                </div>
              </div>
              <div className="presence-summary">
                <div>
                  <span className="status-dot decreased" />
                  <strong>{c.before_only}</strong> before only
                  {mode === "examples" && !full && " in sample"}
                </div>
                <div>
                  <span className="status-dot increased" />
                  <strong>{c.after_only}</strong> after only
                  {mode === "examples" && !full && " in sample"}
                </div>
                <p>
                  Presence describes observation or scope. It does not establish
                  project start or completion.
                </p>
              </div>
              <div className="two-col">
                <Distribution
                  title="Reported progress changes"
                  counts={c.progress_changes}
                  denominator={c.shared_scope_codes}
                />
                <Distribution
                  title="Reported expenditure changes"
                  counts={c.expenditure_changes}
                  denominator={c.shared_scope_codes}
                />
              </div>
              <div className="screening-card">
                <div className="screening-title">
                  <div className="spot-icon sand">
                    <ScanLine size={23} />
                  </div>
                  <div>
                    <h2>Conservative screening</h2>
                    <p>
                      Policy: <code>{c.screening_policy}</code>
                    </p>
                  </div>
                  <div className="screening-count">
                    <strong>
                      {c.trend_eligible} <span>/ {c.shared_scope_codes}</span>
                    </strong>
                    <small>pass the pair-wide gate</small>
                  </div>
                </div>
                <p className="hint">
                  {c.trend_excluded} shared pairs excluded. Exclusion does not
                  prove every individual field unusable; reasons may overlap.
                </p>
                <div className="reason-counts">
                  {Object.entries(c.exclusion_reasons || {})
                    .sort((a, b) => b[1] - a[1])
                    .map(([k, n]) => (
                      <div key={k}>
                        <span>
                          {pretty(k)}
                          <code>{k}</code>
                        </span>
                        <strong>{n}</strong>
                      </div>
                    ))}
                </div>
              </div>
              <div className="two-col">
                <Distribution
                  title="Original target-month shifts"
                  counts={c.completion_date_changes?.original_target_doc_raw}
                  denominator={c.shared_scope_codes}
                />
                <Distribution
                  title="Revised target-month shifts"
                  counts={c.completion_date_changes?.revised_doc_raw}
                  denominator={c.shared_scope_codes}
                />
              </div>
              <div className="section-bar">
                <h2>Presence & scope</h2>
                <span className="quiet">{c.presence_scope}</span>
              </div>
              <div className="table-card">
                {c.presence?.length ? (
                  <div className="table-scroll">
                    <table className="small-table">
                      <thead>
                        <tr>
                          <th>Code</th>
                          <th>Presence</th>
                          <th>Reason</th>
                          <th>Inspect observation</th>
                        </tr>
                      </thead>
                      <tbody>
                        {c.presence.map((p) => (
                          <tr key={p.project_code + p.presence}>
                            <td>{p.project_code}</td>
                            <td>{pretty(p.presence)}</td>
                            <td>
                              {p.reason === "not_in_filtered_scope"
                                ? "Outside the filtered scope"
                                : "Not observed in report"}
                            </td>
                            <td>
                              <button
                                className="text-button"
                                onClick={() =>
                                  onInspect(
                                    p.project_code,
                                    p.presence === "before_only"
                                      ? c.before_month
                                      : c.after_month,
                                  )
                                }
                              >
                                Inspect <ArrowUpRight size={13} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="empty-copy">
                    {full
                      ? "Project-level presence is not included in the documented aggregate example."
                      : "No confirmed scope-membership differences in this sample."}
                  </p>
                )}
                {result.meta.unresolved_sample_presence > 0 && (
                  <p className="empty-copy">
                    {result.meta.unresolved_sample_presence} one-sided sample
                    records have unknown full-report presence. No report-absence
                    reason is assigned.
                  </p>
                )}
              </div>
              <h2 className="subheading">Missing inputs</h2>
              {c.missing_input_counts?.length ? (
                <div className="table-card table-scroll">
                  <table className="small-table">
                    <thead>
                      <tr>
                        <th>Field</th>
                        <th>Before missing</th>
                        <th>After missing</th>
                        <th>Either missing</th>
                        <th>Both known</th>
                      </tr>
                    </thead>
                    <tbody>
                      {c.missing_input_counts.map((r) => (
                        <tr key={r.field}>
                          <td>{pretty(r.field)}</td>
                          <td>{r.before_missing}</td>
                          <td>{r.after_missing}</td>
                          <td>{r.either_missing}</td>
                          <td>{r.both_known}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="table-note">
                    Denominator: {c.shared_scope_codes} shared codes. Counts
                    overlap across fields. {c.missing_field_records} shared
                    records have at least one missing field.
                  </p>
                </div>
              ) : (
                <div className="notice">
                  <Info size={17} />
                  <p>
                    Field-level missing-input counts are not included in this
                    aggregate example. The example reports{" "}
                    {c.missing_field_records} shared records with logged missing
                    fields.
                  </p>
                </div>
              )}
              <details>
                <summary>Before / after quality counts</summary>
                <pre>
                  {JSON.stringify(
                    {
                      before:
                        c.before_quality_counts ?? "Not included in example",
                      after:
                        c.after_quality_counts ?? "Not included in example",
                    },
                    null,
                    2,
                  )}
                </pre>
              </details>
            </>
          )}
          <h2 className="subheading">
            Selected report: missing values & flags
          </h2>
          <div className="table-card table-scroll">
            <table className="small-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Missing reason</th>
                  <th>Occurrences</th>
                </tr>
              </thead>
              <tbody>
                {data.quality_counts.missing_values.map((r) => (
                  <tr key={r.field + r.missing_reason}>
                    <td>{pretty(r.field)}</td>
                    <td>{pretty(r.missing_reason)}</td>
                    <td>{r.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="hint">
            Missingness counts are overlapping field occurrences, not unique
            projects.
          </p>
          <Warnings items={result.warnings} />
          <details>
            <summary>Exact portfolio response & all quality flags</summary>
            <pre>{JSON.stringify(result, null, 2)}</pre>
          </details>
        </>
      )}
    </>
  );
}
