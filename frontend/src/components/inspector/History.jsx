import { useState, useEffect } from "react";
import { X, AlertTriangle, Check, Info } from "lucide-react";
import { MONTHS } from "../../constants.js";
import { monthLabel, decimal, formatValue } from "../../utils/format.js";
import { cn } from "../../utils/cn.js";
import { useRequest } from "../../hooks/useRequest.js";
import { ErrorBox } from "../common/ErrorBox.jsx";
import { Loading } from "../common/Loading.jsx";
import { Warnings } from "../common/Warnings.jsx";
import { MonthSelect } from "../common/MonthSelect.jsx";
import { Pagination } from "../common/Pagination.jsx";
import { Pair } from "./Pair.jsx";

export function History({ client, code, mode, onMonth }) {
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
