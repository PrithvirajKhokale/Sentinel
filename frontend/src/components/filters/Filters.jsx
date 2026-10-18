import { useState, useEffect } from "react";
import { SlidersHorizontal, X } from "lucide-react";
import { IDENTITY_FIELDS } from "../../constants.js";
import { pretty } from "../../utils/format.js";
import { matchingFilterOptions } from "../../utils/filters.js";
import { cn } from "../../utils/cn.js";

export function Filters({ db, client, month, comparisonMonth = "", filters, onChange, mode }) {
  const [open, setOpen] = useState(false);
  const [field, setField] = useState("sector");
  const [search, setSearch] = useState("");
  const [choices, setChoices] = useState({ loading: false, items: null, error: null });
  const count = IDENTITY_FIELDS.reduce((n, f) => n + (filters[f]?.length || 0), 0);

  // Discover all distinct *actual* labels, not merely values on the current page.
  // The live request is protected by the same bearer token and pinned revision.
  useEffect(() => {
    if (!open || mode !== "live") return;
    const controller = new AbortController();
    setChoices({ loading: true, items: null, error: null });
    client.get("/filter-options", {
      report_month: month,
      ...(comparisonMonth ? { comparison_month: comparisonMonth } : {}),
    }, controller.signal)
      .then(({ data }) => {
        if (!controller.signal.aborted) setChoices({ loading: false, items: data, error: null });
      })
      .catch((error) => {
        if (!controller.signal.aborted) setChoices({ loading: false, items: null, error });
      });
    return () => controller.abort();
  }, [open, client, mode, month, comparisonMonth]);

  const sampleMonths = [month, ...(comparisonMonth ? [comparisonMonth] : [])];
  const listed = mode === "examples"
    ? db.snapshots
      .filter((s) => sampleMonths.includes(s.report_month))
      .map((s) => s.identity[field])
    : (choices.items?.[field] || []);
  // Preserve selected options even when users switch months.
  const options = [...new Set([...listed, ...(filters[field] || [])].filter(Boolean))]
    .sort((a, b) => a.localeCompare(b));
  const filtered = matchingFilterOptions(options, search);
  const selected = filters[field] || [];
  const select = (value, checked) => {
    onChange({
      ...filters,
      [field]: checked ? [...new Set([...selected, value])] : selected.filter((v) => v !== value),
    });
  };
  const addTyped = (e) => {
    e.preventDefault();
    const typed = search.trim();
    if (!typed) return;
    // Prefer the exact published capitalization if the typed value matches.
    const exact = options.find((v) => v.toLocaleLowerCase() === typed.toLocaleLowerCase());
    select(exact || typed, true);
    setSearch("");
  };
  return (
    <div className="filter-wrap">
      <button
        className={cn("button filter-button", count && "active")}
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-label={`Filters: ${count} selected`}
      >
        <SlidersHorizontal size={16} />
        Filters{count > 0 && <b className="count">{count}</b>}
      </button>
      {open && (
        <div className="filter-panel">
          <div className="panel-title">
            <strong>Filter reported identity</strong>
            <button aria-label="Close filters" className="icon-button" onClick={() => setOpen(false)}>
              <X size={17} />
            </button>
          </div>
          <div className="filter-tabs">
            {IDENTITY_FIELDS.map((f) => (
              <button
                key={f}
                className={cn(field === f && "selected")}
                onClick={() => { setField(f); setSearch(""); }}
              >
                {pretty(f)}
              </button>
            ))}
          </div>
          <p className="hint">
            Select a reported label or type to find it. Multiple selections match any
            within a field and all selected fields together.
          </p>
          <form className="filter-search" onSubmit={addTyped}>
            <label htmlFor="filter-choice-search">Search {field} labels</label>
            <div className="filter-search-row">
              <input
                id="filter-choice-search"
                type="search"
                autoComplete="off"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={`Search or enter ${field}…`}
              />
              <button className="button" type="submit" disabled={!search.trim()}>
                Add typed
              </button>
            </div>
          </form>
          {mode === "live" && choices.loading && <p className="hint" role="status">Loading available labels…</p>}
          {mode === "live" && choices.error && (
            <p className="hint" role="alert">
              Couldn't load the suggested labels. You can still enter an exact
              label manually; it must match the report to return results.
            </p>
          )}
          {(!choices.loading || mode === "examples") && (
            <>
              <div className="filter-option-count">
                {filtered.length} matching {pretty(field).toLowerCase()} labels
              </div>
              <div className="check-options" role="group" aria-label={`Available ${field} filters`}>
                {filtered.slice(0, 75).map((v) => (
                  <label key={v}>
                    <input
                      type="checkbox"
                      checked={selected.includes(v)}
                      onChange={(e) => select(v, e.target.checked)}
                    />
                    <span>{v}</span>
                  </label>
                ))}
                {!filtered.length && (
                  <p className="hint">No matching label found. Try another spelling, or add the exact value you've typed.</p>
                )}
              </div>
              {filtered.length > 75 && (
                <p className="hint">Showing the first 75 labels. Type more to narrow the list.</p>
              )}
            </>
          )}
          <button className="text-button" onClick={() => { onChange({}); setSearch(""); }}>
            Clear all filters
          </button>
        </div>
      )}
    </div>
  );
}
