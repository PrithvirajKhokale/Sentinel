"""Recover exact public PAIMANA reports; every accepted byte is hash checked."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://paimana-proj.mospi.gov.in"


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.extend(value for key, value in attrs if key == "href" and value)


def read_source(url, timeout=40):
    # Retry transient transport failures, never changed content or failed hash checks.
    for attempt in range(2):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Sentinel source validation/1.0"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 1:
                raise
            time.sleep(1)


def recover(report, root=ROOT):
    target = root / report["pdf"]
    expected = report["source_sha256"]
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Existing source differs from reviewed hash: {target.name}")
        print(f"Verified existing {target.name}", flush=True)
        return
    year, month = map(int, report["report_month_iso"].split("-"))
    fiscal_start = year if month >= 4 else year - 1
    fiscal_year = f"{fiscal_start}-{str(fiscal_start + 1)[-2:]}"
    # Published archive paths are the same files referenced by the portal's ViewPdf links.
    source = f"{ORIGIN}/Content/ArchiveReport/flash/{fiscal_year}/{urllib.parse.quote(target.name)}"
    print(f"Recovering reviewed source {target.name}", flush=True)
    try:
        content = read_source(source)
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        # Compatibility fallback if the publisher moves the static archive path.
        listing = ORIGIN + "/ReportPage/Report?fyear=N&month=0&quater=0&reportType=F"
        parser = Links(); parser.feed(json.loads(read_source(listing))["html"])
        candidates = [link for link in parser.links if target.name in unescape(link)]
        if len(candidates) != 1:
            raise ValueError(f"Expected one exact public source link for {target.name}")
        source = urllib.parse.urljoin(ORIGIN + "/ReportPage/", candidates[0].replace("\\", "/"))
        if urllib.parse.urlsplit(source).netloc != urllib.parse.urlsplit(ORIGIN).netloc:
            raise ValueError("Unexpected source host")
        content = read_source(source)
    if not content.startswith(b"%PDF") or hashlib.sha256(content).hexdigest() != expected:
        raise ValueError(f"Published bytes differ from reviewed source: {target.name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".pdf.tmp")
    temporary.write_bytes(content); temporary.replace(target)
    print(f"Recovered and verified {target.name}", flush=True)


import io
import zipfile

# Immutable public source bundle prepared from the five reviewed PDFs.
# Publish the verified archive as this GitHub Release asset before deploying.
BUNDLE_URL = (
    "https://github.com/PrithvirajKhokale/Sentinel/releases/download/"
    "source-reports-2026-v1/sentinel-source-reports-2026.zip"
)
BUNDLE_SHA256 = "a5da5970b6156935e93a20ef8a31e1aa16c5e805cbf21562ab27371c544f1680"


def recover_bundle(reports, root=ROOT):
    """Recover the exact five reviewed PDFs from one immutable release asset.

    Verify the archive and every member before writing any new source files.
    Existing files are also hash checked; no alternate/changed data is accepted.
    """
    names = [Path(report["pdf"]).name for report in reports]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate source filenames in report catalog")
    pending = []
    for report in reports:
        target = root / report["pdf"]
        if target.is_file():
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            if actual != report["source_sha256"]:
                raise ValueError(f"Existing source differs from reviewed hash: {target.name}")
            print(f"Verified existing {target.name}", flush=True)
        else:
            pending.append(report)
    if not pending:
        return

    print("Downloading pinned, hash-verified Sentinel source archive", flush=True)
    content = read_source(BUNDLE_URL, timeout=120)
    if hashlib.sha256(content).hexdigest() != BUNDLE_SHA256:
        raise ValueError("Source archive differs from pinned SHA-256")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as bundle:
            if sorted(bundle.namelist()) != sorted(names):
                raise ValueError("Source archive does not contain the exact reviewed file list")
            verified = {}
            for report in reports:
                name = Path(report["pdf"]).name
                raw = bundle.read(name)
                if not raw.startswith(b"%PDF") or hashlib.sha256(raw).hexdigest() != report["source_sha256"]:
                    raise ValueError(f"Source archive member differs from reviewed hash: {name}")
                verified[name] = raw
    except zipfile.BadZipFile as exc:
        raise ValueError("Source archive is not a valid ZIP") from exc

    for report in pending:
        target = root / report["pdf"]
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".pdf.tmp")
        temporary.write_bytes(verified[target.name])
        temporary.replace(target)
        print(f"Recovered and verified {target.name}", flush=True)


def main():
    catalog = json.loads((ROOT / "config/monthly_reports.json").read_text())
    recover_bundle(catalog["reports"], ROOT)


if __name__ == "__main__":
    main()
