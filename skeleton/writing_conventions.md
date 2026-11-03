# Writing conventions — {{NAME}} manuscript

Shared writing-style standard for the manuscript prose and figures, followed jointly by the
authors and by any AI agent editing the draft. This file covers paragraph structure,
language, sentences, results prose, equations, figures and the source format. Word-level
wording and punctuation live in `terminology.md`. The rules below come with the manuscript
template; edit them to the authors' taste, and give each new rule its provenance (review
comment, author decision, date) in the Provenance section.

## 1. Paragraph structure

- **One idea per paragraph, developed in as many steps as it needs.** If a paragraph splits
  into two points, break it into two paragraphs. Conversely, a paragraph of one or two
  sentences that only continues the previous paragraph's point is a fragment and is merged
  back.
- **Open with a topic sentence, close with a summarizing one,** so the internal logic reads
  top to bottom.
- **Keep the flow tight:** every sentence advances the paragraph's single point.
- **Lead with the point, not the setup.** Do not open on background when the paragraph's
  point is a result ("Simulations were performed with ...", "Prior work found ..."). Put the
  result first; the setup follows it.
- **Split at the seam.** Three signs a paragraph holds two ideas: a semicolon or colon
  joining two complete claims, two subordinate clauses of the same kind in a row
  (", while ..., while ..."), and a shift in level, e.g. from a single-event quantity to a
  case-level one, or from a result to its implication.
- **Give a new paragraph a subject.** Never open one with a bare "It" or "They" whose
  referent sits in the previous paragraph.

## 2. Language

- **Plain over "elegant."** Write for an engineering reader: direct, concrete wording.
- **Consistent wording; repetition is fine.** One fixed term per concept, reused; do not
  vary a term to avoid repeating it. The terms are fixed in `terminology.md`.
- **No em-dashes in prose** (recast with a comma, colon, parentheses or a new sentence).
- **Keep the tense consistent across parallel sections.** What the model and the experiment
  do is written in the present tense.
- **Spell out every abbreviation at first use**, including ones borrowed from a neighboring
  field.
- **Prose benchmark:** once a section has been revised and approved by the senior author or
  advisor, record it here as the benchmark for style and logical presentation, and match it
  when revising the rest.
- **Use a linear engineering sequence:** scope or operating conditions, what the method or
  figure shows, the numerical result, the physical reason, any limitation or implication.
  Omit a step when it is not needed; do not compress several into one sentence.
- **Name the subject and use a plain verb:** "the method calculates," "Figure 8 shows," "the
  radius increases." Avoid abstract transitions, decorative synonyms and pronouns with
  distant referents.

## 3. Sentences

- **One function per sentence, but join a claim to its immediate consequence.** A sentence
  states an observation, reports a number, explains a mechanism, gives a caveat, or draws an
  implication; when it does several, split it and order the pieces as **conclusion,
  evidence, explanation, significance**. A claim and the consequence that follows directly
  from it may share one sentence, joined by a coordinating conjunction, a relative clause or
  a participle, never by a colon or a semicolon (the colon is reserved for equation leads
  and lists). **Do not follow a sentence with one that opens by repeating its object**
  ("... the heater raises the wall temperature. This temperature rise expands ..."): that
  pair is one sentence. Two results, or a result and its mechanism, stay apart.
- **Keep sentences under about 30 words.** Exceptions: an enumeration, and a claim joined to
  its consequence. A join well past 30 words means the halves were not one point.
- **Use the conventional journal verb:** increase, decrease, remain, indicate, show,
  determine, govern, be attributed to; not "stands out", "exposes", "happens to reach".
- **Cutting words must not cut content.** Numbers, operating conditions, uncertainty
  statements and resolution caveats survive a compression pass unchanged.
- **Keep parallel results parallel:** the same slot order and phrasing for each quantity, so
  the reader can compare them across sentences.

## 4. Results prose

- **State causes qualitatively.** When a result has a plausible physical cause, state the
  cause; do not compute what share of the effect it accounts for, and do not end a
  paragraph with "the remaining difference is not explained by any condition examined
  here". Say what the data do show.
- **No run or analysis bookkeeping in the text.** Re-runs, repeat runs, random-seed
  realizations and reproduction checks are not mentioned; data appear as data of the case.
  Where a second realization was the evidence, state the reason instead (e.g. a small
  sample count). Provenance goes to `TODO.md`.
- **Every quoted number has a source** in a frozen data file or a `stats_*.py` script under
  `figures/scripts/`.

