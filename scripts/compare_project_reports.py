"""Compare validated April/August ongoing-project snapshots by project code."""
import argparse
from collections import Counter
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from difflib import SequenceMatcher

MISSING = {"", "-", "NA", "N/A"}
IDENTITY = ("project_name", "agency", "state", "ministry", "sector")
DATE_FIELDS = ("original_target_doc_raw", "revised_doc_raw")


def bare(value):
    value = value.strip()
    return value[1:-1].strip() if value.startswith("(") and value.endswith(")") else value


def number(value):
    value = bare(value)
    if value.upper() in MISSING:
        return None
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation as error:
        raise ValueError(f"Invalid numeric value: {value!r}") from error


def month_index(value):
    value = bare(value)
    if value.upper() in MISSING:
        return None
    match = re.fullmatch(r"(0[1-9]|1[0-2])/(\d{4})", value)
    if not match:
        raise ValueError(f"Invalid month/year value: {value!r}")
    return int(match.group(2))*12 + int(match.group(1))-1


def change(before, after, date=False):
    a, b = (month_index(before), month_index(after)) if date else (number(before), number(after))
    if a is None and b is None:
        status, delta = "both_missing", None
    elif a is None:
        status, delta = "became_available", None
    elif b is None:
        status, delta = "became_missing", None
    else:
        delta = b-a
        status = "unchanged" if delta == 0 else (
            ("postponed" if delta > 0 else "brought_forward") if date
            else ("increased" if delta > 0 else "decreased"))
    return dict(april_raw=before, august_raw=after, status=status,
                delta=str(delta) if delta is not None else None, raw_text_changed=before != after)


def index_records(records):
    indexed = {}
    for record in records:
        code = record["project_code"]
        if not code or code in indexed:
            raise ValueError(f"Missing or duplicate project code: {code!r}")
        indexed[code] = record
    return indexed


def load_validated(csv_path, audit_path, pdf_path, month):
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    issue_path = audit_path.with_name(audit_path.stem+"_issues.jsonl")
    if not (audit.get("status") == "validated_full" and audit.get("scope") == "full"
            and audit.get("coverage_pass") is True and audit.get("csv_round_trip") == "PASS"
            and audit.get("issues") == [] and issue_path.read_bytes() == b""):
        raise ValueError(f"Dataset has not passed full validation: {audit_path}")
    for path, key in [(csv_path, "csv_sha256"), (pdf_path, "source_sha256"), (issue_path, "issue_log_sha256")]:
        if hashlib.sha256(path.read_bytes()).hexdigest() != audit.get(key):
            raise ValueError(f"Stale or modified input: {path}")
    with csv_path.open(encoding="utf-8", newline="") as stream:
        records = list(csv.DictReader(stream))
    if len(records) != audit["accepted_records"] or any(r["report_month"] != month for r in records):
        raise ValueError(f"Count or report month differs from intended snapshot: {csv_path}")
    index_records(records)
    return records, audit


def load_identity_review(path, april_audit, august_audit):
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = dict(april_pdf=april_audit["source_sha256"], august_pdf=august_audit["source_sha256"])
    if payload.get("input_pdf_sha256") != expected:
        raise ValueError("Identity review belongs to different source PDFs")
    reviews = index_records(payload["reviews"])
    if any(r["classification"] not in {"harmless_text_change", "material_reported_change", "unresolved"}
           or not r.get("reason") for r in reviews.values()):
        raise ValueError("Invalid identity review decision")
    return reviews


def assess_match(a, b, differences, conflict, review):
    if review:
        for month, actual in [("april", a), ("august", b)]:
            if any(actual.get(k) != v for k, v in review["reviewed_values"][month].items()):
                raise ValueError(f"Stale identity review for {a['project_code']}")
        category, reason = review["classification"], review["reason"]
    else:
        category = "unreviewed" if differences or conflict else "unchanged_identity"
        reason = "No manual identity decision; changed identity text requires review." if category == "unreviewed" else "Identity fields match."
    flags = []
    if category in {"material_reported_change", "unresolved", "unreviewed"}:
        flags.append("identity_" + category)
    if change(a["start_date_raw"], b["start_date_raw"], date=True)["status"] not in {"unchanged", "both_missing"}:
        flags.append("reported_start_date_changed")
    if change(a["original_cost_rs_crore_raw"], b["original_cost_rs_crore_raw"])["status"] not in {"unchanged", "both_missing"}:
        flags.append("reported_original_cost_changed")
    for label, field in [("progress", "physical_progress_pct_raw"),
                         ("expenditure", "cumulative_expenditure_rs_crore_raw")]:
        status = change(a[field], b[field])["status"]
        if status == "decreased":
            flags.append("reported_" + label + "_decrease_requires_review")
        elif status in {"both_missing", "became_missing", "became_available"}:
            flags.append(label + "_missing_in_one_or_both_reports")
    for month, row in [("april", a), ("august", b)]:
        start, completion = month_index(row["start_date_raw"]), month_index(row["revised_doc_raw"])
        if start is not None and completion is not None and completion < start:
            flags.append(month + "_revised_completion_before_start")
    return dict(identity_review_classification=category, identity_review_reason=reason,
                trend_eligible=not flags, trend_review_reasons=flags)


