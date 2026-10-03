# April?August 2026 project history

## Coverage and independent source inspection

Each report was inspected independently: cover, contents, Table 1 summary, Table 6 divider/header, ongoing rows, and closing notes. All five identify the ongoing table as Table 6. Counts are published ongoing records, not inferred project populations.

| Report | Records | PDF record pages (1-based) | Ministries / sectors | Count checks | Reviewed visual records |
|---|---:|---|---|---:|---:|
| April | 1,981 | 55?162 | 17 / 22 | 80 | 16 |
| May | 1,987 | 54?162 | 17 / 22 | 80 | 14 |
| June | 1,847 | 59?159 | 17 / 22 | 80 | 11 |
| July | 1,775 | 55?152 | 17 / 22 | 80 | 11 |
| August | 1,731 | 57?152 | 17 / 21 | 78 | 14, plus original first 10 |

All full audits have `status=validated_full`, `coverage_pass=true`, CSV round-trip PASS, continuous serial coverage, no duplicate codes, and empty rejected/ambiguous issue logs. Section totals and each report's Table 1 counts reconcile. Independent reader cell checks cover all eight physical cells per record (May 15,896; June 14,776; July 14,200). This is extraction agreement, not a claim that every source value is correct.

The eight physical columns are serial; project name/agency/code/legacy OCMS/PMG identifiers; state; approval/start month; original target/revised completion month; original/revised cost; cumulative expenditure; physical progress. Money is Rs. crore; progress is percent; source dates are MM/YYYY. April/May use IPM terminology; June onward uses CRIP. Raw decimal precision, parentheses, zero and missing markers remain unchanged. Wrapped agencies and page context use the existing extractor; all contributing source pages and raw physical cells are retained. No actual multipage records were found in these runs.

May contains 11 health records (serials 446?451, 464, 467, 470?472, PDF pages 75?77) with approval `NA`, start `()`, and completion cell containing only `(-)` in the revised slot. Their original completion date is genuinely blank. The narrowly defined parser exception preserves that blank and records `source_empty_fields_json`; it does not synthesize a date or NA. Other unexplained blanks and ambiguous single dates still fail validation.

The 36 new visual fixtures were manually transcribed from rendered May/June/July records, checked with source text for cramped glyphs, and retained in tests/fixtures. They cover first/last records, page boundaries, ministry/sector transitions, wrapped names/agencies, zero expenditure/progress, NA, missing identifiers/dates, and the May date exception. Expected values were not regenerated from extractor output. Additional rendered checks covered large decreases and impossible completion/start order. April/August fixtures and the original first-10 check remain unchanged and passing. All 32 tests pass.

## Temporal metadata and source acquisition

`config/monthly_reports.json` records exact source filenames/SHA-256 hashes, discovered table/page ranges, expected counts, reviewed fixtures, and separate temporal metadata. Obtain the matching flash-report PDFs from the PAIMANA report service identified inside the PDFs, or a teammate's preserved source copies; put them at the exact catalog paths under data/raw/. Verify their hashes against the catalog before extraction. A differently revised PDF requires separate review, not changing its hash to bypass validation. PDFs and generated outputs remain ignored.

| Report label | Documented reporting/submission cutoff (PDF page 2) |
|---|---|
| April 2026 | 2026-05-19 |
| May 2026 | 2026-06-24 |
| June 2026 | 2026-07-24 |
| July 2026 | 2026-08-21 |
| August 2026 | 2026-09-24 |

The source says ?latest by?; this is not a publication or availability date. `publication_date` and `first_available_date` remain null (blank in CSV). Filesystem dates are not substituted. This history is not suitable for time-available modelling without independently established availability dates.

## History and consumer acceptance

The combined CSV has **9,321 snapshots, 2,111 distinct codes, and 1,609 codes observed in all five months**. Its key is `(project_code, report_month_iso)`. Every raw monthly row survives; no absent-month rows, imputation, code-family aggregation or earlier-month overwrites occur. Normalized decimal strings and YYYY-MM dates are additional columns, separate from raw values. Missing stays missing; zero stays zero. Source filename/hash, contributing PDF/printed pages, ministry/sector, physical cells, reviewed source notes and cutoff provenance remain available.

The builder refuses changed/dropped previously written history rows. A corrected source or revised snapshot requires a separately versioned output directory; do not delete old history to bypass this safeguard. Input snapshot CSVs are never rewritten by the builder.

Accept a full snapshot only with `validated_full`, full scope, coverage and round-trip passing, empty extraction issues, and matching PDF/CSV/extractor/reference hashes. The builder enforces these conditions and verifies the reviewed fixture values. Accept history only with `validated_history`, coverage true, and matching catalog, code, source, audit, reference and output hashes. It writes `running` before work and `failed` on failure; an old CSV beside a failed audit is not validated. Empty pipeline issues do not erase source-quality flags or prove trend reliability.

## Adjacent comparisons and limitations

Each comparison retains both raw snapshots, reported changes, missingness and quality flags. April?August's 67 harmless / 40 material / 18 unresolved review decisions apply only to that earlier pair and are never loaded for adjacent pairs. New identity differences remain unreviewed. Auxiliary identifier disappearance is logged separately from conflicting populated identifiers; no conflicting populated auxiliary IDs were found.

