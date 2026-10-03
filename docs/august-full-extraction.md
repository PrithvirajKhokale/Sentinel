# August 2026 full Table 6 extraction

Work branch: `feat/august-full-extraction`, based on merged PR #1 on `main` (`19ed36f`). No model training was performed.

## Coverage and validation

The generated CSV is `data/processed/august_2026_table6_all.csv`. Source rows cover PDF pages 57-152 (96 pages), printed pages 56-151. Results:

| Check | Result |
|---|---|
| Headline ongoing count, PDF page 4 | 1,731 expected / 1,731 extracted |
| Serial coverage | Exactly 1-1731 in source order; no gaps or duplicates |
| Unique project codes | 1,731; no duplicate codes |
| Ministries/departments | 17, matching the headline |
| Unique sectors | 21 |
| Table 6 ministry/sector section totals | All 30 match; sum 1,731 |
| Independent Table 1 counts, PDF pages 24-25 | All 48 match: 30 sectors, 17 ministry totals, one grand total |
| Independent PDF-reader checks | 13,848 project cells agree after whitespace normalization |
| Original first-10 reference | All 190 original fields still match |
| CSV string round-trip | Pass |
| Blank exported fields | None |
| Rejected / ambiguous rows | None; the issue log is empty |
| Actual multi-page project records | None found |
| Actual wrapped agencies | None found; wrapped names and states are present |

The headline scan also records the North Eastern Region's separate count (209 / 11). That regional subtotal is not treated as the full report count. Table 1 ministry/sector counts provide the independent reconciliation of the full table.

## New fields and raw-value policy

The original 19 fields retain their definitions. New fields are `ministry`, `sector`, `pdf_pages`, `printed_pages`, and `source_cells_json`. Headings are carried forward across repeated page headers until a new heading appears. Both Ministry and Department labels are recognized. Ministry names are not inferred from an agency or sector: for example, serial 148 is Ministry of Coal / Railways and serial 149 is Ministry of Power / Coal.

`pdf_page` and `printed_page` are the first source page; the plural fields contain semicolon-separated source pages for a continued record. Validation evidence retains every contributing physical row, its page, raw cell texts and bounding boxes. `source_cells_json` preserves raw line breaks and cell contents in the CSV. Read the CSV as strings; spreadsheet type inference can alter codes and dates.

Names, states and agencies have whitespace joined for readable scalar fields. Exact agency wrapping remains in the raw cells. Parentheses, spelling, date strings, grouping commas, markers, and zero values are not repaired or imputed.

## Wrapped agencies and page continuations

Agency extraction finds the final balanced parenthesized block before identifiers, so an agency may wrap or contain nested parentheses. A separate-line boundary is required to avoid consuming parentheses in the project name.

Physical records are deferred until a subsequent numbered row, heading, total, or table end. An incomplete row can join a fragment on the immediately following page in the same section, either with blank serial or with the same serial repeated. A complete row is never enlarged by an unattributed fragment. Repeated table headers are omitted before assembly. Non-adjacent fragments, different serials, unbalanced agencies, incomplete paired fields, unrecognized layouts, PDF-engine disagreement and reference mismatches are logged with pages and reasons.

Actual August rows fit within their individual pages and agencies occupy a single source line. Continuation and wrapped-agency handling therefore have synthetic test coverage, not evidence of real split records in this PDF.

## Issues and unresolved source limitations

No unresolved extraction ambiguities remain for this August run. Source data limitations remain:

- `approval_date_raw` is `NA` for serials 554 and 1721. Start dates remain present and are not substituted for approval.
- `revised_doc_raw` is `(-)` for 303 projects.
- All 1,731 legacy OCMS and PMG identifiers are `(-)`.
- All 1,731 Table 6 revised costs are `0.00`. The report says revised costs below Rs. 150 crore are under reconciliation; its headline revised-cost figure differs from the table's zero totals. These reported values are retained without reconciliation or reinterpretation.
- Agency placeholders such as `(INVALID CO.)` and inconsistent-looking source dates/spelling remain unchanged.
- Counts and dual-reader agreement establish extraction coverage and transcription consistency, not factual correctness of reported values.
- OCR/scanned reports, different heading conventions, and layouts outside the validated eight-column grid are not supported. April has not been extracted or validated.

The CLI writes accepted rows plus a detailed audit and a separate `*_issues.jsonl` log, and exits nonzero if the audit fails. An output CSV alone is not proof of complete extraction; check `coverage_pass` and the issue log. Explicit markers are counted separately from absent/blank fields.

## Visual review

All fields were checked against rendered source crops for these 14 records, covering six ministries/departments. Full values are retained in `tests/fixtures/august_2026_table6_visual_samples.json`.

| Serials | PDF pages | Purpose |
|---|---|---|
| 19, 20 | 57, 58 | Last/first rows across the first page boundary; carried aviation headings and wrapped name |
| 26, 27 | 58 | Aviation total and transition to Ministry of Coal / Coal |
| 148, 149 | 63 | Coal / Railways to Power / Coal; avoid confusing sector with ministry |
| 554 | 84 | Railways, NA approval, missing revised date, zero expenditure/progress |
| 675, 676 | 89 | Railways to Roads & Highways, long wrapped names and state |
| 1704, 1705 | 150, 151 | Water Resources page boundary; carried ministry/sector context |
| 1708 | 151 | Long agency name, Sardar Sarovar Project |
| 1721 | 151 | Multi-state wrapping, NA approval, zero progress |
| 1731 | 152 | Final record and closing sector total |

