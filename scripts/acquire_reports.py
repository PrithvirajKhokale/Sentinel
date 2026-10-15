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


def main():
    catalog = json.loads((ROOT / "config/monthly_reports.json").read_text())
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(recover, catalog["reports"]))


if __name__ == "__main__":
    main()
