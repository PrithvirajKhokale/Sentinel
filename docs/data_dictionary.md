# Sentinel data dictionary

## Validated scope and identity

This dictionary replaces provisional model fields with the observed April-August ongoing-project schema. See [monthly history](monthly-project-history.md) for full validation and limitations. API names below deliberately map CSV names to structured JSON; the CSV is not silently renamed. Examples are in [contract examples](examples/project-data-contract.json).

`project_code` is the source identifier string (preserve leading zeros), not a generated project_id. `report_month` is YYYY-MM, mapped from `report_month_iso`; `report_month_label` preserves report_month's source label. The logical snapshot key is `(project_code, report_month)`. Dataset version is the canonical manifest SHA-256, covering source reports, computation and schema version; it separates immutable revised artifacts. Keep reported names and identifiers unchanged. Canonical mappings must be explicit, versioned, separately hashed in the revision manifest and exposed apart from raw values; none is active in the MVP. No global identity certainty is implied by a code match. No missing-month snapshot is fabricated.

## Snapshot fields

| API field | CSV/source mapping | Type / meaning |
|---|---|---|
| project_code | project_code | String, mandatory identifier |
| report_month / report_month_label | report_month_iso / report_month | YYYY-MM / raw label |
| serial_no | serial_no | String, report-local source serial |
| identity.project_name / agency / ministry / sector / state | same-named columns | Reported strings, preserve spelling/parentheses; state may be multi-state text |
| values.legacy_ocms_code / pmgid | legacy_ocms_code_raw / pmgid_raw | Raw plus normalized string or null; surrounding identifier parentheses are formatting |
| values.approval_date / start_date | *_date_raw / *_date_normalized | Month values; approval/start are distinct |
| values.original_target_doc / revised_doc | *_raw / *_normalized | Month values, not actual completion dates |
| values.original_cost_rs_crore / revised_cost_rs_crore | *_raw / *_normalized | Exact decimal strings; Rs. crore |
| values.cumulative_expenditure_rs_crore | cumulative_expenditure_rs_crore_raw / normalized | Exact decimal string; cumulative reported expenditure, Rs. crore |
| values.physical_progress_pct | physical_progress_pct_raw / normalized | Exact decimal string, percent |
| provenance.source_filename / source_sha256 | same-named columns | Source filename and SHA-256 |
| provenance.pdf_pages / printed_pages | pdf_pages / printed_pages | Arrays of positive integers, all contributing pages; PDF pages are 1-based |
| provenance.physical_cells | source_cells_json | Parsed ordered array of eight original physical cell strings |
| temporal.reporting_cutoff_date / raw / source_pdf_page | documented_reporting_cutoff_date/raw; cutoff_source_pdf_page | ISO date, literal source text, 1-based PDF page |
| temporal.publication_date / first_available_date | same-named columns | ISO date or null, unknown for all five sources; never inferred from cutoff or file timestamp |
| temporal.source_platform | source_platform | Reported IPM / CRIP label |
| quality.snapshot_flags | snapshot_issues_json plus explicitly linked source notes | Structured warnings, separate from extraction validity |
| quality.source_notes | documented_source_notes_json | Source statements and page provenance, not inferred events |

## Values, missingness and units

Every `values` member has `{raw, normalized, unit, missing_reason}`. Raw is an exact exported string, including commas and parentheses (physical_cells separately retains cell line breaks). Normalized numeric values are canonical decimal strings, never binary floating-point numbers. Normalized date values are YYYY-MM strings, never invented day-one timestamps. Normalized identifiers are strings. Unit is `Rs. crore`, `percent`, `month`, or null for identifiers.

A source missing marker (`NA`, `N/A`, `-`, parenthesized equivalents, `()`) yields normalized null and `missing_reason=source_marker`. A documented literal blank yields raw empty string, normalized null and `missing_reason=source_blank`; preserve source_empty_fields_json evidence. A known value has missing_reason null. Unexpected blanks or malformed values must fail the import, not quietly become missing. Missing, unknown availability and not observed in a month are different concepts.

Parentheses in these table slots group a second value and do not mean negative numbers. Literal minus signs are preserved and checked. Raw `0.00` normalizes to string `0`, never null. August revised costs are published zeros; retain them and warn about baseline comparability. Do not substitute original cost or a prior month's revised cost.

May's 11 verified health records have start `()` and original target date blank with revised `(-)`; this documented source pattern is accepted without invented dates. No numeric missing markers occur in these five full extracts.

## Monitoring indicators and quality

Allowed indicators are reported physical progress and cumulative expenditure; pairwise reported deltas (progress in percentage points, expenditure in Rs. crore); date shifts in months; baseline changes; and observed presence/count summaries. Numeric deltas require both normalized values; otherwise null with missing reason. Formatting-only changes are separately identified. No planned progress, actual completion date, project completion status, model prediction, probability or risk score is available in this history.

Pair `changes` preserves before/after raw values, status, delta and raw_text_changed for every numeric/date field. Status: unchanged, increased/decreased for numbers, postponed/brought_forward for dates, became_available/became_missing/both_missing. Exact status strings follow the existing comparison helper (see API contract). Quality has typed scope (`snapshot`, `pair`, `report`), code, affected field(s), source month/page when available, and a factual reason. Codes cover missing values, completion_before_start, out_of_range, unreviewed_identity_change, conflicting_auxiliary_identifiers, baseline_* fields, reported_*_decrease_requires_review, documented_split_scope_requires_review and documented_publication_inconsistency. Missing auxiliary identifiers are recorded even when they do not block numeric screening.

`trend_eligible` is the existing conservative pair-wide gate; `completion_trend_eligible` adds known-date requirements. Preserve exact exclusion reasons and policy identifier `monthly-history-v1`. No new field-specific eligibility boolean is invented. Field-specific quality reasons are exposed; a conservative pair-wide result establishes neither usability nor unusability of any individual field. The frontend displays null measurements and unknown availability explicitly as "Unknown" while retaining source markers. Zero eligible July-August pairs reflects changed revised-cost baselines under this policy, not proof that all progress/expenditure/date observations are unusable. Field-specific use needs explicit review; raw changes remain accessible.

Portfolio counts measure published ongoing-table observations, not completed projects. Avoid cross-month cost/expenditure sums or mean progress as performance indicators: changing code scope, split projects and missing baselines defeat that interpretation. Count source warnings separately from pair exclusions; totals must declare denominators and filtering scope.
