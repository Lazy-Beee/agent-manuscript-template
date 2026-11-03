# References — provenance, inventory & usage map

Maps every bibliography entry to its `.bib` / PDF in this folder, where it is cited in the
draft, and what it supports. Citation details are authoritative from the matching `.bib`
file. The claim-support check of every entry is in [`citation_audit.md`](citation_audit.md);
the positioning against the closest prior work, kept off the manuscript for the rebuttal,
is in [`related_work_comparison.md`](related_work_comparison.md). Keep this in sync whenever
the bibliography changes, and reconcile it after every
`tools/renumber_citations.py --write` (record the old-to-new map in `TODO.md`).

**Files.** One `.bib` per cited paper, named like its PDF: `<Author - Year - Title>.bib`.
PDFs sit alongside for reading but are gitignored; text layers for full-text claim checks
go to `extracted_text/` (gitignored, derived). A reference reused from a sibling manuscript
is copied with its `.bib`, PDF and sidecar when its citation is written into the draft.

**Reading list.** [`download_list.md`](download_list.md) lists the papers to fetch by
priority, one line per paper with its DOI; the `paper-download` skill verifies the DOIs,
downloads the open-access copies, files the PDFs the author saves from the library, and
ticks the lines as the files land.

**Rule for adding a reference.** Only claim-matched citations: each one supports the
sentence it is attached to, checked in the full text where the claim depends on detail. No
citation is added for journal-name coverage. A new citation takes the next free number until
the finalization renumbering.

The `Cited in` column can be regenerated with `python tools/citation_usage_map.py`.

| # | `.bib` | PDF | Cited in | Supports |
|---|--------|-----|----------|----------|
