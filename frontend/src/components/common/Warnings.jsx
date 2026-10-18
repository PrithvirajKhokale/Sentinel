import { AlertTriangle } from "lucide-react";
import { pretty, monthLabel } from "../../utils/format.js";

export function Warnings({ items = [], title = "Source warnings" }) {
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