| Pair | Shared | Before only | After only | Identity flags | Baseline flags | Progress decreases | Expenditure decreases | Screened / excluded |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| April?May | 1,951 | 30 | 36 | 6 | 16 | 35 | 39 | 1,854 / 97 |
| May?June | 1,825 | 162 | 22 | 584 | 31 | 19 | 38 | 1,172 / 653 |
| June?July | 1,732 | 115 | 43 | 241 | 197 | 91 | 85 | 1,384 / 348 |
| July?August | 1,694 | 81 | 37 | 29 | 1,694 | 13 | 54 | 0 / 1,694 |

Baseline flags include changed approval/start/original/revised cost values. Formatting-only changes do not count as numeric changes. Identity differences, changed baselines, critical missing values, reported decreases, documented split context and source inconsistencies exclude conservative numeric trends. Missing auxiliary/revised-date values are logged even when they do not alone exclude numeric trends; completion trends require known date values. Screened subsets exclude decreases by design and are biased, not representative performance statistics. All July?August shared revised costs change to August's literal zero, so none passes this stricter baseline screen. Zero July?August trend-eligible matches is the result of this conservative, pair-wide screening policy, not proof that all measurements are unusable. Individual progress, expenditure and date observations and changes remain available with field-specific quality reasons in changes_json, baseline_changes_json, missing-value fields and quality_flags_json. Field-specific use requires explicit review of identity, scope and the relevant measurement; this run neither reinterprets revised-cost zeros nor relaxes screening. Do not reinterpret zero as NA or reuse the older April?August screening policy.

Selected reported changes verified against source pages:

- Malanjkhand 400426: April?May progress 84.87 to 23.5 (?61.37 percentage points).
- Nadikudi/Nadikude 400298: June?July progress 55.02 to 2; expenditure 3,119.31 to 2,535.68 crore. Agency and start-date changes also require review.
- Paradip PX/PTA 604859: June?July expenditure 70,820.19 to 8,870.29 crore; Barauni 701324: 74,990.3 to 13,089.84 crore. Agency identities also change.
- BharatNet 706775: July?August expenditure 48,809.69 to 10,320 crore. July explicitly documents a split into 26 projects including the original, with 20 available and six to be onboarded later (PDF page 152). Keep those codes separate. The note does not prove the cause of the expenditure decrease.

Source limitations:

- May page 162 says five IDs were withheld for expenditure inconsistency, but 618816 is actually present in Table 6 (serial 1762, page 149). Preserve the row and contradictory note; flag the affected match.
- June page 160 explicitly withholds 24 IDs for expenditure inconsistency; none is observed in June Table 6. It does not call them completed. July page 152 separately labels 21 withheld IDs completed; retain that source statement without extending it to other absences.
- May and July warn that revised costs below Rs.150 crore are under reconciliation.
- Legacy/PMG identifiers become universally missing from June onward. Missing approval dates remain 11/22/19/12/2 in April?August; revised completion missingness is 354/352/308/348/303. May has 11 empty start markers and 11 source-blank original completion dates. Financial/progress fields have no missing markers.
- Revised completion precedes start for 618393 in June/July and 618106 in July/August; these snapshots are flagged. No date is corrected.
- Headline added/commissioned counts do not close a simple previous-total roll-forward: gaps for May/June/July/August are ?13/?27/?83/?34. This is an unresolved source temporal reconciliation, separate from passing within-report Table 1 reconciliation. Added/commissioned headline counts cannot identify causes for individual presence changes.

Absence does not establish completion or start. Decreases are reported changes with unknown causes. Outstanding identity/scope review, source inconsistencies and unknown availability dates block reliable causal or time-available analyses; they do not block reproducing the published snapshots. No models were trained.

## Reproduction (PowerShell, repository root)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-extraction.txt
$reportCatalog = Get-Content config/monthly_reports.json -Raw | ConvertFrom-Json
foreach ($report in $reportCatalog.reports) {
    $extractionArguments = @('scripts/extract_ongoing_projects.py', $report.pdf,
        '--all', '--output', $report.csv, '--validation', $report.audit)
    foreach ($reference in $report.references) {
        $extractionArguments += @('--reference', $reference)
    }
    & .\.venv\Scripts\python.exe @extractionArguments
    if ($LASTEXITCODE -ne 0) { throw "Extraction failed: $($report.report_month)" }
}
.\.venv\Scripts\python.exe scripts/build_monthly_history.py
if ($LASTEXITCODE -ne 0) { throw 'History validation failed' }
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Outputs: data/processed/monthly_history/april_august_2026_history.csv; four adjacent pairs with changes, presence, questionable matches and separate decrease CSVs; data/validation/monthly_history.json. Per-month full CSV/audit paths are in the catalog. Original first-10 and April?August pair reproduction commands remain in the existing extraction/comparison notes. Generated CSVs, logs, renders, and audits are ignored; fixtures/catalog/code/documentation are reviewable source.
