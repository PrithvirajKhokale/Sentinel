"""Evidence-backed *reported* warning signals; never predictions or risk scores.

Every signal is a description of adjacent published observations, not an
independent assertion of project performance, causes, completion or failure.
Source-pair exclusions are retained, not silently converted into eligibility.
"""
from collections import Counter

SIGNALS = {
    "reported_progress_decrease": {
        "title": "Reported progress decreased",
        "category": "progress",
        "explanation": "The later report gives a lower physical-progress percentage. The cause is unknown.",
        "fields": ("physical_progress_pct_raw",),
    },
    "spending_without_reported_progress": {
        "title": "Expenditure increased; reported progress unchanged",
        "category": "expenditure",
        "explanation": "Cumulative expenditure increased while reported physical progress did not change. This does not prove waste or delay.",
        "fields": ("cumulative_expenditure_rs_crore_raw", "physical_progress_pct_raw"),
    },
    "reported_target_postponed": {
        "title": "Reported revised target moved later",
        "category": "schedule",
        "explanation": "The revised target month in the later report is later. This is not an actual completion date or a measured delay against a work plan.",
        "fields": ("revised_doc_raw",),
    },
}


def signals_for_pair(pair, before, after):
    """Return observed changes with raw evidence and all conservative caveats."""
    if pair["project_code"] != before["project_code"] or pair["project_code"] != after["project_code"]:
        raise ValueError("Project-code mismatch in pair evidence")
    if pair["before_month"] != before["report_month"] or pair["after_month"] != after["report_month"]:
        raise ValueError("Report-month mismatch in pair evidence")
    changes = pair["changes"]
    progress = changes["physical_progress_pct_raw"]
    expenditure = changes["cumulative_expenditure_rs_crore_raw"]
    target = changes["revised_doc_raw"]
    activated = []
    if progress["status"] == "decreased":
        activated.append("reported_progress_decrease")
    if expenditure["status"] == "increased" and progress["status"] == "unchanged":
        activated.append("spending_without_reported_progress")
    if target["status"] == "postponed":
        activated.append("reported_target_postponed")

    pages = {
        "before": before["provenance"]["pdf_pages"],
        "after": after["provenance"]["pdf_pages"],
    }
    sources = {
        "before": before["provenance"]["source_filename"],
        "after": after["provenance"]["source_filename"],
    }
    reasons = pair["trend_review_reasons"]
    results = []
    for code in activated:
        definition = SIGNALS[code]
        evidence = []
        for field in definition["fields"]:
            item = changes[field]
            evidence.append({
                "field": field.removesuffix("_raw"),
                "before_raw": item["before_raw"],
                "after_raw": item["after_raw"],
                "status": item["status"],
                "delta": item.get("delta"),
            })
        results.append({
            "id": f'{pair["project_code"]}:{pair["before_month"]}:{pair["after_month"]}:{code}',
            "project_code": pair["project_code"],
            "project_name": after["identity"]["project_name"],
            "identity": after["identity"],
            "before_month": pair["before_month"],
            "after_month": pair["after_month"],
            "type": code,
            "category": definition["category"],
            "title": definition["title"],
            "explanation": definition["explanation"],
            "evidence": evidence,
            "source_files": sources,
            "source_pdf_pages": pages,
            "pair_wide_review_required": bool(reasons) or not pair["trend_eligible"],
            "review_reasons": list(reasons),
            "identity_review_status": pair["identity_review_status"],
            "policy": "reported-signals-v1",
        })
    return results


def summarize(signals, shared_pairs):
    """Denominators reflect *shared-code comparisons*, not the entire portfolio."""
    kinds = Counter(item["type"] for item in signals)
    review_pairs = {item["project_code"] for item in signals if item["pair_wide_review_required"]}
    return {
        "shared_pairs_in_scope": shared_pairs,
        "projects_with_signals": len({item["project_code"] for item in signals}),
        "total_signals": len(signals),
        "signal_counts": dict(sorted(kinds.items())),
        "signaled_projects_requiring_pair_review": len(review_pairs),
    }
