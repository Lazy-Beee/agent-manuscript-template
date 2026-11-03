# Judgment checks (the part a script cannot do)

The scripted checker (`scripts/preflight_check.py`) handles everything
deterministic: section / figure / table numbering, link integrity, citation
bookkeeping, character-level AI tells, terminology hits, notation status, and a
curated typo / doubled-word pass. This file covers the
checks that need an actual read of the manuscript and a model that understands
what the paper claims. Work through them after the script, and fold the verdicts
into the combined report.

Each section says what to check, why it matters, and how to do it efficiently.
Examples are illustrative, not a fixed expectation.

## 1. Reconcile the status doc / revision log first

**Why:** a manuscript folder often carries its own README, revision log, or
"submission blockers" list. These drift out of sync with the draft faster than
anything else, because the draft gets edited and the log usually does not.
Believing a stale log is how a "known" blocker gets shipped, or how finished work
gets redone.

**Check:** if such a doc exists, read its open / blocker / TODO / done items and
reconcile each against the actual `.md`:
- An item marked open may already be resolved in the draft. Example: a README
  listing "Abstract and Conclusions not written (To Be Filled)" as a high-priority
  blocker, when the draft already carries a complete abstract and a full numbered
  Conclusions section. The log is stale; the manuscript is ahead.
- An item marked done may have regressed (a fixed typo reintroduced, a renumbered
  reference knocked back out of order).
- A "deferred" cleanup may now be trivial to close.
- A doc that maps citation numbers - a `references/citation_audit.md`, or a README cite# <-> bib
  table - must still match the manuscript's numbering. A citation renumber (SKILL.md Step 4) shifts
  the numbers in the `.md` but not in these maps, so they go stale by the same shift. Check each
  mapped number against the current reference list and flag any that no longer line up; citation
  numbers must be consistent across the body, the reference list, and these auxiliary docs.
- Likewise a **figure/table renumber** (SKILL.md, `renumber_figures_tables.py --write`) shifts the
  figure/table numbers in the `.md` but not in any doc that hard-codes them - notably the Fig-N maps
  in the `figures/**/README.md` files - so reconcile those after the pass. The tool renumbers by
  caption/document order and only warns (does not fix) when figures are cited out of ascending order.

Trust the manuscript over the log, and report each mismatch so the author can fix
the log too. This check frames the abstract and conclusion checks below: do not
inherit the log's verdict on them, derive your own from the text.

## 2. Abstract freshness

**Why:** the abstract is written early and revised last, so it is the single most
likely place for a stale claim or a number that no longer matches the results. It
is also the first thing a reviewer reads.

**Check:**
- It is a real abstract, not a placeholder (`To Be Filled`, an empty heading, a
  one-line stub). Per check 1, do not trust a status doc that calls it unwritten;
  read the actual `.md`.
- Every quantitative claim in the abstract appears, with the same value, in the
  body: parameter ranges, case counts, error percentages, the headline numbers.
  Example pattern: an abstract saying "from 2% to 6% as the load increases from
  10 to 30 N" must match the figure or section that reports that trend, and
  "within 10%" must match the validation table.
- Every method or scope claim still describes the current paper (no abandoned
  technique, no dropped case, no renamed quantity).

**How:** read the abstract, list its concrete claims, then confirm each against the
body. Flag any number that appears only in the abstract.

## 3. Conclusions freshness

**Why:** conclusions are numbered takeaways a reader will quote. A conclusion that
overstates, or that points at a result no longer in the paper, is a credibility
hit.

**Check:**
- Not a placeholder; each conclusion traces to a result actually presented in the
  body (a figure, a table, a reported value).
- Numbers and ranges agree with the body and the abstract. If the abstract says
  "50 to 80 um" and the matching conclusion says "50 to 90 um", one is stale.
- No conclusion claims more than the results support (e.g. a causal mechanism the
  paper only conjectures).

## 4. Number and hallucination cross-check

**Why:** AI-assisted drafting and many revision passes introduce numbers that look
plausible but appear nowhere else, or that drifted out of sync between sections.

**Check:** sweep every quantitative statement (ranges, percentages, counts,
physical values, case numbers) and confirm it is consistent everywhere it appears.

