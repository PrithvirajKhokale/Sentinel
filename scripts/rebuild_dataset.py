"""Reproduce all reviewed monthly outputs and history without changing the manifest."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    catalog = json.loads((ROOT / "config/monthly_reports.json").read_text())
    for report in catalog["reports"]:
        args = [sys.executable, "scripts/extract_ongoing_projects.py", report["pdf"],
                "--all", "--output", report["csv"], "--validation", report["audit"]]
        for reference in report["references"]:
            args.extend(["--reference", reference])
        subprocess.run(args, cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/build_monthly_history.py"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
