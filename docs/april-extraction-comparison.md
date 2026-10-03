# April extraction and Aprilâ€“August comparison

Work branch: `feat/april-extraction-comparison`. No models trained.

## Git starting point

This branch was initially created from main at `19ed36f` with the full August implementation carried forward uncommitted. On the follow-up review, fetched origin and safely fast-forwarded `feat/april-extraction-comparison` to merged main `c99e72b` (PR #2), including `ca9c8c4` as an ancestor. All tracked and untracked April files were preserved in retained stashes before integration. An initial broad stash encountered permission-protected empty directories, so an explicit-path stash was used successfully. Overlapping extractor edits were resolved by retaining April table discovery/schema/numeric extensions over the identical August baseline; both August and April experiment entries were retained. Previously untracked August files matched the newly tracked merged versions exactly. Integration used no reset, force-push, new branch commit, or data deletion. Preservation stashes remain available.

## Independently inspected April source

Source: `data/raw/FlashReport_April2026.pdf`, 163 PDF pages, SHA-256 `90a6959e976da6928440efdea9c68847d1178356e4c0ebd078c51026ddb118d5`.

The April contents and actual divider identify **Table 6: All Ongoing Projects**, independently of August. Divider PDF page 54 (printed 53); project rows PDF pages 55â€“162 (printed 54â€“161). The April headline on PDF page 4 reports 1,981 ongoing projects across 17 ministries/departments. PDF page 7 is a separate **North Eastern Region** subtotal, 229 / 12, not an alternative total.

Observed eight physical columns:

| Column | Observed contents / units |
|---|---|
| Sl.No | Published serial |
| Project Name (Agency) (Project Code) (Legacy OCMS) (PMGID) | Name, parenthesized agency, primary code, two auxiliary identifiers |
| State | Single or multi-state text; PAN India occurs |
| Date of Approval (Start Date) | MM/YYYY or literal missing marker |
| Orignal/Target DoC (Revised DoC) | MM/YYYY or marker; source spelling retained in discovery |
| Orignal Cost (Revised Cost) | Rs. crore; April revised values are parenthesized |
| Cumulative Expenditure | Rs. crore |
| Physical Progress | Percent |

April contains integers and variable decimal precision; August generally uses two decimals and grouping commas. April has populated legacy/PMG identifiers and revised costs, unlike many August values. The extractor discovers the named ongoing table and validates its eight-column header; it does not assume the table number or silently accept another schema.

All codes, raw dates, parentheses, markers and zeros remain strings. Readable names/agencies/states join whitespace; `source_cells_json` preserves source line breaks. Each row includes report month, source filename, ministry, sector, first PDF/printed pages and all contributing pages. No missing values are filled.

## Coverage and verification

| Check | April | August regression |
|---|---:|---:|
| Accepted / headline expected | 1,981 / 1,981 | 1,731 / 1,731 |
| Serial coverage | Exactly 1â€“1981 | Exactly 1â€“1731 |
| Ministries/departments | 17 | 17 |
| Unique sectors | 22 | 21 |
| Ongoing-table section count checks | 31 passed | 30 passed |
| Own Table 1 count checks | 49 passed (PDF 24) | 48 passed (PDF 24â€“25) |
| Independent readers' project cells | 15,848 agree | 13,848 agree |
| Visual reference records | 16 passed | Existing 14 passed |
| Original August first-10 reference | â€” | 190 fields passed, full and separate sample runs |
| CSV string round-trip | PASS | PASS |
| Missing serials / duplicate serials / duplicate project codes | None | None |
| Blank exported fields | None | None |
| Rejected or ambiguous extraction rows | None; empty issue log | None; empty issue log |
| Audit status / coverage_pass | validated_full / true | validated_full / true |

All 19 unit tests passed, including the original 13 August tests and six April/comparison tests. Empty fields are distinct from explicit source missing markers. PR preparation reran both full extractions, the separate August first-10 check and the comparison with the final computation code: all four existing audit/summary files were reproduced byte-for-byte. Source, CSV, issue-log, identity-review and comparison-output hashes were verified. Local ignored evidence is recorded in `data/validation/pr_verification.json`.

April visual references were **manually transcribed from rendered PDF rows**, not regenerated from extractor output: serials 1, 4, 20, 21, 26, 27, 154, 155, 309, 525, 567, 573, 785, 1931, 1968, 1981. They span eight ministries/departments, page boundaries 55/56, Coal/Power transitions, railway and road headings, first/last records, populated IDs, NA, and zero expenditure/progress. Fixture: `tests/fixtures/april_2026_ongoing_visual_samples.json` (23 fields per record, 368 comparisons). Generated crops: `data/validation/april_visual_*.png`. Four anomaly counterparts were also visually checked in August: codes 706775 (PDF 149), 709817 (86), 400298 (82), 400426 (71), crops `august_anomaly_*.png`.

No actual April record spanning pages or wrapped agency was found. Those cases remain covered by synthetic August tests. The independent readers compare text from the same cell coordinates after whitespace normalization; this verifies transcription, not the accuracy of administrative source data. Only selected records received visual review; all records received automated cell and count checks.

## Comparison findings

One-to-one join by primary project code, with unique-code checks in both validated snapshots:

| Presence | Projects |
|---|---:|
| Both April and August | 1,617 |
| April only | 364 |
| August only | 114 |

These reconcile exactly: 1617 + 364 = 1981 and 1617 + 114 = 1731. Membership lists and all matched changes are in the generated comparison CSVs. **Absence from August does not establish completion.** April page 162 explicitly excludes five projects for inconsistent cumulative expenditure (618051, 618307, 619065, 619113, 618816). Three (618307, 619065, 618816) appear in August only; that does not establish they started after April.

For the 1,617 matched codes:

| Metric | Increased / postponed | Decreased / brought forward | Unchanged |
|---|---:|---:|---:|
| Physical progress | 1,153 | 92 | 372 |
| Cumulative expenditure | 1,470 | 57 | 90 |
| Original/target completion | 31 | 14 | 1,572 |
| Revised completion | 657 | 17 | 665 |

Revised completion additionally became available for 50 matches; 228 remained missing in both. No matched revised date became missing. Deltas use exact Decimal arithmetic; progress in **percentage points**, expenditure in **Rs. crore**, date changes in **whole months**. Raw before/after values accompany every delta. Missing markers are never treated as zero. Formatting-only changes are distinguished from numeric changes in the JSON audit.

Identity differences affect 794 matched records: agency differs in 783, name in 156, state in 24 (categories overlap); no ministry or sector changes. The original heuristic flagged **125 potential identity/scope conflicts**, when state/ministry/sector differed or name similarity was below 0.8. All 125 now have manual text-review decisions, described below. The heuristic is not proof of code reuse. Agency changes alone are recorded without claiming a conflicting project identity. Deltas remain code-level source comparisons even when identities differ.

Source missing markers:

| Field | April | August |
|---|---:|---:|
| Approval date | 11 | 2 |
| Revised completion date | 354 | 303 |
| Legacy OCMS identifier | 797 | 1,731 |
| PMGID | 768 | 1,731 |

No progress or expenditure markers were missing. Published zeros remain zeros, including August revised costs; their administrative meaning is not inferred.

### Visually confirmed unusual changes

| Code / project | April Ã¢â€ â€™ August | Source PDF pages |
|---|---|---|
| 706775 BharatNet | Expenditure 46431.54 Ã¢â€ â€™ 10,320.00, **âˆ’36,111.54 crore**; revised completion (03/2027) Ã¢â€ â€™ (03/2019), **âˆ’96 months** | 160 Ã¢â€ â€™ 149 |
| 709817 Dadhaparaâ€“Belha fourth line | Progress 65 Ã¢â€ â€™ 10.00, **âˆ’55 pp**; state changes to multi-state, agency/name differ | 82 Ã¢â€ â€™ 86 |
| 400298 Nadikudi/Nadikudeâ€“Srikalahasti | Progress 55.01 Ã¢â€ â€™ 2.00, **âˆ’53.01 pp**; expenditure 3069.35 Ã¢â€ â€™ 2,535.68, **âˆ’533.67 crore**; name/agency differ | 80 Ã¢â€ â€™ 82 |
| 400426 Malanjkhand Copper | Progress 84.87 Ã¢â€ â€™ 32.00, **âˆ’52.87 pp**, with unchanged name/state/agency | 70 Ã¢â€ â€™ 71 |

BharatNet original cost also changes 61109 Ã¢â€ â€™ 12,709.00 and revised cost (188000) Ã¢â€ â€™ 0.00. The completion date predates its published original/target date; these are unresolved source inconsistencies, not parser repairs. Even after excluding the 125 heuristic identity flags, 42 progress decreases and 38 expenditure decreases remain. All decrease rows are exported for review; they are not labelled fraudulent or physical reversals.


## Follow-up identity review and trend screening

All 125 originally flagged matches were reviewed individually against the before/after project descriptions, agencies, states, ministry/sector, original costs, start dates and source-page provenance in the validated snapshots. This was manual review of extracted source text with existing cell validation, **not visual reinspection of all 125 PDF rows**. The previously documented four paired anomaly rows retain visual evidence. No external agency clarification has been obtained.

Tracked review decisions and raw supporting values: `tests/fixtures/april_august_identity_review.json`. Each code has a classification and rationale. Source PDF hashes and reviewed values are checked on regeneration; changed source PDFs, stale decisions, omitted flags or extra decisions fail validation. No visual extraction fixture was regenerated from extractor output.

| Review class, among original 125 | Count | Meaning |
|---|---:|---|
| Harmless text change | 67 | Same named corridor/work and state; shortened labels, punctuation, spelling, reversed word order, added descriptive/budget references, or display rounding. Does not certify metric comparability. |
| Material reported change | 40 | 24 changed state coverages, 15 explicitly different reported endpoints, lengths or work descriptions, and one changed railway-zone agency. Does not establish a physical scope change or cause. |
| Unresolved | 18 | Ambiguous route equivalence, package boundaries, omitted quantities or work-type/length wording; further authoritative evidence needed. |

Examples:

- Harmless identity text: **611751**, Aurangabad-Ankai; shortened doubling-work wording with the same corridor/state and SCR organization label. Its changed start date and reported expenditure decrease still exclude it from screened trends.
- Material metadata: **400012**, Kandla-Gorakhpur LPG pipeline, multi-state coverage becomes Uttar Pradesh only. **709817** adds Maharashtra to the published state field. These are source-field differences, not inferred rerouting.
- Material descriptions: **616841**, Merta City becomes Merta Katyasani; **705385**, published length 100.52km becomes 97km; **619184**, August omits the April km155-181 segment.
- Unresolved agency labels: **400298**, **611752**, **617214**, **617216**, **705632** change SCR to SCoR; organizational handoff versus reporting-label changes cannot be settled from the PDFs. **705764** changes WR to NWR and is a material reported agency difference. Shared zone acronyms and generic ministry-to-office labels elsewhere were reviewed separately; their wording alone does not certify unchanged responsibility.
- Other unresolved: **400204**, administrative-place route versus Bahraich-Khalilabad endpoints; **611754**, rail-over-rail versus rail-road-over wording; **705515**, duplicated "85 85km"; **617412**, omitted residential-quarter quantities.

The tracked review file contains the complete 125-code inventory, exact before/after descriptions, relevant raw costs/start dates, PDF pages and per-code rationales. All 125 have the same original cost numerically, but **102** have a changed reported start date. This alone does not explain any metric change.

`trend_eligible` is a **conservative screening flag**, not proof of reliable performance. `trend_review_reasons` in JSON and `trend_review_reasons_json` in CSV retain every applicable reason. Exclude a match when:

- Identity review is material or unresolved, or changed identity text outside the reviewed 125 remains unreviewed.
- Reported start date or original-cost basis changes.
- Progress or cumulative expenditure decreases (retained as reported changes requiring review, with no cause assigned).
- Either compared progress/expenditure is missing, or a revised completion date precedes the reported start.

This additional guard catches cases outside the original 125, including BharatNet's changed cost basis and expenditure decrease. The **669 other matches with changed identity text** remain unreviewed; this is not a claim that their identities materially conflict. They are conservatively excluded until reviewed. A reviewed harmless identity edit can still be excluded for another reason: only **3 of the 67** pass all current gates.

Across all 1,617 shared codes: **780 pass screening; 837 are excluded**. Overlapping exclusion counts are:

| Reason | Count |
|---|---:|
| Unreviewed changed identity text outside the 125 | 669 |
| Material reported identity/scope differences | 40 |
| Unresolved identity cases | 18 |
| Changed reported start date | 147 |
| Changed original cost | 28 |
| Reported progress decrease | 92 |
| Reported expenditure decrease | 57 |
| August revised completion before start | 1 |

These counts overlap and do not sum to 837. Screened progress: 620 increases, 160 unchanged; screened expenditure: 712 increases, 68 unchanged. These aggregates **exclude decreases by design**, so they must not be presented as an unbiased performance summary or evidence that decreases do not occur. Raw all-match counts remain 92 reported progress decreases and 57 reported expenditure decreases.

New generated `questionable_matches.csv` contains all 837 excluded matches with reasons; `screened_matches.csv` contains 780 passing the gates. Every common/decrease/identity CSV now also includes review class, reason, trend flag, raw original costs and start dates. Raw before/after records and deltas remain intact in the comparison JSON and common CSV. Consumers must apply `trend_eligible` rather than treating all code joins as reliable trends.

No cause is assigned to a reported decrease. Corrections, platform migration, changed scope or reporting errors remain possibilities requiring evidence, not conclusions. Absence from a published ongoing table never establishes completion.

## Source limitations

April identifies IPM/India Investment Grid as source with latest data 19 May 2026; August identifies CRIP with latest data 24 September 2026. Publication month is not a synchronized event timestamp. Changes in reporting platform, identities, scope, cost basis or corrections may explain some differences. The PDFs alone do not resolve them.

April's closing note also states revised costs below Rs.150 crore are under reconciliation. Counts reconcile published ongoing rows, not all real-world projects. Missing auxiliary IDs cannot independently corroborate the code join; all August legacy and PMG fields are markers. Completion dates are reported targets, not evidence of actual commissioning. No completion or causality inference is made.

## Reproduction and validated-output contract

Obtain the exact April and August 2026 PAIMANA flash reports from the MoSPI PAIMANA publications portal (April source note links `https://paimana-proj.mospi.gov.in`), or request these exact copies from the teammate who supplied them. Place them under the filenames below and verify hashes. Do not substitute another revision without inspecting it and creating independent references. PDFs, generated full CSVs, audits and rendered crops remain ignored. Dependencies are pinned in `requirements-extraction.txt`.

Run from repository root in PowerShell:

```powershell
python -m pip install -r requirements-extraction.txt
python scripts/extract_ongoing_projects.py data/raw/FlashReport_April2026.pdf --all --output data/processed/april_2026_ongoing_all.csv --validation data/validation/april_2026_ongoing_all.json --reference tests/fixtures/april_2026_ongoing_visual_samples.json
python scripts/extract_ongoing_projects.py data/raw/FlashReport_August_2026.pdf --all --output data/processed/august_2026_table6_all.csv --validation data/validation/august_2026_table6_all.json --reference tests/fixtures/august_2026_table6_first10.json --reference tests/fixtures/august_2026_table6_visual_samples.json
python scripts/extract_ongoing_projects.py data/raw/FlashReport_August_2026.pdf --limit 10 --output data/processed/august_regression_first10.csv --validation data/validation/august_regression_first10.json --reference tests/fixtures/august_2026_table6_first10.json
python -m unittest discover -s tests -v
python scripts/compare_project_reports.py --april-csv data/processed/april_2026_ongoing_all.csv --april-audit data/validation/april_2026_ongoing_all.json --april-pdf data/raw/FlashReport_April2026.pdf --august-csv data/processed/august_2026_table6_all.csv --august-audit data/validation/august_2026_table6_all.json --august-pdf data/raw/FlashReport_August_2026.pdf --output-dir data/processed/april_august_comparison --summary data/validation/april_august_comparison.json
```

August SHA-256: `af9fad425ca081ab4c1fa49fedc1640ac0e6b199f04372761a31507754a03b02`.

Consumers must require a successful process exit, audit `status=validated_full`, `scope=full`, `coverage_pass=true`, CSV round-trip PASS, empty issues and issue log, and matching source/CSV/issue SHA-256 values. A CSV existing on disk is not a success signal. Each extraction invalidates its audit before work; failed/interrupted/partial outputs must not be consumed as a validated full dataset. The comparator enforces the full-input contract, defaults to the tracked identity review (override with `--identity-review`), verifies source hashes and reviewed values, and invalidates its own summary first. Require `status=validated_comparison`, matching input/output and identity-review hashes, and `trend_eligible=true` for screened trend use. Extraction validation verifies transcription/coverage; it does not certify trend reliability.

Generated outputs: `april_august_common.csv`, `april_only.csv`, `august_only.csv`, `progress_decreases.csv`, `expenditure_decreases.csv`, `identity_differences.csv`, `questionable_matches.csv` and `screened_matches.csv` in `data/processed/april_august_comparison/`. The comparison JSON retains full before/after records and raw formatting changes; each CSV carries source provenance.
