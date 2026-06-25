# President's Cup des SRV — history

Interactive chart of the annual *President's Cup* club standings (2006–2026).
(Built with Claude Code.)

## Data pipeline

The official standings are PDFs in `raw/` (`pc-YYYY.pdf`). Some years are text
PDFs; 2010–2012 and 2014–2019 are scanned images requiring OCR. The CSV is
produced in two reproducible, committed steps:

1. **`extract_raw.py`** → `raw-extract.tsv` (year, raw club name, points).
   Uses the PDF text layer when present, else OCR (poppler + tesseract).
   `raw-extract.tsv` is committed so the next step needs no OCR.

2. **`build_history.py`** → `pc-history.csv`. Maps every raw/OCR club spelling
   onto canonical names (matching `../pde/pde-history.csv` where a club appears
   there) and sorts each year by points. Fails loudly on any unmapped spelling.

```sh
python3 extract_raw.py     # only when raw/ PDFs change; needs pdftotext, tesseract
python3 build_history.py   # regenerate pc-history.csv
python3 -m unittest test_build_history   # validate (run from this directory)
```

## Notes on the data

- Rank is derived in the chart from points, so the CSV stores only points.
- A few clubs appear only in the President's Cup (not in PDE): Seeclub Horgen,
  Regattaverein Luzern, Club Aviron Vallée de Joux, Association Romande
  d'Aviron, Kantonsschule Wettingen, ROZ (Ruderverband Oberer Zürichsee), and
  UCL (acronym in the 2014 results; club identity unconfirmed).
