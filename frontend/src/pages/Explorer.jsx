import { useState, useEffect } from "react";
import { Search, ArrowUpRight, X, Database, CircleHelp, AlertTriangle, Check, CalendarDays, Droplets, Building2 } from "lucide-react";
import { monthLabel, decimal, formatValue } from "../utils/format.js";
import { matches } from "../utils/filters.js";
import { useRequest } from "../hooks/useRequest.js";
import { SectorIcon } from "../components/common/SectorIcon.jsx";
import { ErrorBox } from "../components/common/ErrorBox.jsx";
import { Loading } from "../components/common/Loading.jsx";
import { Warnings } from "../components/common/Warnings.jsx";
import { MonthSelect } from "../components/common/MonthSelect.jsx";
import { Metric } from "../components/common/Metric.jsx";
import { Pagination } from "../components/common/Pagination.jsx";
import { Filters } from "../components/filters/Filters.jsx";
import { FilterChips } from "../components/filters/FilterChips.jsx";

export function Explorer({
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
            client={client}
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
                          <SectorIcon name={s.identity.sector} size={15} />
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
