import { ChevronDown, CalendarDays } from "lucide-react";
import { MONTHS } from "../../constants.js";
import { monthLabel } from "../../utils/format.js";

export function MonthSelect({
  value,
  onChange,
  label = "Report month",
  allowNone = false,
  options = MONTHS,
}) {
  return (
    <label className="month-select">
      <CalendarDays size={16} />
      <span className="sr-only">{label}</span>
      <select
        aria-label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {allowNone && <option value="">No comparison</option>}
        {options.map((m) => (
          <option key={m} value={m}>
            {monthLabel(m)}
          </option>
        ))}
      </select>
      <ChevronDown size={13} />
    </label>
  );
}
