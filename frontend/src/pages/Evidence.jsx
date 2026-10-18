import { ArrowUpRight, X, ScanLine, CircleHelp, FileText, Check, CheckCircle2, ExternalLink, Info } from "lucide-react";
import { MONTHS } from "../constants.js";
import { monthLabel, decimal } from "../utils/format.js";
import { cn } from "../utils/cn.js";

export function Evidence({ db, onInspect }) {
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
