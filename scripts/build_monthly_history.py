"""Build lossless monthly snapshots and unreviewed adjacent-month comparisons."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re

import pymupdf

if __package__:
    from .compare_project_reports import IDENTITY, bare, change, load_validated, month_index, number
else:
    from compare_project_reports import IDENTITY, bare, change, load_validated, month_index, number

NUMBER_FIELDS = ("original_cost_rs_crore_raw", "revised_cost_rs_crore_raw",
                 "cumulative_expenditure_rs_crore_raw", "physical_progress_pct_raw")
DATE_FIELDS = ("approval_date_raw", "start_date_raw", "original_target_doc_raw", "revised_doc_raw")
AUXILIARY_FIELDS = ("legacy_ocms_code_raw", "pmgid_raw")
BASELINE_FIELDS = ("approval_date_raw", "start_date_raw", "original_cost_rs_crore_raw", "revised_cost_rs_crore_raw")
MISSING = {"", "-", "NA", "N/A"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized_value(field, raw):
    if field in NUMBER_FIELDS:
        value = number(raw)
        if value is None:
            return ""
        if not value.is_finite():
            raise ValueError(f"Non-finite number: {raw!r}")
        return format(value.normalize(), "f")
    if field in DATE_FIELDS:
        value = month_index(raw)
        return "" if value is None else f"{value//12:04d}-{value%12+1:02d}"
    raise ValueError(f"Unknown normalized field: {field}")


def missing_fields(record):
    return {field:record[field] for field in (*NUMBER_FIELDS, *DATE_FIELDS, *AUXILIARY_FIELDS)
            if bare(record[field]).upper() in MISSING}


def snapshot_issues(record):
    issues = [dict(kind="missing_value", field=field, raw=raw)
              for field,raw in missing_fields(record).items()]
    for field in NUMBER_FIELDS:
        value = number(record[field])
        if value is not None and (value < 0 or (field == "physical_progress_pct_raw" and value > 100)):
            issues.append(dict(kind="out_of_range", field=field, raw=record[field]))
    revised, start = month_index(record["revised_doc_raw"]), month_index(record["start_date_raw"])
    if revised is not None and start is not None and revised < start:
        issues.append(dict(kind="completion_before_start", field="revised_doc_raw", raw=record["revised_doc_raw"]))
    return issues


def load_catalog(path):
    reports = json.loads(Path(path).read_text(encoding="utf-8"))["reports"]
    months = [r["report_month_iso"] for r in reports]
    if months != [f"2026-{month:02d}" for month in range(4, 9)]:
        raise ValueError("Catalog must contain exactly April-August in order")
    return reports


def load_snapshot(report):
    records, audit = load_validated(Path(report["csv"]), Path(report["audit"]),
                                    Path(report["pdf"]), report["report_month"])
    if audit["source_sha256"] != report["source_sha256"]:
        raise ValueError("Catalog source hash differs from validated PDF")
    if audit.get("extractor_sha256") != digest(Path(__file__).with_name("extract_ongoing_projects.py")):
        raise ValueError("Extraction audit belongs to different computation code; regenerate")
    if len(records) != report["expected_project_count"] or len(audit["ministry_counts"]) != report["expected_ministries"]:
        raise ValueError("Catalog and independently audited headline counts differ")
    if audit["section_count_mismatches"] or audit["table1_count_mismatches"]:
        raise ValueError("Unreconciled report counts")
    actual_pages = sorted({int(p) for r in records for p in r["pdf_pages"].split(";")})
    if [actual_pages[0], actual_pages[-1]] != report["project_pdf_page_range"]:
        raise ValueError("Unexpected project-page coverage")
    checks = {r["serial_no"]:r for r in audit["reference_checks"]}
    by_serial = {r["serial_no"]:r for r in records}
    reference_hashes = {str(Path(path).resolve()):value for path,value in audit.get("reference_sha256", {}).items()}
    for path in report["references"]:
        if reference_hashes.get(str(Path(path).resolve())) != digest(path):
            raise ValueError(f"Missing or stale reviewed reference: {path}")
        for expected in json.loads(Path(path).read_text(encoding="utf-8")):
            if (not checks.get(expected["serial_no"], {}).get("matches")
                    or any(by_serial.get(expected["serial_no"], {}).get(k) != v for k,v in expected.items())):
                raise ValueError("Reference no longer matches validated snapshot")
    if any(r.get("source_sha256") != report["source_sha256"] for r in records):
        raise ValueError("Record-level source hash mismatch")
    with pymupdf.open(report["pdf"]) as pdf:
        cover = " ".join(pdf[0].get_text().split()).upper()
        contents = " ".join(pdf[report["contents_pdf_page"]-1].get_text().split())
        if report["report_month"] not in cover or report["documented_reporting_cutoff_raw"] not in contents:
            raise ValueError("Report label or documented cutoff differs from PDF")
        table = rf"Table\s*{report['observed_table_number']}\s*:\s*All Ongoing Projects"
        if not re.search(table, contents) or not re.search(table, pdf[report["divider_pdf_page"]-1].get_text()):
            raise ValueError("Catalog ongoing-table discovery differs from PDF")
    return records, audit


def history_rows(snapshots, reports):
    rows, seen = [], set()
    for report in reports:
        for raw in snapshots[report["report_month_iso"]]:
            key = (raw["project_code"], report["report_month_iso"])
            if key in seen:
                raise ValueError(f"Duplicate history key: {key}")
            seen.add(key)
            if raw["report_month"] != report["report_month"]:
                raise ValueError("Snapshot month differs from catalog")
            row = dict(raw)
            row.update(report_month_iso=report["report_month_iso"],
                       source_sha256=report["source_sha256"],
                       documented_reporting_cutoff_date=report["documented_reporting_cutoff_date"] or "",
                       documented_reporting_cutoff_raw=report["documented_reporting_cutoff_raw"] or "",
                       cutoff_source_pdf_page=str(report["cutoff_source_pdf_page"]),
                       publication_date=report["publication_date"] or "",
                       first_available_date=report["first_available_date"] or "",
                       source_platform=report["source_platform"],
                       snapshot_issues_json=json.dumps(snapshot_issues(raw), ensure_ascii=False),
                       documented_source_notes_json=json.dumps(
                           [note for note in report["source_notes"] if raw["project_code"] in note.get("project_codes", [])],
                           ensure_ascii=False))
            for field in (*NUMBER_FIELDS, *DATE_FIELDS):
                row[field.removesuffix("_raw")+"_normalized"] = normalized_value(field, raw[field])
            rows.append(row)
    return sorted(rows, key=lambda r:(r["report_month_iso"], r["project_code"]))


def preserve_existing_history(path, records):
    """A regeneration may add snapshots/columns, but never change/drop an old row."""
    if not path.exists():
        return
    indexed = {(r["project_code"],r["report_month_iso"]):r for r in records}
    with path.open(encoding="utf-8", newline="") as stream:
        previous = list(csv.DictReader(stream))
    seen = set()
    for old in previous:
        key = (old["project_code"],old["report_month_iso"])
        if key in seen:
            raise ValueError("Existing history contains duplicate keys")
        seen.add(key)
        current = indexed.get(key)
        if current is None or any(current.get(k) != v for k,v in old.items()):
            raise ValueError(f"Refusing to overwrite an earlier snapshot: {key}; use a versioned output")


def adjacent_pair(before, after, before_report, after_report):
    # Deliberately never load/apply April-August identity-review decisions.
    a = {r["project_code"]:r for r in before}
    b = {r["project_code"]:r for r in after}
    if len(a) != len(before) or len(b) != len(after):
        raise ValueError("Duplicate project codes in adjacent input")
    common, presence = [], []
    for code in sorted(a.keys() | b.keys()):
        provenance = dict(project_code=code, before_month=before_report["report_month_iso"],
                          after_month=after_report["report_month_iso"])
        if code not in a or code not in b:
            raw = a.get(code, b.get(code))
            presence.append(dict(**provenance, presence="before_only" if code in a else "after_only",
                                 observed_snapshot_json=json.dumps(raw, ensure_ascii=False),
                                 interpretation="Published ongoing-table presence only; absence does not establish completion or start."))
            continue
        first, last = a[code], b[code]
        identity = {f:dict(before=first[f],after=last[f]) for f in IDENTITY if first[f] != last[f]}
        changes = {}
        for field in (*NUMBER_FIELDS, *DATE_FIELDS):
            compared = change(first[field],last[field],date=field in DATE_FIELDS)
            changes[field] = dict(before_raw=compared["april_raw"],after_raw=compared["august_raw"],
                                  status=compared["status"],delta=compared["delta"],
                                  raw_text_changed=compared["raw_text_changed"])
        baseline = {f:changes[f] for f in BASELINE_FIELDS
                    if changes[f]["status"] not in {"unchanged","both_missing"}}
        auxiliary = {}
        for field in AUXILIARY_FIELDS:
            x, y = bare(first[field]), bare(last[field])
            missing_x, missing_y = x.upper() in MISSING, y.upper() in MISSING
            status = ("both_missing" if missing_x and missing_y else "became_available" if missing_x
                      else "became_missing" if missing_y else "unchanged" if x == y else "conflicting_identifiers")
            auxiliary[field] = dict(before_raw=first[field],after_raw=last[field],status=status)
        flags = (["unreviewed_identity_change"] if identity else [])
        if any(v["status"] == "conflicting_identifiers" for v in auxiliary.values()):
            flags.append("conflicting_auxiliary_identifiers")
        flags += ["baseline_"+f for f in baseline]
        first_missing, last_missing = missing_fields(first), missing_fields(last)
        critical = set(NUMBER_FIELDS) | {"approval_date_raw", "start_date_raw", "original_target_doc_raw"}
        if critical & (first_missing.keys() | last_missing.keys()):
            flags.append("missing_metric_or_baseline")
        for label, field in [("progress","physical_progress_pct_raw"),("expenditure","cumulative_expenditure_rs_crore_raw")]:
            if changes[field]["status"] == "decreased":
                flags.append("reported_"+label+"_decrease_requires_review")
        for prefix, raw in [("before",first),("after",last)]:
            for issue in snapshot_issues(raw):
                if issue["kind"] != "missing_value":
                    flags.append(prefix+"_"+issue["kind"]+"_"+issue["field"])
        notes = [dict(report_month=r["report_month_iso"], **n)
                 for r in (before_report,after_report) for n in r["source_notes"]
                 if code in n.get("project_codes",[])]
        if any(n["kind"] == "documented_project_split" for n in notes):
            flags.append("documented_split_scope_requires_review")
        if any("inconsistent" in n["kind"] or "exclusion" in n["kind"] for n in notes):
            flags.append("documented_publication_inconsistency")
        flags = list(dict.fromkeys(flags))
        common.append(dict(**provenance, identity_review_status="not_reviewed_for_this_pair",
                           identity_differences_json=json.dumps(identity,ensure_ascii=False),
                           baseline_changes_json=json.dumps(baseline,ensure_ascii=False),
                           auxiliary_identifier_changes_json=json.dumps(auxiliary,ensure_ascii=False),
                           quality_flags_json=json.dumps(flags+["before_missing_"+f for f in first_missing]
                                                         +["after_missing_"+f for f in last_missing]),
                           before_missing_values_json=json.dumps(first_missing,ensure_ascii=False),
                           after_missing_values_json=json.dumps(last_missing,ensure_ascii=False),
                           changes_json=json.dumps(changes,ensure_ascii=False),
                           trend_eligible=str(not flags),
                           completion_trend_eligible=str(not flags and not (set(DATE_FIELDS) & (first_missing.keys() | last_missing.keys()))),
                           trend_review_reasons_json=json.dumps(flags),
                           source_notes_json=json.dumps(notes,ensure_ascii=False),
                           before_snapshot_json=json.dumps(first,ensure_ascii=False),
                           after_snapshot_json=json.dumps(last,ensure_ascii=False),
                           progress_before_raw=first["physical_progress_pct_raw"],
                           progress_after_raw=last["physical_progress_pct_raw"],
                           progress_status=changes["physical_progress_pct_raw"]["status"],
                           progress_delta_pp=changes["physical_progress_pct_raw"]["delta"] or "",
                           expenditure_before_raw=first["cumulative_expenditure_rs_crore_raw"],
                           expenditure_after_raw=last["cumulative_expenditure_rs_crore_raw"],
                           expenditure_status=changes["cumulative_expenditure_rs_crore_raw"]["status"],
                           expenditure_delta_rs_crore=changes["cumulative_expenditure_rs_crore_raw"]["delta"] or ""))
    summary = dict(before_month=before_report["report_month_iso"],after_month=after_report["report_month_iso"],
                   before_count=len(a),after_count=len(b),shared=len(common),
                   before_only=len(a.keys()-b.keys()),after_only=len(b.keys()-a.keys()),
                   unreviewed_identity_changes=sum(bool(json.loads(r["identity_differences_json"])) for r in common),
                   changed_baselines=sum(bool(json.loads(r["baseline_changes_json"])) for r in common),
                   auxiliary_identity_conflicts=sum("conflicting_auxiliary_identifiers" in json.loads(r["trend_review_reasons_json"]) for r in common),
                   missing_field_records=sum(bool(json.loads(r["before_missing_values_json"]) or json.loads(r["after_missing_values_json"])) for r in common),
                   progress_changes=dict(Counter(r["progress_status"] for r in common)),
                   expenditure_changes=dict(Counter(r["expenditure_status"] for r in common)),
                   completion_date_changes={f:dict(Counter(json.loads(r["changes_json"])[f]["status"] for r in common))
                                            for f in ("original_target_doc_raw","revised_doc_raw")},
                   trend_eligible=sum(r["trend_eligible"]=="True" for r in common),
                   trend_excluded=sum(r["trend_eligible"]=="False" for r in common),
                   exclusion_reasons=dict(Counter(reason for r in common for reason in json.loads(r["trend_review_reasons_json"]))),
                   headline_roll_forward_expected=(len(a)+after_report["headline_newly_added_during_month"]-after_report["headline_commissioned_during_month"])
                       if "headline_newly_added_during_month" in after_report else None,
                   headline_roll_forward_difference=(len(b)-(len(a)+after_report["headline_newly_added_during_month"]-after_report["headline_commissioned_during_month"]))
                       if "headline_newly_added_during_month" in after_report else None,
                   identity_review_policy="No pair-specific decisions exist for this pair; April-August decisions are not reused.",
                   absence_interpretation="Absence does not establish completion.")
    assert summary["shared"]+summary["before_only"]==len(a)
    assert summary["shared"]+summary["after_only"]==len(b)
    return common, presence, summary


def write_csv(path, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary = path.with_suffix(path.suffix+".tmp")
    fields = list(rows[0]) if rows else ["project_code"]
    with temporary.open("w",encoding="utf-8",newline="") as stream:
        writer = csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with temporary.open(encoding="utf-8",newline="") as stream:
        restored = list(csv.DictReader(stream))
    expected = [{k:str(v) if v is not None else "" for k,v in r.items()} for r in rows]
    if restored != expected:
        raise ValueError("History/comparison CSV string round-trip failed")
    temporary.replace(path)
    return digest(path)


def run(catalog_path, output_dir, validation_path):
    reports = load_catalog(catalog_path)
    snapshots, audits = {}, {}
    for report in reports:
        records, audit = load_snapshot(report)
        snapshots[report["report_month_iso"]],audits[report["report_month_iso"]] = records,audit
    rows = history_rows(snapshots,reports)
    history_path = output_dir/"april_august_2026_history.csv"
    preserve_existing_history(history_path,rows)
    hashes = {"history":write_csv(history_path,rows)}
    summaries = []
    for before,after in zip(reports,reports[1:]):
        common,presence,summary = adjacent_pair(snapshots[before["report_month_iso"]],snapshots[after["report_month_iso"]],before,after)
        label = before["report_month_iso"]+"_"+after["report_month_iso"]
        for suffix,selected in [
            ("changes",common),("presence",presence),
            ("questionable",[r for r in common if r["trend_eligible"]=="False"]),
            ("progress_decreases",[r for r in common if r["progress_status"]=="decreased"]),
            ("expenditure_decreases",[r for r in common if r["expenditure_status"]=="decreased"])]:
            name = label+"_"+suffix
            hashes[name] = write_csv(output_dir/(name+".csv"),selected)
        summaries.append(summary)
    summary = dict(status="validated_history",csv_round_trip="PASS",coverage_pass=True,
                   total_snapshot_rows=len(rows),unique_project_codes=len({r["project_code"] for r in rows}),
                   per_month_counts=dict(Counter(r["report_month_iso"] for r in rows)),
                   missing_months_filled=False,earlier_snapshot_overwrite=False,
                   all_five_months_present_codes=len(set.intersection(*[{r["project_code"] for r in records} for records in snapshots.values()])),
                   catalog_sha256=digest(catalog_path),history_builder_sha256=digest(__file__),
                   extractor_sha256=digest(Path(__file__).with_name("extract_ongoing_projects.py")),
                   comparison_helpers_sha256=digest(Path(__file__).with_name("compare_project_reports.py")),
                   input_hashes={r["report_month_iso"]:dict(pdf=digest(r["pdf"]),csv=digest(r["csv"]),audit=digest(r["audit"]),
                                                          references={p:digest(p) for p in r["references"]}) for r in reports},
                   output_hashes=hashes,pairs=summaries,
                   month_missing_fields={r["report_month_iso"]:dict(Counter(f for row in snapshots[r["report_month_iso"]] for f in missing_fields(row))) for r in reports},
                   month_snapshot_issue_counts={r["report_month_iso"]:dict(Counter(i["kind"] for row in snapshots[r["report_month_iso"]] for i in snapshot_issues(row))) for r in reports},
                   availability_policy="Report labels and documented reporting cutoffs are separate; unknown publication/first availability dates stay unknown. Not a time-available training dataset.",
                   trend_policy="All changes are reported changes without inferred causes. Unreviewed identity changes, changed baselines, critical missing values, decreases and source issues exclude screened trends. Auxiliary/revised-date missingness is separately logged; screened aggregates exclude decreases by design and are biased.",
                   source_observations={r["report_month_iso"]:r.get("source_observations",[]) for r in reports},
                   issues=[])
    validation_path.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2,ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog",type=Path,default=Path("config/monthly_reports.json"))
    parser.add_argument("--output-dir",type=Path,default=Path("data/processed/monthly_history"))
    parser.add_argument("--validation",type=Path,default=Path("data/validation/monthly_history.json"))
    args = parser.parse_args()
    args.validation.parent.mkdir(parents=True,exist_ok=True)
    args.validation.write_text(json.dumps(dict(status="running",coverage_pass=False,reason="History run has not completed"))+"\n",encoding="utf-8")
    try:
        run(args.catalog,args.output_dir,args.validation)
    except Exception as error:
        args.validation.write_text(json.dumps(dict(status="failed",coverage_pass=False,reason=str(error)))+"\n",encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