Generated source crops are saved under `data/validation/visual_*.png`. Review included code, name, agency, state, dates, costs, expenditure, progress and section/page context, not just numeric values.

## Obtain the source PDF

The PDF is deliberately absent from Git. A clone does not contain it. Obtain the exact `FlashReport_August_2026.pdf` from the teammate who supplied the reports, using the team's chosen file-sharing channel, and copy it into `data/raw/`. No shared folder or stable download URL is configured in this repository; do not assume GitHub supplies the input. The report identifies PAIMANA/MoSPI as its source, but a later portal export may differ.

Verify the received file before extraction:

- Filename: `FlashReport_August_2026.pdf`
- Size: 6,468,411 bytes
- SHA-256: `af9fad425ca081ab4c1fa49fedc1640ac0e6b199f04372761a31507754a03b02`

```powershell
New-Item -ItemType Directory -Force data/raw | Out-Null
# Copy the file received from your teammate into data/raw before proceeding.
$reportHash = (Get-FileHash -LiteralPath data/raw/FlashReport_August_2026.pdf -Algorithm SHA256).Hash.ToLowerInvariant()
if ($reportHash -ne 'af9fad425ca081ab4c1fa49fedc1640ac0e6b199f04372761a31507754a03b02') { throw 'Source PDF differs from the verified input' }
```

If the hash differs, obtain the verified copy or perform a new review; do not replace fixture values to make a different source pass. Never regenerate the visual reference from extractor output.

## Reproduce

From the repository root, create a local environment and install the already pinned extraction dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-extraction.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
.\.venv\Scripts\python.exe scripts/extract_ongoing_projects.py data/raw/FlashReport_August_2026.pdf --all --output data/processed/august_2026_table6_all.csv --validation data/validation/august_2026_table6_all.json --reference tests/fixtures/august_2026_table6_first10.json --reference tests/fixtures/august_2026_table6_visual_samples.json
if ($LASTEXITCODE -ne 0) { throw 'Full extraction failed; inspect the audit and issue log' }
.\.venv\Scripts\python.exe scripts/extract_ongoing_projects.py data/raw/FlashReport_August_2026.pdf --limit 10 --output data/validation/august_first10_regression.csv --validation data/validation/august_first10_regression.json --reference tests/fixtures/august_2026_table6_first10.json
if ($LASTEXITCODE -ne 0) { throw 'First-10 regression failed' }
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
```

Without `--all` or `--limit`, the default remains the first 10 records. `--reference` checks a subset by serial number and may be repeated. The committed 10-row CSV and original fixture remain unchanged. The full CSV and audit must be regenerated locally and remain ignored.

## Consumer acceptance rules

The final code was rerun with both unchanged fixtures. All 13 tests and the separate first-10 extraction passed. The 14 visual records were compared again with fresh source renders; expected values were not regenerated. Their fixture SHA-256 remains `bae1848aa4d8e83d95a7fb6dbd22d8465d3e694138c1d0699a3db51369746ac0`.

The existence of a CSV is insufficient. The CLI invalidates the prior audit before reading the input: an interrupted or exceptional run leaves `status: running` and `coverage_pass: false`. Completed failures use `status: failed` and exit nonzero. Successful limited runs use `validated_sample`; successful full runs use `validated_full`. A limited run that returns fewer than its requested records also fails coverage. Accepted rows may still be written on failure for inspection.

Consumers of the full dataset must require a zero process exit code for the generating run, `status == validated_full`, `scope == full`, `coverage_pass == true`, `csv_round_trip == PASS`, no issues, and an empty issue log. Verify the actual CSV's SHA-256 against the audit's `csv_sha256`, and the source against `source_sha256`, so an edited or stale output cannot borrow another output's audit. The audit also records `output_path` and `issue_log_sha256`. Treat missing audits or hashes as unvalidated.

Example gate before loading the full CSV (run from the repository root):

```python
import hashlib
import json
from pathlib import Path

csv_path = Path("data/processed/august_2026_table6_all.csv")
audit_path = Path("data/validation/august_2026_table6_all.json")
issues_path = Path("data/validation/august_2026_table6_all_issues.jsonl")
source_path = Path("data/raw/FlashReport_August_2026.pdf")
audit = json.loads(audit_path.read_text(encoding="utf-8"))
valid = (
    audit.get("status") == "validated_full"
    and audit.get("scope") == "full"
    and audit.get("coverage_pass") is True
    and audit.get("csv_round_trip") == "PASS"
    and audit.get("issues") == []
    and issues_path.read_bytes() == b""
    and hashlib.sha256(csv_path.read_bytes()).hexdigest() == audit.get("csv_sha256")
    and hashlib.sha256(source_path.read_bytes()).hexdigest() == audit.get("source_sha256")
    and hashlib.sha256(issues_path.read_bytes()).hexdigest() == audit.get("issue_log_sha256")
)
if not valid:
    raise RuntimeError("Full extraction is incomplete, failed, stale, or modified")
```

Failed-reference and aborted-input runs were exercised separately in ignored diagnostic paths. Both refused validated status; the valid full audit was preserved.

Source PDFs, the new generated full CSV and validation artifacts remain ignored. No new dependency is required. Only extraction code, tests, fixed fixtures and documentation belong in this change.
