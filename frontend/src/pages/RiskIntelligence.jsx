import { useState, useEffect } from "react";
import { ArrowRight, ChevronLeft, ChevronRight, ScanLine, CircleHelp, AlertTriangle, Info } from "lucide-react";
import { pretty, monthLabel, decimal } from "../utils/format.js";
import { cn } from "../utils/cn.js";
import { useRequest } from "../hooks/useRequest.js";
import { ErrorBox } from "../components/common/ErrorBox.jsx";
import { Loading } from "../components/common/Loading.jsx";
import { MonthSelect } from "../components/common/MonthSelect.jsx";
import { Metric } from "../components/common/Metric.jsx";
import { Filters } from "../components/filters/Filters.jsx";
import { FilterChips } from "../components/filters/FilterChips.jsx";

export function RiskIntelligence({ db, client, mode, month, setMonth, filters, setFilters, onInspect }) {
  if (mode !== "live") {
    return (
      <>
        <div className="page-heading">
          <div>
            <div className="eyebrow">EVIDENCE-BASED SCREENING</div>
            <h1>Risk intelligence<span className="heading-dot">.</span></h1>
            <p>Reported changes that may deserve closer review, with their original sources.</p>
          </div>
        </div>
        <div className="notice amber">
          <Info size={20} />
          <p>This view requires the validated live API. Reference examples are deliberately not treated as a complete risk assessment. Use <strong>Connect API</strong> above to enable it.</p>
        </div>
      </>
    );
  }
  return (
    <LiveRiskIntelligence
      db={db} client={client} month={month} setMonth={setMonth}
      filters={filters} setFilters={setFilters} onInspect={onInspect}
    />
  );
}
const RISK_TYPES = [
  ["", "All reported signals"],
  ["reported_progress_decrease", "Progress decreased"],
  ["spending_without_reported_progress", "Spending with unchanged progress"],
  ["reported_target_postponed", "Revised target moved later"],
];
function LiveRiskIntelligence({ db, client, month, setMonth, filters, setFilters, onInspect }) {
  const [kind, setKind] = useState("");
  const [nameInput, setNameInput] = useState("");
  const [codeInput, setCodeInput] = useState("");
  const [nameSearch, setNameSearch] = useState("");
  const [codeSearch, setCodeSearch] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 20;
  useEffect(() => {
    const timer = setTimeout(() => { setNameSearch(nameInput.trim()); setCodeSearch(codeInput.trim()); }, 250);
    return () => clearTimeout(timer);
  }, [nameInput, codeInput]);
  useEffect(() => setPage(1), [kind, month, filters, nameSearch, codeSearch]);
  const { result, loading, error } = useRequest(client, "/risk-signals", {
    report_month: month, ...filters, page, page_size: pageSize,
    ...(nameSearch ? { q: nameSearch } : {}),
    ...(codeSearch ? { project_code: [codeSearch] } : {}),
    ...(kind ? { signal_type: kind } : {}),
  });
  const data = result?.data;
  const summary = data?.summary;
  const pagination = result?.meta?.pagination;
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">EVIDENCE-BASED SCREENING</div>
          <h1>Risk intelligence<span className="heading-dot">.</span></h1>
          <p>Reported warning signals, source context and review requirements. Not a prediction.</p>
        </div>
        <MonthSelect value={month} onChange={setMonth} />
      </div>
      <div className="notice amber">
        <Info size={18} />
        <p><strong>Not a risk score.</strong> These are changes between adjacent published reports, not verified project outcomes. A field may require further review even when its reported change is shown. Missing observations are not proof of completion.</p>
      </div>
      <div className="signals-controls">
        <label>
          <span>Project name contains</span>
          <input aria-label="Search risk signals by project name"
            placeholder="Type any part of the name…" value={nameInput}
            onChange={(e) => setNameInput(e.target.value)} />
        </label>
        <label>
          <span>Project code (exact)</span>
          <input aria-label="Filter risk signals by project code"
            placeholder="e.g. 400298" value={codeInput}
            onChange={(e) => setCodeInput(e.target.value)} />
        </label>
        <label>
          <span>Reported signal type</span>
          <select aria-label="Reported signal type" value={kind} onChange={(e) => setKind(e.target.value)}>
            {RISK_TYPES.map(([value, label]) => <option value={value} key={value}>{label}</option>)}
          </select>
        </label>
        <Filters db={db} client={client} month={month} filters={filters}
          onChange={setFilters} mode="live" />
      </div>
      <FilterChips filters={filters} onChange={setFilters} />
      {error ? <ErrorBox error={error} /> : loading ? <Loading /> : (
        <>
          <div className="metrics four">
            <Metric label="Shared reported pairs" value={decimal(String(summary.shared_pairs_in_scope))}
              note={data.comparison_month ? `${monthLabel(data.comparison_month)} → ${monthLabel(month)}` : "No adjacent prior report"} />
            <Metric label="Projects with signals" value={decimal(String(summary.projects_with_signals))}
              note="Based on selected identity scope" icon={AlertTriangle} />
            <Metric label="Reported signals" value={decimal(String(summary.total_signals))}
              note="A project may have multiple signals" icon={ScanLine} />
            <Metric label="Flagged projects needing review"
              value={decimal(String(summary.signaled_projects_requiring_pair_review))}
              note="Conservative pair-wide flags" icon={CircleHelp} />
          </div>
          <div className="signal-summary">
            {RISK_TYPES.filter(([code]) => code).map(([code, label]) => (
              <button key={code} onClick={() => setKind(code)}
                className={cn("signal-summary-pill", kind === code && "selected")}>
                <span>{label}</span><strong>{summary.signal_counts[code] || 0}</strong>
              </button>
            ))}
          </div>
          <div className="signals-title">
            <h2>Reported observations</h2>
            <span>{pagination.total_items} matching signals</span>
          </div>
          {!data.comparison_month ? (
            <div className="empty-state"><h3>No earlier adjacent report</h3>
              <p>Select May–August to compare against the immediately preceding observed reporting month.</p></div>
          ) : !data.signals.length ? (
            <div className="empty-state"><h3>No signals on this page</h3>
              <p>This is not a declaration that any project is safe or complete. Adjust the month or filters to view other observations.</p></div>
          ) : (
            <div className="signal-list">
              {data.signals.map((s) => (
                <article className="signal-card" key={s.id}>
                  <div className="signal-card-top">
                    <div>
                      <span className="eyebrow">{s.category.toUpperCase()} · {monthLabel(s.before_month)} → {monthLabel(s.after_month)}</span>
                      <h3>{s.title}</h3>
                      <p className="signal-project">{s.project_name} · {s.project_code}</p>
                    </div>
                    {s.pair_wide_review_required && <span className="badge amber">Review required</span>}
                  </div>
                  <p>{s.explanation}</p>
                  <div className="signal-evidence">
                    {s.evidence.map((e) => (
                      <div className="signal-evidence-row" key={e.field}>
                        <strong>{pretty(e.field)}</strong>
                        <span>Before: <code>{e.before_raw}</code></span>
                        <span>After: <code>{e.after_raw}</code></span>
                        <span>{e.status}{e.delta !== null ? ` · Δ ${e.delta}` : ""}</span>
                      </div>
                    ))}
                  </div>
                  <p className="signal-sources">
                    Source: {s.source_files.before} (PDF {s.source_pdf_pages.before.join(", ")})
                    {" → "}{s.source_files.after} (PDF {s.source_pdf_pages.after.join(", ")})
                  </p>
                  {s.pair_wide_review_required && (
                    <p className="signal-review">Pair-wide review reasons: {s.review_reasons.join(", ") || "Conservative screening gate"}. These do not independently determine individual field validity.</p>
                  )}
                  <button className="button signal-inspect" onClick={() => onInspect(s.project_code, s.after_month, "history")}>
                    Inspect project history <ArrowRight size={15} />
                  </button>
                </article>
              ))}
            </div>
          )}
          <div className="signals-pagination">
            <span>Page {pagination.page} of {Math.max(pagination.total_pages, 1)}</span>
            <button className="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              <ChevronLeft size={16} /> Previous
            </button>
            <button className="button" disabled={page >= pagination.total_pages} onClick={() => setPage(page + 1)}>
              Next <ChevronRight size={16} />
            </button>
          </div>
        </>
      )}
    </>
  );
}