def compare_records(april_records, august_records, identity_reviews=None):
    april, august = index_records(april_records), index_records(august_records)
    common_codes = sorted(april.keys() & august.keys())
    only_april = [april[c] for c in sorted(april.keys() - august.keys())]
    only_august = [august[c] for c in sorted(august.keys() - april.keys())]
    common = []
    for code in common_codes:
        a, b = april[code], august[code]
        differences = {field:dict(april=a[field], august=b[field])
                       for field in IDENTITY if a[field] != b[field]}
        similarity = SequenceMatcher(None, a["project_name"].casefold(), b["project_name"].casefold()).ratio()
        # Differences are review flags, not claims that the code was reused.
        conflict = any(field in differences for field in ("state", "ministry", "sector")) or (
            "project_name" in differences and similarity < 0.8)
        assessment = assess_match(a, b, differences, conflict, (identity_reviews or {}).get(code))
        common.append(dict(project_code=code, april=a, august=b, **assessment,
                           identity_differences=differences, name_similarity=round(similarity, 4),
                           potential_identity_conflict=conflict,
                           progress=change(a["physical_progress_pct_raw"], b["physical_progress_pct_raw"]),
                           expenditure=change(a["cumulative_expenditure_rs_crore_raw"], b["cumulative_expenditure_rs_crore_raw"]),
                           completion_dates={field:change(a[field], b[field], date=True) for field in DATE_FIELDS}))
    flagged_codes = {r["project_code"] for r in common if r["potential_identity_conflict"]}
    if identity_reviews is not None and set(identity_reviews) != flagged_codes:
        raise ValueError("Identity review must cover exactly the current heuristic flags")
    eligible = [r for r in common if r["trend_eligible"]]
    summary = dict(identity_review_counts=dict(Counter(r["identity_review_classification"] for r in common
                                                       if r["potential_identity_conflict"])),
                   trend_eligible_records=len(eligible), trend_excluded_records=len(common)-len(eligible),
                   trend_exclusion_reason_counts=dict(Counter(reason for r in common for reason in r["trend_review_reasons"])),
                   screened_progress_changes=dict(Counter(r["progress"]["status"] for r in eligible)),
                   screened_expenditure_changes=dict(Counter(r["expenditure"]["status"] for r in eligible)),
                   trend_policy="Screening eligibility is not proof of reliable performance. All raw reported decreases require review; identity, baseline and source anomalies are excluded from screened aggregates.",
                   april_records=len(april), august_records=len(august),
                   present_in_both=len(common), only_april=len(only_april), only_august=len(only_august),
                   identity_difference_counts=dict(Counter(field for row in common for field in row["identity_differences"])),
                   potential_identity_conflicts=[row["project_code"] for row in common if row["potential_identity_conflict"]],
                   progress_changes=dict(Counter(row["progress"]["status"] for row in common)),
                   expenditure_changes=dict(Counter(row["expenditure"]["status"] for row in common)),
                   completion_date_changes={field:dict(Counter(row["completion_dates"][field]["status"] for row in common))
                                            for field in DATE_FIELDS},
                   progress_decreases=[row["project_code"] for row in common if row["progress"]["status"] == "decreased"],
                   expenditure_decreases=[row["project_code"] for row in common if row["expenditure"]["status"] == "decreased"],
                   absence_interpretation="Presence in these published ongoing tables only; absence does not establish completion.",
                   delta_units=dict(progress="percentage points", expenditure="Rs. crore", completion_dates="months"),
                   missing_markers={
                       month:dict(Counter(field for row in records for field in
                                         ("approval_date_raw", "start_date_raw", *DATE_FIELDS,
                                          "physical_progress_pct_raw", "cumulative_expenditure_rs_crore_raw",
                                          "legacy_ocms_code_raw", "pmgid_raw")
                                         if bare(row[field]).upper() in MISSING))
                       for month, records in [("APRIL 2026", april_records), ("AUGUST 2026", august_records)]})
    return common, only_april, only_august, summary


