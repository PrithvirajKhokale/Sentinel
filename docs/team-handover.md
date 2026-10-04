# Sentinel team handover

## Ownership and current delivery

- Prithviraj: Data/ML. Maintain extraction and source-quality review; investigate defensible outcome labels before model training.
- Kaushik: Backend, as requested. Own database/import/API maintenance and frontend integration.
- Tahiyya: Proposed frontend owner; confirm this assignment with her. Build the React + Vite monitoring dashboard.

PR #6 merged the PostgreSQL importer and project list/detail endpoints. PR #7 adds project history and portfolio summaries. Use merged main after PR #7 is reviewed and merged as the shared starting point. The frontend, authentication, shared deployment and prediction models have not been implemented.

The five reports contain 9,321 monthly snapshots across 2,111 project codes. There are 7,202 stored adjacent comparisons. PR #7 reports 62 tests passing against real PostgreSQL, including existing regressions. These are local reported results; each teammate should reproduce relevant checks on their own machine.

## Before starting

1. Accept the repository invitation if still pending. Repository owner checks Settings > Collaborators for accepted access. Invitation acceptance has not been verified by this guide.
2. Clone https://github.com/PrithvirajKhokale/Sentinel, or safely update an existing checkout. Preserve uncommitted work; do not reset or force-push.
3. Start a separate branch from merged main. Suggested names: feat/backend-integration (Kaushik), feat/frontend-monitoring (Tahiyya), feat/completed-project-label-audit (Prithviraj).
4. Read [architecture](architecture.md), [API contract](api_contract.md), [data dictionary](data_dictionary.md), and [request/response examples](examples/project-data-contract.json).
5. Submit separate PRs. Coordinate changes to the API contract before implementing incompatible behavior.

## Kaushik: reproduce and maintain the backend

Start with [backend-local.md](backend-local.md). It contains PowerShell commands for dependencies, Docker PostgreSQL, migrations, validated import, serving, requests and tests.

A clone does not include PDFs, full generated CSVs/audits, database contents or revision archives. Obtain the matching source PDFs from Prithviraj's preserved copies or the report service. Place them at these exact paths:

| Report | Local path |
|---|---|
| April | data/raw/FlashReport_April2026.pdf |
| May | data/raw/FlashReport_May2026.pdf |
| June | data/raw/FlashReport_June_2026.pdf |
| July | data/raw/FlashReport_July_2026.pdf |
| August | data/raw/FlashReport_August_2026.pdf |

Verify source hashes against [the catalog](../config/monthly_reports.json). Do not change catalog hashes to accept a different PDF. From the repository root, PowerShell:

~~~powershell
$catalog = Get-Content config/monthly_reports.json -Raw | ConvertFrom-Json
foreach ($report in $catalog.reports) {
    $actual = (Get-FileHash -LiteralPath $report.pdf -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $report.source_sha256) { throw "Source hash mismatch: $($report.pdf)" }
}
~~~

Follow [monthly history reproduction](monthly-project-history.md) to regenerate extraction outputs and audits, then follow backend-local.md to migrate and import. Use personal local credentials; keep secrets and generated files ignored. Do not share someone else's database password.

Local defaults: PostgreSQL 127.0.0.1:5433; API 127.0.0.1:8000. API documentation is http://127.0.0.1:8000/docs on the machine running the API. Another person's localhost does not point to Prithviraj's machine.

After merging PR #7, an already imported PR #6 database needs no new migration or reimport solely for these read endpoints. A fresh teammate setup still needs migrations and an import.

First deliverable: demonstrate all four endpoints locally and reproduce tests with BACKEND_TEST_DATABASE_URL set. Without that variable, integration tests are skipped, so a passing command alone does not prove database behavior.

Then support frontend integration. Agree with Tahiyya on local development ports and a Vite /api proxy to the local backend. Keep the API contract stable. Authentication/authorization must precede shared deployment; provider and roles remain decisions. Performance benchmarks and unpaginated comparison/presence metadata are later backend work.

## Tahiyya: build the monitoring frontend

If she accepts frontend ownership, start React + Vite on her own branch. The documented JSON examples allow UI work immediately without waiting for a local database.

First deliverable:
- Project list with report-month selection, name search, exact filters and pagination.
- Project detail showing raw/normalized values, units, source pages and warnings.
- Monthly history with explicit gaps and reported adjacent changes.
- Portfolio counts and quality summaries, with comparison denominators and scope-versus-report absence.
- Loading, empty, error and unavailable-dataset states.

Use the examples for development mocks, then integrate all four real endpoints with Kaushik. Do not present mock data as live data. A portfolio endpoint does not accept name search or project-code filters; do not silently imply that its counts reflect those list-only filters.

Show null as Unknown and preserve literal zero. Dates represent months; do not invent days. Keep exact decimal strings for display. Label reported progress/expenditure decreases as reported changes with unknown causes. Missing from a report and 100% progress do not establish completion.

Pin dataset_version across related calls and pages once resolved, so the UI does not mix revisions. Render field/report warnings and source provenance. Do not add fabricated risk scores, predictions, completion badges or model accuracy.

Agree local proxy/ports with Kaushik. No frontend launch commands are provided yet because the frontend has not been created. Shared hosting is a separate authenticated deployment task.

## Prithviraj: move to Data/ML

Maintain the validated ongoing-report pipeline and begin an independent audit of completed-project tables. Inspect each source's table label and columns rather than assuming a table number or schema is identical.

First deliverable: a label-feasibility note with source pages and examples, documenting whether actual completion dates, original targets, revised targets, original budgets and defensible final costs are available. Report missingness, conflicting identities and ambiguous scope. Cumulative expenditure is not automatically a settled final cost.

Define the prediction target, assessment date, reference baseline, outcome window and exclusion policy before training. Unknown publication/first-availability dates currently prevent a verified time-available training dataset. Do not infer labels from disappearance, progress=100%, or conservative trend gates. Keep raw data and field-specific review reasons.

No model is trained yet. Training and evaluation should follow an accepted label/data design, with project separation and temporal leakage checks.

## Handover acceptance

- PR #7 reviewed and merged; teammates start from that main revision.
- Relevant uncommitted local work preserved, then local main updated safely.
- Kaushik and Tahiyya have accepted access; roles agreed with both.
- Kaushik has matching PDFs or knows how to obtain them; source hashes match.
- Kaushik reproduces backend setup and relevant PostgreSQL checks.
- Tahiyya can start against examples immediately; live integration follows her local backend setup or coordinated development with Kaushik.
- Each person has a separate branch and a concrete first deliverable.

Do not delay teammates while attempting to finish authentication, deployment or ML yourself. These are owned follow-up tasks.
