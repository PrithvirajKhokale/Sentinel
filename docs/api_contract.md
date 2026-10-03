# MVP project data API contract v1

The first local implementation delivers GET /projects and GET /projects/{project_code}; history and portfolio-summary remain specified for later delivery. See [local backend](backend-local.md). FastAPI/Pydantic are retained. Base path `/api/v1`; the initial demo is local on loopback only, with a React + Vite frontend. Retain PostgreSQL/SQLAlchemy storage. Authentication and authorization are required before any shared deployment; they are not implemented here. Grounding: validated April-August history (9,321 snapshots / 2,111 codes). See [dictionary](data_dictionary.md) for the complete snapshot value object and units and [actual-record examples](examples/project-data-contract.json).

## Dataset and envelopes

Every successful response is `{data, meta, warnings}`. `meta` contains `contract_version="1"`, `dataset_version` (canonical dataset manifest SHA-256), `validation_status="validated_history"`, and effective `filters`. List/history responses also contain `pagination`. Consumers must not combine pages from different versions. Optional `dataset_version` query selects an available immutable version; omission selects the active validated version. Unknown version: 404. Invalid/partial artifacts are never served: 503 DATASET_NOT_VALIDATED if no validated serving version exists. An older valid active version may remain available, explicitly identified, after a failed regeneration.

`warnings` are structured `{scope, code, fields, report_month, source_pdf_pages, message}`; unavailable context is null or an empty array, never invented. Full snapshot fields are those in the dictionary. All values keep raw strings and normalized decimal/month strings or null. Explicit nulls are retained in JSON. The UI displays unknown values as "Unknown" rather than zero or a fabricated date. No predictions, risk probability, completion status or implicit absent-month rows appear.

## Revision manifest

`dataset_version` is lowercase SHA-256 of the canonical manifest bytes, not the history CSV hash. Canonical encoding: UTF-8 JSON, sorted object keys recursively, separators comma/colon without spaces, ensure_ascii=true, no BOM or trailing newline. Arrays are ordered: source_reports ascending report_month, computation paths as listed in the schema below, references ascending path, mappings ascending mapping_id. No timestamps or self-hash enter the manifest.

Manifest version 1 contains schema_version (`project-data-v1`), source_reports (month, filename, source hash), computation (path/hash for extractor, history builder, comparison helper and extraction dependencies), catalog hash, reviewed reference path/hashes, canonical_mappings (empty for MVP; future entries require mapping_id, version, path, hash), and outputs (history hash and adjacent output hash map). [The concrete canonical manifest](examples/dataset-manifest.json) covers the validated sources and final computation. Validation audits are checked independently on import; output hashes must match both audits and manifest. A source, computation, schema, mapping or output change creates a new revision. Preserve earlier manifests and their artifacts separately; an active revision pointer never destroys the prior revision.

Raw names/codes are immutable reported values. Any future canonical mapping is explicit, versioned, hashed and separately exposed; it cannot replace raw values, silently change filters, merge identities or alter the snapshot key. No canonical mapping is applied by the MVP.

## Endpoints

| Method / route | Data | Selection |
|---|---|---|
| GET /projects | Array of full project snapshots | Required report_month; one row per code in that report |
| GET /projects/{project_code} | One full project snapshot | Required report_month; exact snapshot, no fallback to another month |
| GET /projects/{project_code}/history | Array of full snapshots, plus comparisons in meta | Optional from_month/to_month, defaults dataset bounds; ascending month |
| GET /portfolio-summary | Report-scoped counts and optional adjacent-pair monitoring summary | Required report_month; optional comparison_month, which must be immediately preceding calendar month |

Snapshot detail 404 PROJECT_NOT_OBSERVED means no published ongoing snapshot for that code/month; it never means completed. History 404 PROJECT_NOT_FOUND means code unknown in the selected dataset. Known code with no records inside a valid range returns an empty 200 history. Detail and list for a report absent from the dataset return 404 REPORT_NOT_AVAILABLE.

## Filters and pagination

- report_month, from_month, to_month and comparison_month use YYYY-MM and must be supported report months; malformed values are 422. Range order must be valid; unsupported month is 404 REPORT_NOT_AVAILABLE.
- List and summary accept exact case-sensitive reported `ministry`, `sector`, `state`, and `agency` strings. `state` matches the full source label, not inferred multi-state membership. Repeated parameters mean OR within that field; fields combine with AND. Unrecognized but valid strings yield an empty scope.
- List accepts repeated `project_code` and optional `q` (1-200 characters), case-insensitive literal substring of project_name. No fuzzy identity matching. Filters apply to the selected month, never a latest description.
- List/history use `page` (integer >=1, default 1), `page_size` (1-100, default 25). `pagination={page,page_size,total_items,total_pages}`; total_pages=0 for empty sets; a page beyond the end is an empty 200. No fabricated example request IDs or cursors. Stable list sort is project_code ascending as a string, history sort report_month ascending. Arbitrary sort is not supported in v1.
- Unknown query parameters and invalid types/limits return 422 VALIDATION_ERROR. Filters are echoed in canonical arrays/scalars. Each endpoint only accepts its documented parameters; history does not accept identity filters, so identity changes cannot hide earlier observations.