**How / red flags:**
- A value that appears in exactly one place and is not backed by a figure or table.
- The same quantity with two different values in two sections.
- A case count or parameter range in the text that disagrees with the parameter
  table (e.g. text says "15 cases" but the table lists a different number).
- Suspiciously round or symmetric numbers in otherwise messy data.
- Citations to results, equations, sections, or figures by number that do not
  exist or point to the wrong place.

Distrust, verify, and flag rather than fix - a wrong number is the author's to
correct, not yours to guess.

## 5. Citation-claim support

**Why:** a citation attached to the wrong sentence, or a claim with no support, is
a substantive error a script cannot see (the script only checks that `[N]` has a
list entry).

**Check:** for each in-text `[N]`, read the sentence and the reference title and
confirm the reference plausibly supports that specific claim. Flag:
- A specific empirical or numeric claim with no citation where one is expected.
- A citation whose title is clearly about a different material, method, or process
  than the sentence claims.
- Placeholder citations the script already flagged (`[citation here?]`,
  `[citation if exist]`) - these are author TODOs; list them as blockers, never
  invent a reference.

## 6. Figure and table sub-panel cross-references

**Why:** the script verifies the figure *number* exists, but not the *panel
letters*. Multi-panel figures are where cross-refs rot, and a wrong panel letter is
invisible to a numbering check because the figure number itself is right.

**Check:** for each in-text reference to a sub-panel (e.g. "Figure 8a and 8b",
"Figure 10d", "Figure 21b-c"), read the caption's panel map and confirm:
- The cited panel letters exist. Captions usually enumerate them, e.g.
  "a-b) load group; c-d) speed group; e-f) temperature group".
- The letters match what the caption assigns each panel to. The classic failure is
  a panel reused across two groups: the body introduces the speed group as
  "Figure 8c and 8d", then introduces the temperature group as "Figure 8d and 8e" -
  panel d is claimed twice and the temperature group should read "8e and 8f". The
  figure number (8) is correct, so only a panel-by-panel read against the caption
  catches it.
- Caption and body agree on what the figure depicts (no leftover description from a
  superseded figure), and the panel-letter style in the caption (e.g. "c1-c6" vs
  "(c)") matches how the body cites it.

## 7. Heading, section, and equation numbering sanity

**Why:** sections get renumbered during restructuring. The script now flags
duplicate section numbers and sibling gaps mechanically (e.g. two `3.2.1` headings
left by a restructure), but the *semantic* layer still needs a read.

**Check:**
- Account for every FAIL in the scripted SECTIONS result (a duplicate number is
  always an error). Investigate each INFO sibling-gap - it may be intentional (a
  section deliberately removed) or a real omission.
- Account for every APPENDICES warning or failure. The scripted pass checks
  first-citation order, heading continuity, appendix equation continuity, and
  dangling `Eq. (A.n)` references; use `tools/renumber_appendices.py` for the
  deterministic rewrite, then verify that each moved appendix still supports the
  main-text sentence that cites it.
- In-text "Eq. (N)" / "Equation N" references point to the equation carrying that
  tag, and the equations are numbered contiguously (the `\#(N)` tags the script
  flags are the pandoc artifact, not the numbers themselves).
- Subsection cross-references ("as discussed in Section 2.1.4") resolve to the
  right section. A section referenced for two distinct topics should be
  intentional, not a stale pointer.

## 8. External notation table

**Why:** `notation.md` is maintained outside the draft, so a valid equation can
still leave the symbol table stale. The script can resolve equation tags and
detect recorded open issues, but it cannot decide whether a symbol's stated
meaning, scope, or units match the science.

**Check:**
- Every symbol introduced or used in an equation appears in `notation.md`, with
  the same spelling, accents, boldface, subscripts, and capitalization.
- Each entry gives the current meaning, units where applicable, and the actual
  introduction or equation location. Remove entries for symbols no longer used.
- A symbol is not assigned two meanings. Put a newly found collision under
  `Open notation issues` until it is resolved; list an intentional reuse under
  `Accepted notation reuse` only when the context makes the distinction clear.
- After any equation renumbering or appendix move, reconcile every equation
  location in the table and rerun the NOTATION preflight check.
- Read equations and surrounding prose together: all variables are introduced,
  vector/scalar notation is consistent, and the symbol table does not substitute
  a more convenient meaning for the one actually used in the manuscript.

