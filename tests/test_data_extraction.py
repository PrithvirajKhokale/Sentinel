"""Regression and boundary tests for lossless Table 6 extraction."""
import json
from pathlib import Path
import unittest

from scripts.extract_ongoing_projects import assemble, audit, parse_row

REFERENCE = json.loads((Path(__file__).parent / "fixtures/august_2026_table6_first10.json").read_text(encoding="utf-8"))


def cells_for(record):
    return [record["serial_no"], "\n".join([record["project_name"], record["agency"],
            "(" + record["project_code"] + ")",
            record["legacy_ocms_code_raw"] + " " + record["pmgid_raw"]]),
            record["state"], record["approval_date_raw"] + "\n" + record["start_date_raw"],
            record["original_target_doc_raw"] + "\n" + record["revised_doc_raw"],
            record["original_cost_rs_crore_raw"] + "\n" + record["revised_cost_rs_crore_raw"],
            record["cumulative_expenditure_rs_crore_raw"], record["physical_progress_pct_raw"]]


def row(cells, page=57):
    return dict(cells=cells, page=page, printed_page=page-1,
                source_filename="sample.pdf", report_month="AUGUST 2026")


def headings():
    return [row(["", "Ministry of Civil Aviation"] + [None]*6),
            row(["", "Aviation & Aviation Infrastructure"] + [None]*6)]


class ExtractionTests(unittest.TestCase):
    def test_original_reference_fields(self):
        for expected in REFERENCE:
            actual = parse_row(cells_for(expected))
            for key, value in actual.items():
                self.assertEqual(value, expected[key])

    def test_wrapped_nested_agency(self):
        cells = cells_for(REFERENCE[0])
        cells[1] = "Project (Phase I)\n(Authority of India\n(Subsidiary))\n(000123)\n(-) (-)"
        actual = parse_row(cells)
        self.assertEqual(actual["project_name"], "Project (Phase I)")
        self.assertEqual(actual["agency"], "(Authority of India (Subsidiary))")
        self.assertEqual(actual["project_code"], "000123")

    def test_record_across_page_boundary(self):
        first = cells_for(REFERENCE[0])
        first[1] = REFERENCE[0]["project_name"] + "\n(Airport Authority of"
        second = ["", "India [AAI])\n(612786)\n(-) (-)"] + [""]*6
        records, evidence, issues, _, _ = assemble(headings()+[row(first),row(second,58)])
        self.assertEqual(issues, [])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["agency"], REFERENCE[0]["agency"])
        self.assertEqual(records[0]["pdf_pages"], "57;58")
        self.assertEqual(records[0]["revised_cost_rs_crore_raw"], "0.00")
        self.assertEqual(len(evidence[0]["parts"]), 2)

    def test_ambiguous_fragment_not_appended_to_complete_record(self):
        records, _, issues, _, _ = assemble(headings()+[
            row(cells_for(REFERENCE[0])), row(["", "unattributed text"]+[""]*6,58)])
        self.assertEqual(len(records),1)
        self.assertEqual(len(issues),1)
        self.assertEqual(issues[0]["pdf_page"],58)
        self.assertIn("cannot be safely attached",issues[0]["reason"])

    def test_nonadjacent_fragment_is_rejected(self):
        first = cells_for(REFERENCE[0])
        first[1] = "Project\n(Agency"
        records, _, issues, _, _ = assemble(headings()+[
            row(first),row(["", ")\n(612786)\n(-) (-)"]+[""]*6,59)])
        self.assertEqual(records,[])
        self.assertEqual(len(issues),2)

    def test_zero_and_missing_markers_are_distinct(self):
        actual = parse_row(cells_for(REFERENCE[4]))
        self.assertEqual(actual["revised_doc_raw"],"(-)")
        self.assertEqual(actual["revised_cost_rs_crore_raw"],"0.00")

    def test_invalid_date_is_rejected(self):
        cells = cells_for(REFERENCE[0])
        cells[3] = "13/2023\n(01/2024)"
        with self.assertRaisesRegex(ValueError, "Ambiguous approval"):
            parse_row(cells)

    def test_heading_context_and_totals(self):
        physical = headings()+[row(cells_for(REFERENCE[0])),
                    row(["", "Total (1)", "", "", "", "265.91\n0.00", "186.36", ""])]
        records, _, issues, totals, _ = assemble(physical)
        self.assertEqual(issues,[])
        self.assertTrue(totals[0]["matches"])
        self.assertEqual(records[0]["ministry"],"Ministry of Civil Aviation")
        self.assertEqual(records[0]["sector"],"Aviation & Aviation Infrastructure")

    def test_full_coverage_reconciles_table1(self):
        physical = headings()+[row(cells_for(REFERENCE[0])),
                    row(["", "Total (1)", "", "", "", "265.91\n0.00", "186.36", ""])]
        records, _, issues, totals, _ = assemble(physical)
        result = audit(records, physical, totals,
                       [dict(ongoing_projects=1, ministries=1)], issues, True,
                       [dict(kind="grand_total", count=1, pdf_page=24)])
        self.assertTrue(result["coverage_pass"])
        partial = audit(records, physical, totals, [], issues, False, requested_limit=2)
        self.assertFalse(partial["coverage_pass"])

    def test_paired_values_split_across_pages(self):
        first = cells_for(REFERENCE[0])
        first[3], first[4], first[5] = "03/2023", "01/2026", "265.91"
        second = ["", "", "", "(01/2024)", "(09/2026)", "0.00", "", ""]
        records, _, issues, _, _ = assemble(headings()+[row(first),row(second,58)])
        self.assertEqual(issues, [])
        self.assertEqual(records[0]["start_date_raw"], "(01/2024)")
        self.assertEqual(records[0]["revised_cost_rs_crore_raw"], "0.00")

    def test_table1_mismatch_fails_coverage(self):
        physical = headings()+[row(cells_for(REFERENCE[0])),
                    row(["", "Total (1)", "", "", "", "265.91\n0.00", "186.36", ""])]
        records, _, issues, totals, _ = assemble(physical)
        result = audit(records, physical, totals,
                       [dict(ongoing_projects=1, ministries=1)], issues, True,
                       [dict(kind="grand_total", count=2, pdf_page=24)])
        self.assertFalse(result["coverage_pass"])
        self.assertEqual(len(result["table1_count_mismatches"]), 1)

    def test_repeated_serial_continuation(self):
        first = cells_for(REFERENCE[0])
        first[1] = REFERENCE[0]["project_name"] + "\n(Airport Authority of"
        second = ["1", "India [AAI])\n(612786)\n(-) (-)"] + [""]*6
        records, _, issues, _, _ = assemble(headings()+[row(first),row(second,58)])
        self.assertEqual(issues, [])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["pdf_pages"], "57;58")

    def test_duplicate_code_and_serial_audited(self):
        physical = headings()+[row(cells_for(REFERENCE[0])),row(cells_for(REFERENCE[0]))]
        records, _, issues, totals, _ = assemble(physical)
        result = audit(records, physical, totals, [], issues, True)
        self.assertEqual(result["duplicate_project_codes"],{"612786":["1","1"]})
        self.assertEqual(result["duplicate_serials"],{"1":2})
        self.assertFalse(result["coverage_pass"])


if __name__ == "__main__":
    unittest.main()
