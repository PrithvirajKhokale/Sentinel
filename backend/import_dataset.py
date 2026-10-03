"""Validate and archive a revision, then atomically import and activate it."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import tempfile
from sqlalchemy import insert, select
from sqlalchemy.orm import Session
from scripts.build_monthly_history import (adjacent_pair, digest, history_rows, load_catalog,
                                           load_snapshot, write_csv)
from .db import engine_from_env
from .models import ActiveDataset, Comparison, Revision, Snapshot
from .presentation import snapshot, warning

ROOT = Path(__file__).resolve().parents[1]
COMPUTATION = ["scripts/extract_ongoing_projects.py", "scripts/build_monthly_history.py",
               "scripts/compare_project_reports.py", "requirements-extraction.txt"]


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def validate_bundle(root, manifest_path):
    root = Path(root).resolve()
    checked = {}
    def checked_digest(path):
        path = Path(path).resolve()
        value = digest(path)
        if path in checked and checked[path] != value:
            raise ValueError("Artifact changed during validation")
        checked[path] = value
        return value
    def local(path):
        result = (root/path).resolve()
        if not result.is_relative_to(root):
            raise ValueError("Artifact path escapes the source workspace")
        return result
    manifest_path = Path(manifest_path)
    if not manifest_path.is_absolute():
        manifest_path = local(manifest_path)
    blob = manifest_path.read_bytes()
    m = json.loads(blob)
    if blob != json.dumps(m, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8"):
        raise ValueError("Manifest is not canonical JSON")
    if set(m) != {"manifest_version", "schema_version", "source_reports", "computation", "catalog_sha256", "references", "canonical_mappings", "outputs"}:
        raise ValueError("Unexpected manifest schema")
    if m["manifest_version"] != "1" or m["schema_version"] != "project-data-v1" or m["canonical_mappings"] != []:
        raise ValueError("Unsupported manifest/schema/mappings")
    catalog_path = local("config/monthly_reports.json")
    if checked_digest(catalog_path) != m["catalog_sha256"]:
        raise ValueError("Catalog hash mismatch")
    reports = load_catalog(catalog_path)
    sources = [dict(report_month=r["report_month_iso"], filename=Path(r["pdf"]).name, sha256=checked_digest(local(r["pdf"]))) for r in reports]
    if sources != m["source_reports"]:
        raise ValueError("Source manifest mismatch")
    expected_code = [dict(path=p, sha256=checked_digest(local(p))) for p in COMPUTATION]
    if expected_code != m["computation"] or any(checked_digest(ROOT/p) != checked_digest(local(p)) for p in COMPUTATION):
        raise ValueError("Manifest computation differs from executing validator")
    references = [dict(path=p, sha256=checked_digest(local(p))) for p in sorted({p for r in reports for p in r["references"]})]
    if references != m["references"]:
        raise ValueError("Reference hash mismatch")
    audit_path = local("data/validation/monthly_history.json")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if not (audit.get("status") == "validated_history" and audit.get("coverage_pass") is True
            and audit.get("csv_round_trip") == "PASS" and audit.get("issues") == []):
        raise ValueError("History audit is failed or partial")
    for field,path in [("catalog_sha256", catalog_path), ("history_builder_sha256",local(COMPUTATION[1])),
                       ("extractor_sha256",local(COMPUTATION[0])), ("comparison_helpers_sha256",local(COMPUTATION[2]))]:
        if audit.get(field) != checked_digest(path):
            raise ValueError("Stale history computation audit")
    snapshots = {}
    artifacts = {catalog_path, audit_path, manifest_path.resolve()}
    artifacts.update(local(p) for p in COMPUTATION)
    artifacts.update(local(p["path"]) for p in references)
    # Verify reviewed reference paths explicitly without changing process cwd.
    for r in reports:
        report = dict(r)
        for key in ("pdf", "csv", "audit"):
            report[key] = str(local(r[key]))
            artifacts.add(local(r[key]))
        report["references"] = [str(local(p)) for p in r["references"]]
        a = json.loads(local(r["audit"]).read_text(encoding="utf-8"))
        expected_refs = {str(local(p)):checked_digest(local(p)) for p in r["references"]}
        actual_refs = {str(local(p)):h for p,h in a.get("reference_sha256",{}).items()}
        if actual_refs != expected_refs:
            raise ValueError("Stale extraction reference hashes")
        # load_snapshot resolves audit reference paths against the repository root;
        # this command intentionally requires that root as its working directory.
        records, _ = load_snapshot(report)
        snapshots[r["report_month_iso"]] = records
        for key,path in [("pdf",r["pdf"]),("csv",r["csv"]),("audit",r["audit"])]:
            if audit["input_hashes"][r["report_month_iso"]][key] != checked_digest(local(path)):
                raise ValueError("History input hash mismatch")
        if audit["input_hashes"][r["report_month_iso"]]["references"] != {p:checked_digest(local(p)) for p in r["references"]}:
            raise ValueError("History reference hashes mismatch")
        artifacts.add(local(r["audit"]).with_name(Path(r["audit"]).stem+"_issues.jsonl"))
    records = history_rows(snapshots, reports)
    history = local("data/processed/monthly_history/april_august_2026_history.csv")
    if read_csv(history) != records or checked_digest(history) != m["outputs"]["history_sha256"]:
        raise ValueError("History raw/normalized snapshots differ from audited inputs")
    artifacts.add(history)
    expected_hashes = {"history":checked_digest(history)}
    comparisons = []
    with tempfile.TemporaryDirectory() as tmp:
        for before,after in zip(reports,reports[1:]):
            common,presence,_ = adjacent_pair(snapshots[before["report_month_iso"]],snapshots[after["report_month_iso"]],before,after)
            comparisons.extend(common)
            label = before["report_month_iso"]+"_"+after["report_month_iso"]
            for suffix,selected in [("changes",common),("presence",presence),
                    ("questionable",[r for r in common if r["trend_eligible"]=="False"]),
                    ("progress_decreases",[r for r in common if r["progress_status"]=="decreased"]),
                    ("expenditure_decreases",[r for r in common if r["expenditure_status"]=="decreased"])]:
                key = label+"_"+suffix
                generated = Path(tmp)/(key+".csv")
                expected_hashes[key] = write_csv(generated,selected)
                path = local("data/processed/monthly_history/"+key+".csv")
                if checked_digest(path) != expected_hashes[key]:
                    raise ValueError("Comparison does not reproduce from validated snapshots")
                artifacts.add(path)
    if audit["output_hashes"] != expected_hashes or m["outputs"] != dict(history_sha256=expected_hashes["history"], adjacent_outputs_sha256={k:v for k,v in expected_hashes.items() if k!="history"}):
        raise ValueError("Manifest/audit output hashes mismatch")
    report_warnings = []
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))["reports"]
    for r in catalog:
        for note in r.get("source_notes",[])+r.get("source_observations",[]):
            report_warnings.append(warning(note["kind"], ["revised_cost_rs_crore"] if note["kind"] == "revised_cost_reconciliation" else [], r["report_month_iso"], [note.get("source_pdf_page",note.get("source_note_pdf_page"))], note.get("text",note.get("observation")), scope="report"))
    report_warnings.append(warning("published_revised_cost_zeros", ["revised_cost_rs_crore"], "2026-08", [],
                                   "Published revised costs are literal zeros. Preserve zeros; review field comparability.", "report"))
    blobs = {str(p.relative_to(root)):p.read_bytes() for p in artifacts}
    for path,expected in checked.items():
        if path.is_relative_to(root) and path in artifacts:
            if hashlib.sha256(blobs[str(path.relative_to(root))]).hexdigest() != expected:
                raise ValueError("Artifact changed before archival")
    if blobs[str(manifest_path.resolve().relative_to(root))] != blob:
        raise ValueError("Manifest changed during validation")
    return dict(version=hashlib.sha256(blob).hexdigest(), manifest=blob.decode("utf-8"), reports=[r["report_month_iso"] for r in reports],
                warnings=report_warnings, snapshots=[snapshot(r) for r in records], comparisons=comparisons,
                artifacts=blobs)


def archive_bundle(bundle, directory):
    target = Path(directory)/bundle["version"]
    target.mkdir(parents=True, exist_ok=True)
    for name,blob in bundle["artifacts"].items():
        path = target/name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != blob:
                raise ValueError("Existing revision archive differs; never overwrite")
        else:
            with path.open("xb") as stream:
                stream.write(blob)


def activate_bundle(engine, bundle):
    # Lock one persistent pointer so concurrent import activation is serialized.
    with Session(engine) as session, session.begin():
        active = session.execute(select(ActiveDataset).where(ActiveDataset.id==1).with_for_update()).scalar_one()
        existing = session.get(Revision,bundle["version"])
        if existing:
            if existing.manifest != bundle["manifest"]:
                raise ValueError("Revision hash collision")
        else:
            session.add(Revision(version=bundle["version"], manifest=bundle["manifest"], reports=bundle["reports"], warnings=bundle["warnings"]))
            session.flush()
            payloads = [dict(version=bundle["version"], project_code=s["project_code"], report_month=s["report_month"],
                            payload=s, **s["identity"]) for s in bundle["snapshots"]]
            session.execute(insert(Snapshot),payloads)
            if bundle["comparisons"]:
                session.execute(insert(Comparison),[dict(version=bundle["version"],project_code=c["project_code"],
                    before_month=c["before_month"],after_month=c["after_month"],payload=c) for c in bundle["comparisons"]])
        active.version = bundle["version"]
    return bundle["version"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="docs/examples/dataset-manifest.json")
    parser.add_argument("--archive-dir", default="data/revisions")
    args = parser.parse_args()
    if Path.cwd().resolve() != ROOT:
        parser.error("Run this command from the repository root")
    bundle = validate_bundle(ROOT,args.manifest)
    archive_bundle(bundle,args.archive_dir)
    version = activate_bundle(engine_from_env(),bundle)
    print(json.dumps(dict(activated=version,snapshots=len(bundle["snapshots"]),comparisons=len(bundle["comparisons"]))))


if __name__ == "__main__":
    main()