History comparison pairs are drawn from complete filtered-range snapshots before pagination and reference codes/months rather than duplicating full snapshots. Include only immediately adjacent calendar months where both snapshots exist. A missing month is explicitly listed in `meta.not_observed_months`, and a gap is never bridged to calculate an adjacent trend. Comparisons preserve full changes, identity differences, baseline/auxiliary changes, missing values, quality flags and conservative eligibility reasons. Both raw snapshots remain addressable by detail endpoints. Each comparison has project_code, before_month, after_month, identity_review_status, screening_policy, trend_eligible, completion_trend_eligible, changes, identity_differences, baseline_changes, auxiliary_identifier_changes, before_missing_values, after_missing_values, quality_flags, trend_review_reasons and source_notes. These map directly from corresponding JSON columns in adjacent outputs; keys inside changes/baseline/missing-value maps retain CSV `_raw` field names for traceability. Numeric/date change delta is a decimal/integer string or null, with units determined by the dictionary. Warning fields in the API use snapshot value names without `_raw`. Pagination never creates comparison pairs from page endpoints.

## Monitoring and portfolio semantics

Portfolio data: `report_month`, `counts={snapshot_records,distinct_project_codes,ministries,sectors}`, `quality_counts` (by warning code, field and missing reason), and optional `comparison`. Without comparison_month, comparison is null. With it, shared/before_only/after_only, progress/expenditure change-status counts and conservative eligibility counts come from the matching adjacent comparisons, not the April-August reviewed pair. Before/after filters apply independently to their own reported fields: crossing a filter boundary is scope membership change, not necessarily report absence. Presence outputs must distinguish `not_in_filtered_scope` from `not_observed_in_report` by checking the unfiltered snapshot index.

Return comparison denominators: before_scope_count, after_scope_count, shared_scope_codes, missing-input counts and exclusion counts. Report source warnings with their page and report month. All decreases are reported differences with unknown causes; source split notes do not prove their cause. No completion count is inferred from absence, 100% progress or headline commissioned totals. No cross-month financial sum or portfolio risk score is proposed.

`trend_eligible=false` is a conservative screening outcome, proof of neither usability nor unusability of individual fields. In July-August all 1,694 shared matches are excluded because revised-cost baselines change to literal published zeros; other field-specific reasons also remain visible. Keep zeros, raw changes and the policy unchanged. No field-specific eligibility score is asserted without review.

## Errors

All errors, including FastAPI request validation, use `{error:{code,message,details},meta:{contract_version,dataset_version}}`. details is an array of `{location,code,message}`; location is a path such as `query.report_month`. dataset_version is null when unresolved. Do not return stack traces, secrets, source filesystem paths or fabricated records.

| HTTP | Code | Meaning |
|---|---|---|
| 422 | VALIDATION_ERROR | Invalid type/format/range or unsupported parameter |
| 404 | REPORT_NOT_AVAILABLE / DATASET_NOT_FOUND | Well-formed but unavailable report/version |
| 404 | PROJECT_NOT_FOUND / PROJECT_NOT_OBSERVED | Unknown code / absent exact snapshot |
| 503 | DATASET_NOT_VALIDATED | No acceptable validated serving dataset |
| 500 | INTERNAL_ERROR | Unexpected service failure, generic message |

Shared deployment must enforce authentication and authorization first. Reserve 401 AUTHENTICATION_REQUIRED for missing/invalid credentials and 403 ACCESS_DENIED for insufficient access, using this same envelope. Provider, roles and session/token mechanism remain decisions; this document implements none. Local demo must bind loopback and must not be exposed as an unauthenticated shared service.

## Examples and acceptance

[Representative JSON responses](examples/project-data-contract.json) contain separate request/response examples for list, detail, history, portfolio and validation error. Values are mapped from validated records and adjacent outputs; error example is explicitly illustrative. Example detail uses July Ken-Betwa to show zero progress and missing dates; history uses June/July Nadikude to show reported decreases and identity/baseline flags. Full unfiltered July-August portfolio counts illustrate zero eligible pairs without suppressing changes.

Remaining implementation decisions: authentication provider/roles, local ports, revision storage/retention operations, exact storage/index design and reviewed field-specific suitability rules. Future acceptance checks should prove exact decimal/raw/null preservation, source traceability, stable pagination, scoped counts and membership distinctions, missing-month gaps, conservative reasons and fail-closed dataset import. The implemented endpoint scope and reproduction checks are documented in the local backend guide.
