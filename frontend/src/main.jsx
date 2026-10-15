import React, { useState, useEffect, useMemo, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  Shield,
  Moon,
  Sun,
  Search,
  SlidersHorizontal,
  ArrowUpRight,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  X,
  LockKeyhole,
  Database,
  Layers,
  ScanLine,
  GitCompareArrows,
  CircleHelp,
  AlertTriangle,
  FileText,
  Check,
  CheckCircle2,
  CalendarDays,
  TrainFront,
  Plane,
  Droplets,
  Zap,
  Building2,
  RefreshCw,
  ExternalLink,
  Download,
  Info,
  Hash,
  MapPin,
} from "lucide-react";
import {
  createClient,
  MONTHS,
  IDENTITY_FIELDS,
  LABELS,
  pretty,
  monthLabel,
  decimal,
  formatValue,
  matches,
} from "./api";
import "./styles.css";
const cn = (...a) => a.filter(Boolean).join(" ");
function Icon({ name, size = 18, ...rest }) {
  const C =
    {
      Railways: TrainFront,
      "Water Resources": Droplets,
      "Aviation & Aviation Infrastructure": Plane,
      Power: Zap,
    }[name] || Building2;
  return <C size={size} {...rest} />;
}
function useRequest(client, path, params) {
  const [state, set] = useState({ loading: true });
  const key = JSON.stringify(params);
  useEffect(() => {
    const a = new AbortController();
    set({ loading: true });
    client
      .get(path, params, a.signal)
      .then((result) => {
        if (!a.signal.aborted) set({ result, loading: false });
      })
      .catch((error) => {
        if (!a.signal.aborted) set({ error, loading: false });
      });
    return () => a.abort();
  }, [client, path, key]);
  return state;
}
function ErrorBox({ error }) {
  return (
    <div className="error-box" role="alert">
      <AlertTriangle size={19} />
      <div>
        <strong>{error.code || "Unable to load data"}</strong>
        <p>{error.message}</p>
        {error.details?.map((d, i) => (
          <p key={i}>
            {d.location}: {d.message}
          </p>
        ))}
      </div>
    </div>
  );
}
function Loading() {
  return (
    <div className="loading" role="status">
      <RefreshCw size={19} /> Loading reported data…
    </div>
  );
}
function Warnings({ items = [], title = "Source warnings" }) {
  if (!items.length) return null;
  return (
    <div className="warnings">
      <div className="mini-title">
        <AlertTriangle size={15} />
        {title}
        <span>{items.length}</span>
      </div>
      {items.map((w, i) => (
        <div className="warning" key={i}>
          <strong>{pretty(w.code)}</strong>
          <p>{w.message}</p>
          <small>
            {w.scope} {w.report_month ? `· ${monthLabel(w.report_month)}` : ""}
            {w.source_pdf_pages?.length
              ? ` · PDF ${w.source_pdf_pages.join(", ")}`
              : ""}
            {w.fields?.length ? ` · ${w.fields.map(pretty).join(", ")}` : ""}
          </small>
        </div>
      ))}
    </div>
  );
}
function Filters({ db, month, filters, onChange, mode }) {
  const [open, set] = useState(false),
    [field, setField] = useState("sector");
  const count = IDENTITY_FIELDS.reduce(
    (n, f) => n + (filters[f]?.length || 0),
    0,
  );
  return (
    <div className="filter-wrap">
      <button
        className={cn("button filter-button", count && "active")}
        onClick={() => set(!open)}
        aria-expanded={open}
      >
        <SlidersHorizontal size={16} />
        Filters{count > 0 && <b className="count">{count}</b>}
      </button>
      {open && (
        <div className="filter-panel">
          <div className="panel-title">
            <strong>Filter reported identity</strong>
            <button
              aria-label="Close filters"
              className="icon-button"
              onClick={() => set(false)}
            >
              <X size={17} />
            </button>
          </div>
          <div className="filter-tabs">
            {IDENTITY_FIELDS.map((f) => (
              <button
                key={f}
                className={cn(field === f && "selected")}
                onClick={() => setField(f)}
              >
                {pretty(f)}
              </button>
            ))}
          </div>
          <p className="hint">
            Exact source labels. Multiple choices match any in a field.
          </p>
          {mode === "live" ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const val = new FormData(e.currentTarget).get("exact");
                if (val)
                  onChange({
                    ...filters,
                    [field]: [...new Set([...(filters[field] || []), val])],
                  });
                e.currentTarget.reset();
              }}
            >
              <label className="sr-only" htmlFor="exact">
                Exact {field} label
              </label>
              <input
                id="exact"
                name="exact"
                placeholder={`Exact reported ${field}`}
                required
              />
              <button className="button" type="submit">
                Add filter
              </button>
            </form>
          ) : (
            <div className="check-options">
              {[
                ...new Set(
                  db.snapshots
                    .filter(
                      (s) =>
                        s.report_month === month ||
                        s.report_month === MONTHS[MONTHS.indexOf(month) - 1],
                    )
                    .map((s) => s.identity[field]),
                ),
              ]
                .sort()
                .map((v) => (
                  <label key={v}>
                    <input
                      type="checkbox"
                      checked={filters[field]?.includes(v) || false}
                      onChange={(e) =>
                        onChange({
                          ...filters,
                          [field]: e.target.checked
                            ? [...(filters[field] || []), v]
                            : (filters[field] || []).filter((x) => x !== v),
                        })
                      }
                    />
                    <span>{v}</span>
                  </label>
                ))}
            </div>
          )}
          <button className="text-button" onClick={() => onChange({})}>
            Clear all filters
          </button>
        </div>
      )}
    </div>
  );
}
function FilterChips({ filters, onChange }) {
  return (
    <div className="filter-chips">
      {IDENTITY_FIELDS.flatMap((f) =>
        (filters[f] || []).map((v) => (
          <button
            key={f + v}
            onClick={() =>
              onChange({ ...filters, [f]: filters[f].filter((x) => x !== v) })
            }
          >
            {pretty(f)}: {v}
            <X size={12} />
          </button>
        )),
      )}
    </div>
  );
}
function MonthSelect({
  value,
  onChange,
  label = "Report month",
  allowNone = false,
  options = MONTHS,
}) {
  return (
    <label className="month-select">
      <CalendarDays size={16} />
      <span className="sr-only">{label}</span>
      <select
        aria-label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {allowNone && <option value="">No comparison</option>}
        {options.map((m) => (
          <option key={m} value={m}>
            {monthLabel(m)}
          </option>
        ))}
      </select>
      <ChevronDown size={13} />
    </label>
  );
}
function Metric({ label, value, note, icon: IC = Layers }) {
  return (
    <div className="metric">
      <div className="metric-label">
        {label}
        <IC size={16} />
      </div>
      <strong>{value}</strong>
      <small>{note}</small>
    </div>
  );
}
function Pagination({ pagination, onPage }) {
  if (!pagination) return null;
  const p = pagination;
  return (
    <div className="pagination">
      <span>
        {p.total_items
          ? `${(p.page - 1) * p.page_size + 1}–${Math.min(p.page * p.page_size, p.total_items)} of ${decimal(String(p.total_items))} records`
          : "0 records"}{" "}
        · sorted by source code
      </span>
      <div>
        <label>
          Rows{" "}
          <select
            aria-label="Rows per page"
            value={p.page_size}
            onChange={(e) => onPage(1, Number(e.target.value))}
          >
            {[5, 10, 25, 50, 100].map((n) => (
              <option key={n}>{n}</option>
            ))}
          </select>
        </label>
        <button
          className="icon-button"
          aria-label="Previous page"
          disabled={p.page <= 1}
          onClick={() => onPage(p.page - 1, p.page_size)}
        >
          <ChevronLeft size={17} />
        </button>
        <span>{p.total_pages ? `${p.page} / ${p.total_pages}` : "0 / 0"}</span>
        <button
          className="icon-button"
          aria-label="Next page"
          disabled={p.page >= p.total_pages}
          onClick={() => onPage(p.page + 1, p.page_size)}
        >
          <ChevronRight size={17} />
        </button>
      </div>
    </div>
  );
}
function Explorer({
  db,
  client,
  mode,
  month,
  setMonth,
  filters,
  setFilters,
  onInspect,
  onGap,
}) {
  const [q, setQ] = useState(""),
    [code, setCode] = useState(""),
    [page, setPage] = useState(1),
    [size, setSize] = useState(10),
    [query, setQuery] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setQuery(q.trim()), 250);
    return () => clearTimeout(t);
  }, [q]);
  useEffect(() => setPage(1), [month, JSON.stringify(filters), query, code]);
  const params = {
    report_month: month,
    ...filters,
    page,
    page_size: size,
    ...(query ? { q: query } : {}),
    ...(code.trim()
      ? {
          project_code: code
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        }
      : {}),
  };
  const { result, loading, error } = useRequest(client, "/projects", params);
  const rows = result?.data || [];
  const selectedSamples = db.snapshots.filter(
    (s) => s.report_month === month && matches(s, filters),
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">THE EVIDENCE, IN VIEW</div>
          <h1>
            Project explorer<span className="heading-dot">.</span>
          </h1>
          <p>
            Follow the projects. Inspect the source. Understand what changed.
          </p>
        </div>
        <MonthSelect value={month} onChange={setMonth} />
      </div>
      <div className="metrics">
        {mode === "examples" ? (
          <>
            <Metric
              label="Reference records"
              value={
                db.snapshots.filter((s) => s.report_month === month).length
              }
              note={`${monthLabel(month)} · checked source excerpts`}
            />
            <Metric
              label="Sectors in sample"
              value={
                new Set(selectedSamples.map((s) => s.identity.sector)).size
              }
              note="Reported sector labels"
              icon={Building2}
            />
            <Metric
              label="Missing fields"
              value={selectedSamples.reduce(
                (n, s) =>
                  n +
                  Object.values(s.values).filter((v) => v.normalized === null)
                    .length,
                0,
              )}
              note="Field occurrences · overlapping"
              icon={CircleHelp}
            />
          </>
        ) : (
          <>
            <Metric
              label="Matching projects"
              value={result?.meta?.pagination?.total_items ?? "—"}
              note="Within the selected report scope"
            />
            <Metric
              label="Snapshot month"
              value={monthLabel(month, true)}
              note={month.slice(0, 4)}
              icon={CalendarDays}
            />
            <Metric
              label="Dataset revision"
              value={result?.meta.dataset_version?.slice(0, 8) || "—"}
              note="Pinned throughout this session"
              icon={Database}
            />
          </>
        )}
      </div>
      <div className="section-bar">
        <h2>
          Reported projects{" "}
          <span>{result?.meta?.pagination?.total_items ?? "—"}</span>
        </h2>
        <span className="quiet">
          Source code order <Check size={14} />
        </span>
      </div>
      <div className="table-card">
        <div className="toolbar">
          <div className="search-field">
            <Search size={19} />
            <input
              aria-label="Search project names"
              placeholder="Search project names…"
              maxLength={200}
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            {q && (
              <button
                className="icon-button"
                aria-label="Clear search"
                onClick={() => setQ("")}
              >
                <X size={15} />
              </button>
            )}
            <kbd>NAME</kbd>
          </div>
          <input
            className="code-input"
            aria-label="Filter project codes"
            placeholder="Project code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          <Filters
            db={db}
            month={month}
            filters={filters}
            onChange={setFilters}
            mode={mode}
          />
        </div>
        <FilterChips filters={filters} onChange={setFilters} />
        {error ? (
          <ErrorBox error={error} />
        ) : loading ? (
          <Loading />
        ) : (
          <>
            <div className="table-scroll">
              <table className="project-table">
                <thead>
                  <tr>
                    <th>PROJECT / SOURCE CODE</th>
                    <th>SECTOR & LOCATION</th>
                    <th>REPORTED PROGRESS</th>
                    <th>
                      EXPENDITURE <span>₹ CRORE</span>
                    </th>
                    <th>SOURCE QUALITY</th>
                    <th>
                      <span className="sr-only">Inspect</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((s) => (
                    <tr key={s.project_code}>
                      <td>
                        <button
                          className="project-name"
                          onClick={() =>
                            onInspect(s.project_code, s.report_month)
                          }
                        >
                          {s.identity.project_name}
                        </button>
                        <span className="project-code">{s.project_code}</span>
                      </td>
                      <td>
                        <span className="sector">
                          <Icon name={s.identity.sector} size={15} />
                          {s.identity.sector}
                        </span>
                        <small className="location">{s.identity.state}</small>
                      </td>
                      <td>
                        <div className="progress-value">
                          {formatValue(s.values.physical_progress_pct)}
                        </div>
                        <div className="progress-track">
                          <i
                            style={{
                              width: `${Math.max(0, Math.min(100, Number(s.values.physical_progress_pct.normalized || 0)))}%`,
                            }}
                          />
                        </div>
                      </td>
                      <td className="numeric">
                        {decimal(
                          s.values.cumulative_expenditure_rs_crore.normalized,
                        )}
                      </td>
                      <td>
                        <span className="quality-badge">
                          <AlertTriangle size={12} />
                          {s.quality.snapshot_flags.length} flags
                        </span>
                      </td>
                      <td>
                        <button
                          className="icon-button inspect"
                          aria-label={`Inspect ${s.project_code}`}
                          onClick={() =>
                            onInspect(s.project_code, s.report_month)
                          }
                        >
                          <ArrowUpRight size={18} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!rows.length && (
              <div className="empty-state">
                <Search size={26} />
                <h3>No matching projects</h3>
                <p>Try a shorter name, an exact code, or clear the filters.</p>
                <button
                  className="button"
                  onClick={() => {
                    setQ("");
                    setCode("");
                    setFilters({});
                  }}
                >
                  Reset search
                </button>
              </div>
            )}
            <Pagination
              pagination={result?.meta.pagination}
              onPage={(p, s) => {
                setPage(p);
                setSize(s);
              }}
            />
          </>
        )}
      </div>
      <Warnings items={result?.warnings} />
      <div className="spotlights">
        <button
          className="spotlight"
          onClick={() => {
            setMonth("2026-07");
            onInspect("701530", "2026-07");
          }}
        >
          <div className="spot-icon">
            <Droplets size={22} />
          </div>
          <div>
            <span className="eyebrow">LOOK CLOSER</span>
            <h3>Zero is a reported value.</h3>
            <p>Ken–Betwa: inspect zero progress and unknown dates.</p>
          </div>
          <ArrowUpRight size={20} />
        </button>
        <button className="spotlight" onClick={onGap}>
          <div className="spot-icon sand">
            <CalendarDays size={22} />
          </div>
          <div>
            <span className="eyebrow">READ BETWEEN REPORTS</span>
            <h3>A gap is part of the story.</h3>
            <p>See why an absent month never becomes a trend.</p>
          </div>
          <ArrowUpRight size={20} />
        </button>
      </div>
    </>
  );
}
function ValueCard({ field, value }) {
  return (
    <div className="value-card">
      <span>{pretty(field)}</span>
      <strong>{formatValue(value)}</strong>
      <small>
        {value.unit === "Rs. crore" ? "Rs. crore · " : ""}Raw:{" "}
        <code>{value.raw === "" ? '"" (blank)' : value.raw}</code>
      </small>
      {value.missing_reason && (
        <small className="missing">{pretty(value.missing_reason)}</small>
      )}
    </div>
  );
}
function ObjectTable({ object, label }) {
  if (!object || !Object.keys(object).length)
    return <p className="hint">No {label.toLowerCase()} recorded.</p>;
  return (
    <div className="table-scroll">
      <table className="small-table">
        <thead>
          <tr>
            <th>Field</th>
            <th>Before · raw</th>
            <th>After · raw</th>
            <th>Status / delta</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(object).map(([field, c]) => (
            <tr key={field}>
              <td>{pretty(field)}</td>
              <td>
                <code>{c.before_raw ?? c.before ?? "Unknown"}</code>
              </td>
              <td>
                <code>{c.after_raw ?? c.after ?? "Unknown"}</code>
              </td>
              <td>
                {c.status ? pretty(c.status) : "Changed"}
                {c.delta !== undefined && (
                  <small className="delta">
                    {c.delta === null
                      ? "Unknown delta"
                      : `${c.delta} ${field.includes("progress") ? "pp" : field.includes("crore") ? "Rs. crore" : field.includes("date") || field.includes("doc") ? "months" : ""}`}
                  </small>
                )}
                {c.raw_text_changed && c.status === "unchanged" && (
                  <small>Formatting changed</small>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function Pair({ pair }) {
  return (
    <div className="pair-panel">
      <div className="pair-title">
        <h3>
          {monthLabel(pair.before_month)} <ArrowRight size={16} />{" "}
          {monthLabel(pair.after_month)}
        </h3>
        <span className={cn("badge", pair.trend_eligible ? "green" : "amber")}>
          {pair.trend_eligible ? "Passes conservative gate" : "Review required"}
        </span>
      </div>
      <p className="hint">
        Reported differences; causes are unknown. Pair-wide screening does not
        decide individual field suitability.
      </p>
      <ObjectTable object={pair.changes} label="Reported changes" />
      <details open={Object.keys(pair.identity_differences || {}).length > 0}>
        <summary>
          Identity differences{" "}
          <span>{Object.keys(pair.identity_differences || {}).length}</span>
        </summary>
        <ObjectTable
          object={pair.identity_differences}
          label="Identity differences"
        />
      </details>
      <details>
        <summary>Baseline changes & auxiliary identifiers</summary>
        <ObjectTable object={pair.baseline_changes} label="Baseline changes" />
        <ObjectTable
          object={pair.auxiliary_identifier_changes}
          label="Auxiliary identifiers"
        />
      </details>
      <details>
        <summary>Missing inputs & screening reasons</summary>
        <div className="pair-meta">
          <div>
            <strong>Before missing</strong>
            {Object.entries(pair.before_missing_values || {}).map(([f, v]) => (
              <p key={f}>
                {pretty(f)}: <code>{v === "" ? '""' : v}</code>
              </p>
            ))}
          </div>
          <div>
            <strong>After missing</strong>
            {Object.entries(pair.after_missing_values || {}).map(([f, v]) => (
              <p key={f}>
                {pretty(f)}: <code>{v === "" ? '""' : v}</code>
              </p>
            ))}
          </div>
        </div>
        <p className="hint">
          Policy: <code>{pair.screening_policy}</code> · identity:{" "}
          <code>{pair.identity_review_status}</code> · completion gate:{" "}
          {String(pair.completion_trend_eligible)}
        </p>
        <ul className="reason-list">
          {pair.trend_review_reasons?.map((r) => (
            <li key={r}>
              {pretty(r)} <code>{r}</code>
            </li>
          ))}
        </ul>
        <details>
          <summary>All quality flags</summary>
          <ul>
            {pair.quality_flags?.map((f) => (
              <li key={f}>
                <code>{f}</code>
              </li>
            ))}
          </ul>
        </details>
      </details>
      {pair.source_notes?.length > 0 && (
        <details>
          <summary>Pair source notes</summary>
          <pre>{JSON.stringify(pair.source_notes, null, 2)}</pre>
        </details>
      )}
    </div>
  );
}
function History({ client, code, mode, onMonth }) {
  const [from, setFrom] = useState("2026-04"),
    [to, setTo] = useState("2026-08"),
    [page, setPage] = useState(1),
    [size, setSize] = useState(25),
    [pairIndex, setPair] = useState(0);
  const { result, loading, error } = useRequest(
    client,
    `/projects/${encodeURIComponent(code)}/history`,
    { from_month: from, to_month: to, page, page_size: size },
  );
  useEffect(() => {
    setPage(1);
    setPair(0);
  }, [from, to, code]);
  if (loading) return <Loading />;
  if (error) return <ErrorBox error={error} />;
  const pairs = result.meta.comparisons || [],
    rows = result.data,
    range = MONTHS.filter((m) => m >= from && m <= to);
  return (
    <>
      <div className="history-controls">
        <MonthSelect label="From month" value={from} onChange={setFrom} />
        <span>to</span>
        <MonthSelect label="To month" value={to} onChange={setTo} />
      </div>
      <div className="timeline">
        {range.map((m) => {
          const row = rows.find((s) => s.report_month === m),
            gap = result.meta.not_observed_months?.includes(m),
            sample = result.meta.sample_omitted_months?.includes(m);
          return (
            <button
              key={m}
              disabled={!row}
              className={cn(
                "timeline-month",
                gap && "gap",
                sample && "omitted",
                row && "observed",
              )}
              onClick={() => onMonth(m)}
            >
              <span className="timeline-point">
                {gap ? (
                  <X size={12} />
                ) : row ? (
                  <Check size={12} />
                ) : (
                  <span>·</span>
                )}
              </span>
              <strong>{monthLabel(m, true)}</strong>
              <small>
                {gap
                  ? "Not observed"
                  : sample
                    ? "Not in sample"
                    : row
                      ? "Observed"
                      : "Other page"}
              </small>
            </button>
          );
        })}
      </div>
      {result.meta.not_observed_months?.length > 0 && (
        <div className="notice amber">
          <AlertTriangle size={17} />
          <div>
            <strong>Explicit report gap</strong>
            <p>
              {result.meta.not_observed_months
                .map((m) => monthLabel(m))
                .join(", ")}
              : no ongoing-table observation. Absence does not establish
              completion. Adjacent comparisons never bridge this gap.
            </p>
          </div>
        </div>
      )}
      {result.meta.sample_omitted_months?.length > 0 && (
        <div className="notice">
          <Info size={17} />
          <p>
            Some months are not included in the reference sample. Their report
            presence is unknown here; they are not treated as report gaps.
          </p>
        </div>
      )}
      <div className="table-scroll">
        <table className="small-table">
          <thead>
            <tr>
              <th>Month</th>
              <th>Progress</th>
              <th>Expenditure · ₹ crore</th>
              <th>Reported name</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.report_month}>
                <td>
                  <button
                    className="text-button"
                    onClick={() => onMonth(s.report_month)}
                  >
                    {monthLabel(s.report_month)}
                  </button>
                </td>
                <td>
                  {formatValue(s.values.physical_progress_pct)}
                  <small>raw {s.values.physical_progress_pct.raw}</small>
                </td>
                <td>
                  {decimal(s.values.cumulative_expenditure_rs_crore.normalized)}
                  <small>
                    raw {s.values.cumulative_expenditure_rs_crore.raw}
                  </small>
                </td>
                <td>{s.identity.project_name}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination
        pagination={result.meta.pagination}
        onPage={(p, s) => {
          setPage(p);
          setSize(s);
        }}
      />
      <h3 className="subheading">Adjacent reported changes</h3>
      {pairs.length ? (
        <>
          <label className="pair-select">
            Comparison{" "}
            <select
              aria-label="Adjacent comparison"
              value={Math.min(pairIndex, pairs.length - 1)}
              onChange={(e) => setPair(Number(e.target.value))}
            >
              {pairs.map((p, i) => (
                <option value={i} key={p.before_month}>
                  {monthLabel(p.before_month)} → {monthLabel(p.after_month)}
                </option>
              ))}
            </select>
          </label>
          <Pair pair={pairs[Math.min(pairIndex, pairs.length - 1)]} />
        </>
      ) : (
        <p className="hint">
          No adjacent comparison in this range. Gaps are never bridged.
        </p>
      )}
      <Warnings items={result.warnings} />
      <p className="hint">
        Comparison metadata covers the whole selected range, even when snapshot
        rows are paginated.
      </p>
    </>
  );
}
function Provenance({ s, meta }) {
  return (
    <>
      <div className="source-file">
        <FileText size={29} />
        <div>
          <strong>{s.provenance.source_filename}</strong>
          <p>
            PDF pages {s.provenance.pdf_pages.join(", ")} · printed pages{" "}
            {s.provenance.printed_pages.join(", ")} · serial {s.serial_no}
          </p>
        </div>
      </div>
      <div className="definition-list">
        <div>
          <span>Source platform</span>
          <strong>{s.temporal.source_platform}</strong>
        </div>
        <div>
          <span>Reporting cutoff</span>
          <strong>{s.temporal.reporting_cutoff_date || "Unknown"}</strong>
        </div>
        <div>
          <span>Cutoff source text</span>
          <strong>{s.temporal.reporting_cutoff_raw}</strong>
        </div>
        <div>
          <span>Cutoff source page</span>
          <strong>PDF {s.temporal.source_pdf_page}</strong>
        </div>
        <div>
          <span>Publication date</span>
          <strong>{s.temporal.publication_date || "Unknown"}</strong>
        </div>
        <div>
          <span>First available date</span>
          <strong>{s.temporal.first_available_date || "Unknown"}</strong>
        </div>
      </div>
      <div className="notice">
        <Info size={17} />
        <p>
          A reporting cutoff is not a publication date. Unknown availability is
          retained explicitly.
        </p>
      </div>
      <h3 className="subheading">Source fingerprint</h3>
      <code className="hash-block">{s.provenance.source_sha256}</code>
      <h3 className="subheading">Dataset revision</h3>
      <code className="hash-block">{meta.dataset_version}</code>
      <h3 className="subheading">Original physical cells</h3>
      {s.provenance.physical_cells?.length ? (
        <ol className="physical-cells">
          {s.provenance.physical_cells.map((c, i) => (
            <li key={i}>
              <pre>{c}</pre>
            </li>
          ))}
        </ol>
      ) : (
        <p className="hint">
          Original cell text is not included in this reference fixture. The
          source fields above are preserved; no physical cells have been
          reconstructed.
        </p>
      )}
      {s.quality.source_notes?.length > 0 && (
        <>
          <h3 className="subheading">Source notes</h3>
          <pre>{JSON.stringify(s.quality.source_notes, null, 2)}</pre>
        </>
      )}
    </>
  );
}
function Inspector({ selection, client, mode, onClose, onSelect }) {
  const [tab, setTab] = useState(selection.tab || "overview");
  const ref = useRef();
  const { result, loading, error } = useRequest(
    client,
    `/projects/${encodeURIComponent(selection.code)}`,
    { report_month: selection.month },
  );
  useEffect(() => {
    const prev = document.activeElement;
    ref.current?.focus();
    const fn = (e) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab") {
        const nodes = [
          ...ref.current.querySelectorAll(
            'button:not(:disabled),input,select,summary,a,[tabindex="0"]',
          ),
        ].filter((x) => x.getClientRects().length);
        const first = nodes[0],
          last = nodes.at(-1);
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", fn);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", fn);
      document.body.style.overflow = "";
      prev?.focus();
    };
  }, []);
  const s = result?.data;
  const download = () => {
    const u = URL.createObjectURL(
      new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = u;
    a.download = `sentinel-${selection.code}-${selection.month}.json`;
    a.click();
    URL.revokeObjectURL(u);
  };
  return (
    <div
      className="drawer-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <section
        className="drawer"
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-labelledby="inspector-title"
        tabIndex={-1}
      >
        <div className="drawer-top">
          <span className="eyebrow">PROJECT / {selection.code}</span>
          <div>
            {s && (
              <button
                className="icon-button"
                aria-label="Download snapshot JSON"
                onClick={download}
              >
                <Download size={18} />
              </button>
            )}
            <button
              className="icon-button"
              aria-label="Close inspector"
              onClick={onClose}
            >
              <X size={21} />
            </button>
          </div>
        </div>
        <h2 id="inspector-title">
          {s?.identity.project_name || `Project ${selection.code}`}
        </h2>
        <div className="drawer-subtitle">
          <MapPin size={15} />
          {s?.identity.state || "Reported identity"}
          <span>·</span>
          {monthLabel(selection.month)}
        </div>
        <div className="drawer-tabs" role="tablist">
          {["overview", "history", "provenance"].map((t) => (
            <button
              role="tab"
              aria-selected={tab === t}
              key={t}
              onClick={() => setTab(t)}
            >
              {pretty(t)}
            </button>
          ))}
        </div>
        <div className="drawer-body">
          {tab === "history" ? (
            <History
              client={client}
              code={selection.code}
              mode={mode}
              onMonth={(m) => {
                onSelect({ ...selection, month: m });
                setTab("overview");
              }}
            />
          ) : loading ? (
            <Loading />
          ) : error ? (
            <ErrorBox error={error} />
          ) : tab === "provenance" ? (
            <Provenance s={s} meta={result.meta} />
          ) : (
            <>
              <span className="badge green">
                <Icon name={s.identity.sector} size={13} />
                {s.identity.sector}
              </span>
              <div className="value-grid">
                {[
                  "physical_progress_pct",
                  "cumulative_expenditure_rs_crore",
                  "original_cost_rs_crore",
                  "revised_cost_rs_crore",
                ].map((f) => (
                  <ValueCard field={f} value={s.values[f]} key={f} />
                ))}
              </div>
              {s.values.revised_cost_rs_crore.normalized === "0" &&
                s.report_month === "2026-08" && (
                  <div className="notice amber">
                    <AlertTriangle size={17} />
                    <p>
                      August reports a literal revised-cost zero. It is
                      preserved as published; baseline comparisons require
                      review.
                    </p>
                  </div>
                )}
              <h3 className="subheading">Dates & identifiers</h3>
              <div className="value-grid compact">
                {[
                  "approval_date",
                  "start_date",
                  "original_target_doc",
                  "revised_doc",
                  "legacy_ocms_code",
                  "pmgid",
                ].map((f) => (
                  <ValueCard field={f} value={s.values[f]} key={f} />
                ))}
              </div>
              <h3 className="subheading">Reported identity</h3>
              <div className="definition-list">
                {["agency", "ministry", "state"].map((f) => (
                  <div key={f}>
                    <span>{pretty(f)}</span>
                    <strong>{s.identity[f]}</strong>
                  </div>
                ))}
              </div>
              <Warnings
                items={[...s.quality.snapshot_flags, ...result.warnings]}
                title="Warnings retained from source"
              />
              {s.quality.source_notes?.length > 0 && (
                <details>
                  <summary>Linked source notes</summary>
                  <pre>{JSON.stringify(s.quality.source_notes, null, 2)}</pre>
                </details>
              )}
              <button className="button wide" onClick={() => setTab("history")}>
                <CalendarDays size={16} />
                Explore monthly history
                <ArrowRight size={16} />
              </button>
              <p className="hint">
                Raw and normalized values are shown together. Unknown never
                becomes zero.
              </p>
              <details>
                <summary>Exact response JSON</summary>
                <pre>{JSON.stringify(result, null, 2)}</pre>
              </details>
            </>
          )}
        </div>
      </section>
    </div>
  );
}
function Distribution({ title, counts, denominator }) {
  return (
    <div className="distribution">
      <div className="mini-title">
        {title}
        <span>{denominator} shared</span>
      </div>
      {Object.entries(counts || {}).map(([k, n]) => (
        <div className="distribution-row" key={k}>
          <span>
            <i className={cn("status-dot", k)} />
            {pretty(k)}
          </span>
          <div className="distribution-track">
            <i
              className={k}
              style={{
                width: denominator ? `${(n / denominator) * 100}%` : "0%",
              }}
            />
          </div>
          <strong>{decimal(String(n))}</strong>
        </div>
      ))}
    </div>
  );
}
function Portfolio({
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
function Evidence({ db, onInspect }) {
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">KNOW WHAT YOU'RE LOOKING AT</div>
          <h1>
            Evidence & gaps<span className="heading-dot">.</span>
          </h1>
          <p>
            The source, its limits, and the distinctions that keep the data
            honest.
          </p>
        </div>
        <span className="badge green">
          <FileText size={13} /> Contract v1
        </span>
      </div>
      <div className="gap-card" id="documented-gap">
        <span className="eyebrow">DOCUMENTED BACKEND ACCEPTANCE CASE</span>
        <h2>Project 611752: June is a report gap.</h2>
        <p>
          The backend guide records observations in April, May, July, and
          August. June has no ongoing-table observation.
        </p>
        <div className="timeline gap-demo">
          {MONTHS.map((m) => (
            <div
              className={cn(
                "timeline-month",
                m === "2026-06" ? "gap" : "observed",
              )}
              key={m}
            >
              <span className="timeline-point">
                {m === "2026-06" ? <X size={13} /> : <Check size={13} />}
              </span>
              <strong>{monthLabel(m, true)}</strong>
              <small>{m === "2026-06" ? "Not observed" : "Observed"}</small>
            </div>
          ))}
        </div>
        <div className="gap-pairs">
          <span>
            Apr → May <CheckCircle2 size={14} />
          </span>
          <span className="broken">May ⇢ Jul · no comparison</span>
          <span>
            Jul → Aug <CheckCircle2 size={14} />
          </span>
        </div>
        <p className="hint">
          This is a documented gap case, not fabricated snapshot data. Its raw
          snapshots are not bundled. A live API history response uses{" "}
          <code>meta.not_observed_months</code> to expose this gap directly.
        </p>
      </div>
      <div className="evidence-grid">
        <div className="evidence-card">
          <CircleHelp size={24} />
          <h3>Unknown means unknown.</h3>
          <p>
            Source markers and literal blanks keep their raw text and missing
            reason. Publication dates are not inferred from submission cutoffs.
          </p>
          <button
            className="text-button"
            onClick={() => onInspect("701530", "2026-07")}
          >
            Inspect missing dates <ArrowUpRight size={15} />
          </button>
        </div>
        <div className="evidence-card">
          <ScanLine size={24} />
          <h3>Keep the original signal.</h3>
          <p>
            Published zeros stay zero. Reported decreases remain visible with
            review reasons. An exclusion is a conservative policy result.
          </p>
          <button
            className="text-button"
            onClick={() => onInspect("400298", "2026-07", "history")}
          >
            Inspect reported decreases <ArrowUpRight size={15} />
          </button>
        </div>
        <div className="evidence-card">
          <FileText size={24} />
          <h3>Trace it to the source.</h3>
          <p>
            Every sample includes its PDF filename, page references, source
            hash, reported identity, and original field strings.
          </p>
          <button
            className="text-button"
            onClick={() => onInspect("701128", "2026-08", "provenance")}
          >
            Inspect source cells <ArrowUpRight size={15} />
          </button>
        </div>
      </div>
      <div className="section-bar">
        <h2>Source report register</h2>
        <span className="quiet">April–August 2026</span>
      </div>
      <div className="table-card table-scroll">
        <table className="small-table report-table">
          <thead>
            <tr>
              <th>Report</th>
              <th>Source</th>
              <th>Reporting cutoff</th>
              <th>Published observations</th>
              <th>Availability</th>
            </tr>
          </thead>
          <tbody>
            {db.reports.map((r) => (
              <tr key={r.report_month_iso}>
                <td>{monthLabel(r.report_month_iso)}</td>
                <td>
                  {r.pdf.split("/").at(-1)}
                  <details>
                    <summary>Source hash & notes</summary>
                    <code className="hash-block">{r.source_sha256}</code>
                    <pre>{JSON.stringify(r.source_notes, null, 2)}</pre>
                  </details>
                </td>
                <td>
                  {r.documented_reporting_cutoff_date}
                  <small>PDF {r.cutoff_source_pdf_page}</small>
                </td>
                <td>{decimal(String(r.expected_project_count))}</td>
                <td>
                  Unknown<small>Publication & first availability</small>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="notice">
        <Info size={17} />
        <p>
          Reference mode contains {db.snapshots.length} checked snapshots and{" "}
          {db.comparisons.length} adjacent comparisons, not the complete
          dataset. Months omitted from the sample are labeled separately from
          true report gaps. Some fixtures omit original physical cells; they are
          never reconstructed.
        </p>
      </div>
      <div className="doc-links">
        <a
          href="https://github.com/PrithvirajKhokale/Sentinel/blob/f2f50631414386b0a3fb6eb2b2ec5d98f7f89a76/docs/api_contract.md"
          target="_blank"
          rel="noreferrer"
        >
          Read the API contract <ExternalLink size={14} />
        </a>
        <a
          href="https://github.com/PrithvirajKhokale/Sentinel/blob/f2f50631414386b0a3fb6eb2b2ec5d98f7f89a76/docs/backend-local.md"
          target="_blank"
          rel="noreferrer"
        >
          Backend & gap documentation <ExternalLink size={14} />
        </a>
      </div>
    </>
  );
}
function Connection({ config, onApply, onClose }) {
  const [mode, setMode] = useState(config.mode),
    [base, setBase] = useState(config.base || ""),
    [token, setToken] = useState(""),
    [error, setError] = useState(""),
    [connecting, setConnecting] = useState(false);
  useEffect(() => {
    const fn = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", fn);
    return () => document.removeEventListener("keydown", fn);
  }, []);
  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (mode === "live") {
      try {
        const u = new URL(base, location.origin);
        if (
          u.origin !== location.origin && u.protocol !== "https:" &&
          !(
            location.protocol === "http:" &&
            ["127.0.0.1", "localhost", "[::1]"].includes(u.hostname)
          )
        )
          throw Error(
            "Use an authenticated HTTPS endpoint. Loopback HTTP is supported when the frontend also runs locally.",
          );
        if (u.username || u.password || u.search || u.hash)
          throw Error(
            "Use an API base URL without embedded credentials, queries, or fragments.",
          );
      } catch (e) {
        setError(e.message);
        return;
      }
    }
    const next = { mode, base: base.trim().replace(/\/$/, ""), token };
    if (mode === "live") {
      setConnecting(true);
      try {
        await createClient(null, next).get("/projects", { report_month: "2026-08", page_size: 1 });
      } catch (e) {
        setError(e.message);
        setConnecting(false);
        return;
      }
    }
    onApply(next);
    onClose();
  };
  return (
    <div className="modal-backdrop">
      <section
        className="connection-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="connection-title"
      >
        <div className="panel-title">
          <h2 id="connection-title">Data connection</h2>
          <button
            className="icon-button"
            aria-label="Close connection"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>
        <p>
          Explore the source examples, or connect your existing Sentinel API.
        </p>
        <form onSubmit={submit}>
          <div className="source-choice">
            <label className={cn(mode === "examples" && "selected")}>
              <input
                type="radio"
                name="source"
                value="examples"
                checked={mode === "examples"}
                onChange={() => setMode("examples")}
              />
              <span>
                <strong>Reference examples</strong>
                <small>Checked excerpts and documented comparisons</small>
              </span>
            </label>
            <label className={cn(mode === "live" && "selected")}>
              <input
                type="radio"
                name="source"
                value="live"
                checked={mode === "live"}
                onChange={() => setMode("live")}
              />
              <span>
                <strong>Live Sentinel API</strong>
                <small>List, detail, history & portfolio contract v1</small>
              </span>
            </label>
          </div>
          {mode === "live" && (
            <>
              <label className="form-label">
                API base URL
                <input
                  autoFocus
                  type="url"
                  aria-label="API base URL"
                  placeholder="https://your-api.example/api/v1"
                  value={base}
                  onChange={(e) => setBase(e.target.value)}
                  required
                />
              </label>
              <label className="form-label">
                Bearer token (if required)
                <input
                  type="password"
                  aria-label="API bearer token"
                  autoComplete="off"
                  placeholder="Optional · held only in memory"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                />
              </label>
              <p className="hint">
                Use a reachable authenticated service with CORS configured for
                this site's origin. Use /api/v1 when the API and interface share
                a host. Credentials are never saved in
                browser storage. A failed API request stays visible.
              </p>
            </>
          )}
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button className="button primary wide" type="submit" disabled={connecting}>
            {connecting ? "Checking connection…" : mode === "examples" ? "Use reference examples" : "Connect API"}
            <ArrowRight size={16} />
          </button>
        </form>
      </section>
    </div>
  );
}
function App() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || "light");
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#111a16" : "#164f43");
    try { localStorage.setItem("sentinel-theme", theme); } catch { /* Storage may be disabled. */ }
  }, [theme]);
  const [db, setDb] = useState(),
    [loadError, setLoadError] = useState(),
    [page, setPage] = useState("explore"),
    [month, setMonth] = useState("2026-08"),
    [filters, setFilters] = useState({}),
    [selection, setSelection] = useState(null),
    [connection, setConnection] = useState(false),
    [config, setConfig] = useState(() => {
      const base = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? "/api/v1" : "");
      return base ? { mode: "live", base } : { mode: "examples" };
    });
  useEffect(() => {
    fetch("/reference-data.json")
      .then((r) => {
        if (!r.ok) throw Error("Could not load reference data.");
        return r.json();
      })
      .then(setDb)
      .catch(setLoadError);
  }, []);
  const client = useMemo(
    () => (db ? createClient(db, config) : null),
    [db, config],
  );
  const inspect = (code, m, tab) => setSelection({ code, month: m, tab });
  if (loadError) return <ErrorBox error={loadError} />;
  if (!db) return <Loading />;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setPage("explore");
          }}
        >
          <span className="brand-mark">
            <Shield size={24} strokeWidth={1.7} />
          </span>
          <span>
            sentinel<span className="brand-period">.</span>
          </span>
        </a>
        <div className="workspace-label">PROJECT INTELLIGENCE</div>
        <nav aria-label="Main navigation">
          {[
            ["explore", "Project explorer", Search],
            ["portfolio", "Portfolio comparisons", GitCompareArrows],
            ["evidence", "Evidence & gaps", FileText],
          ].map(([k, l, IC]) => (
            <button
              key={k}
              className={cn("nav-item", page === k && "selected")}
              onClick={() => setPage(k)}
            >
              <IC size={18} />
              <span>{l}</span>
              {page === k && <i />}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <div className="orbit-mark">
            <Shield size={33} strokeWidth={1} />
          </div>
          <strong>Evidence over assumption.</strong>
          <p>Explore what the reports say, with their limits intact.</p>
          <span>APR — AUG 2026</span>
        </div>
        <div className="sidebar-footer">
          <div className="avatar">PK</div>
          <div>
            <strong>Sentinel workspace</strong>
            <span>
              <LockKeyhole size={11} />
              Private access
            </span>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>Sentinel</span>
            <ChevronRight size={13} />
            <strong>
              {page === "explore"
                ? "Project explorer"
                : page === "portfolio"
                  ? "Portfolio comparisons"
                  : "Evidence & gaps"}
            </strong>
          </div>
          <div className="topbar-actions">
            <button
              className="theme-toggle"
              type="button"
              aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              aria-pressed={theme === "dark"}
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            >
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <span className="private-badge">
              <LockKeyhole size={12} />
              Private
            </span>
            <button
              className="source-button"
              onClick={() => setConnection(true)}
            >
              <span
                className={cn(
                  "live-dot",
                  config.mode === "live" && "connected",
                )}
              />
              {config.mode === "examples" ? "Reference examples" : "Live API"}
              <ChevronDown size={13} />
            </button>
          </div>
        </header>
        <main>
          <div className="source-banner">
            <span>
              <span className="live-dot" />
              {config.mode === "examples"
                ? "REFERENCE EXAMPLES"
                : "LIVE API SESSION"}
            </span>
            <p>
              {config.mode === "examples"
                ? "Checked source excerpts. Sample coverage is limited; full-report comparison is labeled separately."
                : "Responses use the selected API and a pinned dataset revision."}
            </p>
            <button onClick={() => setConnection(true)}>
              {config.mode === "examples" ? "Connect API" : "Change connection"}
              <ArrowRight size={13} />
            </button>
          </div>
          {page === "explore" ? (
            <Explorer
              db={db}
              client={client}
              mode={config.mode}
              month={month}
              setMonth={setMonth}
              filters={filters}
              setFilters={setFilters}
              onInspect={inspect}
              onGap={() => setPage("evidence")}
            />
          ) : page === "portfolio" ? (
            <Portfolio
              db={db}
              client={client}
              mode={config.mode}
              month={month}
              setMonth={setMonth}
              filters={filters}
              setFilters={setFilters}
              onInspect={inspect}
            />
          ) : (
            <Evidence db={db} onInspect={inspect} />
          )}
          <footer className="page-footer">
            <span>
              <Shield size={13} />
              SENTINEL
            </span>
            <p>Reported observations. Source values preserved.</p>
            <span>CONTRACT v1</span>
          </footer>
        </main>
      </div>
      {selection && (
        <Inspector
          key={selection.code}
          selection={selection}
          client={client}
          mode={config.mode}
          onClose={() => setSelection(null)}
          onSelect={setSelection}
        />
      )}{" "}
      {connection && (
        <Connection
          config={config}
          onApply={(c) => {
            setConfig(c);
            setSelection(null);
            setFilters({});
          }}
          onClose={() => setConnection(false)}
        />
      )}
    </div>
  );
}
createRoot(document.getElementById("root")).render(<App />);
