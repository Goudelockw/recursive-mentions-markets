import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from rmm import librarian, paths


class LibrarianOutputsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.out = root / "outputs"
        for f in ["trade-sheets/2026-10/2026-10-26_trade-sheet.md",
                  "trade-sheets/2026-10/2026-11-02_trade-sheet.md",   # wrong month folder
                  "trade-sheets/2026-06/2026-06-01_trade-sheet.csv",  # over 90 days
                  "trade-sheets/2026-10/notes.txt",
                  "weekly/2026-W44_weekly-review.md",
                  "weekly/2026-W20_cost-report.md",                   # over 90 days
                  "weekly/Weekly Review.md",
                  "models/index.html",
                  "models/v1_2026-05-01/fit-report.md",               # old but live
                  "models/v2_2026-05-08/fit-report.md",               # old, not live, not newest 3
                  "models/v3_2026-10-01/fit-report.md",
                  "models/v4_2026-10-08/fit-report.md",
                  "models/v5_2026-10-15/fit-report.md",
                  "models/scratch.csv",
                  "experiments/EXP-0001_news-volume/report.md",
                  "experiments/news/report.md",
                  "costs/neon-usage.csv",
                  "archive/trade-sheets/2026-01/2026-01-05_trade-sheet.md",
                  "misc/x.md"]:
            p = self.out / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x")
        self.patches = [mock.patch.object(paths, "ROOT", root), mock.patch.object(paths, "OUTPUTS", self.out)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_rules(self):
        r = librarian.Report(date(2026, 10, 27))
        librarian.check_outputs(r, live_versions={1})
        moves = {str(m.src.relative_to(self.out)): str(m.dst.relative_to(self.out)) for m in r.moves}
        self.assertEqual(moves, {
            "trade-sheets/2026-10/2026-11-02_trade-sheet.md": "trade-sheets/2026-11/2026-11-02_trade-sheet.md",
            "trade-sheets/2026-06/2026-06-01_trade-sheet.csv": "archive/trade-sheets/2026-06/2026-06-01_trade-sheet.csv",
            "weekly/2026-W20_cost-report.md": "archive/weekly/2026/2026-W20_cost-report.md",
            "models/v2_2026-05-08": "archive/models/v2_2026-05-08",
        })
        self.assertEqual(sorted(p for p, _ in r.misnamed), [
            "outputs/experiments/news/report.md", "outputs/misc/x.md", "outputs/models/scratch.csv",
            "outputs/trade-sheets/2026-10/notes.txt", "outputs/weekly/Weekly Review.md"])

    def test_models_skipped_without_db(self):
        r = librarian.Report(date(2026, 10, 27))
        librarian.check_outputs(r, live_versions=None)
        self.assertFalse(any("models" in str(m.src) for m in r.moves))
        self.assertTrue(r.notes)

    def test_apply_moves_untracked_files(self):
        r = librarian.Report(date(2026, 10, 27))
        librarian.check_outputs(r, live_versions={1})
        for m in r.moves:
            librarian._move(m.src, m.dst)
        self.assertTrue((self.out / "archive/models/v2_2026-05-08/fit-report.md").exists())
        self.assertTrue((self.out / "trade-sheets/2026-11/2026-11-02_trade-sheet.md").exists())


class LibrarianDocsTest(unittest.TestCase):
    def test_repo_docs_reference_real_commands(self):
        r = librarian.Report(date(2026, 10, 27))
        librarian.check_docs(r, objects=None, runs=None)
        self.assertEqual([x for x in r.docs if "not a command" in x[1] or "not documented" in x[1]], [])

    def test_services_parsed(self):
        self.assertIn("ops-fixes", librarian.services_in_system_md())
        self.assertIn("research-weekly", librarian.services_in_system_md())


if __name__ == "__main__":
    unittest.main()