## 5. Equations and appendix blocks

- **One shape per block:** a lead sentence ending with a colon, the equation, then the
  parameter definitions opening with "Here, ...". Do not continue past the equation with
  "where ...".
- **Punctuate equations as parts of sentences:** a comma on an equation followed by another
  in the same sentence, a period on the last.
- **Reference equations as `Eq. (3)`**, and `Eq. (A.3)` in the appendix.
- **Maintain `notation.md` with the equations:** update a symbol's meaning, unit and
  location whenever an equation is added, removed, renamed or renumbered.

## 6. Figures

- **Explain the figure before using it:** walk the reader through what it shows, then draw
  the conclusions.
- **One lead sentence per figure, then the results.** Name what the figure plots, panel by
  panel, before any number is quoted from it.
- **Cite a figure once, where it is introduced.** Panel-level pointers carry the panel label
  in parentheses (Figure 4(c), Figures 4(e2) and 4(f2)).
- **Walk-through before the image, implications after the caption.**
- **Each figure must be self-guiding**, through in-figure annotation or the text.
- **Captions describe only;** interpretation and results go in the body.
- **Axis and colorbar units** go in brackets only when the quantity has one ("T [K]"); a
  dimensionless quantity carries no "[-]".

## 7. Source format

- Display equations: `$$ ... \tag{N} $$` (appendix: `\tag{A.N}`); never the Word
  `\#\left( N \right)` form.
- Figures: an image paragraph `![](figures/<content_name>.png)` followed by a caption
  paragraph `Figure N. ...`; add an unquoted `{width=60%}` only for a figure meant to sit
  narrower than the column.
- Tables: a caption paragraph `Table N. ...` above a pipe table; a grouped first column
  carries the group label in its first row and blank cells below.
- Citations: `\[N\]`, groups `\[6, 7, 8\]`; the reference list under `# References` is
  hand-numbered `\[N\] Authors, Title, Journal Volume (Year) Pages. https://doi.org/...`.
- One paragraph per line, so a diff shows paragraph-level changes.
- Placeholders in the draft: `*(to be written)*` or `[to be filled]`; the preflight fails on
  the second form until it is filled.

## 8. Applying these in a revision

**Work section by section:** revise one section, get it approved, commit it alone; run the
mechanical checks (word count, sentence length, terminology, citations, figures, tables)
once at the end of the pass.

### Final language-and-consistency pass

- **Do not change the title** in a language pass.
- **Make the smallest sufficient edit.** Preserve technical meaning, causal relationships,
  scope, numerical values, operating conditions and qualifiers.
- **Defer logic changes and major rewrites** to a separate review; record them.
- **Apply `terminology.md` and `notation.md` exactly.**
- **Check sentence readability and paragraph flow.**
- **Check figures and tables:** introduced before interpretation, parenthesized panel
  labels, consistent terminology, units and ranges.
- **Check manuscript-wide consistency:** the Abstract, Introduction roadmap, section
  previews and Conclusions agree with the body.
- **Check citations and numerical style:** each citation supports its claim; approximate
  wording only for estimates; en dashes for numerical ranges.
- **Verify before committing:** the diff holds only the approved section; `git diff
  --check` and the full preflight pass.

Lessons from section-by-section sweeps:

- **A pass over prose is also a pass for stale claims.** A restructure leaves promises
  behind it in the roadmap, the contribution paragraph, the Abstract and the Conclusions.
- **Rewriting a sentence is when terminology drift shows**, most where prose describes a
  measurement or borrows a word from a neighboring method. Check it against
  `terminology.md`.
- **Prefer the smallest structural change that fixes the reading:** merge a one-sentence
  lead into the paragraph below, or move an existing sentence to the front.
- **Do not fold another open review item into the pass.** Note it and leave it.

## 9. Manuscript-specific notes

*(Rules that apply to this manuscript only, each with its date and source. Example: the
model section is self-contained for a reader who does not have the companion paper in hand;
an imported concept is stated, then credited.)*

## Provenance

*(Where each rule came from: a reviewer comment ID, an advisor meeting, an author decision,
with dates. The template's rules came from earlier manuscripts' review rounds and the
authors' working decisions.)*

## Related standards

- `terminology.md` — preferred terms, spelling, hedging, punctuation, verbatim exceptions.
- `notation.md` — symbol meanings, units, locations, open issues, accepted reuse.
- `known_inconsistencies.md` — deliberate text-versus-implementation differences; read it
  before flagging a mismatch.
