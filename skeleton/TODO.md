# {{NAME}} — TODO

Open items for `{{DRAFT}}.md`, and the record of every decision behind the text. See also
the in-draft `*(...)*` notes. Run bookkeeping (launch, progress, archive of simulations)
does not belong here: it goes to a notes file in the run's data directory, with a one-line
pointer from the item that needs it.

**Data state ({{DATE}}) — READ THIS FIRST.** No case data are in the text yet. When data
land, state here which runs the text uses, where they are on disk, what is frozen into
`figures/scripts/figdata/`, and what is still pending.

<!--
Item format (delete this comment once the file has real items):

- [ ] **Short title stating the task.** Context, the data or files involved, and the
      options. Decisions carry their source and date: "(author, YYYY-MM-DD)",
      "(advisor meeting YYYY-MM-DD)", or a reviewer's comment ID such as "R2 C7".
- [x] **Short title -- DONE YYYY-MM-DD (`abc1234`).** What was done and where. Options not
      chosen stay with the reason. Original item: <the text as first written>.

A section handed to another session or person gets a heading that says so, with the date:
"## §6 <title> — handed to a separate session (YYYY-MM-DD)".
A renumbering is recorded once, with its old-to-new map.
-->

## Writing

- [ ] **Abstract — defer until the body is complete.** Write it only after the results
      sections are final, so its scope, numbers and limitations match the manuscript.
- [ ] **§1 Introduction.** Plan the paragraphs (process and problem; what experiments
      cannot see; existing models; this model; contribution; roadmap) before drafting.
      Every citation is claim-checked against its source. Record the positioning against
      the closest prior work in `references/related_work_comparison.md` (for the rebuttal,
      not the draft).
- [ ] **§2 Methodology.** 2.1 Model (self-contained for the target journal's reader;
      credit the source of every imported concept), 2.2 Experiment design.
- [ ] **§3 Validation.**
- [ ] **§4 Results.** Plan the section split with the author (dividing sections by scale
      rather than by variable often reads better).
- [ ] **Limitations** (now §5; renumbered as results sections are added).
- [ ] **Conclusions — write last** (now §6), each conclusion traced to a result in the body.
- [ ] **End matter:** CRediT, Funding, Declaration of competing interest, Data availability,
      Declaration of generative AI (the authors' own wording; name the tool and its use),
      Acknowledgements.

## Figures

- [ ] Plan the figure set in `figures/README.md` (content names, draft numbers, scripts,
      data) before the first figure is drawn.

## Data-pending

*(Items that wait for simulation or experiment data, each with the data it needs.)*

## Sync with the origin manuscript

*(For a sequel: record each audit against the origin as "audit against <origin>
`<from>..<to>`", one ported item per commit, so the next audit starts after the last
recorded commit. Delete this section if the manuscript has no origin.)*

## Finalization (deferred)

- [ ] Reconcile `notation.md` after the last equation edit; resolve every open issue and
      verify all symbol meanings, units and equation locations.
- [ ] `python tools/renumber_appendices.py --write` (dry run first).
- [ ] `python tools/renumber_citations.py --write`; reconcile `references/README.md` and
      `references/citation_audit.md`; record the old-to-new map here.
- [ ] `python tools/renumber_figures_tables.py --write`; update the `figures/README.md`
      table and any script docstring that names a draft number.
- [ ] Citation audit complete for every entry (`references/citation_audit.md`, method in
      its header); each finding decided by the author.
- [ ] Preflight plus the judgment checks of the `manuscript-to-docx` skill; report, then
      fix on the author's word; render and verify the docx.

## References directory policy

Every cited reference lives in `references/` (one `.bib` per cited paper, text sidecars in
`extracted_text/`, PDFs gitignored). A reference reused from a sibling manuscript is copied
with its `.bib`, PDF and sidecar when its citation is actually written into the draft.

---

## Done / archived (kept for provenance)
