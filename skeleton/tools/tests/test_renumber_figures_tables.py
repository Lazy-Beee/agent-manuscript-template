import importlib.util
import pathlib
import unittest


SCRIPT = pathlib.Path(__file__).parents[1] / "renumber_figures_tables.py"
SPEC = importlib.util.spec_from_file_location("renumber_figures_tables", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


# Captions 1, 3, 4 (2 was removed), so the mapping must be {1: 1, 3: 2, 4: 3}. The
# references exercise the bare, letter-suffix, parenthesised-suffix, panel-join and
# figure-join forms; every number in a join must be renumbered, not only the first.
SAMPLE = """# Title

Figure 1 opens. Figures 3(a) and 3(b) plot it, and Figure 3(c) explains it.
Figure 4(e–g) compares, Figure 4a shows, and Figures 3 and 4 close.
Figure 4(a, d) marks both.

![](figures/one.png)

Figure 1. One.

![](figures/three.png)

Figure 3. Three: (a) x, (b) y, (c) z.

![](figures/four.png)

Figure 4. Four: (a) p, (d) q, (e–g) r.
"""

EXPECTED = """# Title

Figure 1 opens. Figures 2(a) and 2(b) plot it, and Figure 2(c) explains it.
Figure 3(e–g) compares, Figure 3a shows, and Figures 2 and 3 close.
Figure 3(a, d) marks both.

![](figures/one.png)

Figure 1. One.

![](figures/three.png)

Figure 2. Three: (a) x, (b) y, (c) z.

![](figures/four.png)

Figure 3. Four: (a) p, (d) q, (e–g) r.
"""


class RenumberFiguresTest(unittest.TestCase):
    def test_mapping_and_coverage(self):
        a = MOD.analyze(SAMPLE, "figure")
        self.assertEqual(a["mapping"], {1: 1, 3: 2, 4: 3})
        self.assertEqual(a["undefined"], [])
        self.assertEqual(a["orphans"], [])
        self.assertEqual(a["dup"], [])

    def test_parenthesised_panel_join_is_fully_renumbered(self):
        a = MOD.analyze(SAMPLE, "figure")
        out = MOD.rewrite(SAMPLE, "figure", a["mapping"])
        self.assertEqual(out, EXPECTED)
        # the regression: the second number of "Figures 3(a) and 3(b)" used to be left stale
        self.assertNotIn("and 3(b)", out)

    def test_tokens_keep_parenthesised_suffix(self):
        toks = MOD._tokens("3(a) and 3(b–c)")
        self.assertEqual([(t.group(1), t.group(2)) for t in toks],
                         [("3", "(a)"), ("3", "(b–c)")])
        self.assertEqual(MOD.mentioned_numbers("3(a) and 3(b–c)"), [3, 3])


if __name__ == "__main__":
    unittest.main()
