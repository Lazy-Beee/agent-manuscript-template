---
name: manuscript-to-docx
description: >-
  Convert a scientific manuscript from Markdown to a submission-ready .docx with
  pandoc, AFTER a pre-conversion QA pass: abstract/conclusion freshness, figure
  and table numbering, citation/reference consistency, AI-tell em-dashes and
  off-house-style terminology, external notation-table consistency, leftover
  placeholders, hallucination and number cross-checks, and broken image links.
  Use this whenever the user wants to render, convert, export, or "pandoc" a
  manuscript/paper/draft .md to Word/.docx, produce the final deliverable, or run
  pre-submission / pre-render checks on a manuscript. Trigger even if they only
  say "convert to docx" without mentioning checks, and even if they only ask for
  the checks without mentioning conversion.
---

# Manuscript Markdown to docx

A two-phase workflow for turning a manuscript Markdown source into a clean,
submission-ready Word document:

1. **Pre-flight QA** (read-only) surfaces the things that drift in a working `.md` and
   embarrass an author at submission.
2. **Render** runs pandoc and verifies the resulting `.docx`.

The pre-flight pass never edits the manuscript silently. It reports; the author decides
what to fix. The `.md` is the live working source: numbers in the abstract and conclusions
lag the body as results are re-run, figures get reordered, citations get renumbered, and
AI-assisted edits leave em-dashes and off-house-style wording. Catching these before the
docx goes to a co-author or a journal saves a review round-trip.

Plain agents without skill support run the same steps by hand: the commands below are
ordinary Python, PowerShell and bash scripts.

## When NOT to silently proceed

- Do **not** edit the manuscript `.md` without showing the findings and getting an
  explicit go-ahead. Report first.
- Do **not** overwrite an existing `.docx` that is open in Word: Word locks the file and
  pandoc will fail or write a corrupt file. Confirm it is closed first.
- The render itself creates/overwrites a `.docx` (a derived artifact, not the source);
  that is fine once the author approves the render.

## Step 0 - Locate the inputs

- **Working manuscript**: the main `.md` (title, abstract, numbered sections, reference
  list). If several `.md` files exist, pick the working source and say which one.
- **terminology.md** beside it, if present: the house wording standard and the source of
  the terminology check.
- **notation.md** beside it, if present: the external symbol table. Any symbol definition,
  equation tag, or symbol location changed in the manuscript is updated there in the same
  edit.