def write_csv(path, records, fieldnames=None):
    with path.open("w", encoding="utf-8", newline="") as stream:
        fields = fieldnames or (list(records[0]) if records else ["project_code"])
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def flatten(row):
    a, b = row["april"], row["august"]
    result = dict(project_code=row["project_code"], potential_identity_conflict=str(row["potential_identity_conflict"]),
                  identity_differences_json=json.dumps(row["identity_differences"], ensure_ascii=False),
                  identity_review_classification=row["identity_review_classification"],
                  identity_review_reason=row["identity_review_reason"],
                  trend_eligible=str(row["trend_eligible"]),
                  trend_review_reasons_json=json.dumps(row["trend_review_reasons"]))
    for prefix, source in [("april", a), ("august", b)]:
        for field in ("serial_no", *IDENTITY, "source_filename", "report_month", "pdf_pages", "original_cost_rs_crore_raw", "start_date_raw"):
            result[prefix+"_"+field] = source[field]
    for label in ("progress", "expenditure"):
        for key in ("april_raw", "august_raw", "status", "delta"):
            result[label+"_"+key] = row[label][key]
    for field in DATE_FIELDS:
        for key in ("april_raw", "august_raw", "status", "delta"):
            result[field+"_"+key] = row["completion_dates"][field][key]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--april-csv", type=Path, required=True)
    parser.add_argument("--april-audit", type=Path, required=True)
    parser.add_argument("--april-pdf", type=Path, required=True)
    parser.add_argument("--august-csv", type=Path, required=True)
    parser.add_argument("--august-audit", type=Path, required=True)
    parser.add_argument("--august-pdf", type=Path, required=True)
    parser.add_argument("--identity-review", type=Path,
                        default=Path(__file__).resolve().parents[1]/"tests/fixtures/april_august_identity_review.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    # Invalidate any earlier comparison summary before input validation.
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(dict(status="running", reason="Comparison has not completed"))+"\n", encoding="utf-8")
    april, april_audit = load_validated(args.april_csv, args.april_audit, args.april_pdf, "APRIL 2026")
    august, august_audit = load_validated(args.august_csv, args.august_audit, args.august_pdf, "AUGUST 2026")
    reviews = load_identity_review(args.identity_review, april_audit, august_audit)
    common, only_april, only_august, summary = compare_records(april, august, reviews)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "common": args.output_dir/"april_august_common.csv",
        "only_april": args.output_dir/"april_only.csv",
        "only_august": args.output_dir/"august_only.csv",
        "progress_decreases": args.output_dir/"progress_decreases.csv",
        "expenditure_decreases": args.output_dir/"expenditure_decreases.csv",
        "identity_differences": args.output_dir/"identity_differences.csv",
        "questionable_matches": args.output_dir/"questionable_matches.csv",
        "screened_matches": args.output_dir/"screened_matches.csv",
    }
    write_csv(outputs["common"], [flatten(row) for row in common])
    write_csv(outputs["only_april"], only_april)
    write_csv(outputs["only_august"], only_august)
    for kind, predicate in [
        ("progress_decreases", lambda row:row["progress"]["status"] == "decreased"),
        ("expenditure_decreases", lambda row:row["expenditure"]["status"] == "decreased"),
        ("identity_differences", lambda row:bool(row["identity_differences"])),
        ("questionable_matches", lambda row:not row["trend_eligible"]),
        ("screened_matches", lambda row:row["trend_eligible"])]:
        write_csv(outputs[kind], [flatten(row) for row in common if predicate(row)])
    summary.update(status="validated_comparison",
                   identity_review_sha256=hashlib.sha256(args.identity_review.read_bytes()).hexdigest(),
                   input_hashes=dict(april_csv=april_audit["csv_sha256"], august_csv=august_audit["csv_sha256"],
                                     april_pdf=april_audit["source_sha256"], august_pdf=august_audit["source_sha256"]),
                   output_hashes={kind:hashlib.sha256(path.read_bytes()).hexdigest() for kind,path in outputs.items()},
                   records=common)
    args.summary.write_text(json.dumps(summary, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k != "records"}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