Treat an incorrect or missing symbol definition as a blocker. A clearly recorded
open naming choice is review-level during drafting but must be resolved before
submission.

## 9. Full read-through: grammar, typos, and flow

**Why:** the targeted checks above each look at one axis. Grammar, word-choice,
agreement, tense, and flow errors are scattered through ordinary sentences, and
only a deliberate linear read of the whole manuscript catches them. This is the
copy-edit pass. The scripted PROSE check flags a curated set of typos and doubled
words mechanically; this section is the read a script cannot replace.

**How:** read the manuscript top to bottom as a reader would, not skimming. Keep a
running list and report each item with location and a suggested correction; do not
silently rewrite. Watch especially for the patterns a non-native author tends to
produce, where the tells cluster:

- **Word-confusion typos** a spellchecker misses because the word is real: "form"
  where "from" is meant, "donates" for "denotes", "real" for
  "reveal", "loose" for "loosely". Read for sense, not just spelling.
- **Verb form / tense**: "is tracing" -> "is traced", "is grinded" -> "ground",
  "are tunned" -> "tuned". Keep tense consistent: present for established facts and
  model behaviour, past for what was done in this study. A methods section that
  drifts between "we apply" and "we applied" reads as unfinished.
- **Subject-verb agreement**: "The interval between measurements are set" -> "is set",
  "three cross-section are measured" -> "cross-sections are".
- **Articles (a / an / the)** - the most frequent tell. "applies to unordered
  data set" -> "applies to an unordered data set", "from a choose sample" ->
  "from a chosen sample". Check every singular countable noun has its article.
- **Double modal / redundant verb**: "which will can be observed" -> "can be
  observed".
- **Singular / plural** of "cross-section", "dimension", "vortex / vortices", and
  units.
- **Run-ons and fragments**: a sentence like "However, since the sample is
  heated again in the second step." has no main clause - it is a
  fragment and needs its consequence, or a comma into the next sentence.
- **Awkward or ambiguous phrasing**, repeated words, and sentences so long the
  subject is lost before the verb.
- **Consistency**: one spelling per term throughout (and the house spelling per
  `terminology.md`), acronyms defined once at first use and not redefined,
  hyphenation consistent ("cross-section" vs "cross section").

Treat clear grammar errors and meaning-changing typos as **blockers for a clean
submission** - a reviewer will notice; minor style is review-level. The goal is a
manuscript that reads as finished, not merely machine-checked.

## 10. Paragraph length and structure: bloat, fragments, and mergeable pairs

**Why:** a paragraph is the unit a reader uses to follow an argument. Two
failure modes hide from every check above. A bloated paragraph repeats its own
topic sentence, restates numbers already given elsewhere, or carries a road-map
of the sections that follow. A fragment paragraph (under about 40 words) that is
not an equation lead-in or a "Here, ... is ..." definition usually belongs to the
paragraph before or after it, and splitting the two separates a conclusion from
its evidence. Both read as unfinished to a reviewer and inflate the word count.

**How:** tabulate the body paragraphs by section with their word counts (a short
script over the markdown, skipping headings, captions, image lines, equations,
tables, and list items) and read the outliers in context.

- **Bloat, upper tail:** read every paragraph well above the mean (look at those
  above about twice the mean body paragraph length).
  Ask of each sentence whether it adds a fact, a reason, or a step that no
  neighbouring sentence carries. Typical cuts: a justification given in full in
  two places (state it once and point to the section), a definition restated in
  a discussion section, numbers repeated from the section they were established
  in, a closing sentence that restates the opener, and the "Section X does A,
  Section Y does B" road-map beyond what a one-line orientation needs. Keep the
  numbers where they are first established (Abstract, Results); the Conclusions
  carry the direction of an effect, not its magnitude.
- **Fragments, lower tail:** for every body paragraph under about 40 words that
  is not an equation lead-in or the "Here, ..." line after an equation, ask
  whether it continues the previous paragraph or introduces the next. If its
  topic is the same, merge and drop the duplicated connective ("therefore"
  twice in a row, a forward pointer such as "The results below separate ..."
  that the merged paragraph makes redundant).
