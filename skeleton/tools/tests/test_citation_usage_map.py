import importlib.util
import pathlib
import unittest


SCRIPT = pathlib.Path(__file__).parents[1] / "citation_usage_map.py"
SPEC = importlib.util.spec_from_file_location("citation_usage_map", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


SAMPLE = """# Title

# 1. Introduction

Powder impacts disturb the pool \\[1\\]. Models resolve the
particles \\[1, 2\\] at high cost.

# 2. Method

The solver follows \\[2\\].

# References

\\[1\\] A. Author, "First paper on impacts," *J. One,* 2020.

\\[2\\] B. Author, "Second paper on solvers," *J. Two,* 2021.
"""


class CitationUsageMapTest(unittest.TestCase):
    def test_uses_follow_groups_and_sections(self):
        body, refs = MOD.split_body_refs(SAMPLE)
        uses = MOD.collect_uses(body)
        self.assertEqual(len(uses[1]), 2)
        self.assertEqual(len(uses[2]), 2)
        self.assertEqual(uses[1][1]["group"], "[1, 2]")
        self.assertEqual(uses[2][1]["section"], "2. Method")
        self.assertIn("Models resolve the particles [1, 2] at high cost.", uses[1][1]["sentence"])

    def test_entry_title_and_match(self):
        titles = {"Author - 2020 - First paper on impacts": "first paper on impacts",
                  "Author - 2021 - Second paper on solvers": "second paper on solvers"}
        score, stem = MOD.best_match('A. Author, "First paper on impacts," *J. One,* 2020.', titles)
        self.assertEqual(stem, "Author - 2020 - First paper on impacts")
        self.assertGreater(score, 0.9)

    def test_plain_brackets_and_wrapped_entries(self):
        # a draft that writes [N] without backslashes and wraps its reference entries
        text = SAMPLE.replace("\\[", "[").replace("\\]", "]").replace(
            '[2] B. Author, "Second paper on solvers," *J. Two,* 2021.',
            '[2] B. Author, "Second paper on\nsolvers," *J. Two,*\n2021.')
        body, refs = MOD.split_body_refs(text)
        uses = MOD.collect_uses(body)
        self.assertEqual(len(uses[1]), 2)
        self.assertEqual(uses[1][1]["group"], "[1, 2]")
        entries = MOD.parse_entries(refs)
        self.assertEqual(sorted(entries), [1, 2])
        self.assertEqual(entries[2], 'B. Author, "Second paper on solvers," *J. Two,* 2021.')
        # the escaped form still parses to the same entries
        self.assertEqual(MOD.parse_entries(MOD.split_body_refs(SAMPLE)[1]), entries)

    def test_match_prefers_first_author_and_year(self):
        # an entry without a quoted title, two stems by the same first author in the same
        # year and a third by another author: the author-year guard keeps the third out and
        # the title-word overlap separates the two candidates
        titles = {"Hall - 1988 - Introduction to the Theory of Coverage Processes":
                  "introduction to the theory of coverage processes",
                  "Author - 2026 - First study of impacts on pools":
                  "first study of impacts on pools: a numerical study",
                  "Author - 2026 - Second study of mixing in pools":
                  "second study of mixing in pools based on the same method"}
        entry = ("A. Author, B. Other, Second study of mixing in pools based on the same method, "
                 "in preparation (2026).")
        score, stem = MOD.best_match(entry, titles)
        self.assertEqual(stem, "Author - 2026 - Second study of mixing in pools")
        self.assertGreater(score, 0.7)
        self.assertEqual(MOD.stem_author_year("Carslaw and Jaeger - 1959 - Conduction of Heat in Solids"),
                         ("carslaw", "1959"))
        self.assertEqual(MOD.stem_author_year("no stem form"), (None, None))

    def test_batches(self):
        self.assertEqual(MOD.parse_batches("1-2,3-3", [1, 2, 3]), [("1-2", [1, 2]), ("3-3", [3])])
        self.assertEqual(MOD.parse_batches(None, [1, 2]), [("all", [1, 2])])


if __name__ == "__main__":
    unittest.main()
