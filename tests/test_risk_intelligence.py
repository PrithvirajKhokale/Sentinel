"""Regression tests for factual warning signals, no inferred risk scores."""
import unittest
from backend.risk_intelligence import signals_for_pair, summarize


def fixture(progress=("5", "3", "decreased", "-2"), spending=("100", "120", "increased", "20"),
            target=("06/2028", "07/2028", "postponed", "1"), review=None):
    values = [("physical_progress_pct_raw", progress), ("cumulative_expenditure_rs_crore_raw", spending),
              ("revised_doc_raw", target)]
    changes = {k: dict(before_raw=a, after_raw=b, status=status, delta=delta)
               for k, (a,b,status,delta) in values}
    reasons = ["baseline_revised_cost_rs_crore_raw"] if review is None else review
    pair = {
        "project_code": "000321", "before_month": "2026-07", "after_month": "2026-08",
        "identity_review_status": "not_reviewed_for_this_pair", "trend_eligible": False,
        "trend_review_reasons": reasons, "changes": changes,
    }
    identity = dict(project_name="Example from report", ministry="Test ministry", agency="Agency",
                    state="State", sector="Sector")
    def snap(month, filename, pg):
        return {"project_code":"000321","report_month":month,"identity":identity,
                "provenance":{"pdf_pages":[pg],"source_filename":filename}}
    return pair,snap("2026-07","jul.pdf",3),snap("2026-08","aug.pdf",10)


class RiskSignalsTests(unittest.TestCase):
    def test_reported_decrease_and_schedule_shift_preserve_exact_evidence(self):
        pair,a,b=fixture()
        items=signals_for_pair(pair,a,b)
        self.assertEqual({i["type"] for i in items},
                         {"reported_progress_decrease","reported_target_postponed"})
        for item in items:
            self.assertTrue(item["pair_wide_review_required"])
            self.assertEqual(item["review_reasons"],["baseline_revised_cost_rs_crore_raw"])
            self.assertEqual(item["source_pdf_pages"],{"before":[3],"after":[10]})
            self.assertEqual(item["source_files"],{"before":"jul.pdf","after":"aug.pdf"})
            self.assertEqual(item["project_code"],"000321")
            self.assertNotIn("risk_score",item)
            self.assertNotIn("probability",item)
        progress=next(i for i in items if i["category"]=="progress")
        self.assertEqual(progress["evidence"][0],{"field":"physical_progress_pct",
            "before_raw":"5","after_raw":"3","status":"decreased","delta":"-2"})

    def test_spend_growth_with_static_progress_only_when_both_observed(self):
        pair,a,b=fixture(progress=("5","5","unchanged","0"),
                         spending=("100","120","increased","20"),
                         target=("06/2028","06/2028","unchanged","0"))
        items=signals_for_pair(pair,a,b)
        self.assertEqual([i["type"] for i in items],["spending_without_reported_progress"])
        self.assertEqual(len(items[0]["evidence"]),2)
        pair["changes"]["physical_progress_pct_raw"]["status"]="became_missing"
        self.assertEqual(signals_for_pair(pair,a,b),[])

    def test_no_invention_for_missing_inputs_or_zero_flags(self):
        pair,a,b=fixture(progress=("-","-","both_missing",None),
                         spending=("0","0","unchanged","0"),
                         target=("(-)","(-)","both_missing",None))
        self.assertEqual(signals_for_pair(pair,a,b),[])
        self.assertEqual(summarize([],3),{"shared_pairs_in_scope":3,"projects_with_signals":0,
                                         "total_signals":0,"signal_counts":{},
                                         "signaled_projects_requiring_pair_review":0})

    def test_source_mismatch_rejected_and_counts_are_project_distinct(self):
        pair,a,b=fixture()
        rows=signals_for_pair(pair,a,b)
        self.assertEqual(summarize(rows,1)["projects_with_signals"],1)
        b["project_code"]="different"
        with self.assertRaisesRegex(ValueError,"Project-code mismatch"):
            signals_for_pair(pair,a,b)


if __name__ == "__main__":
    unittest.main()
