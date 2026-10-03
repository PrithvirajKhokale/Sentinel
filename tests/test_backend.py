"""PostgreSQL integration checks in a disposable, uniquely named schema."""
import copy
import json
import os
from pathlib import Path
import unittest
import uuid
from unittest.mock import patch
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy.orm import Session
from backend.app import create_app
from backend.db import engine_from_env
from backend.import_dataset import activate_bundle, validate_bundle, ROOT
from backend.models import ActiveDataset, Comparison, Revision, Snapshot


@unittest.skipUnless(os.environ.get("BACKEND_TEST_DATABASE_URL"), "Set a loopback PostgreSQL BACKEND_TEST_DATABASE_URL")
class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value=os.environ["BACKEND_TEST_DATABASE_URL"]
        with patch.dict(os.environ,DATABASE_URL=value):
            cls.admin=engine_from_env()
        cls.schema="test_backend_"+uuid.uuid4().hex
        with cls.admin.begin() as c:c.execute(text(f'CREATE SCHEMA {cls.schema}'))
        cls.engine=create_engine(value,connect_args={"options":f"-csearch_path={cls.schema}"})
        with cls.engine.begin() as c:
            cfg=Config("alembic.ini");cfg.attributes["connection"]=c
            command.upgrade(cfg,"head")
        cls.bundle=validate_bundle(ROOT,"docs/examples/dataset-manifest.json")
        activate_bundle(cls.engine,cls.bundle)
        cls.client=TestClient(create_app(cls.engine),raise_server_exceptions=False)

    @classmethod
    def tearDownClass(cls):
        cls.client.close();cls.engine.dispose()
        with cls.admin.begin() as c:c.execute(text(f'DROP SCHEMA {cls.schema} CASCADE'))
        cls.admin.dispose()

    def test_real_import_counts_and_idempotence(self):
        activate_bundle(self.engine,self.bundle)
        with Session(self.engine) as s:
            self.assertEqual(s.scalar(select(func.count()).select_from(Snapshot).where(Snapshot.version==self.bundle["version"])),9321)
            self.assertEqual(s.scalar(select(func.count()).select_from(Comparison).where(Comparison.version==self.bundle["version"])),7202)
            self.assertEqual(s.get(ActiveDataset,1).version,self.bundle["version"])

    def test_duplicate_keys_rollback_after_insert(self):
        bad=copy.deepcopy(self.bundle);bad["version"]="a"*64
        bad["snapshots"]=[bad["snapshots"][0],bad["snapshots"][0]]
        with self.assertRaises(IntegrityError):activate_bundle(self.engine,bad)
        with Session(self.engine) as s:
            self.assertIsNone(s.get(Revision,bad["version"]))
            self.assertEqual(s.get(ActiveDataset,1).version,self.bundle["version"])

    def test_comparison_failure_rolls_back_snapshots_and_pointer(self):
        bad=copy.deepcopy(self.bundle);bad["version"]="b"*64
        bad["snapshots"]=bad["snapshots"][:1]
        bad["comparisons"]=bad["comparisons"][:1]
        with self.assertRaises(IntegrityError):activate_bundle(self.engine,bad)
        with Session(self.engine) as s:
            self.assertEqual(s.scalar(select(func.count()).select_from(Snapshot).where(Snapshot.version==bad["version"])),0)
            self.assertIsNone(s.get(Revision,bad["version"]))
            self.assertEqual(s.get(ActiveDataset,1).version,self.bundle["version"])

    def test_prior_revision_remains_queryable(self):
        alternate=copy.deepcopy(self.bundle);alternate["version"]="c"*64
        alternate["snapshots"]=[next(r for r in alternate["snapshots"] if r["project_code"]=="701530" and r["report_month"]=="2026-07")]
        alternate["comparisons"]=[]
        try:
            activate_bundle(self.engine,alternate)
            current=self.client.get("/api/v1/projects?report_month=2026-07").json()
            self.assertEqual(current["meta"]["dataset_version"],alternate["version"])
            old=self.client.get("/api/v1/projects?report_month=2026-07&dataset_version="+self.bundle["version"]).json()
            self.assertEqual(old["meta"]["pagination"]["total_items"],1775)
        finally:activate_bundle(self.engine,self.bundle)

    def test_corrupt_manifest_never_changes_active(self):
        from tempfile import NamedTemporaryFile
        manifest=json.loads(self.bundle["manifest"])
        manifest["source_reports"][0]["sha256"]="0"*64
        with NamedTemporaryFile(suffix=".json",mode="w",encoding="utf-8",delete=False,dir=ROOT/"data/validation") as f:
            json.dump(manifest,f,sort_keys=True,separators=(",",":"),ensure_ascii=True)
            path=Path(f.name)
        try:
            with self.assertRaisesRegex(ValueError,"Source manifest mismatch"):
                validate_bundle(ROOT,path)
        finally:
            path.unlink()
        with Session(self.engine) as s:self.assertEqual(s.get(ActiveDataset,1).version,self.bundle["version"])

    def test_failed_audit_never_changes_active(self):
        original=Path.read_text
        def read(path,*args,**kwargs):
            content=original(path,*args,**kwargs)
            if path.name=="monthly_history.json":
                a=json.loads(content);a["status"]="failed";return json.dumps(a)
            return content
        with patch.object(Path,"read_text",read):
            with self.assertRaisesRegex(ValueError,"failed or partial"):
                validate_bundle(ROOT,"docs/examples/dataset-manifest.json")
        with Session(self.engine) as s:self.assertEqual(s.get(ActiveDataset,1).version,self.bundle["version"])

    def test_database_immutability(self):
        for table in ["dataset_revisions","monthly_snapshots","adjacent_comparisons"]:
            with self.assertRaises(DBAPIError),self.engine.begin() as c:
                c.execute(text(f"DELETE FROM {table}"))
            with self.assertRaises(DBAPIError),self.engine.begin() as c:
                c.execute(text(f"TRUNCATE {table} CASCADE"))

    def test_repeated_filters_and_intersection(self):
        response=self.client.get("/api/v1/projects",params=[("report_month","2026-08"),("project_code","701530"),("project_code","400298"),("sector","Railways")])
        self.assertEqual(response.status_code,200)
        self.assertEqual([s["project_code"] for s in response.json()["data"]],["400298"])
        self.assertEqual(response.json()["meta"]["filters"]["project_code"],["400298","701530"])
        response=self.client.get("/api/v1/projects",params={"report_month":"2026-08","state":"Madhya Pradesh"})
        self.assertNotIn("701530",[s["project_code"] for s in response.json()["data"]])

    def test_pagination_stable_and_empty(self):
        first=self.client.get("/api/v1/projects?report_month=2026-08&page_size=2").json()
        second=self.client.get("/api/v1/projects?report_month=2026-08&page_size=2&page=2").json()
        codes=[r["project_code"] for r in first["data"]+second["data"]]
        self.assertEqual(codes,sorted(set(codes)))
        self.assertEqual(first["meta"]["pagination"],dict(page=1,page_size=2,total_items=1731,total_pages=866))
        self.assertEqual(self.client.get("/api/v1/projects?report_month=2026-08&page=999").json()["data"],[])
        empty=self.client.get("/api/v1/projects?report_month=2026-08&sector=no-such-sector").json()
        self.assertEqual(empty["meta"]["pagination"]["total_pages"],0)

    def test_missing_zero_raw_and_provenance_match_example(self):
        actual=self.client.get("/api/v1/projects/701530?report_month=2026-07")
        expected=json.loads(Path("docs/examples/project-data-contract.json").read_text(encoding="utf-8"))["examples"]["project_detail"]["response"]
        self.assertEqual(actual.status_code,200)
        self.assertEqual(actual.json()["data"],expected["data"])
        values=actual.json()["data"]["values"]
        self.assertIsNone(values["approval_date"]["normalized"])
        self.assertEqual(values["physical_progress_pct"]["normalized"],"0")
        august=self.client.get("/api/v1/projects/701530?report_month=2026-08").json()
        self.assertEqual(august["data"]["values"]["revised_cost_rs_crore"]["raw"],"0.00")
        self.assertIsNone(august["data"]["temporal"]["publication_date"])
        self.assertTrue(august["warnings"])
        medical=self.client.get("/api/v1/projects/706965?report_month=2026-05").json()
        self.assertEqual(medical["data"]["values"]["original_target_doc"]["missing_reason"],"source_blank")

    def test_literal_search(self):
        response=self.client.get("/api/v1/projects",params={"report_month":"2026-08","q":"%"})
        self.assertEqual(response.status_code,200)
        self.assertTrue(all("%" in r["identity"]["project_name"] for r in response.json()["data"]))
        response=self.client.get("/api/v1/projects",params={"report_month":"2026-08","q":"ken-betwa"})
        self.assertIn("701530",[r["project_code"] for r in response.json()["data"]])

    def test_invalid_requests_have_contract_envelopes(self):
        for query in ["", "report_month=August", "report_month=2026-13", "report_month=2026-08&page=0", "report_month=2026-08&page_size=101", "report_month=2026-08&bogus=1", "report_month=2026-08&q=", "report_month=2026-08&dataset_version=bad"]:
            with self.subTest(query=query):
                r=self.client.get("/api/v1/projects?"+query)
                self.assertEqual(r.status_code,422)
                self.assertEqual(r.json()["error"]["code"],"VALIDATION_ERROR")
                self.assertEqual(set(r.json()),{"error","meta"})
        self.assertEqual(self.client.get("/api/v1/projects/701530?report_month=2026-07&page=2").status_code,422)
        expected=json.loads(Path("docs/examples/project-data-contract.json").read_text(encoding="utf-8"))["examples"]["validation_error"]["response"]
        self.assertEqual(self.client.get("/api/v1/projects?report_month=August").json(),expected)

    def test_no_active_dataset_and_internal_errors(self):
        empty_schema="test_empty_"+uuid.uuid4().hex
        with self.admin.begin() as c:c.execute(text(f"CREATE SCHEMA {empty_schema}"))
        empty_engine=create_engine(os.environ["BACKEND_TEST_DATABASE_URL"],connect_args={"options":f"-csearch_path={empty_schema}"})
        try:
            with empty_engine.begin() as c:
                cfg=Config("alembic.ini");cfg.attributes["connection"]=c;command.upgrade(cfg,"head")
            with TestClient(create_app(empty_engine),raise_server_exceptions=False) as client:
                r=client.get("/api/v1/projects?report_month=2026-08")
                self.assertEqual(r.status_code,503)
                self.assertEqual(r.json()["error"]["code"],"DATASET_NOT_VALIDATED")
            with patch("backend.app.Session",side_effect=RuntimeError("sensitive-internal-text")):
                r=self.client.get("/api/v1/projects?report_month=2026-08")
                self.assertEqual(r.status_code,500)
                self.assertNotIn("sensitive-internal-text",r.text)
                self.assertEqual(r.json()["error"]["code"],"INTERNAL_ERROR")
        finally:
            empty_engine.dispose()
            with self.admin.begin() as c:c.execute(text(f"DROP SCHEMA {empty_schema} CASCADE"))

    def test_unavailable_reports_revisions_and_absent_snapshot(self):
        for url,code in [("/api/v1/projects?report_month=2026-09","REPORT_NOT_AVAILABLE"),
                         ("/api/v1/projects?report_month=2026-08&dataset_version="+"f"*64,"DATASET_NOT_FOUND"),
                         ("/api/v1/projects/unknown?report_month=2026-08","PROJECT_NOT_OBSERVED")]:
            r=self.client.get(url);self.assertEqual(r.status_code,404);self.assertEqual(r.json()["error"]["code"],code)
        pinned=self.client.get("/api/v1/projects?report_month=2026-08&dataset_version="+self.bundle["version"])
        self.assertEqual(pinned.status_code,200)


class ConfigurationTests(unittest.TestCase):
    def test_nonloopback_database_rejected(self):
        with patch.dict(os.environ,DATABASE_URL="postgresql+psycopg://u:CHANGE_ME@example.com/db"):
            with self.assertRaises(ValueError):engine_from_env()


class ArchiveTests(unittest.TestCase):
    def test_archive_never_overwrites_prior_bytes(self):
        from tempfile import TemporaryDirectory
        from backend.import_dataset import archive_bundle
        with TemporaryDirectory() as tmp:
            first=dict(version="a"*64,artifacts={"report.pdf":b"source one"})
            second=dict(version="b"*64,artifacts={"report.pdf":b"source two"})
            archive_bundle(first,tmp);archive_bundle(second,tmp)
            archive_bundle(first,tmp)
            self.assertEqual((Path(tmp)/first["version"]/"report.pdf").read_bytes(),b"source one")
            with self.assertRaisesRegex(ValueError,"never overwrite"):
                archive_bundle(dict(version=first["version"],artifacts={"report.pdf":b"changed"}),tmp)