- **Logical pairs:** a short paragraph that interprets the numbers of the
  paragraph before it (an implication, a caveat, a comparison to the literature
  that turns on those numbers) is a merge candidate even when both are of
  ordinary length. A paragraph that mixes two topics (validation errors and
  parameter effects, motivation and model description) is a split-then-regroup
  candidate: move the second topic to join the paragraph that continues it.
- **Where a figure sits between the two halves**, move the image line to just
  after the paragraph that first cites the figure so the merged text stays
  contiguous.

Apply the house sentence rules when merging: the topic sentence stands alone, a
joined sentence stays at or below 30 words, no colon or semicolon as a sentence
join. Report each candidate with location, word counts, and the proposed
merged or trimmed text; do not silently rewrite, since the author reviews each
paragraph. Re-run the word count afterwards and quote the before/after body
count.

## 11. Logical redundancy: the same point made twice

**Why:** section 10 finds bloat by length. Redundancy of content is independent
of length: a justification argued in full in two sections, a Discussion
sentence copied verbatim into the Conclusions, a definition restated where the
term is used, or two sentences of one paragraph that say the same thing in
different words. Each costs words and, worse, invites the reviewer to look for
a difference between the two statements that is not there. Ordinary manuscripts
accumulate these through revision, when a point is added where it is needed
without removing it where it was.

**How:** the manuscript, not a script, is the source, but a grep pass makes the
read efficient. Take each load-bearing point and search for its distinctive
phrase across the whole file, then read every hit in context.

- **Justifications and assumptions:** an approximation argued in the methods
  ("the flow stays laminar at these Reynolds numbers, so no turbulence model is
  used") should appear once in full. The assumption list, the limitations
  section, and the appendix point to it ("(Section 2.1.4)") rather than
  re-arguing it.
- **Discussion versus Conclusions versus Abstract:** the Abstract and the
  Conclusions may echo the Discussion, but not in the same sentence. Search for
  the distinctive phrase of each conclusion and check that the
  Discussion states the argument and the Conclusions state the outcome in
  their own words. Three verbatim copies of one sentence is the usual find.
- **Definitions restated at use:** a metric defined in the methods
  ("the index $I$ measures how long the disturbance persists")
  should not be redefined in a results or summary paragraph that only uses it.
  Search for the defined symbol and read each prose sentence that carries it.
- **Numbers in more than two places:** a value belongs where it is established
  (a Results section) and may be repeated once where it is compared or in the
  Abstract. A third occurrence, especially in the Conclusions, is redundant;
  the Conclusions carry the direction and the order of magnitude of an
  effect, not its digits.
- **Within one paragraph:** a topic sentence that is restated by a later
  sentence of the same paragraph ("the coating fails once the load exceeds the
  threshold" and, two sentences on, "above the threshold load the coating
  fails"), or a closing sentence that repeats the opener. Keep one, usually the more
  specific.
- **Road-maps and back-summaries:** a section opener that lists what each
  subsection does, and a summary section that repeats what the subsections
  found, are both legitimate once. Check that the opener of section N does
  not also preview section N+1, and that the summary does not re-argue.
- **Symmetric pairs:** where a method treats two quantities alike (inlet and
  outlet, x and y), define them together ("the 95th percentiles of the
  nonzero x(t) and y(t) values") rather than in two parallel paragraphs or
  bullets that differ only in the subscript.

For each finding give both locations, quote the shorter duplicate, and say
which copy to keep and why (the one where the point is established, or the more
specific one). As in section 10, propose the wording; the author decides.

## Folding results into the report

Summarize each area as a one-line verdict in the combined report:

```
Status doc:  in sync | STALE (<which item>)
Abstract:    fresh | STALE (<which claim>)
Conclusions: fresh | STALE (<which>)
Numbers:     consistent | MISMATCH (<where>)
Citations:   supported | GAP (<where>)
Sub-panels:  resolve | BROKEN (<which ref>)
Sections:    clean | DUPLICATE/GAP (<which>)
Notation:    consistent | STALE (<symbol, where>)
Read-through: clean | ISSUES (<n grammar/typo>)
Paragraphs:  tight | BLOAT/FRAGMENT (<which>)
Redundancy:  none | DUPLICATE (<which point, where>)
```

A stale abstract/conclusion, a number mismatch, a duplicate section number, or a
meaning-changing grammar error or typo is a **blocker** - it should be fixed before
the docx is treated as submission-ready, even though pandoc will happily render it.
