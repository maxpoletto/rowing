#!/usr/bin/env python3
"""Extract raw (year, club, points) rows from the President's Cup PDFs.

For each raw/pc-YYYY.pdf:
  * use the PDF text layer (pdftotext -layout) when present;
  * otherwise OCR the page (pdftoppm @300dpi + tesseract, psm 6).
The result is written to raw-extract.tsv (tab-separated: year, raw_club, points)
and is committed so that normalization (build_history.py) is reproducible
without re-running OCR.

Requires the poppler tools (pdftotext, pdftoppm) and tesseract on PATH.

Parsing is robust to:
  * single-column and the 2009 two-column layout,
  * 'Punkt' vs 'Punkte',
  * OCR-mangled rank numbers ('1.' -> 'Al.', 'ts', 'iP', ...),
  * narrative lines that mention points (the longest record run wins).
"""
import os
import re
import subprocess
import sys
import tempfile

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw")
OUT = os.path.join(os.path.dirname(__file__), "raw-extract.tsv")
OCR_DPI = 300

PTS = re.compile(r"(\d+)\s+Punkt(?:e)?\b")
# Leading numeric rank, e.g. '1.', '12)', '3:'.
NUM_RANK = re.compile(r"^\s*\d+\s*[.\):;,]?\s*")
# OCR-mangled rank: a 1-3 char alnum token + optional punct, then >=2 spaces.
# Intra-club word gaps are single spaces, so real club names are not stripped.
OCR_RANK = re.compile(r"^[\dA-Za-z]{1,3}[.\):;,]?\s{2,}")


def clean_club(chunk):
    c = chunk.strip()
    c = NUM_RANK.sub("", c)
    c = OCR_RANK.sub("", c)
    c = re.sub(r"\s+", " ", c).strip(" .,:;")
    return c


def line_records(line):
    out, prev = [], 0
    for m in PTS.finditer(line):
        club = clean_club(line[prev:m.start()])
        prev = m.end()
        if club:
            out.append((club, int(m.group(1))))
    return out


def parse_text(text):
    """Return records of the longest contiguous run of record lines."""
    runs, current = [], []
    for line in text.splitlines():
        if not line.strip():
            continue  # blank lines are transparent
        recs = line_records(line)
        if recs:
            current.extend(recs)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return max(runs, key=len) if runs else []


def pdf_text(path):
    return subprocess.run(
        ["pdftotext", "-layout", path, "-"],
        capture_output=True, text=True, check=True,
    ).stdout


def ocr_text(path):
    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, "page")
        subprocess.run(["pdftoppm", "-r", str(OCR_DPI), "-png", path, base],
                       check=True, capture_output=True)
        png = sorted(f for f in os.listdir(tmp) if f.endswith(".png"))[0]
        return subprocess.run(
            ["tesseract", os.path.join(tmp, png), "-", "--psm", "6",
             "-c", "preserve_interword_spaces=1"],
            capture_output=True, text=True, check=True,
        ).stdout


def main():
    rows = []
    for fn in sorted(os.listdir(RAW_DIR)):
        m = re.match(r"pc-(\d{4})\.pdf$", fn)
        if not m:
            continue
        year, path = m.group(1), os.path.join(RAW_DIR, fn)
        text = pdf_text(path)
        if not text.strip():
            text = ocr_text(path)
        recs = parse_text(text)
        if not recs:
            print(f"WARNING: no records parsed for {fn}", file=sys.stderr)
        for club, pts in recs:
            rows.append((year, club, pts))
    with open(OUT, "w", encoding="utf-8") as fh:
        for year, club, pts in rows:
            fh.write(f"{year}\t{club}\t{pts}\n")
    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
