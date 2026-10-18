import { pretty, decimal } from "../../utils/format.js";
import { cn } from "../../utils/cn.js";

export function Distribution({ title, counts, denominator }) {
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
