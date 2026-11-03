# Citation accuracy audit

Each bibliography entry checked against its source: where the cited content appears in the
original, and whether the manuscript's use is accurate. Companion to
[`README.md`](README.md) (cite number to `.bib` to usage map). Relabel every entry after a
citation renumbering, and re-check the usage of any citation whose sentence was rewritten.
The audit is one of the checks before each version (README).

Verdicts:
- **ACCURATE**: the source supports the claim as worded.
- **ACCURATE-NUANCE**: supported, with a defensible qualification stated in the entry
  (different alloy or process, weaker evidence than the wording, an analog material, rounding).
- **MISMATCH**: the claim is not supported or is misstated. Fix the sentence or the citation
  before the next version.
- **NOT-FOUND**: the cited content was not located in the source.
- **[--]**: removed from the bibliography; the entry is kept because the source was read.

## How to run it

1. `python tools/citation_usage_map.py --batches <ranges>` writes, for every entry, each use
   in the draft (heading, line, sentence) and its `.bib`, PDF and text sidecar, as one usage
   pack per batch in `references/audit_work/` (gitignored). Fix wrong `.bib` matches with
   `--override`.
2. Audit each batch of about 10 to 15 entries, grouped by theme (introduction, models, methods,
   material properties). Batches can go to parallel agents; they read the repository only and
   write their blocks to `audit_work/`.
3. For every use, read the sentence in context and find the content in the source: search the
   text sidecar, and open the PDF for pages, tables, figures and equations. Material-property
   values: find each value and its conditions, and check the unit conversion and the
   description ("read from a curve", "analog alloy"). Check the bibliographic entry against
   the PDF's first page. An entry shared with a sibling manuscript may reuse that audit's source
   location, but its usage here is checked anew.
4. Merge the blocks below, update the Summary, and list the findings for the author. The audit
   does not change the draft. Each fix goes to the author first.

## Summary

*(Date, numbering scheme, counts per verdict, the ACCURATE-NUANCE list with one line each,
entries not re-read in this pass and why, and that every entry is cited and none is orphaned.)*

<!--
Entry format (delete this comment once the file has a real entry):

### [N] Author et al. YEAR — VERDICT
- Claim (Section x.y, with [M] if grouped): what the draft uses it for, one line per distinct use.
- Source: section, page, table or figure where the content is.
- Quote: "one short verbatim quote".
- Note: caveats; what is cited and what is not; "PDF read YYYY-MM-DD".
- Entry: OK, or the bibliographic discrepancy.
-->

## Findings for the author

*(Each MISMATCH, NOT-FOUND, overstatement or bibliographic error: draft line, the problem, a
suggested minimal fix, and the author's decision once given, with its date.)*
