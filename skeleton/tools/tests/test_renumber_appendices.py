import importlib.util
import pathlib
import unittest


SCRIPT = pathlib.Path(__file__).parents[1] / "renumber_appendices.py"
SPEC = importlib.util.spec_from_file_location("renumber_appendices", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)
PREFLIGHT_SCRIPT = (pathlib.Path(__file__).parents[2] / ".claude" / "skills"
                    / "manuscript-to-docx" / "scripts" / "preflight_check.py")
PREFLIGHT_SPEC = importlib.util.spec_from_file_location("preflight_check", PREFLIGHT_SCRIPT)
PREFLIGHT = importlib.util.module_from_spec(PREFLIGHT_SPEC)
PREFLIGHT_SPEC.loader.exec_module(PREFLIGHT)


SAMPLE = """# Title

See Appendix A.2 and Appendix A.1. Appendix A.3 is cited last.
Eq. (A.2) supports the first citation, and Eq. (A.1) supports the second.

# Appendix A. Details

## A.1 First

first equation
$$ x = 1 \\tag{A.1} $$

## A.2 Second

second equation
$$ y = 2 \\tag{A.2} $$

## A.3 Third

third equation
$$ z = 3 \\tag{A.3} $$

# References
"""


class RenumberAppendicesTests(unittest.TestCase):
    def test_reorders_blocks_references_and_equations(self):
        result = MOD.transform(SAMPLE)
        self.assertFalse(result["errors"])
        self.assertEqual(result["desired"], [2, 1, 3])
        out = result["text"]
        self.assertLess(out.index("## A.1 Second"), out.index("## A.2 First"))
        self.assertIn("See Appendix A.1 and Appendix A.2.", out)
        self.assertIn("Eq. (A.1) supports the first citation", out)
        self.assertIn("Eq. (A.2) supports the second", out)
        self.assertLess(out.index(r"\tag{A.1}"), out.index(r"\tag{A.2}"))

    def test_is_idempotent(self):
        first = MOD.transform(SAMPLE)
        second = MOD.transform(first["text"])
        self.assertFalse(second["errors"])
        self.assertEqual(second["text"], first["text"])

    def test_undefined_appendix_is_fatal(self):
        broken = SAMPLE.replace("Appendix A.3 is cited last", "Appendix A.4 is cited last")
        result = MOD.transform(broken)
        self.assertTrue(any("undefined appendix" in msg for msg in result["errors"]))

    def test_preflight_flags_first_citation_order(self):
        lines = [(i + 1, line) for i, line in enumerate(SAMPLE.splitlines())]
        issues, _summary = PREFLIGHT.check_appendices(lines)
        self.assertTrue(any("renumber_appendices.py" in msg for _sev, _ln, msg in issues))

    def test_preflight_flags_equation_gap(self):
        broken = SAMPLE.replace(r"\tag{A.2}", r"\tag{A.4}")
        lines = [(i + 1, line) for i, line in enumerate(broken.splitlines())]
        issues, _summary = PREFLIGHT.check_appendices(lines)
        self.assertTrue(any(sev == PREFLIGHT.FAIL and "equation tag" in msg
                            for sev, _ln, msg in issues))

    def test_preflight_expands_appendix_range(self):
        ranged = SAMPLE.replace(
            "See Appendix A.2 and Appendix A.1. Appendix A.3 is cited last.",
            "See Appendices A.1–A.3.")
        lines = [(i + 1, line) for i, line in enumerate(ranged.splitlines())]
        issues, _summary = PREFLIGHT.check_appendices(lines)
        self.assertFalse(any("never cited" in msg for _sev, _ln, msg in issues))


if __name__ == "__main__":
    unittest.main()
