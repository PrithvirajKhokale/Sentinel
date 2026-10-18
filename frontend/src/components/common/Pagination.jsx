import { ChevronLeft, ChevronRight } from "lucide-react";
import { decimal } from "../../utils/format.js";

export function Pagination({ pagination, onPage }) {
  if (!pagination) return null;
  const p = pagination;
  return (
    <div className="pagination">
      <span>
        {p.total_items
          ? `${(p.page - 1) * p.page_size + 1}–${Math.min(p.page * p.page_size, p.total_items)} of ${decimal(String(p.total_items))} records`
          : "0 records"}{" "}
        · sorted by source code
      </span>
      <div>
        <label>
          Rows{" "}
          <select
            aria-label="Rows per page"
            value={p.page_size}
            onChange={(e) => onPage(1, Number(e.target.value))}
          >
            {[5, 10, 25, 50, 100].map((n) => (
              <option key={n}>{n}</option>
            ))}
          </select>
        </label>
        <button
          className="icon-button"
          aria-label="Previous page"
          disabled={p.page <= 1}
          onClick={() => onPage(p.page - 1, p.page_size)}
        >
          <ChevronLeft size={17} />
        </button>
        <span>{p.total_pages ? `${p.page} / ${p.total_pages}` : "0 / 0"}</span>
        <button
          className="icon-button"
          aria-label="Next page"
          disabled={p.page >= p.total_pages}
          onClick={() => onPage(p.page + 1, p.page_size)}
        >
          <ChevronRight size={17} />
        </button>
      </div>
    </div>
  );
}
