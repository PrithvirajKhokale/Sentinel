"""Monthly missing-date, immutable-history and pair-specific screening checks."""
import json
import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.extract_ongoing_projects import assemble, audit, parse_row
from scripts.build_monthly_history import adjacent_pair, history_rows, load_catalog, load_snapshot, normalized_value, preserve_existing_history, write_csv
from test_data_extraction import cells_for, row


def sample():
    return json.loads((Path(__file__).parent/"fixtures/may_2026_ongoing_visual_samples.json").read_text(encoding="utf-8"))[0]


def report(month="2026-05", label="MAY 2026"):
    return dict(report_month_iso=month,report_month=label,source_sha256="source",
                documented_reporting_cutoff_date="2026-06-24",
                documented_reporting_cutoff_raw="latest by 24th June 2026",
                cutoff_source_pdf_page=2,publication_date=None,first_available_date=None,
                source_platform="IPM",source_notes=[])


class MonthlyHistoryTests(unittest.TestCase):
    def test_three_manually_reviewed_fixtures(self):
        for month,count in [("may",14),("june",11),("july",11)]:
            refs=json.loads((Path(__file__).parent/f"fixtures/{month}_2026_ongoing_visual_samples.json").read_text(encoding="utf-8"))
            self.assertEqual(len(refs),count)
            for expected in refs:
                cells=cells_for(expected)
                if not expected["original_target_doc_raw"]:cells[4]="(-)"
                actual=parse_row(cells)
                for key,value in actual.items():
                    self.assertEqual(value,expected[key])

    def test_source_blank_and_parentheses_are_preserved(self):
        refs=json.loads((Path(__file__).parent/"fixtures/may_2026_ongoing_visual_samples.json").read_text(encoding="utf-8"))
        medical=next(r for r in refs if r["project_code"]=="706965")
        cells=cells_for(medical);cells[0]="1";cells[4]="(-)"
        records,_,issues,totals,_=assemble([
            row(["","Ministry of Health & Family Welfare"]+[None]*6,75),
            row(["","Healthcare"]+[None]*6,75),row(cells,75),
            row(["","Total (1)"]+[None]*6,75)])
        self.assertEqual(issues,[])
        self.assertEqual(records[0]["original_target_doc_raw"],"")
        self.assertEqual(records[0]["start_date_raw"],"()")
        result=audit(records,[row(cells)],totals,[],[],False)
        self.assertTrue(result["coverage_pass"])
        self.assertEqual(result["blank_fields"],{})
        self.assertEqual(result["source_empty_fields"],{"original_target_doc_raw":["1"]})
        self.assertEqual(result["explicit_missing_markers"]["start_date_raw"],["1"])
        altered=dict(records[0],state="")
        self.assertFalse(audit([altered],[row(cells)],totals,[],[],False)["coverage_pass"])

    def test_ambiguous_single_completion_still_rejected(self):
        cells=cells_for(sample());cells[4]="03/2026"
        with self.assertRaisesRegex(ValueError,"expected two values"):parse_row(cells)
        cells[3]="NA"
        with self.assertRaisesRegex(ValueError,"expected two values"):parse_row(cells)

    def test_normalized_values_are_separate_and_missing_is_not_zero(self):
        r=sample();r["original_cost_rs_crore_raw"]="1,000.00"
        reports=[report()];rows=history_rows({"2026-05":[r]},reports)
        self.assertEqual(rows[0]["original_cost_rs_crore_raw"],"1,000.00")
        self.assertEqual(rows[0]["original_cost_rs_crore_normalized"],"1000")
        self.assertEqual(normalized_value("physical_progress_pct_raw","0.00"),"0")
        for marker in ["","(-)","()","NA"]:
            self.assertEqual(normalized_value("start_date_raw",marker),"")
        self.assertEqual(rows[0]["start_date_normalized"],"2024-01")
        self.assertEqual(rows[0]["publication_date"],"")
        self.assertEqual(rows[0]["first_available_date"],"")
        self.assertEqual(rows[0]["documented_reporting_cutoff_date"],"2026-06-24")
        self.assertEqual(r["original_cost_rs_crore_raw"],"1,000.00")

    def test_history_does_not_fill_absent_months(self):
        a=sample();b=dict(a,project_code="000123",report_month="JUNE 2026")
        rows=history_rows({"2026-05":[a],"2026-06":[b]},[report(),report("2026-06","JUNE 2026")])
        self.assertEqual(len(rows),2)
        self.assertEqual({(r["project_code"],r["report_month_iso"]) for r in rows},{(a["project_code"],"2026-05"),("000123","2026-06")})
        with self.assertRaisesRegex(ValueError,"Duplicate history key"):
            history_rows({"2026-05":[a,a]},[report()])

    def test_earlier_history_cannot_be_changed_or_dropped(self):
        rows=history_rows({"2026-05":[sample()]},[report()])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"history.csv";write_csv(path,rows)
            preserve_existing_history(path,rows)
            preserve_existing_history(path,[dict(rows[0],extra_column="new")])
            with self.assertRaisesRegex(ValueError,"overwrite"):
                preserve_existing_history(path,[dict(rows[0],physical_progress_pct_raw="71")])
            with self.assertRaisesRegex(ValueError,"overwrite"):preserve_existing_history(path,[])
            with path.open(encoding="utf-8",newline="") as stream:
                self.assertEqual(list(csv.DictReader(stream)),rows)

    def test_adjacent_presence_and_previous_reviews_are_not_reused(self):
        a=sample();b=dict(a,project_name="Different name")
        before=report();after=report("2026-06","JUNE 2026")
        with patch("scripts.compare_project_reports.load_identity_review",side_effect=AssertionError("Pair decisions must not be read")):
            common,presence,summary=adjacent_pair([a,dict(a,project_code="only-before")],[b,dict(b,project_code="only-after")],before,after)
        self.assertEqual(summary["shared"],1)
        self.assertEqual(summary["before_only"],1);self.assertEqual(summary["after_only"],1)
        self.assertEqual(common[0]["identity_review_status"],"not_reviewed_for_this_pair")
        self.assertEqual(common[0]["trend_eligible"],"False")
        self.assertIn("unreviewed_identity_change",json.loads(common[0]["trend_review_reasons_json"]))
        self.assertTrue(all("does not establish completion" in r["interpretation"] for r in presence))
        self.assertEqual(json.loads(common[0]["before_snapshot_json"]),a)

    def test_decreases_baselines_and_missing_values_remain_flagged(self):
        a=sample()
        for field,value,expected in [
            ("physical_progress_pct_raw","65","reported_progress_decrease_requires_review"),
            ("cumulative_expenditure_rs_crore_raw","100","reported_expenditure_decrease_requires_review"),
            ("revised_cost_rs_crore_raw","0.00","baseline_revised_cost_rs_crore_raw"),
            ("start_date_raw","()","missing_metric_or_baseline")]:
            with self.subTest(field=field):
                b=dict(a,**{field:value})
                rows,_,_=adjacent_pair([a],[b],report(),report("2026-06","JUNE 2026"))
                self.assertEqual(rows[0]["trend_eligible"],"False")
                self.assertIn(expected,json.loads(rows[0]["trend_review_reasons_json"]))
                self.assertEqual(json.loads(rows[0]["after_snapshot_json"])[field],value)
        b=dict(a,original_cost_rs_crore_raw="265.910",revised_cost_rs_crore_raw="(265.910)")
        rows,_,_=adjacent_pair([a],[b],report(),report("2026-06","JUNE 2026"))
        self.assertEqual(rows[0]["baseline_changes_json"],"{}")
        self.assertEqual(rows[0]["trend_eligible"],"True")
        self.assertTrue(json.loads(rows[0]["changes_json"])["original_cost_rs_crore_raw"]["raw_text_changed"])
        self.assertIn("pmgid_raw",json.loads(rows[0]["before_missing_values_json"]))

    def test_known_auxiliary_identity_conflict_and_missingness(self):
        a=dict(sample(),pmgid_raw="(123)");b=dict(a,pmgid_raw="(456)")
        rows,_,summary=adjacent_pair([a],[b],report(),report("2026-06","JUNE 2026"))
        self.assertEqual(summary["auxiliary_identity_conflicts"],1)
        self.assertEqual(rows[0]["trend_eligible"],"False")
        self.assertIn("conflicting_auxiliary_identifiers",json.loads(rows[0]["trend_review_reasons_json"]))
        rows,_,_=adjacent_pair([a],[dict(a,pmgid_raw="(-)")],report(),report("2026-06","JUNE 2026"))
        self.assertEqual(json.loads(rows[0]["auxiliary_identifier_changes_json"])["pmgid_raw"]["status"],"became_missing")
        self.assertIn("after_missing_pmgid_raw",json.loads(rows[0]["quality_flags_json"]))
        self.assertEqual(rows[0]["trend_eligible"],"True")

    def test_documented_split_is_flagged_without_cross_code_merge(self):
        a=sample();a["project_code"]="706775"
        after=report("2026-07","JULY 2026")
        after["source_notes"]=[dict(kind="documented_project_split",project_codes=["706775","child"])]
        common,presence,_=adjacent_pair([a],[a,dict(a,project_code="child")],report("2026-06","JUNE 2026"),after)
        self.assertEqual(len(common),1);self.assertEqual(len(presence),1)
        self.assertEqual(common[0]["trend_eligible"],"False")
        self.assertIn("documented_split_scope_requires_review",json.loads(common[0]["trend_review_reasons_json"]))

    def test_stale_computation_audit_is_rejected(self):
        catalog=dict(report(),csv="sample.csv",audit="sample.json",pdf="sample.pdf")
        with patch("scripts.build_monthly_history.load_validated",return_value=([sample()],{"source_sha256":"source","extractor_sha256":"outdated"})):
            with self.assertRaisesRegex(ValueError,"different computation code"):load_snapshot(catalog)

    def test_duplicate_pair_codes_are_rejected(self):
        a=sample()
        with self.assertRaisesRegex(ValueError,"Duplicate project codes"):
            adjacent_pair([a,a],[a],report(),report("2026-06","JUNE 2026"))

    def test_catalog_order_and_unknown_availability(self):
        reports=load_catalog(Path("config/monthly_reports.json"))
        self.assertEqual([r["report_month_iso"] for r in reports],["2026-04","2026-05","2026-06","2026-07","2026-08"])
        self.assertTrue(all(r["publication_date"] is None and r["first_available_date"] is None for r in reports))
