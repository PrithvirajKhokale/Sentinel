# Sentinel — Experiments

## Experiment 001 — Model Comparison

### Objective

Compare candidate models for project risk prediction.

### Models

- Baseline
- Random Forest
- XGBoost

### Results

| Model | Metric | Result |
|---|---|---|
| Baseline | [Metric] | [Value] |
| Random Forest | [Metric] | [Value] |
| XGBoost | [Metric] | [Value] |

### Conclusion

[Record conclusion based on actual results.]

### Next Step

[Record next experiment.]

## Data extraction check - 2026-10-03

Extracted August 2026 Table 6 serials 1-10. All 80 physical cells agreed between two PDF readers; all 190 exported fields matched the visually reviewed reference, and CSV round-trip passed. See [extraction notes](data-extraction.md). No models were trained.

## Full August data extraction check - 2026-10-03

Extracted all 1,731 Table 6 records across 17 ministries/departments and 21 sectors. Serial coverage, 30 section totals, and 48 independent Table 1 count entries match. No duplicate project codes, blank fields, or rejected/ambiguous rows. The original first-10 reference still passes. See [full extraction audit](august-full-extraction.md) for visual samples, missing markers, and source limitations. No models were trained.

Review preparation: final full extraction and audit regenerated; all 13 tests, first-10 reference, and unchanged 14-record visual reference passed. Audit status is validated_full and the issue log is empty. Source acquisition, regeneration, hashes, and consumer acceptance rules are documented in the full extraction audit.

## April-August snapshot comparison - 2026-10-03

April 1,981 and August 1,731 published ongoing projects passed full extraction audits. Code join: 1,617 shared, 364 April only, 114 August only. Observed 92 progress decreases and 57 expenditure decreases; source and identity changes require review. Absence does not establish completion. All 19 tests and original August reference checks passed. See [findings and reproduction](april-extraction-comparison.md). No models trained.

Merged-main integration and identity review: branch safely fast-forwarded to c99e72b, including August ca9c8c4; April additions preserved. All 125 flags reviewed: 67 harmless identity-text changes, 40 material reported differences, 18 unresolved. Conservative trend gates retain all raw changes but exclude questionable matches (780 screened / 837 excluded). All 19 tests and April/August regressions rerun successfully. Decreases are reported changes with unknown causes; absence does not establish completion. No model training.
