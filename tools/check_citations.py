"""
Check every citation's metadata against the publisher's own record.

    python tools/check_citations.py            # report
    python tools/check_citations.py --strict   # exit 1 on any mismatch

WHAT THIS IS AND IS NOT
-----------------------
This asks CrossRef and PubMed whether each reference exists and whether the
year, volume and pages in evidence.py agree with the publisher's record. It
catches the specific failure that gets noticed in review: a citation that has
drifted a volume or transposed a page range.

It does NOT read the paper. It cannot tell you whether the source supports the
claim made from it - only a person can, and evidence.py keeps a separate flag
for that. The two are deliberately different fields, because collapsing them
would let a machine lookup masquerade as scholarship.

Two sources cannot be checked this way and both are recorded as such rather
than quietly skipped: ISO 9613-1, whose publisher blocks automated access, and
Wollack 1963, which predates DOIs in a journal that no longer exists. The
second is the one most worth a human's time.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gaukavach import evidence as ev  # noqa: E402

UA = "gaukavach-citation-check/1.0 (pre-submission metadata check)"


def _run(args: list[str]) -> str:
    """Bytes in, safe text out. Publisher pages carry bytes that the console
    encoding cannot represent, and text=True dies on them mid-read."""
    r = subprocess.run(args, capture_output=True)
    return (r.stdout or b"").decode("utf-8", "replace")


def _get(url: str) -> dict | None:
    try:
        return json.loads(_run(["curl", "-s", "--max-time", "25", url,
                                "-H", f"User-Agent: {UA}"]))
    except Exception:
        return None


def by_doi(doi: str) -> dict | None:
    d = _get(f"https://api.crossref.org/works/{doi}")
    return d.get("message") if isinstance(d, dict) else None


def title_of(citation: str) -> str:
    """The title is what sits between the year parenthesis and the journal."""
    m = re.search(r"\)\.\s*(.+?)\.\s+[A-Z]", citation)
    return m.group(1) if m else citation


def by_title(citation: str) -> dict | None:
    title = title_of(citation)
    q = "+".join(re.sub(r"[^A-Za-z0-9 ]", " ", title).split()[:14])
    d = _get(f"https://api.crossref.org/works?query.bibliographic={q}&rows=5")
    if not d:
        return None
    key = " ".join(title.lower().split()[:5])
    for item in d.get("message", {}).get("items", []):
        got = (item.get("title") or [""])[0].lower()
        if key and key in got:
            return item
    return None


def web_source(url: str, must_contain: str) -> bool | None:
    """For standards and agency pages there is no DOI - check the page itself."""
    nl = chr(10)
    out = _run(["curl", "-s", "-L", "--max-time", "25", "-w", nl + "%{http_code}",
                url, "-H", f"User-Agent: {UA}"])
    body, _, code = out.rpartition(nl)
    if code.strip() != "200":
        return None                      # blocked or gone; say so, do not guess
    return must_contain.lower() in body.lower()


def by_pubmed(pmid: str) -> dict | None:
    d = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
             f"?db=pubmed&id={pmid}&retmode=json")
    if not isinstance(d, dict):
        return None
    try:
        r = d["result"][pmid]
    except Exception:
        return None
    return {"title": [r.get("title", "")],
            "container-title": [r.get("fulljournalname", "")],
            "volume": r.get("volume"), "page": r.get("pages"),
            "issued": {"date-parts": [[int(r.get("pubdate", "0")[:4] or 0)]]}}


def agrees(citation: str, md: dict) -> tuple[bool, str]:
    """Do the year, volume and first page in our string match the record?"""
    year = str(md.get("issued", {}).get("date-parts", [["?"]])[0][0])
    vol = str(md.get("volume") or "")
    page = str(md.get("page") or "")
    bad = []
    if year and year not in citation:
        bad.append(f"year {year}")
    if vol and not re.search(rf"\b{re.escape(vol)}\b", citation):
        bad.append(f"volume {vol}")
    if page:
        first = page.split("-")[0]
        if first and first not in citation:
            bad.append(f"page {first}")
    return (not bad), ", ".join(bad)


def main() -> int:
    strict = "--strict" in sys.argv
    ok = mismatch = unreachable = 0

    print(f"{'src':<5}{'result':<12}detail")
    print("-" * 74)
    for k, s in ev.SOURCES.items():
        if not s.url and "Journal of Auditory Research" not in s.citation:
            continue
        if s.first_party_verified:
            continue

        md = None
        doi = re.search(r"10\.\d{4,9}/[^\s\"']+", s.url or "")
        pmid = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", s.url or "")
        if doi:
            md = by_doi(doi.group(0).rstrip("."))
        elif pmid:
            md = by_pubmed(pmid.group(1))
        if md is None and not (doi or pmid):
            # a standard or an agency page, not a journal article
            if "iso.org" in (s.url or "") or "osha.gov" in (s.url or ""):
                needle = "9613" if "iso.org" in s.url else "ultrasound"
                hit = web_source(s.url, needle)
                time.sleep(0.35)
                if hit is True:
                    ok += 1
                    print(f"{k:<5}{'PAGE OK':<12}publisher page names {needle!r}")
                elif hit is False:
                    mismatch += 1
                    print(f"{k:<5}{'MISMATCH':<12}page does not mention {needle!r}")
                else:
                    unreachable += 1
                    print(f"{k:<5}{'BLOCKED':<12}publisher refuses automated access")
                continue
            md = by_title(s.citation)
        time.sleep(0.35)

        if md is None:
            unreachable += 1
            print(f"{k:<5}{'NOT INDEXED':<12}no public record found; needs a human")
            continue
        good, why = agrees(s.citation, md)
        if good:
            ok += 1
            print(f"{k:<5}{'MATCH':<12}{(md.get('title') or [''])[0][:56]}")
        else:
            mismatch += 1
            print(f"{k:<5}{'MISMATCH':<12}registry disagrees on {why}")

    print()
    print(f"{ok} match, {mismatch} mismatch, {unreachable} not indexed")
    print()
    print("A match means the reference exists and its year, volume and pages are")
    print("right. It does NOT mean anyone has read it - see first_party_verified,")
    print("which only a person can set.")
    return 1 if (strict and mismatch) else 0


if __name__ == "__main__":
    raise SystemExit(main())
