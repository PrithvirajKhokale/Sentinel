import { Layers } from "lucide-react";

export function Metric({ label, value, note, icon: IC = Layers }) {
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
