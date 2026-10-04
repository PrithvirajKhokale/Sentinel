"""Present stored comparisons and count reported monitoring data without inference."""
from collections import Counter
import json
from .presentation import warning

IDENTITY_FILTERS = ("ministry", "sector", "state", "agency")


def month_number(month):
    year,number = map(int,month.split("-"))
    return year*12+number-1


def month_range(start,end):
    return [f"{n//12:04d}-{n%12+1:02d}" for n in range(month_number(start),month_number(end)+1)]


def present_comparison(raw):
    result = {key:raw[key] for key in ("project_code","before_month","after_month","identity_review_status")}
    result.update(screening_policy="monthly-history-v1",trend_eligible=raw["trend_eligible"]=="True",
                  completion_trend_eligible=raw["completion_trend_eligible"]=="True")
    for field in ("changes","identity_differences","baseline_changes","auxiliary_identifier_changes",
                  "before_missing_values","after_missing_values","quality_flags","trend_review_reasons","source_notes"):
        result[field] = json.loads(raw[field+"_json"])
    return result


def quality_counts(payloads):
    flags,missing = Counter(),Counter()
    for payload in payloads:
        for item in payload["quality"]["snapshot_flags"]:
            for field in item["fields"]:
                flags[item["code"],field] += 1
        for field,value in payload["values"].items():
            if value["missing_reason"] is not None:
                missing[field,value["missing_reason"]] += 1
    return dict(snapshot_flags=[dict(code=k[0],field=k[1],count=v) for k,v in sorted(flags.items())],
                missing_values=[dict(field=k[0],missing_reason=k[1],count=v) for k,v in sorted(missing.items())])


def scoped_codes(rows,filters):
    return {code for code,row in rows.items()
            if all(not filters.get(field) or getattr(row,field) in filters[field] for field in IDENTITY_FILTERS)}


def portfolio_comparison(before,after,before_scope,after_scope,raw_pairs,before_month,after_month):
    common = sorted(before_scope & after_scope)
    # No scope membership difference is counted as a shared-code numeric trend.
    pairs = [present_comparison(raw_pairs[code]) for code in common]
    presence = []
    for codes,label,other in [(before_scope-after_scope,"before_only",after),
                              (after_scope-before_scope,"after_only",before)]:
        for code in sorted(codes):
            presence.append(dict(project_code=code,presence=label,
                                 reason="not_in_filtered_scope" if code in other else "not_observed_in_report"))
    reasons = Counter(reason for pair in pairs for reason in pair["trend_review_reasons"])
    fields = sorted(next(iter(before.values())).payload["values"]) if before else sorted(next(iter(after.values())).payload["values"]) if after else []
    missing_counts = []
    for field in fields:
        before_missing = sum(before[code].payload["values"][field]["normalized"] is None for code in common)
        after_missing = sum(after[code].payload["values"][field]["normalized"] is None for code in common)
        either = sum(before[code].payload["values"][field]["normalized"] is None or after[code].payload["values"][field]["normalized"] is None for code in common)
        missing_counts.append(dict(field=field,before_missing=before_missing,after_missing=after_missing,
                                   either_missing=either,both_known=len(common)-either))
    result = dict(before_month=before_month,after_month=after_month,
        before_scope_count=len(before_scope),after_scope_count=len(after_scope),shared_scope_codes=len(common),
        before_only=len(before_scope-after_scope),after_only=len(after_scope-before_scope),
        presence_scope="filtered_report" if before_scope != set(before) or after_scope != set(after) else "unfiltered_report",
        presence=presence,
        presence_breakdown={side:dict(Counter(p["reason"] for p in presence if p["presence"]==side)) for side in ("before_only","after_only")},
        progress_changes=dict(Counter(p["changes"]["physical_progress_pct_raw"]["status"] for p in pairs)),
        expenditure_changes=dict(Counter(p["changes"]["cumulative_expenditure_rs_crore_raw"]["status"] for p in pairs)),
        completion_date_changes={field:dict(Counter(p["changes"][field]["status"] for p in pairs)) for field in ("original_target_doc_raw","revised_doc_raw")},
        missing_field_records=sum(bool(p["before_missing_values"] or p["after_missing_values"]) for p in pairs),
        missing_input_counts=missing_counts,
        before_quality_counts=quality_counts([before[c].payload for c in sorted(before_scope)]),
        after_quality_counts=quality_counts([after[c].payload for c in sorted(after_scope)]),
        screening_policy="monthly-history-v1",trend_eligible=sum(p["trend_eligible"] for p in pairs),
        trend_excluded=sum(not p["trend_eligible"] for p in pairs),exclusion_reasons=dict(sorted(reasons.items())))
    assert result["shared_scope_codes"]+result["before_only"]==result["before_scope_count"]
    assert result["shared_scope_codes"]+result["after_only"]==result["after_scope_count"]
    return result


def history_pair_warnings(pair,before,after):
    pages = list(dict.fromkeys(before["provenance"]["pdf_pages"]+after["provenance"]["pdf_pages"]))
    result = []
    decreases = [field.removesuffix("_raw") for field in ("physical_progress_pct_raw","cumulative_expenditure_rs_crore_raw")
                 if pair["changes"][field]["status"]=="decreased"]
    if decreases:
        result.append(warning("reported_decreases",decreases,None,pages,"Reported decreases require review; cause is unknown.","pair"))
    for reason in pair["trend_review_reasons"]:
        if reason.startswith("reported_") and "decrease" in reason:
            continue
        fields = [field.removesuffix("_raw") for field in pair["changes"] if field in reason]
        if reason=="unreviewed_identity_change":
            fields = list(pair["identity_differences"])
        if reason=="conflicting_auxiliary_identifiers":
            fields = [field.removesuffix("_raw") for field,value in pair["auxiliary_identifier_changes"].items() if value["status"]=="conflicting_identifiers"]
        if reason=="missing_metric_or_baseline":
            critical = {"original_cost_rs_crore_raw","revised_cost_rs_crore_raw",
                        "cumulative_expenditure_rs_crore_raw","physical_progress_pct_raw",
                        "approval_date_raw","start_date_raw","original_target_doc_raw"}
            fields = sorted(f.removesuffix("_raw") for f in
                            (pair["before_missing_values"].keys()|pair["after_missing_values"].keys()) & critical)
        result.append(warning(reason,fields,None,pages,
                              "Conservative pair-wide review reason; individual field suitability requires explicit review.","pair"))
    return result
