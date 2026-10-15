"""Recover the catalog's exact public PAIMANA reports; never accept changed bytes."""
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
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


def main():
    catalog = json.loads((ROOT / "config/monthly_reports.json").read_text())
    url = ORIGIN + "/ReportPage/Report?fyear=N&month=0&quater=0&reportType=F"
    with urllib.request.urlopen(url, timeout=45) as response:
        parser = Links(); parser.feed(json.load(response)["html"])
    for report in catalog["reports"]:
        target = ROOT / report["pdf"]
        expected = report["source_sha256"]
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                raise ValueError(f"Existing source differs from reviewed hash: {target.name}")
            print(f"Verified existing {target.name}"); continue
        candidates = [link for link in parser.links if Path(report["pdf"]).name in unescape(link)]
        if len(candidates) != 1:
            raise ValueError(f"Expected one exact public source link for {target.name}")
        source = urllib.parse.urljoin(ORIGIN + "/ReportPage/", candidates[0].replace("\\", "/"))
        if urllib.parse.urlsplit(source).netloc != urllib.parse.urlsplit(ORIGIN).netloc:
            raise ValueError("Unexpected source host")
        with urllib.request.urlopen(source, timeout=90) as response:
            content = response.read()
        if not content.startswith(b"%PDF") or hashlib.sha256(content).hexdigest() != expected:
            raise ValueError(f"Published bytes differ from reviewed source: {target.name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".pdf.tmp")
        temporary.write_bytes(content); temporary.replace(target)
        print(f"Recovered and verified {target.name}")


if __name__ == "__main__":
    main()
