"""Source acquisition stays fail-closed without depending on the portal listing."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.acquire_reports import recover


class SourceAcquisitionTests(unittest.TestCase):
    def report(self, content):
        return {"pdf":"data/raw/FlashReport_April2026.pdf", "report_month_iso":"2026-04",
                "source_sha256":hashlib.sha256(content).hexdigest()}

    def test_verified_existing_source_never_uses_network(self):
        content=b"%PDF-exact"
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); report=self.report(content); p=root/report["pdf"]
            p.parent.mkdir(parents=True); p.write_bytes(content)
            with patch("scripts.acquire_reports.read_source", side_effect=AssertionError("No network")):
                recover(report, root)

    def test_static_archive_succeeds_without_dynamic_listing(self):
        content=b"%PDF-exact"
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); report=self.report(content)
            with patch("scripts.acquire_reports.read_source", return_value=content) as read:
                recover(report, root)
                self.assertEqual(read.call_count,1)
                self.assertIn('/Content/ArchiveReport/flash/2026-27/FlashReport_April2026.pdf',read.call_args.args[0])
            self.assertEqual((root/report['pdf']).read_bytes(),content)


    def test_bundle_recovery_checks_full_archive_and_skips_network_for_cached_files(self):
        import io
        import zipfile
        from scripts.acquire_reports import recover_bundle
        files = {
            "FlashReport_April2026.pdf": b"%PDF-april-exact",
            "FlashReport_May2026.pdf": b"%PDF-may-exact",
        }
        reports = [
            {"pdf": "data/raw/" + name, "source_sha256": hashlib.sha256(value).hexdigest()}
            for name, value in files.items()
        ]
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            for name, value in files.items():
                archive.writestr(name, value)
        raw = data.getvalue()
        with tempfile.TemporaryDirectory() as d, \
             patch("scripts.acquire_reports.BUNDLE_SHA256", hashlib.sha256(raw).hexdigest()), \
             patch("scripts.acquire_reports.read_source", return_value=raw) as download:
            root = Path(d)
            recover_bundle(reports, root)
            self.assertEqual(download.call_count, 1)
            for name, value in files.items():
                self.assertEqual((root / "data/raw" / name).read_bytes(), value)
            with patch("scripts.acquire_reports.read_source", side_effect=AssertionError("unexpected network")):
                recover_bundle(reports, root)

    def test_bundle_recovery_rejects_changed_member_without_writing_files(self):
        import io
        import zipfile
        from scripts.acquire_reports import recover_bundle
        expected = b"%PDF-verified"
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr("FlashReport_April2026.pdf", b"%PDF-tampered")
        raw = data.getvalue()
        reports = [self.report(expected)]
        with tempfile.TemporaryDirectory() as d, \
             patch("scripts.acquire_reports.BUNDLE_SHA256", hashlib.sha256(raw).hexdigest()), \
             patch("scripts.acquire_reports.read_source", return_value=raw):
            with self.assertRaisesRegex(ValueError, "differs"):
                recover_bundle(reports, Path(d))
            self.assertFalse((Path(d) / reports[0]["pdf"]).exists())

    def test_wrong_published_bytes_do_not_create_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report=self.report(b"%PDF-exact")
            with patch("scripts.acquire_reports.read_source",return_value=b"%PDF-revised"):
                with self.assertRaisesRegex(ValueError,'differ'):recover(report,root)
            self.assertFalse((root/report['pdf']).exists())
