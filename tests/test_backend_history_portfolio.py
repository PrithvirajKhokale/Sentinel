"""Real PostgreSQL history gaps, stored comparisons and portfolio scope tests."""
from collections import Counter
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import test_backend as baseline
from backend.import_dataset import activate_bundle


@unittest.skipUnless(os.environ.get("BACKEND_TEST_DATABASE_URL"),"Set loopback PostgreSQL BACKEND_TEST_DATABASE_URL")
class HistoryPortfolioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline.BackendTests.setUpClass.__func__(cls)
        cls.snapshots={(r["project_code"],r["report_month"]):r for r in cls.bundle["snapshots"]}

    @classmethod
    def tearDownClass(cls):
        baseline.BackendTests.tearDownClass.__func__(cls)

    def get(self,url,params=None):
        response=self.client.get(url,params=params)
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    def test_history_real_gap_and_no_bridging(self):
        response=self.get("/api/v1/projects/611752/history")
        self.assertEqual([r["report_month"] for r in response["data"]],["2026-04","2026-05","2026-07","2026-08"])
        self.assertEqual(response["meta"]["not_observed_months"],["2026-06"])
        self.assertEqual([(p["before_month"],p["after_month"]) for p in response["meta"]["comparisons"]],
                         [("2026-04","2026-05"),("2026-07","2026-08")])
        self.assertTrue(all(r==self.snapshots[r["project_code"],r["report_month"]] for r in response["data"]))

    def test_history_comparisons_are_before_pagination(self):
        first=self.get("/api/v1/projects/400298/history",{"page_size":1})
        second=self.get("/api/v1/projects/400298/history",{"page_size":1,"page":2})
        beyond=self.get("/api/v1/projects/400298/history",{"page_size":1,"page":10})
        self.assertEqual(first["data"][0]["report_month"],"2026-04")
        self.assertEqual(second["data"][0]["report_month"],"2026-05")
        self.assertEqual(beyond["data"],[])
        self.assertEqual(first["meta"]["pagination"],dict(page=1,page_size=1,total_items=5,total_pages=5))
        self.assertEqual(first["meta"]["comparisons"],second["meta"]["comparisons"])
        self.assertEqual(first["meta"]["comparisons"],beyond["meta"]["comparisons"])
        self.assertEqual(len(first["meta"]["comparisons"]),4)

    def test_history_reference_changes_and_pair_decisions(self):
        with patch("scripts.compare_project_reports.load_identity_review",side_effect=AssertionError("Never reuse April-August reviews")):
            response=self.get("/api/v1/projects/400298/history",{"from_month":"2026-06","to_month":"2026-07"})
        expected=json.loads(Path("docs/examples/project-data-contract.json").read_text(encoding="utf-8"))["examples"]["monthly_history"]["response"]
        self.assertEqual(response["data"],expected["data"])
        self.assertEqual(response["meta"],expected["meta"])
        self.assertIn(expected["warnings"][0],response["warnings"])
        pair=response["meta"]["comparisons"][0]
        self.assertEqual(pair["changes"]["physical_progress_pct_raw"]["delta"],"-53.02")
        self.assertEqual(pair["changes"]["cumulative_expenditure_rs_crore_raw"]["delta"],"-583.63")
        self.assertEqual(pair["identity_review_status"],"not_reviewed_for_this_pair")
        self.assertFalse(pair["trend_eligible"])

    def test_history_known_empty_range_and_single_month(self):
        empty=self.get("/api/v1/projects/400005/history",{"from_month":"2026-05","to_month":"2026-08"})
        self.assertEqual(empty["data"],[])
        self.assertEqual(empty["meta"]["not_observed_months"],["2026-05","2026-06","2026-07","2026-08"])
        self.assertEqual(empty["meta"]["comparisons"],[])
        self.assertEqual(empty["meta"]["pagination"]["total_pages"],0)
        one=self.get("/api/v1/projects/701530/history",{"from_month":"2026-07","to_month":"2026-07"})
        self.assertEqual(len(one["data"]),1);self.assertEqual(one["meta"]["comparisons"],[])
        self.assertIsNone(one["data"][0]["values"]["approval_date"]["normalized"])
        self.assertEqual(one["data"][0]["values"]["physical_progress_pct"]["normalized"],"0")

    def test_portfolio_matches_validated_full_counts(self):
        response=self.get("/api/v1/portfolio-summary",{"report_month":"2026-08","comparison_month":"2026-07"})
        expected=json.loads(Path("docs/examples/project-data-contract.json").read_text(encoding="utf-8"))["examples"]["portfolio_summary"]["response"]["data"]
        for key in ("counts","quality_counts"):self.assertEqual(response["data"][key],expected[key])
        actual=response["data"]["comparison"]
        for key,value in expected["comparison"].items():self.assertEqual(actual[key],value,key)
        self.assertEqual(actual["shared_scope_codes"],1694)
        self.assertEqual(actual["trend_eligible"],0)
        self.assertEqual(actual["exclusion_reasons"]["baseline_revised_cost_rs_crore_raw"],1694)
        self.assertEqual(actual["progress_changes"]["decreased"],13)
        self.assertEqual(actual["expenditure_changes"]["decreased"],54)
        self.assertEqual(sum(actual["progress_changes"].values()),1694)
        self.assertEqual(actual["presence_breakdown"]["before_only"],{"not_observed_in_report":81})
        self.assertEqual(actual["presence_breakdown"]["after_only"],{"not_observed_in_report":37})
        self.assertTrue(any(w["code"]=="conservative_pair_screen" for w in response["warnings"]))

    def test_independent_month_filters_distinguish_scope_changes(self):
        for agency,side in [("(CAO/C/SCoR SCoR mor)","after_only"),("(South Central Railway [SCR] - II)","before_only")]:
            response=self.get("/api/v1/portfolio-summary",{"report_month":"2026-07","comparison_month":"2026-06","agency":agency})
            comparison=response["data"]["comparison"]
            affected=next(p for p in comparison["presence"] if p["project_code"]=="400298")
            self.assertEqual(affected,dict(project_code="400298",presence=side,reason="not_in_filtered_scope"))
            self.assertEqual(comparison["shared_scope_codes"]+comparison["before_only"],comparison["before_scope_count"])
            self.assertEqual(comparison["shared_scope_codes"]+comparison["after_only"],comparison["after_scope_count"])
            selected={month:{r["project_code"] for r in self.bundle["snapshots"] if r["report_month"]==month and r["identity"]["agency"]==agency} for month in ["2026-06","2026-07"]}
            self.assertEqual(comparison["before_scope_count"],len(selected["2026-06"]))
            self.assertEqual(comparison["after_scope_count"],len(selected["2026-07"]))
            self.assertEqual(comparison["shared_scope_codes"],len(selected["2026-06"]&selected["2026-07"]))

    def test_repeated_filters_empty_scope_and_no_comparison(self):
        parameters=[("report_month","2026-07"),("sector","Railways"),("sector","Water Resources"),("state","Andhra Pradesh")]
        result=self.get("/api/v1/portfolio-summary",parameters)
        selected=[r for r in self.bundle["snapshots"] if r["report_month"]=="2026-07" and r["identity"]["sector"] in {"Railways","Water Resources"} and r["identity"]["state"]=="Andhra Pradesh"]
        self.assertEqual(result["data"]["counts"]["snapshot_records"],len(selected))
        self.assertIsNone(result["data"]["comparison"])
        self.assertEqual(result["meta"]["filters"]["sector"],["Railways","Water Resources"])
        empty=self.get("/api/v1/portfolio-summary",{"report_month":"2026-08","comparison_month":"2026-07","ministry":"no-such-ministry"})
        self.assertEqual(empty["data"]["counts"],dict(snapshot_records=0,distinct_project_codes=0,ministries=0,sectors=0))
        self.assertEqual(empty["data"]["comparison"]["shared_scope_codes"],0)
        self.assertEqual(empty["data"]["comparison"]["presence"],[])
        self.assertEqual(empty["data"]["comparison"]["exclusion_reasons"],{})

    def test_portfolio_missingness_has_field_denominators(self):
        result=self.get("/api/v1/portfolio-summary",{"report_month":"2026-08","comparison_month":"2026-07"})["data"]["comparison"]
        fields={item["field"]:item for item in result["missing_input_counts"]}
        self.assertEqual(fields["revised_cost_rs_crore"]["both_known"],1694)
        self.assertEqual(fields["pmgid"]["either_missing"],1694)
        for item in fields.values():self.assertEqual(item["both_known"]+item["either_missing"],1694)
        self.assertEqual(result["before_quality_counts"],self.get("/api/v1/portfolio-summary",{"report_month":"2026-07"})["data"]["quality_counts"])
        may=self.get("/api/v1/portfolio-summary",{"report_month":"2026-05"})
        blank=next(i for i in may["data"]["quality_counts"]["missing_values"] if i["field"]=="original_target_doc")
        self.assertEqual(blank,dict(field="original_target_doc",missing_reason="source_blank",count=11))

    def test_new_endpoint_invalid_parameters(self):
        urls=["/api/v1/projects/701530/history?from_month=July", "/api/v1/projects/701530/history?from_month=2026-08&to_month=2026-04",
              "/api/v1/projects/701530/history?page_size=101", "/api/v1/projects/701530/history?sector=Railways",
              "/api/v1/projects/701530/history?report_month=2026-07", "/api/v1/projects/701530/history?dataset_version=bad",
              "/api/v1/portfolio-summary", "/api/v1/portfolio-summary?report_month=2026-08&comparison_month=2026-06",
              "/api/v1/portfolio-summary?report_month=2026-08&comparison_month=2026-08", "/api/v1/portfolio-summary?report_month=2026-08&page=1",
              "/api/v1/portfolio-summary?report_month=2026-08&q=rail", "/api/v1/portfolio-summary?report_month=2026-08&project_code=701530"]
        for url in urls:
            with self.subTest(url=url):
                r=self.client.get(url);self.assertEqual(r.status_code,422,r.text)
                self.assertEqual(r.json()["error"]["code"],"VALIDATION_ERROR")
                self.assertEqual(set(r.json()),{"error","meta"})

    def test_new_endpoint_unavailable_data_errors(self):
        cases=[("/api/v1/projects/no-such-code/history","PROJECT_NOT_FOUND"),
               ("/api/v1/projects/701530/history?from_month=2026-03","REPORT_NOT_AVAILABLE"),
               ("/api/v1/portfolio-summary?report_month=2026-04&comparison_month=2026-03","REPORT_NOT_AVAILABLE"),
               ("/api/v1/portfolio-summary?report_month=2026-09","REPORT_NOT_AVAILABLE")]
        for endpoint in ["/api/v1/projects/701530/history?", "/api/v1/portfolio-summary?report_month=2026-08&"]:
            cases.append((endpoint+"dataset_version="+"f"*64,"DATASET_NOT_FOUND"))
        for url,code in cases:
            r=self.client.get(url);self.assertEqual(r.status_code,404,r.text);self.assertEqual(r.json()["error"]["code"],code)

    def test_both_endpoints_honor_revision_selection(self):
        # A deliberately small prior-revision test fixture; never loaded by the CLI.
        alternate=copy.deepcopy(self.bundle);alternate["version"]="d"*64
        alternate["snapshots"]=[r for r in alternate["snapshots"] if r["project_code"]=="611752"]
        alternate["comparisons"]=[r for r in alternate["comparisons"] if r["project_code"]=="611752"]
        try:
            activate_bundle(self.engine,alternate)
            latest=self.get("/api/v1/portfolio-summary",{"report_month":"2026-08"})
            self.assertEqual(latest["data"]["counts"]["snapshot_records"],1)
            old=self.get("/api/v1/portfolio-summary",{"report_month":"2026-08","dataset_version":self.bundle["version"]})
            self.assertEqual(old["data"]["counts"]["snapshot_records"],1731)
            old_history=self.get("/api/v1/projects/400298/history",{"dataset_version":self.bundle["version"]})
            self.assertEqual(len(old_history["data"]),5)
            self.assertEqual(self.client.get("/api/v1/projects/400298/history").status_code,404)
        finally:activate_bundle(self.engine,self.bundle)

    def test_incomplete_stored_comparisons_fail_without_invention(self):
        incomplete=copy.deepcopy(self.bundle);incomplete["version"]="e"*64
        incomplete["snapshots"]=[r for r in incomplete["snapshots"] if r["project_code"]=="400298" and r["report_month"] in {"2026-06","2026-07"}]
        incomplete["comparisons"]=[]
        try:
            activate_bundle(self.engine,incomplete)
            for url in ["/api/v1/projects/400298/history", "/api/v1/portfolio-summary?report_month=2026-07&comparison_month=2026-06"]:
                r=self.client.get(url)
                self.assertEqual(r.status_code,500)
                self.assertEqual(r.json()["error"]["code"],"INTERNAL_ERROR")
                self.assertNotIn("data",r.json())
        finally:activate_bundle(self.engine,self.bundle)

    def test_field_specific_missing_warning_is_not_pair_usability(self):
        response=self.get("/api/v1/projects/701530/history",{"from_month":"2026-07","to_month":"2026-08"})
        critical=next(w for w in response["warnings"] if w["code"]=="missing_metric_or_baseline")
        self.assertEqual(critical["fields"],["approval_date"])
        pair=response["meta"]["comparisons"][0]
        self.assertFalse(pair["trend_eligible"])
        self.assertIn("pmgid_raw",pair["before_missing_values"])
        self.assertEqual(response["data"][-1]["values"]["revised_cost_rs_crore"]["normalized"],"0")
        self.assertIsNone(response["data"][-1]["values"]["approval_date"]["normalized"])

    def test_portfolio_decrease_warning_targets_affected_fields(self):
        for sector,field in [("Electricity Generation","cumulative_expenditure_rs_crore"),
                             ("Education","physical_progress_pct")]:
            with self.subTest(sector=sector):
                response=self.get("/api/v1/portfolio-summary",{"report_month":"2026-08","comparison_month":"2026-07","sector":sector})
                warning=next(w for w in response["warnings"] if w["code"]=="reported_decreases")
                self.assertEqual(warning["fields"],[field])
