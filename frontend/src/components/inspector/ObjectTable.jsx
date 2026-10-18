import { pretty } from "../../utils/format.js";

export function ObjectTable({ object, label }) {
  if (!object || !Object.keys(object).length)
    return <p className="hint">No {label.toLowerCase()} recorded.</p>;
  return (
    <div className="table-scroll">
      <table className="small-table">
        <thead>
          <tr>
            <th>Field</th>
            <th>Before · raw</th>
            <th>After · raw</th>
            <th>Status / delta</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(object).map(([field, c]) => (
            <tr key={field}>
              <td>{pretty(field)}</td>
              <td>
                <code>{c.before_raw ?? c.before ?? "Unknown"}</code>
              </td>
              <td>
                <code>{c.after_raw ?? c.after ?? "Unknown"}</code>
              </td>
              <td>
                {c.status ? pretty(c.status) : "Changed"}
                {c.delta !== undefined && (
                  <small className="delta">
                    {c.delta === null
                      ? "Unknown delta"
                      : `${c.delta} ${field.includes("progress") ? "pp" : field.includes("crore") ? "Rs. crore" : field.includes("date") || field.includes("doc") ? "months" : ""}`}
                  </small>
                )}
                {c.raw_text_changed && c.status === "unchanged" && (
                  <small>Formatting changed</small>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
