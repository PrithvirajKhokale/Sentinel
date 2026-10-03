"""Extract the discovered PAIMANA All Ongoing Projects table with raw values and audits."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re

import pdfplumber
import pymupdf

MONTH = r"(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+(20\d{2})"
MARKERS = {"-", "(-)", "NA", "(NA)", "N/A", "(N/A)"}


def normalize(value):
    return " ".join((value or "").split())


def pair(value, label):
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if len(lines) != 2:
        raise ValueError(f"{label}: expected two values, got {value!r}")
    return lines


def split_agency(text):
    """Locate the final balanced parenthesized agency, including wrapped/nested text."""
    text = text.rstrip()
    if not text.endswith(")"):
        raise ValueError("Agency must end in a closing parenthesis")
    depth = 0
    for index in range(len(text) - 1, -1, -1):
        if text[index] == ")":
            depth += 1
        elif text[index] == "(":
            depth -= 1
            if depth == 0:
                if index and text[index - 1] != "\n":
                    raise ValueError("Agency boundary is not a separate source line")
                name = text[:index].strip()
                if not name:
                    raise ValueError("Missing project name")
                return normalize(name), normalize(text[index:])
    raise ValueError("Unbalanced agency parentheses")


def parse_row(cells):
    if len(cells) != 8 or any(c is None for c in cells):
        raise ValueError(f"Incomplete project row: {cells!r}")
    identity = cells[1].strip()
    # Read the identifier block from the end; retain marker parentheses.
    match = re.search(r"\n\(([^()\n]+)\)\s*\n(\([^()]*\))\s+(\([^()]*\))\s*$", identity)
    if not match:
        raise ValueError("Missing or ambiguous project/legacy/PMG identifier block")
    name, agency = split_agency(identity[:match.start()])
    approval, start = pair(cells[3], "approval/start")
    original_doc, revised_doc = pair(cells[4], "completion")
    original_cost, revised_cost = pair(cells[5], "cost")
    for label, value in [("approval", approval), ("start", start),
                         ("original completion", original_doc), ("revised completion", revised_doc)]:
        bare = value[1:-1] if value.startswith("(") and value.endswith(")") else value
        if bare not in {"-", "NA", "N/A"} and not re.fullmatch(r"(0[1-9]|1[0-2])/\d{4}", bare):
            raise ValueError(f"Ambiguous {label} date: {value!r}")
    for label, value in [("original cost", original_cost), ("revised cost", revised_cost),
                         ("expenditure", cells[6].strip()), ("progress", cells[7].strip())]:
        bare = value[1:-1] if label == "revised cost" and value.startswith("(") and value.endswith(")") else value
        if value not in MARKERS and not re.fullmatch(r"-?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", bare):
            raise ValueError(f"Ambiguous {label}: {value!r}")
    return dict(
        serial_no=cells[0], project_name=name, agency=agency, project_code=match.group(1),
        legacy_ocms_code_raw=match.group(2), pmgid_raw=match.group(3),
        state=normalize(cells[2]), approval_date_raw=approval, start_date_raw=start,
        original_target_doc_raw=original_doc, revised_doc_raw=revised_doc,
        original_cost_rs_crore_raw=original_cost, revised_cost_rs_crore_raw=revised_cost,
        cumulative_expenditure_rs_crore_raw=cells[6].strip(),
        physical_progress_pct_raw=cells[7].strip(),
    )


def ministry_heading(text):
    return bool(re.match(r"^(Ministry of|Department of|Department for)\b", text))


def join_fragments(first, following):
    if len(first) != 8 or len(following) != 8:
        raise ValueError("Continuation does not have eight columns")
    if following[0] and following[0] != first[0]:
        raise ValueError("Continuation has a different serial")
    return [first[0]] + ["\n".join(v for v in (first[i], following[i]) if v) for i in range(1, 8)]


def assemble(rows, limit=None):
    """Carry heading context and defer finalization until the next numbered row.

    A blank-serial non-heading fragment is joined only on the immediately following
    page in the same section. Uncertain fragments are logged rather than guessed.
    """
    records, evidence, issues, totals, headings = [], [], [], [], []
    ministry = sector = ""
    pending = None
    section_serials = []

    def issue(row, reason, kind="rejected"):
        issues.append(dict(kind=kind, pdf_page=row["page"], serial_no=(row["cells"][0] or ""),
                           reason=reason, raw_cells=row["cells"]))

    def finish():
        nonlocal pending
        if pending is None:
            return
        try:
            parsed = parse_row(pending["cells"])
            if not pending["ministry"] or not pending["sector"]:
                raise ValueError("Missing ministry/sector context")
            pages = [part["page"] for part in pending["parts"]]
            printed = [part["printed_page"] for part in pending["parts"]]
            parsed.update(source_filename=pending["parts"][0]["source_filename"],
                          report_month=pending["parts"][0]["report_month"],
                          pdf_page=str(pages[0]), printed_page=str(printed[0]),
                          ministry=pending["ministry"], sector=pending["sector"],
                          pdf_pages=";".join(map(str, dict.fromkeys(pages))),
                          printed_pages=";".join(map(str, dict.fromkeys(printed))),
                          source_cells_json=json.dumps(pending["cells"], ensure_ascii=False))
            records.append(parsed)
            evidence.append(dict(serial_no=parsed["serial_no"], project_code=parsed["project_code"],
                                 parts=pending["parts"]))
        except ValueError as error:
            issue(dict(pending["parts"][0], cells=pending["cells"]), str(error))
            issues[-1]["pdf_pages"] = [part["page"] for part in pending["parts"]]
            issues[-1]["parts"] = pending["parts"]
        pending = None

    for row in rows:
        cells = row["cells"]
        if len(cells) != 8:
            finish()
            issue(row, "Physical row has an unexpected column count")
            continue
        serial = (cells[0] or "").strip()
        label = normalize(cells[1])
        if serial.isdigit():
            if pending and serial == pending["cells"][0] and row["page"] == pending["parts"][-1]["page"] + 1:
                try:
                    parse_row(pending["cells"])
                except ValueError:
                    pending["cells"] = join_fragments(pending["cells"], cells)
                    pending["parts"].append(row)
                    continue
            finish()
            if limit is not None and len(records) >= limit:
                break
            section_serials.append(serial)
            pending = dict(cells=[c or "" for c in cells], parts=[row],
                           ministry=ministry, sector=sector)
        elif re.fullmatch(r"Total\s*\(\d+\)", label):
            finish()
            expected = int(re.search(r"\d+", label).group())
            totals.append(dict(pdf_page=row["page"], ministry=ministry, sector=sector,
                               expected=expected, observed=len(section_serials),
                               serials=section_serials[:], matches=expected == len(section_serials),
                               raw_cells=cells))
            section_serials = []
        elif not serial and label and all(c is None for c in cells[2:]):
            finish()
            if ministry_heading(label):
                if section_serials:
                    issue(row, "New ministry before preceding section total", "ambiguous")
                ministry, sector = label, ""
            else:
                if section_serials:
                    issue(row, "New sector before preceding section total", "ambiguous")
                sector = label
            headings.append(dict(pdf_page=row["page"], ministry=ministry, sector=sector, label=label))
        elif not serial and any(c for c in cells[1:]):
            # A continuation must follow directly at a page boundary. A complete
            # prior row is never enlarged using an unnumbered row.
            previous_complete = False
            if pending:
                try:
                    parse_row(pending["cells"])
                    previous_complete = True
                except ValueError:
                    pass
            if pending and row["page"] == pending["parts"][-1]["page"] + 1 and not previous_complete:
                pending["cells"] = join_fragments(pending["cells"], cells)
                pending["parts"].append(row)
            else:
                issue(row, "Unnumbered non-heading row cannot be safely attached", "ambiguous")
        elif serial or label:
            finish()
            issue(row, "Unrecognized physical row", "ambiguous")
    finish()
    if limit is not None and len(records) > limit:
        records, evidence = records[:limit], evidence[:limit]
    return records, evidence, issues, totals, headings


def read_pdf(source, limit=None):
    rows, disagreements, page_issues = [], [], []
    with pdfplumber.open(source) as pdf, pymupdf.open(source) as independent:
        divider = next((i for i, p in enumerate(independent)
                        if re.search(r"Table\s*\d+\s*:\s*All Ongoing Projects", p.get_text())
                        and "CONTENTS" not in p.get_text()), None)
        if divider is None:
            raise ValueError("All Ongoing Projects table divider not found")
        discovered_table = re.search(r"Table\s*(\d+)\s*:\s*All Ongoing Projects", independent[divider].get_text()).group(1)
        report_counts = []
        for i in range(divider):
            independent_page = independent[i]
            text = independent_page.get_text()
            headline = re.search(r"(\d[\d,]*)\s*\|\s*(\d+)\s*\nOngoing Projects\s*\|", text)
            if headline:
                report_counts.append(dict(table_number=discovered_table, table_divider_pdf_page=divider+1, pdf_page=i+1, ongoing_projects=int(headline.group(1).replace(",", "")),
                                          ministries=int(headline.group(2))))
        table1 = []
        allocated = ""
        for i in range(divider):
            if "Ministry-wise Ongoing Projects" not in independent[i].get_text():
                continue
            for table in pdf.pages[i].extract_tables():
                if not table or table[0][:2] != ["Sl.No", "Allocated To"]:
                    continue
                for values in table[1:]:
                    if values[1]:
                        allocated = normalize(values[1])
                    if values[0] == "Total":
                        table1.append(dict(kind="grand_total", pdf_page=i+1, count=int(values[3])))
                    elif normalize(values[2]) == "Total":
                        table1.append(dict(kind="ministry", pdf_page=i+1, ministry=allocated, count=int(values[3])))
                    else:
                        table1.append(dict(kind="sector", pdf_page=i+1, ministry=allocated,
                                           sector=normalize(values[2]), count=int(values[3])))
        for i in range(divider + 1, len(pdf.pages)):
            page = pdf.pages[i]
            independent_page = independent[i]
            text = independent_page.get_text()
            if "All Ongoing Projects" not in text:
                break
            month = re.search(r"\b" + MONTH + r"\b", text)
            printed = re.search(r"\bPage\s+(\d+)\b", text)
            if not month or not printed:
                page_issues.append(dict(kind="rejected", pdf_page=i+1, reason="Missing page provenance"))
                continue
            words = independent_page.get_text('words')
            found = False
            for table in page.find_tables():
                values = table.extract()
                if not values or values[0][0] != "Sl.No":
                    continue
                required_headers = ["Sl.No", "Project Name", "State", "Date of Approval",
                                    "Orignal/Target DoC", "Orignal Cost", "Cumulative", "Physical Progress"]
                if len(values[0]) != 8 or any(label not in normalize(value)
                                                           for label, value in zip(required_headers, values[0])):
                    page_issues.append(dict(kind="rejected", pdf_page=i+1,
                                            reason="Unsupported ongoing-project schema", raw_header=values[0]))
                    continue
                found = True
                for j, cells in enumerate(values[1:], 1):
                    checked = []
                    for column, bbox in enumerate(table.rows[j].cells):
                        if bbox is None:
                            continue
                        other = " ".join(w[4] for w in words
                                         if bbox[0] <= (w[0]+w[2])/2 <= bbox[2]
                                         and bbox[1] <= (w[1]+w[3])/2 <= bbox[3])
                        matches = normalize(other) == normalize(cells[column])
                        checked.append(dict(column=column+1, bbox=list(bbox),
                                            pdfplumber_text=cells[column], pymupdf_text=other, matches=matches))
                        if not matches:
                            disagreements.append(dict(kind="ambiguous", pdf_page=i+1, serial_no=cells[0] or "",
                                                      column=column+1, reason="PDF engines disagree",
                                                      grid_text=cells[column], independent_text=other))
                    rows.append(dict(page=i+1, printed_page=int(printed.group(1)),
                                     report_month=month.group(0), source_filename=source.name,
                                     cells=cells, cells_checked=checked))
            if not found:
                page_issues.append(dict(kind="rejected", pdf_page=i+1, reason="No recognized Table 6 grid"))
            page.close()
            if limit is not None and sum((r["cells"][0] or "").isdigit() for r in rows) > limit:
                break
            if (i - divider) % 10 == 0:
                print(f"Read through PDF page {i+1}", flush=True)
    return rows, disagreements + page_issues, report_counts, table1


def audit(records, rows, totals, report_counts, issues, full, table1=None, requested_limit=None):
    serials = [int(r["serial_no"]) for r in records]
    physical = [int(r["cells"][0]) for r in rows if (r["cells"][0] or "").isdigit()]
    expected = report_counts[0]["ongoing_projects"] if report_counts else max(physical, default=0)
    count = Counter(serials)
    codes = defaultdict(list)
    for record in records:
        codes[record["project_code"]].append(record["serial_no"])
    blank, markers = defaultdict(list), defaultdict(list)
    for record in records:
        for key, value in record.items():
            if not value:
                blank[key].append(record["serial_no"])
            elif value in MARKERS:
                markers[key].append(record["serial_no"])
    ministry_counts = dict(Counter(r["ministry"] for r in records))
    result = dict(scope="full" if full else "sample", requested_limit=requested_limit, report_counts=report_counts,
                  expected_project_count=expected, accepted_records=len(records),
                  physical_numbered_rows=len(physical), serial_min=min(serials, default=None),
                  serial_max=max(serials, default=None),
                  missing_serials=sorted(set(range(1, expected+1)) - set(serials)) if full else [],
                  duplicate_serials={str(k):v for k,v in count.items() if v > 1},
                  serial_order_matches=serials == sorted(serials),
                  duplicate_project_codes={k:v for k,v in codes.items() if len(v)>1},
                  blank_fields=dict(blank), explicit_missing_markers=dict(markers),
                  ministry_counts=ministry_counts, unique_sectors=sorted({r["sector"] for r in records}),
                  section_count_checks=totals, section_count_mismatches=[t for t in totals if not t["matches"]],
                  section_total_sum=sum(t["expected"] for t in totals),
                  multi_page_records=[r["serial_no"] for r in records if ";" in r["pdf_pages"]],
                  issues=issues)
    table1_checks = []
    for expected_group in table1 or []:
        if expected_group["kind"] == "grand_total":
            observed = len(records)
        elif expected_group["kind"] == "ministry":
            observed = ministry_counts.get(expected_group["ministry"], 0)
        else:
            observed = sum(r["ministry"] == expected_group["ministry"] and r["sector"] == expected_group["sector"]
                           for r in records)
        table1_checks.append(dict(**expected_group, observed=observed, matches=observed == expected_group["count"]))
    result["table1_count_checks"] = table1_checks if full else []
    result["table1_count_mismatches"] = [c for c in table1_checks if not c["matches"]] if full else []
    result["coverage_pass"] = (not full or len(records) == expected) and not (
        result["missing_serials"] or result["duplicate_serials"] or result["duplicate_project_codes"]
        or result["blank_fields"] or result["section_count_mismatches"] or issues
        or not result["serial_order_matches"])
    if not full and requested_limit is not None:
        result["coverage_pass"] &= len(records) == requested_limit
    if full:
        result["coverage_pass"] &= bool(report_counts) and len(ministry_counts) == report_counts[0]["ministries"]
        result["coverage_pass"] &= result["section_total_sum"] == expected
        result["coverage_pass"] &= bool(table1_checks) and not result["table1_count_mismatches"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--limit", type=int, default=None)
    group.add_argument("--all", action="store_true", help="Read all Table 6 records")
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--reference", type=Path, action="append", default=[],
                        help="Visually reviewed subset, matched by serial; may be repeated")
    args = parser.parse_args()
    limit = None if args.all else (args.limit if args.limit is not None else 10)
    if limit is not None and limit < 1:
        parser.error("--limit must be positive")
    args.validation.parent.mkdir(parents=True, exist_ok=True)
    issue_path = args.validation.with_name(args.validation.stem + "_issues.jsonl")
    # Invalidate any old success audit before reading inputs or replacing output.
    incomplete = dict(status="running", coverage_pass=False,
                      scope="full" if args.all else "sample",
                      output_path=str(args.output.resolve()), reason="Run has not completed")
    args.validation.write_text(json.dumps(incomplete, indent=2)+"\n", encoding="utf-8")
    issue_path.write_text(json.dumps(dict(kind="incomplete", reason="Run has not completed"))+"\n",
                          encoding="utf-8")
    rows, issues, report_counts, table1 = read_pdf(args.pdf, limit)
    records, evidence, row_issues, totals, headings = assemble(rows, limit)
    # Engine disagreements anywhere in a full run are unresolved issues. Sample
    # validation includes only its source pages/serials.
    if not args.all:
        selected = {r["serial_no"] for r in records}
        issues = [i for i in issues if not i.get("serial_no") or i.get("serial_no") in selected]
    issues += row_issues
    reference_checks = []
    by_serial = {r["serial_no"]:r for r in records}
    for reference_path in args.reference:
        for expected in json.loads(reference_path.read_text(encoding="utf-8")):
            actual = by_serial.get(expected["serial_no"], {})
            mismatches = {key:dict(expected=value, actual=actual.get(key))
                          for key,value in expected.items() if actual.get(key) != value}
            if mismatches:
                issues.append(dict(kind="ambiguous", pdf_page=expected.get("pdf_page"),
                                   serial_no=expected["serial_no"], reason="Reference mismatch",
                                   mismatches=mismatches))
            reference_checks.append(dict(serial_no=expected["serial_no"],
                                         fields_checked=len(expected), matches=not mismatches))
    result = audit(records, rows, totals, report_counts, issues, args.all, table1, requested_limit=limit)
    result.update(source_filename=args.pdf.name,
                  source_sha256=hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
                  reference_checks=reference_checks, headings=headings, evidence=evidence)
    args.validation.parent.mkdir(parents=True, exist_ok=True)
    # Always write rejection/ambiguity evidence, even when extraction is incomplete.
    issue_path = args.validation.with_name(args.validation.stem + "_issues.jsonl")
    issue_path.write_text("".join(json.dumps(i, ensure_ascii=False)+"\n" for i in issues), encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        result["csv_round_trip"] = "NO RECORDS"
    else:
        with args.output.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
        with args.output.open(encoding="utf-8", newline="") as stream:
            result["csv_round_trip"] = "PASS" if list(csv.DictReader(stream)) == records else "FAIL"
    valid = result["coverage_pass"] and result["csv_round_trip"] == "PASS"
    result.update(status=("validated_full" if args.all else "validated_sample") if valid else "failed",
                  output_path=str(args.output.resolve()),
                  csv_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest() if records else None,
                  issue_log_sha256=hashlib.sha256(issue_path.read_bytes()).hexdigest())
    args.validation.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    summary = {key:value for key,value in result.items()
               if key not in {"evidence", "headings", "section_count_checks", "explicit_missing_markers", "issues", "table1_count_checks"}}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if not result["coverage_pass"] or result["csv_round_trip"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
