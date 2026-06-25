#!/usr/bin/env python3
"""Validation tests for the President's Cup data pipeline.

Run: python3 -m unittest pc/test_build_history.py  (from repo root)
or:  python3 -m unittest discover -s pc
"""
import csv
import os
import unittest

import build_history as bh

HERE = os.path.dirname(__file__)
PDE_CSV = os.path.join(HERE, os.pardir, "pde", "pde-history.csv")

# Rank-1 club + points per year, verified by hand against every source PDF
# (text layer or the rendered scan). Regression anchors for the whole pipeline.
WINNERS = {
    2006: ("SC Luzern", 60), 2007: ("SC Luzern", 92), 2008: ("RC Baden", 79),
    2009: ("RC Baden", 81), 2010: ("RC Baden", 96), 2011: ("RC Baden", 91),
    2012: ("Basler RC", 108), 2013: ("SC Zürich", 165), 2014: ("SC Zug", 149),
    2015: ("SC Zürich", 192), 2016: ("SC Zug", 138), 2017: ("SC Zürich", 161),
    2018: ("SC Zürich", 122), 2019: ("Grasshopper RC Zürich", 159),
    2020: ("SC Zürich", 58), 2021: ("CA Vevey", 26), 2022: ("Basler RC", 180),
    2023: ("Basler RC", 289), 2024: ("Basler RC", 171), 2025: ("Basler RC", 196),
    2026: ("Belvoir RC Zürich", 186),
}

# Number of result rows per year (entries, counting ties separately).
COUNTS = {
    2006: 17, 2007: 26, 2008: 26, 2009: 29, 2010: 31, 2011: 30, 2012: 32,
    2013: 31, 2014: 33, 2015: 33, 2016: 31, 2017: 35, 2018: 33, 2019: 35,
    2020: 33, 2021: 15, 2022: 34, 2023: 39, 2024: 29, 2025: 29, 2026: 32,
}


def normalized_rows():
    return bh.normalize(bh.load_rows(), bh.build_alias_map())


class TestNormalizationMap(unittest.TestCase):
    def test_clubs_and_variants_cover_same_shorts(self):
        self.assertEqual(set(bh.CLUBS), set(bh.VARIANTS),
                         "CLUBS and VARIANTS must define the same short names")

    def test_alias_map_has_no_collisions(self):
        bh.build_alias_map()  # raises on a variant mapping to two clubs

    def test_every_raw_spelling_is_mapped(self):
        normalized_rows()  # raises SystemExit if any raw is unmapped

    def test_shared_clubs_match_pde_names(self):
        """Clubs present in PDE must use identical long+short names there."""
        pde = {}
        with open(PDE_CSV, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                pde[r["ClubShortName"]] = r["ClubLongName"]
        shared = set(bh.CLUBS) & set(pde)
        self.assertTrue(shared, "expected overlap with PDE clubs")
        for short in sorted(shared):
            self.assertEqual(bh.CLUBS[short], pde[short],
                             f"long name for {short!r} differs from PDE")


class TestOutput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = normalized_rows()
        cls.by_year = {}
        for year, long, short, pts in cls.rows:
            cls.by_year.setdefault(year, []).append((short, pts))

    def test_years_present(self):
        self.assertEqual(set(self.by_year), set(WINNERS))

    def test_points_are_positive(self):
        for _, _, _, pts in self.rows:
            self.assertGreater(pts, 0)

    def test_winners(self):
        for year, expected in WINNERS.items():
            top = max(self.by_year[year], key=lambda sp: sp[1])
            self.assertEqual(top, expected, f"winner mismatch for {year}")

    def test_row_counts(self):
        for year, n in COUNTS.items():
            self.assertEqual(len(self.by_year[year]), n,
                             f"row count mismatch for {year}")

    def test_no_duplicate_club_within_year(self):
        for year, entries in self.by_year.items():
            shorts = [s for s, _ in entries]
            self.assertEqual(len(shorts), len(set(shorts)),
                             f"duplicate club within {year}")

    def test_long_name_defined_for_every_short(self):
        for _, long, short, _ in self.rows:
            self.assertEqual(long, bh.CLUBS[short])


class TestCommittedCsvInSync(unittest.TestCase):
    def test_csv_matches_fresh_build(self):
        """pc-history.csv must equal a fresh normalization of the raw extract."""
        rows = normalized_rows()
        rows.sort(key=lambda r: (r[0], -r[3], r[2]))
        with open(bh.OUT, encoding="utf-8") as fh:
            reader = csv.reader(fh)
            header = next(reader)
            self.assertEqual(header, ["Year", "ClubLongName", "ClubShortName", "Points"])
            committed = [(int(y), lo, sh, int(p)) for y, lo, sh, p in reader]
        self.assertEqual(committed, rows,
                         "pc-history.csv is stale; re-run build_history.py")


if __name__ == "__main__":
    unittest.main()
