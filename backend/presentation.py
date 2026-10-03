import json
from scripts.compare_project_reports import bare
from .schemas import SnapshotResponse

FIELDS = ("legacy_ocms_code", "pmgid", "approval_date", "start_date", "original_target_doc",
          "revised_doc", "original_cost_rs_crore", "revised_cost_rs_crore",
          "cumulative_expenditure_rs_crore", "physical_progress_pct")


def warning(code, fields, month, pages, message, scope="snapshot"):
    return dict(scope=scope, code=code, fields=fields, report_month=month,
                source_pdf_pages=pages, message=message)


def snapshot(r):
    values = {}
    for field in FIELDS:
        raw = r[field+"_raw"]
        identifier = field in {"legacy_ocms_code", "pmgid"}
        normalized = (None if bare(raw).upper() in {"", "-", "NA", "N/A"} else bare(raw)) if identifier else r[field+"_normalized"] or None
        values[field] = dict(raw=raw, normalized=normalized,
                             unit=None if identifier else "Rs. crore" if "crore" in field else "percent" if field == "physical_progress_pct" else "month",
                             missing_reason=("source_blank" if raw == "" else "source_marker") if normalized is None else None)
    pages = list(map(int, r["pdf_pages"].split(";")))
    flags = [warning(i["kind"], [i["field"].removesuffix("_raw")], r["report_month_iso"], pages,
                     "Source reports a missing value." if i["kind"] == "missing_value" else "Source measurement requires review.")
             for i in json.loads(r["snapshot_issues_json"])]
    return SnapshotResponse.model_validate(dict(
        project_code=r["project_code"], report_month=r["report_month_iso"], report_month_label=r["report_month"], serial_no=r["serial_no"],
        identity={k:r[k] for k in ("project_name", "agency", "ministry", "sector", "state")}, values=values,
        provenance=dict(source_filename=r["source_filename"], source_sha256=r["source_sha256"], pdf_pages=pages,
                        printed_pages=list(map(int,r["printed_pages"].split(";"))), physical_cells=json.loads(r["source_cells_json"])),
        temporal=dict(reporting_cutoff_date=r["documented_reporting_cutoff_date"] or None,
                      reporting_cutoff_raw=r["documented_reporting_cutoff_raw"], source_pdf_page=int(r["cutoff_source_pdf_page"]),
                      publication_date=r["publication_date"] or None, first_available_date=r["first_available_date"] or None,
                      source_platform=r["source_platform"]),
        quality=dict(snapshot_flags=flags, source_notes=json.loads(r["documented_source_notes_json"])))).model_dump()
