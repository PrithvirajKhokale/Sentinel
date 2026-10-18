import { X } from "lucide-react";
import { IDENTITY_FIELDS } from "../../constants.js";
import { pretty } from "../../utils/format.js";

export function FilterChips({ filters, onChange }) {
  return (
    <div className="filter-chips">
      {IDENTITY_FIELDS.flatMap((f) =>
        (filters[f] || []).map((v) => (
          <button
            key={f + v}
            onClick={() =>
              onChange({ ...filters, [f]: filters[f].filter((x) => x !== v) })
            }
          >
            {pretty(f)}: {v}
            <X size={12} />
          </button>
        )),
      )}
    </div>
  );
}
