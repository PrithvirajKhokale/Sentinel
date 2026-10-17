# Risk Intelligence – Phase 3 implementation and handoff

## What is already implemented (initial reported-signals slice)

**Status:** Feature branch `feat/risk-intelligence`; not merged or deployed until its tests and review pass.

The backend endpoint `GET /api/v1/risk-signals` compares immediately adjacent monthly published observations for project codes found in both reports. It accepts `report_month`, optional `project_code`, `q` (name substring), identity filters (`ministry`, `sector`, `state`, `agency`), `signal_type`, `page`, `page_size`, and `dataset_version`. It reuses the existing bearer-token access controls, revision pinning, error envelopes, and source data. It does **not** alter immutable snapshots or comparisons.

The initial deterministic rules are:

| Code | Trigger | Strict interpretation |
|---|---|---|
| `reported_progress_decrease` | Adjacent physical-progress `status=decreased` | Lower progress *reported*, cause unknown |
| `spending_without_reported_progress` | Expenditure `status=increased` and physical-progress `status=unchanged` | Reported expenditure increased with unchanged reported progress; **not** proof of waste |
| `reported_target_postponed` | Revised target month `status=postponed` | Later stated revised target; **not** a verified work-delay outcome |

Each result supplies source project code and latest reported identity, exact before/after raw values, stored numeric or month deltas, pair months, PDF filenames and pages, the original pair-wide review reasons, and the policy identifier `reported-signals-v1`. It does not calculate probabilities, scores, verified project performance, or completion outcomes. A report missing a project is **not** interpreted as completion. A pair-wide review exclusion does not prove each individual field unusable; this v1 screen exposes descriptive observations with explicit cautions rather than certifying comparability.

The summary count denominator is **shared observed codes within the current filtered scope**, not the total project portfolio. Summary totals cover the whole selected scope even when the response page or signal-type filter displays only part of it; `meta.pagination` counts the matching signals for the selected type. Report months with no immediately adjacent prior report produce zero comparisons and an explicit null comparison month.

The React page adds a fourth sidebar entry, **Risk intelligence**, with source context, summary counts, type selection, identity filters, pagination, evidence cards and project-history inspection. Reference-example mode clearly indicates that full-report screening requires the live API rather than fabricating full-dataset results.

## Acceptance tests before merging/deploying

1. Run frontend Node tests and Vite production build; verify page can be opened and changed in light/dark mode.
2. Run pure-Python signal rule tests with missing data, reported zeros, revision caveats and mismatched pair provenance.
3. Run PostgreSQL integration tests over the complete validated five-month dataset: `2026-08` should compare with `2026-07`, preserve 1,694 shared codes for unfiltered scope, return bounded pagination and revision metadata, and reject unavailable dates/bad input.
4. In the live browser, confirm selection by report month, signal category and Ministry/Sector/State/Agency labels, and inspect at least two source PDFs to manually check before/after values.
5. Check the project-history drilldown, loading/empty/error states, API authentication, revision pinning and private frontend access.
6. Review PR against `feat/frontend-backend-integration`, then merge after checks. The feature branch does not auto-deploy. Schedule production deployment with rollback ready only after sign-off.

## Remaining milestones to finish Sentinel

- **3B – Reporting coverage:** Show absent/before-only/after-only observations separately from risk signals; gap detection must use available report months, never impute missing snapshots.
- **3C – Multi-month monitoring:** Add a clearly specified 3+ observed-month stagnation signal and test identity/scope continuity, missingness and raw-date caveats; do not infer that an absence means project completion.
- **3D – Quality review:** Define and validate **field-specific** comparability decisions with documented human review for baseline, revised-cost zero, project split and identity conflicts. Do not bypass the existing pair-wide warnings.
- **4A – ML feasibility:** Have Yousuf define measurable targets grounded in *future observed reports*, test whether more historical months are needed, avoid target leakage, and report baseline performance including coverage and confidence intervals. A model is not promised until evaluation supports it.
- **4B – Model integration (only if valid):** Version model training data, baseline features, evaluation and explanation policy. Add separately labeled predicted outputs only if the project team approves their interpretation.
- **5 – Production polish:** Complete private-site publishing, authorization appropriate to team users, end-to-end regression testing, review/merge policy, sustainable database retention and backups, README/demo and ownership handoff.

## Roles
- Data + frontend: user – dataset validation, dashboard, user experience and final cross-system acceptance
- Backend: Tahiyya – signal API, field-eligibility review endpoints, security and PostgreSQL tests
- ML: Yousuf – label audit, feature engineering, baseline modeling, time-aware evaluation and interpretability

**Scope boundary:** Until the ML target feasibility and evaluations pass, describe Sentinel as a historical infrastructure monitoring system with **evidence-backed reported signals**, not a validated predictor of delay/cost-overrun probabilities.
