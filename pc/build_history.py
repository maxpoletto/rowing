#!/usr/bin/env python3
"""Normalize raw-extract.tsv into pc-history.csv.

Reads the committed raw extraction (year, raw_club, points) and maps every raw
club spelling -- including OCR variants (Zurich/Ziirich, Kisnacht, ...) and
historical name forms -- onto the canonical club names, matching the short/long
names used in ../pde/pde-history.csv wherever a club appears there.

Output columns match pde-history.csv: Year,ClubLongName,ClubShortName,Points
sorted per year by points descending (ties broken by club name).
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(__file__)
RAW = os.path.join(HERE, "raw-extract.tsv")
OUT = os.path.join(HERE, "pc-history.csv")

# Canonical short -> long name. Shared clubs use the exact PDE names; the few
# PC-only clubs (not in pde-history.csv) are marked.
CLUBS = {
    "Aviron Romand Zürich": "Aviron Romand Zürich",
    "Basler RC": "Basler Ruder-Club",
    "Belvoir RC Zürich": "Belvoir Ruderclub Zürich",
    "CA Vésenaz": "Club Aviron Vésenaz",
    "CA Vevey": "Club Aviron Vevey",
    "CA Ville Fribourg": "Club Aviron Ville Fribourg",
    "CC Lugano": "Club Canottieri Lugano",
    "Forward RC Morges": "Forward Rowing Club Morges",
    "Grasshopper RC Zürich": "Grasshopper Ruderclub Zürich",
    "Lausanne-Sports SA": "Lausanne-Sports Section Aviron",
    "Nordiska Zürich": "Nordiska Roddföreningen Zürich",
    "Polytechniker RC Zürich": "Polytechniker Ruderclub Zürich",
    "RC Aarburg": "Ruderclub Aarburg",
    "RC Baden": "Ruderclub Baden",
    "RC Bern": "Rowing Club Bern",
    "RC Blauweiss Basel": "Ruderclub Blauweiss Basel",
    "RC Cham": "Ruderclub Cham",
    "RC Erlenbach": "Ruderclub Erlenbach",
    "RC Greifensee": "Ruderclub Greifensee",
    "RC Hallwilersee": "Ruderclub Hallwilersee",
    "RC Kaufleuten Zürich": "Ruderclub Kaufleuten Zürich",
    "RC Kreuzlingen": "Ruderclub Kreuzlingen",
    "RC Lausanne": "Rowing Club Lausanne",
    "RC Olten": "Ruderclub Olten",
    "RC Rapperswil-Jona": "Ruderclub Rapperswil-Jona",
    "RC Reuss Luzern": "Ruderclub Reuss Luzern",
    "RC Sarnen": "Ruderclub Sarnen",
    "RC Schaffhausen": "Ruderclub Schaffhausen",
    "RC Thalwil": "Ruderclub Thalwil",
    "RC Uster": "Ruderclub Uster",
    "RC Wohlensee": "Ruderclub Wohlensee",
    "RC Zürich": "Ruderclub Zürich",
    "RG Zürich": "Rudergesellschaft Zürich",
    "SA Fribourg": "Société d'Aviron Fribourg",
    "SC Arbon": "Seeclub Arbon",
    "SC Biel": "Seeclub Biel",
    "SC Küsnacht": "Seeclub Küsnacht",
    "SC Locarno": "Società Canottieri Locarno",
    "SC Luzern": "Seeclub Luzern",
    "SC Richterswil": "Seeclub Richterswil",
    "SC Sempach": "Seeclub Sempach",
    "SC Stäfa": "Seeclub Stäfa",
    "SC Stansstad": "Seeclub Stansstad",
    "SC Sursee": "Seeclub Sursee",
    "SC Wädenswil": "Seeclub Wädenswil",
    "SC Zug": "See-Club Zug",
    "SC Zürich": "Seeclub Zürich",
    "SN Genève SA": "Société Nautique de Genève Section Aviron",
    "SN Neuchâtel": "Société Nautique de Neuchâtel",
    "SN Étoile Bienne": "Société Nautique Étoile Bienne",
    "Solothurner RC": "Solothurner Ruderclub",
    "Union Nautique Yverdon": "Union Nautique Yverdon",
    # PC-only clubs (do not appear in pde-history.csv):
    "ARA": "Association Romande d'Aviron",
    "CA Vallée de Joux": "Club Aviron Vallée de Joux",
    "KS Wettingen": "Kantonsschule Wettingen",
    "Regattaverein Luzern": "Regattaverein Luzern",
    "ROZ": "Ruderverband Oberer Zürichsee",
    "SC Horgen": "Seeclub Horgen",
    "UCL": "UCL",  # unexpanded: club identity unknown (per source, 2014)
}

# Canonical short -> the pre()-normalized raw spellings seen in the PDFs.
VARIANTS = {
    "Aviron Romand Zürich": ["Aviron Romand Zürich", "Aviron Romand Zurich",
                             "Aviron Romand Ziirich"],
    "Basler RC": ["Basler RC", "Basler Ruder-Club"],
    "Belvoir RC Zürich": ["Belvoir RC Zürich", "Belvoir RC Zurich",
                          "Belvoir RC Zirich", "RC Belvoir Zürich",
                          "Belvoir Ruderclub Zürich"],
    "CA Vésenaz": ["CA Vésenaz", "CA Vesenaz", "Club Aviron Vésenaz",
                   "Club d'Aviron Vésenaz", "Club d'Aviron Vesenaz",
                   "Club d'aviron Vésenaz"],
    "CA Vevey": ["CA Vevey", "CA Aviron Vevey", "Club Aviron Vevey",
                 "Club de l'Aviron Vevey", "Club d'Aviron Vevey",
                 "Club d'aviron Vevey"],
    "CA Ville Fribourg": ["CA Ville Fribourg", "Club Aviron Ville Fribourg"],
    "CC Lugano": ["CC Lugano", "Club Canottieri Lugano"],
    "Forward RC Morges": ["FRC Morges", "Forward RC Morges",
                          "Forward Rowing Club Morges", "Forward Morges"],
    "Grasshopper RC Zürich": ["Grasshopper RC Zürich", "Grasshopper Club Zürich",
                              "Grasshopper Club Zurich", "Grasshopper Club Zirich",
                              "Grasshopper Club Ziirich", "GC Zürich"],
    "Lausanne-Sports SA": ["Lausanne Sports", "Lausanne Sport",
                           "Lausanne Sports Aviron", "Lausanne-Sports Aviron",
                           "Lausanne Sports Section Aviron"],
    "Nordiska Zürich": ["Nordiska Zürich", "Nordiska Zurich",
                        "Nordiska Roddföreningen Zürich"],
    "Polytechniker RC Zürich": ["Polytechniker RC Zürich", "Polytechniker RC Zurich",
                                "Polytechniker RC", "Polytechniker Ruderclub Zürich",
                                "Polytechniker RC Ziirrich"],
    "RC Aarburg": ["RC Aarburg", "Ruderclub Aarburg", "Ruder-Club Aarburg",
                   "Ruder Club Aarburg"],
    "RC Baden": ["RC Baden", "Ruderclub Baden", "Ruder-Club Baden",
                 "Ruder Club Baden"],
    "RC Bern": ["RC Bern", "Rowing Club Bern"],
    "RC Blauweiss Basel": ["RC Blauweiss Basel", "Ruderclub Blauweiss Basel",
                           "Ruder-Club Blauweiss Basel"],
    "RC Cham": ["RC Cham", "Ruderclub Cham", "Ruder-Club Cham", "Ruder Club Cham"],
    "RC Erlenbach": ["RC Erlenbach", "Ruderclub Erlenbach", "Ruder-Club Erlenbach"],
    "RC Greifensee": ["RC Greifensee"],
    "RC Hallwilersee": ["RC Hallwilersee", "Ruderclub Hallwilersee"],
    "RC Kaufleuten Zürich": ["RC Kaufleuten Zürich", "RC Kaufleuten Zurich",
                             "RC Kaufleuten", "Ruder Club Kaufleuten"],
    "RC Kreuzlingen": ["RC Kreuzlingen"],
    "RC Lausanne": ["RC Lausanne", "Rowing Club Lausanne"],
    "RC Olten": ["RC Olten", "Ruderclub Olten"],
    "RC Rapperswil-Jona": ["RC Rapperswil-Jona", "Ruder Club Rapperswil-Jona"],
    "RC Reuss Luzern": ["RC Reuss Luzern", "RC Reuss", "Ruderclub Reuss Luzern"],
    "RC Sarnen": ["RC Sarnen", "Ruderclub Sarnen"],
    "RC Schaffhausen": ["RC Schaffhausen", "Ruderclub Schaffhausen",
                        "Ruder-Club Schaffhausen", "Ruder Club Schaffhausen"],
    "RC Thalwil": ["RC Thalwil", "Ruderclub Thalwil", "Ruder-Club Thalwil"],
    "RC Uster": ["RC Uster", "Ruderclub Uster"],
    "RC Wohlensee": ["Ruderclub Wohlensee"],
    "RC Zürich": ["RC Zürich", "Ruderclub Zürich", "Ruderclub Zurich",
                  "Ruder-Club Zürich", "Ruder-Club Zurich", "Ruder Club Zürich",
                  "Ruder Club Zurich"],
    "RG Zürich": ["RG Zürich", "Rudergesellschaft Zürich",
                  "Rudergesellschaft Zurich"],
    "SA Fribourg": ["SA Fribourg", "Société d'Aviron Fribourg",
                    "Société d'aviron Fribourg"],
    "SC Arbon": ["SC Arbon", "Seeclub Arbon"],
    "SC Biel": ["SC Biel", "Seeclub Biel"],
    "SC Küsnacht": ["SC Küsnacht", "Seeclub Küsnacht", "Seeclub Kiisnacht",
                    "Seeclub Kusnacht", "Seeclub Kisnacht", "Fy Seeclub Kisnacht"],
    "SC Locarno": ["SC Locarno", "CC Locarno", "Società Canottieri Locarno",
                   "Societa Canottieri Locarno"],
    "SC Luzern": ["SC Luzern", "Seeclub Luzern", "See-Club Luzern"],
    "SC Richterswil": ["Seeclub Richterswil"],
    "SC Sempach": ["Seeclub Sempach"],
    "SC Stäfa": ["SC Stäfa", "Seeclub Stäfa", "Seeclub Stafa"],
    "SC Stansstad": ["Seeclub Stansstad"],
    "SC Sursee": ["SC Sursee", "Seeclub Sursee"],
    "SC Wädenswil": ["Seeclub Wädenswil", "Seeclub Wadenswil"],
    "SC Zug": ["Seeclub Zug", "See-Club Zug"],
    "SC Zürich": ["SC Zürich", "Seeclub Zürich", "Seeclub Zurich",
                  "Seeclub Ziirich", "Seeclub Zirich", "Seeclub Zitirich"],
    "SN Genève SA": ["Société Nautique Genève", "Société Nautique Genéve",
                     "Société Nautique Genève Section Aviron"],
    "SN Neuchâtel": ["SN Neuchâtel", "Société Nautique Neuchâtel"],
    "SN Étoile Bienne": ["SN Etoile Bienne", "Société Nautique Etoile Bienne"],
    "Solothurner RC": ["Solothurner RC", "Solothurner Ruder Club",
                       "Solothurner Ruder-Club"],
    "Union Nautique Yverdon": ["Union Nautique Yverdon"],
    "ARA": ["Association Romande d'Aviron", "Association Romande Aviron"],
    "CA Vallée de Joux": ["Club Aviron Vallée de Joux"],
    "KS Wettingen": ["Kantonsschule Wettingen"],
    "Regattaverein Luzern": ["Regattaverein Luzern"],
    "ROZ": ["ROZ"],
    "SC Horgen": ["Seeclub Horgen"],
    "UCL": ["UCL"],
}


def pre(s):
    """Normalize punctuation/OCR junk so spelling variants share one key."""
    s = re.sub(r"[’‘‚`]", "'", s)
    s = re.sub(r"[–—‐−]", "-", s)
    s = re.sub(r"[„“”\"*|()+?,]", "", s)
    s = re.sub(r"^\s*\d+\s*[.\):;]?\s+", "", s)        # leading numeric rank
    s = re.sub(r"^[A-Za-z0-9]{1,3}\.{1,2}\s+", "", s)  # leading OCR rank 'Z1..'
    return re.sub(r"\s+", " ", s).strip(" .,:;-")


def build_alias_map():
    alias = {}
    for short, variants in VARIANTS.items():
        for v in variants:
            key = pre(v)
            if key in alias and alias[key] != short:
                raise ValueError(f"variant {key!r} maps to both "
                                 f"{alias[key]!r} and {short!r}")
            alias[key] = short
    return alias


def load_rows():
    rows = []
    with open(RAW, encoding="utf-8") as fh:
        for line in fh:
            year, club, pts = line.rstrip("\n").split("\t")
            rows.append((int(year), club, int(pts)))
    return rows


def normalize(rows, alias):
    unknown = set()
    out = []
    for year, raw, pts in rows:
        short = alias.get(pre(raw))
        if short is None:
            unknown.add(raw)
            continue
        out.append((year, CLUBS[short], short, pts))
    if unknown:
        for u in sorted(unknown):
            print(f"UNMAPPED: {u!r}", file=sys.stderr)
        raise SystemExit(f"{len(unknown)} unmapped club spelling(s); "
                         "add them to VARIANTS.")
    return out


def write_csv(rows):
    # sort by year asc, then points desc, then short name for stable ties.
    rows.sort(key=lambda r: (r[0], -r[3], r[2]))
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Year", "ClubLongName", "ClubShortName", "Points"])
        for year, long, short, pts in rows:
            w.writerow([year, long, short, pts])
    return len(rows)


def main():
    alias = build_alias_map()
    rows = normalize(load_rows(), alias)
    n = write_csv(rows)
    print(f"Wrote {n} rows to {OUT}")


if __name__ == "__main__":
    main()
