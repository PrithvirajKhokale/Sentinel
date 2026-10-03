"""Extract a limited, traceable sample from PAIMANA Table 6; no numeric/date coercion."""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

import pdfplumber
import pymupdf


def normalize(value):
    return " ".join((value or "").split())


def pair(value, label):
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if len(lines) != 2:
        raise ValueError(f"{label}: expected two values, got {value!r}")
    return lines


def parse_row(cells):
    if len(cells) != 8 or any(c is None for c in cells):
        raise ValueError(f"Incomplete project row: {cells!r}")
    identity = cells[1].splitlines()
    if len(identity) < 4:
        raise ValueError("Incomplete project identity")
    code = re.fullmatch(r"\(([^()]*)\)", identity[-2].strip())
    ids = re.fullmatch(r"(\([^()]*\))\s+(\([^()]*\))", identity[-1].strip())
    agency = identity[-3].strip()
    if not code or not ids or not (agency.startswith("(") and agency.endswith(")")):
        raise ValueError(f"Unsupported identity layout: {cells[1]!r}")
    approval, start = pair(cells[3], "approval/start")
    original_doc, revised_doc = pair(cells[4], "completion")
    original_cost, revised_cost = pair(cells[5], "cost")
    return dict(
        serial_no=cells[0], project_name=normalize(" ".join(identity[:-3])),
        agency=agency, project_code=code.group(1),
        legacy_ocms_code_raw=ids.group(1), pmgid_raw=ids.group(2),
        state=normalize(cells[2]), approval_date_raw=approval,
        start_date_raw=start, original_target_doc_raw=original_doc,
        revised_doc_raw=revised_doc, original_cost_rs_crore_raw=original_cost,
        revised_cost_rs_crore_raw=revised_cost,
        cumulative_expenditure_rs_crore_raw=cells[6].strip(),
        physical_progress_pct_raw=cells[7].strip(),
    )


def extract(source, limit):
    records, evidence = [], []
    with pdfplumber.open(source) as pdf, pymupdf.open(source) as independent:
        divider = next((i for i, p in enumerate(independent)
                        if re.search(r"Table\s*6\s*:\s*All Ongoing Projects", p.get_text())
                        and "CONTENTS" not in p.get_text()), None)
        if divider is None:
            raise ValueError("Table 6 divider not found")
        for i in range(divider + 1, len(pdf.pages)):
            page = pdf.pages[i]
            text = independent[i].get_text()
            if "All Ongoing Projects" not in text:
                break
            month = re.search(r"\b(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+(20\d{2})\b", text)
            printed = re.search(r"\bPage\s+(\d+)\b", text)
            if not month or not printed:
                raise ValueError(f"Missing provenance on PDF page {i+1}")
            for table in page.find_tables():
                cells_by_row = table.extract()
                if not cells_by_row or cells_by_row[0][0] != "Sl.No":
                    continue
                for row_index, cells in enumerate(cells_by_row):
                    if not cells[0] or not cells[0].isdigit():
                        continue
                    expected = len(records) + 1
                    if int(cells[0]) != expected:
                        raise ValueError(f"Expected serial {expected}, found {cells[0]}")
                    # Independently read each physical cell with a second PDF engine.
                    checked = []
                    for column, bbox in enumerate(table.rows[row_index].cells):
                        if bbox is None:
                            raise ValueError("Missing physical cell")
                        other = independent[i].get_textbox(pymupdf.Rect(bbox))
                        if normalize(other) != normalize(cells[column]):
                            raise ValueError(f"PDF page {i+1}, serial {expected}, column {column}: engine disagreement")
                        checked.append({"column": column + 1, "bbox": list(bbox),
                                        "pdfplumber_text": cells[column], "pymupdf_text": other,
                                        "matches": True})
                    record = parse_row(cells)
                    record.update(source_filename=source.name, report_month=month.group(0),
                                  pdf_page=str(i+1), printed_page=printed.group(1))
                    records.append(record)
                    evidence.append({"serial_no": record["serial_no"], "project_code": record["project_code"],
                                     "pdf_page": i+1, "cells_checked": checked})
                    if len(records) == limit:
                        return records, evidence
    raise ValueError(f"Only {len(records)} records found; requested {limit}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--reference", type=Path, help="Optional visually reviewed reference JSON")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    records, evidence = extract(args.pdf, args.limit)
    reference_checks = []
    if args.reference:
        reference = json.loads(args.reference.read_text(encoding="utf-8"))
        if len(reference) != len(records):
            raise ValueError("Reference record count differs")
        for record, expected in zip(records, reference):
            mismatches = {key: {"expected": value, "actual": record.get(key)}
                          for key, value in expected.items() if record.get(key) != value}
            if mismatches:
                raise ValueError(f"Reference mismatch: {mismatches}")
            reference_checks.append({"serial_no": record["serial_no"], "fields_checked": len(expected), "matches": True})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    with args.output.open(encoding="utf-8", newline="") as stream:
        if list(csv.DictReader(stream)) != records:
            raise ValueError("CSV round-trip failed")
    args.validation.parent.mkdir(parents=True, exist_ok=True)
    result = dict(source_filename=args.pdf.name,
                  source_sha256=hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
                  records=len(records), physical_cells_checked=len(records)*8,
                  independent_pdf_cell_checks="PASS", csv_round_trip="PASS",
                  reference_checks=reference_checks, evidence=evidence)
    args.validation.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(f"PASS: {len(records)} records, {len(records)*8} physical cells, CSV round-trip; {len(reference_checks)} reference records")
    print(f"CSV: {args.output}\nValidation: {args.validation}")
    for record in records:
        print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
