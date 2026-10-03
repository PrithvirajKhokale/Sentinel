"""April value conventions and snapshot comparison safeguards."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from scripts.compare_project_reports import change, compare_records, index_records, load_validated, load_identity_review
from scripts.extract_ongoing_projects import parse_row
from test_data_extraction import cells_for

class AprilComparisonTests(unittest.TestCase):
    def test_april_manually_reviewed_values(self):
        refs=json.loads((Path(__file__).parent/'fixtures/april_2026_ongoing_visual_samples.json').read_text())
        for expected in refs:
            for key,value in parse_row(cells_for(expected)).items():
                self.assertEqual(value,expected[key])

    def test_zero_is_available_and_decimal_is_exact(self):
        self.assertEqual(change('0','0.00')['status'],'unchanged')
        self.assertEqual(change('(-)','0')['status'],'became_available')
        self.assertEqual(change('1,000.01','999.99')['delta'],'-0.02')
        self.assertEqual(change('(2520)','2,520.00')['delta'],'0.00')

    def test_completion_months_and_missing_values(self):
        self.assertEqual(change('(03/2027)','(03/2019)',date=True)['delta'],'-96')
        self.assertEqual(change('NA','(-)',date=True)['status'],'both_missing')
        self.assertEqual(change('03/2026','(-)',date=True)['status'],'became_missing')
        with self.assertRaises(ValueError): change('13/2026','03/2027',date=True)

    def test_presence_and_identity_are_separate(self):
        base=dict(original_cost_rs_crore_raw='100',project_code='000123',project_name='Original name',agency='(Agency)',state='A',ministry='M',sector='S',physical_progress_pct_raw='0',cumulative_expenditure_rs_crore_raw='0',original_target_doc_raw='03/2026',revised_doc_raw='(-)',approval_date_raw='NA',start_date_raw='(-)',legacy_ocms_code_raw='(-)',pmgid_raw='(-)')
        common,a,b,summary=compare_records([base,dict(base,project_code='April')],[dict(base,state='B'),dict(base,project_code='August')])
        self.assertEqual(common[0]['project_code'],'000123')
        self.assertTrue(common[0]['potential_identity_conflict'])
        self.assertEqual([r['project_code'] for r in a],['April'])
        self.assertEqual([r['project_code'] for r in b],['August'])
        self.assertIn('does not establish completion',summary['absence_interpretation'])
        self.assertFalse(common[0]['trend_eligible'])
        # A reviewed harmless text edit may pass; material and unresolved may not.
        before=base;after=dict(base,project_name='Renamed text')
        review=dict(project_code='000123',classification='harmless_text_change',reason='Reviewed spelling',reviewed_values=dict(april={'project_name':before['project_name']},august={'project_name':after['project_name']}))
        for category,eligible in [('harmless_text_change',True),('material_reported_change',False),('unresolved',False)]:
            with self.subTest(category=category):
                reviewed=dict(review,classification=category)
                rows,_,_,_=compare_records([before],[after],{'000123':reviewed})
                self.assertEqual(rows[0]['trend_eligible'],eligible)
        for field,value,reason in [('physical_progress_pct_raw','-1','reported_progress_decrease_requires_review'),('cumulative_expenditure_rs_crore_raw','-1','reported_expenditure_decrease_requires_review'),('start_date_raw','(01/2026)','reported_start_date_changed'),('original_cost_rs_crore_raw','200','reported_original_cost_changed')]:
            with self.subTest(field=field):
                rows,_,_,_=compare_records([before],[dict(after,**{field:value})],{'000123':review})
                self.assertFalse(rows[0]['trend_eligible'])
                self.assertIn(reason,rows[0]['trend_review_reasons'])
        stale=dict(review,reviewed_values={'april':{'project_name':'Wrong'},'august':{'project_name':after['project_name']}})
        with self.assertRaisesRegex(ValueError,'Stale identity'): compare_records([before],[after],{'000123':stale})
        with self.assertRaisesRegex(ValueError,'cover exactly'): compare_records([before],[after],{})
        payload=json.loads((Path(__file__).parent/'fixtures/april_august_identity_review.json').read_text())
        self.assertEqual(len(index_records(payload['reviews'])),125)
        for record in payload['reviews']:
            self.assertTrue(record['reason'])
            self.assertIn(record['classification'],{'harmless_text_change','material_reported_change','unresolved'})

    def test_duplicate_codes_fail(self):
        with self.assertRaises(ValueError): index_records([{'project_code':'1'},{'project_code':'1'}])

    def test_partial_or_stale_audit_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);csv_path=root/'data.csv';pdf=root/'source.pdf';audit=root/'audit.json';issues=root/'audit_issues.jsonl'
            csv_path.write_text('project_code,report_month\n1,APRIL 2026\n');pdf.write_bytes(b'PDF');issues.write_bytes(b'')
            payload=dict(status='validated_full',scope='full',coverage_pass=True,csv_round_trip='PASS',issues=[],accepted_records=1,csv_sha256=hashlib.sha256(csv_path.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),issue_log_sha256=hashlib.sha256(b'').hexdigest())
            audit.write_text(json.dumps(payload))
            self.assertEqual(len(load_validated(csv_path,audit,pdf,'APRIL 2026')[0]),1)
            review_path=root/'review.json'
            review_path.write_text(json.dumps(dict(input_pdf_sha256={'april_pdf':'wrong','august_pdf':'wrong'},reviews=[])))
            with self.assertRaisesRegex(ValueError,'different source PDFs'):
                load_identity_review(review_path,payload,payload)
            payload['scope']='sample';audit.write_text(json.dumps(payload))
            with self.assertRaises(ValueError): load_validated(csv_path,audit,pdf,'APRIL 2026')
            payload['scope']='full';audit.write_text(json.dumps(payload));csv_path.write_text('modified')
            with self.assertRaisesRegex(ValueError,'Stale'): load_validated(csv_path,audit,pdf,'APRIL 2026')
