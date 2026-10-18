import { ArrowRight } from "lucide-react";
import { pretty, monthLabel } from "../../utils/format.js";
import { cn } from "../../utils/cn.js";
import { ObjectTable } from "./ObjectTable.jsx";

export function Pair({ pair }) {
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
