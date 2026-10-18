import { ArrowRight } from "lucide-react";

export function SourceBanner({ mode, onOpenConnection }) {
  return (
    <div className="source-banner">
      <span>
        <span className="live-dot" />
        {mode === "examples" ? "REFERENCE EXAMPLES" : "LIVE API SESSION"}
      </span>
      <p>
        {mode === "examples"
          ? "Checked source excerpts. Sample coverage is limited; full-report comparison is labeled separately."
          : "Responses use the selected API and a pinned dataset revision."}
      </p>
      <button onClick={onOpenConnection}>
        {mode === "examples" ? "Connect API" : "Change connection"}
        <ArrowRight size={13} />
      </button>
    </div>
  );
}