- **figures/** and **references/** folders alongside.
- Any existing **.docx** with the target name (so the render does not clobber an open file).

## Step 1 - Mechanical checks (scripted, deterministic)

```
python "<skill>/scripts/preflight_check.py" "<manuscript.md>" [--terminology "<terminology.md>"] [--notation "<notation.md>"]
```

Read-only. It reports, with line numbers and a FAIL/WARN/INFO severity:

- **Sections**: numbered headings carry no duplicate or skipped number.
- **Appendices**: `A.n` sections are sequential and follow first-citation order in the
  main text; appendix equation tags are continuous and resolve from every `Eq. (A.n)`.
- **Figures / Tables**: captions are sequential with no gaps or duplicates, every in-text
  `Figure N` / `Table N` resolves to a caption, and captions are numbered in document
  order. A caption numbered out of order (a figure appended during drafting) is WARNed and
  renumbered at finalization with `renumber_figures_tables.py`.
- **Images**: every `![](figures/...)` target exists on disk.
- **Citations**: every in-text `[N]` has a reference entry, the list has no gaps, no entry
  is uncited, and numbering follows first appearance.
- **Em-dashes**: flags `—` in prose (an AI tell; recast with comma, colon, parentheses, or
  a separate sentence). En-dash ranges (`150–350`) are correct and not flagged.
- **Placeholders / artifacts**: `To Be Filled`, `[citation here?]`, TODO/TBD, and
  Word->pandoc leftovers (`\#` equation tags, quoted `{width="..."}` attributes, "AI-generated
  content" alt text). An unquoted `{width=NN%}` is a deliberate display width.
- **Terminology**: the "Do not use" entries of `terminology.md` (multi-word entries always;
  single words only in rows whose Note carries `[enforced]`), plus any built-in
  `DEFAULT_FORBIDDEN` terms in the script.
- **Notation**: the symbol table is present, rows under `Open notation issues` are
  reported, and stale `Eq. (...)` locations fail.
- **Bare terms**: optional context-aware rules (`BARE_TERM_RULES` in the script, empty by
  default) for short forms that should be spelled out.
- **Prose typos**: a curated set of word-confusion typos and doubled words, plus double
  spaces. Not a spellchecker; the read-through in Step 2 still matters.

## Step 2 - Judgment checks (reading the manuscript)

The script cannot reason about meaning. Work through `references/checklist.md`:

- **Status-doc reconciliation**: reconcile each open/done item of the README, TODO or
  revision log against the draft. Trust the manuscript, not the log; report mismatches.
- **Abstract and Conclusions freshness**: real text, and every number and claim matches
  the body and the figures.
- **Number / hallucination cross-check**: every quantitative claim appears, consistent, in
  the body or a figure. Distrust round numbers and values that appear in one place only.
- **Citation-claim support**: each `[N]` plausibly supports its sentence.
- **Figure sub-panel cross-refs**: cited panel letters exist and match the caption.
- **Full read-through** for grammar, word choice, agreement, tense and flow.
- **Paragraph length and structure**: bloated paragraphs and fragments (checklist §10).
- **Logical redundancy**: the same point made twice (checklist §11).

## Step 3 - Report, do not edit

```
## Pre-flight report - <manuscript name>

### Blockers (fix before submission)
- <file:line> - <issue> - <why> - suggest: <fix>

### House style / freshness (review)
- ...

### Minor / informational
- ...

Mechanical: FAIL=<n> WARN=<n>. Judgment: <abstract/conclusion/number verdicts>.
Recommend: <render now | fix blockers first>.
```

Then stop and let the author choose.

## Step 4 - Apply fixes (only on approval)

Apply approved fixes to the `.md` and re-run Step 1. Keep edits surgical and on-style:
recast em-dashes rather than deleting content, swap only the exact off-style term, and
never invent a citation or a number to silence a placeholder; those go back to the author.
When a fix changes a symbol, its definition, an equation number, or where a symbol is
introduced, update `notation.md` before rerunning the checker.

**Deterministic finalization order** (each tool is a dry run without `--write` and refuses
to write when a reference does not resolve):

1. `python tools/renumber_appendices.py --write`: moves complete `## A.n` blocks into
   first-citation order and renumbers appendix equations and references.
2. `python tools/renumber_citations.py --write`: renumbers citations into first-appearance
   order and reorders the reference list. Then update the citation maps in
   `references/README.md` and `references/citation_audit.md` by hand.
3. `python tools/renumber_figures_tables.py --write`: renumbers figures and tables by
   caption position in the document; preserves panel suffixes and en-dash ranges; ignores
   the abbreviated `Fig.` (reserved for external figures). Then update `figures/README.md`.
4. Reconcile `notation.md` with the final symbols and equation locations; rerun the
   preflight.

## Step 5 - Render to docx

Confirm the target `.docx` is not open in Word, then run the wrapper, which adds the Lua
filters, the bundled reference doc, and `--resource-path`:

```
scripts/render.ps1 "<manuscript.md>" [-Output "<out.docx>"]        # PowerShell
scripts/render.sh  "<manuscript.md>" [out.docx]                     # bash
```

The underlying pandoc command:

```
pandoc "<manuscript.md>" --from=markdown+tex_math_dollars-implicit_figures --to=docx \
  --resource-path="<manuscript-dir>" \
  --lua-filter "<skill>/filters/mergecol.lua" --lua-filter "<skill>/filters/eqnum.lua" \
  --lua-filter "<skill>/filters/caption_style.lua" --lua-filter "<skill>/filters/refs_left.lua" \
  --reference-doc "<skill>/assets/reference.docx" -o "<output.docx>"
```

**Smaller docx for review copies:** `-Jpg` (PowerShell) / `--jpg` (bash) re-encodes the
figures as JPEG (quality 85, width capped at 2600 px, about 400 dpi at a 6.5 in column) in a
temporary staging copy; the source `.md` and `figures/` are never modified. Downscaling, not
quality, is what shrinks the file. A JPG render appends a note saying its figures are
compressed; `-NoJpgNote` / `--no-jpg-note` suppresses it. Options: `-JpgQuality` (default
85), `-JpgMaxWidth` (default 2600; 0 keeps full resolution). The default render keeps the
original PNGs for the highest-fidelity deliverable.

Notes:

- **Equations**: end a display equation with `\tag{N}` inside `$$ ... $$`; `eqnum.lua`
  renders a borderless equation/number row. Do not use the Word->pandoc
  `\#\left( N \right)` form.
- **Grouped tables**: write a pipe table with the group label in the group's first row and
  blank cells below; `mergecol.lua` merges them and `format_grouped_tables.py` centers the
  merged cells and adds a rule above each group.
- **`-implicit_figures`** is deliberate: captions live in explicit `Figure N.` paragraphs,
  so an image's alt text must not become a second caption.
- **`caption_style.lua`** gives `Figure N.` / `Table N.` paragraphs the Word caption styles
  with a bold label, and gives image-only paragraphs a centred keep-with-next style so a
  figure never parts from its caption.
- **`refs_left.lua`** keeps the reference list left-aligned while the body is justified.
- **Reference doc**: `assets/reference.docx` is pandoc's default with a Letter page and
  1 in margins (6.5 in column), justified `Body Text`, an 11 pt non-italic `Caption`, and a
  left-aligned `Bibliography` style. Pass `-ReferenceDoc` / `--reference-doc` for a journal
  template; that template then supplies the styles.
- **Image size**: pandoc places an image at pixels / dpi and only scales it *down* to the
  column, so figures authored at most 6.5 in wide are placed unscaled. Without a page size
  in the reference doc, pandoc falls back to a 5.83 in column and silently shrinks every
  figure.
- Run from the manuscript folder, or pass absolute paths; `--resource-path` must point at
  the folder that holds `figures/`.

## Step 6 - Post-render verification

- Tables render as real Word tables (pipe tables are safe; simple tables can regress to
  text).
- Display equations are numbered, right-aligned, with no literal `#`.
- Grouped table cells are merged where expected.
- Every figure is embedded and sits with its caption.
- Captions use the caption styles, with only the label bold; a sentence that merely starts
  with "Figure 10 shows ..." stays body text.
- Body text is justified; headings, captions, table cells and references are not.
- The abstract and conclusions are present and current.
- For a JPG render, the compressed-figure note is the last paragraph.

Report what you verified and anything still off. Do not call the docx submission-ready if
any blocker from Step 3 was deferred.

## Scope notes

Tuned to a single-`.md` manuscript with a hand-numbered reference list and content-named
figures (file names decoupled from Figure N). If a manuscript uses pandoc `[@key]`
citations with a `.bib`, the citation check does not apply: render with
`--citeproc --bibliography=<refs.bib> --csl=<style.csl>` instead.
