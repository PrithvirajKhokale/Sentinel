# August 2026 Table 6 extraction sample

Reviewed on 2026-10-03. Both local inputs exist: `data/raw/FlashReport_April2026.pdf` (3,215,216 bytes) and `data/raw/FlashReport_August_2026.pdf` (6,468,411 bytes). Only August was extracted. Work is on `feat/data-extraction`; no model training.

The extractor has since been extended to the full August table; see [full extraction audit](august-full-extraction.md) for current behavior, continuation support and limitations. The results below describe the original sample run.

## Source and scope

August has 153 PDF pages. Table 6: All Ongoing Projects has a divider at PDF page 56 (printed page 55). Its data starts at PDF page 57 (printed page 56). Serial numbers 1–10 are all on that first data page under Ministry of Civil Aviation / Aviation & Aviation Infrastructure. The CSV carries `source_filename`, `report_month` as the literal `AUGUST 2026`, one-based `pdf_page`, and `printed_page`. Month is read from the page, not inferred from a filename.

## Observed columns

| Physical column | CSV fields | Units / interpretation |
|---|---|---|
| Sl.No | serial_no | Source order, string |
| Project Name (Agency) (Project Code) (Legacy OCMS Code) (PMGID) | project_name, agency, project_code, legacy_ocms_code_raw, pmgid_raw | Names and identifiers; code remains a string; agency and missing identifiers retain parentheses |
| State | state | Text; wrapped lines joined |
| Date of Approval (Start Date) MM/YYYY | approval_date_raw, start_date_raw | Month/year text; parenthesized start date retained |
| Orignal/Target DoC (Revised DoC) MM/YYYY | original_target_doc_raw, revised_doc_raw | Original/target and revised completion date; raw month/year or marker |
| Orignal Cost / Revised Cost in Rs. Crore | original_cost_rs_crore_raw, revised_cost_rs_crore_raw | Indian rupees crore; grouping commas and two decimal places retained |
| Cumulative Expenditure in Rs. Crore | cumulative_expenditure_rs_crore_raw | Indian rupees crore |
| Physical Progress (%) | physical_progress_pct_raw | Percent, as printed |

The PDF spells “Original” as “Orignal”. Ministry and sector are merged section headings, not project rows; they are documented here rather than treated as records. There is no separate actual completion date or planned physical progress in these observed columns. No approval/start dates are substituted for one another.

## Preservation and extraction problems

- Every value is exported as text. No date parsing, numeric conversion, imputation, or missing-value substitution occurs.
- All 10 revised costs are literally `0.00`; they remain zero. The report's closing notes say revised costs below Rs. 150 crore may or may not be correct and are under reconciliation. Do not interpret these zeros as missing or confirmed final costs.
- Legacy OCMS and PMG identifiers are `(-)` for all 10 records. Revised completion dates for serials 5 and 8 are `(-)`; they are not invented.
- Names, identifiers, two dates, and two costs share physical cells. Parsing separates these only after checking their layout; unexpected layouts fail explicitly.
- Long names and “Jammu and Kashmir” wrap across lines. Whitespace is normalized in project names and state only; spelling, punctuation, and the duplicated “Building Building” in record 1 are retained. Raw physical-cell text and bounding boxes are saved in validation evidence.
- Repeated table headers, merged ministry/sector labels, totals, and the divider must be skipped. The table is found by its divider, not a hard-coded page number.
- This is a text-bearing PDF; OCR was not needed. Other layouts, multiline agencies, or records split across pages are not yet supported or validated. April extraction is untested.

## Run

Install the pinned direct dependencies into a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-extraction.txt
.\.venv\Scripts\python.exe scripts/extract_ongoing_projects.py data/raw/FlashReport_August_2026.pdf --output data/processed/august_2026_table6_first10.csv --validation data/validation/august_2026_table6_first10.json --reference tests/fixtures/august_2026_table6_first10.json
```

The script accepts any source path, output path, validation path, and positive `--limit` (default 10). The reference is optional for other reports; those runs receive independent cell checks but no visual-reference certification. The current CLI writes accepted records and diagnostics, then exits nonzero if coverage or reference validation fails; see the full extraction audit.

## Validation results

Visually inspected the rendered PDF page against all 10 exported records, including full names, agencies, codes, state, all four dates, both costs, expenditure, progress, and provenance. The reference JSON was recorded from that review, independently of the extraction output.

The executed script passed:
- 10 sequential project records, no heading/total records.
- 80 physical cells matched between pdfplumber's grid extraction and PyMuPDF's independent text reads of the same bounding boxes (whitespace-normalized comparison).
- 190 exported fields matched the visually reviewed reference (19 fields per record).
- CSV write/read round-trip matched all strings, including commas, parentheses, and zeros.

The generated validation JSON includes source SHA-256, both engines' cell text, cell coordinates, and per-record reference results. The rendered page is at `data/validation/august_table6_page57.png`. The CSV sample is explicitly tracked; generated validation evidence and source PDFs are ignored; the extractor, dependency file, reference fixture, and documentation remain eligible for Git tracking.

| Serial | Code | Project (short label) | Original cost (Rs. crore) | Revised cost | Expenditure (Rs. crore) | Progress (%) | Revised DoC |
|---|---|---|---|---|---|---|---|
| 1 | 612786 | Kadapa | 265.91 | 0.00 | 186.36 | 83.00 | (09/2026) |
| 2 | 701107 | Vijayawada | 611.80 | 0.00 | 600.58 | 91.20 | (11/2026) |
| 3 | 701121 | Rajahmundry | 347.15 | 0.00 | 190.89 | 97.00 | (10/2026) |
| 4 | 706724 | Guwahati | 1,712.00 | 0.00 | 2,670.23 | 99.50 | (06/2026) |
| 5 | 612183 | Bihta | 1,413.00 | 0.00 | 19.44 | 4.48 | (-) |
| 6 | 612194 | Darbhanga | 911.66 | 0.00 | 453.47 | 72.60 | (11/2026) |
| 7 | 701101 | Patna | 1,216.90 | 0.00 | 1,216.11 | 99.35 | (08/2026) |
| 8 | 619054 | Keshod | 363.10 | 0.00 | 109.27 | 48.76 | (-) |
| 9 | 701126 | Dholera | 1,305.00 | 0.00 | 987.56 | 89.00 | (09/2026) |
| 10 | 611047 | Jammu | 861.37 | 0.00 | 388.13 | 61.35 | (11/2026) |

Full-report follow-ups: [August full extraction](august-full-extraction.md) and [April extraction and comparison](april-extraction-comparison.md).

## April?August monthly history

See [monthly history validation and reproduction](monthly-project-history.md) for independently inspected May, June and July sources, complete snapshots, reviewed fixtures, adjacent comparisons, and source limitations.
