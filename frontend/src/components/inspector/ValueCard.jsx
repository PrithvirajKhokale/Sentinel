import { pretty, formatValue } from "../../utils/format.js";

export function ValueCard({ field, value }) {
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
