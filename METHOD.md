# Manuscript writing-interaction method

How the authors and AI coding agents write a journal manuscript together in a git
repository: the agent edits a Markdown draft and keeps the records, the author reviews
every change and decides. The method grew out of writing several simulation-and-experiment
papers this way, through collaborator and advisor review rounds and a journal submission.
The rules an agent follows day to day are condensed in each repository's `AGENTS.md`; this
file explains them.

Where this file and a repository's own `writing_conventions.md` or `terminology.md`
disagree, the repository file wins for that manuscript.

---

## 1. Roles

| Who | Does | Does not |
|---|---|---|
| **Author** (the person driving the agent) | Decides content, structure, wording and scope; reviews every diff or rendered docx; gives the word to commit, push, upload or delete; relays co-author and advisor decisions; coordinates parallel agent sessions | |
| **Co-authors / advisor** | Review rendered docx copies (comments, tracked changes, meeting decisions) | Edit the Markdown |
| **AI agent** | Edits the `.md` and its companion files, runs the checks, renders on request, records every decision, reports the state | Commit, push, publish, upload, delete or message other sessions unasked; decide a content question that belongs to the author |

The conversation can be in any language. **Files on disk are written in the manuscript's
language** (English for most journals): draft, TODO, README, notes, scripts, commit
messages.

## 2. The repository is the manuscript record

- **One manuscript, one git repository.** The history is the revision record: one reviewed
  item per commit, so any sentence can be traced to the decision that produced it.
- **The Markdown is the single working source** (equations in LaTeX, hand-numbered
  reference list). The `.docx` is a derived render and is never edited by hand; edits a
  co-author makes in a docx are ported back into the Markdown.
- **Lean git policy.** Tracked: text (`.md`) and scripts (`.py`, `.ps1`). Untracked:
  `.docx`, `.pptx`, `.pdf`, images, `.npz`, `.csv`, `archive/`. Frozen figure data that
  must be kept is force-added (`git add -f`). Text is stored with LF line endings.
- **`archive/` is frozen and read-only** (reviewed docx versions, closed review records).
- **Companion files and their authority:**

  | File | Authority over | Rule |
  |---|---|---|
  | `README.md` | Status, structure, target journals, provenance, layout, render command | The status line carries its date |
  | `TODO.md` | Open items, the data state, every decision with its date and source | The decision log; see Section 5 |
  | `writing_conventions.md` | Paragraph, sentence, figure and equation style | Each rule carries its provenance |
  | `terminology.md` | One preferred term per concept; spelling, hedging, punctuation | Its table feeds the preflight checker |
  | `notation.md` | Symbol meaning, unit and location; open and accepted reuse | Updated in the same edit as the equation |
  | `known_inconsistencies.md` | Accepted differences between the text and the implementation | Entries only after the author accepts them; never re-raised |
  | `figures/README.md` | Figure provenance; the only place figure numbers appear | Figures are content-named, so reordering is a Markdown-only change |
  | `references/README.md`, `citation_audit.md` | Citation number to `.bib` map; claim-support audit | Reconciled after every renumbering; the audit is a check before each version |
  | `references/related_work_comparison.md` | Positioning against the closest prior work | Off-manuscript, for the rebuttal |

- **Numbers are assigned late.** During drafting a new citation takes the next free number
  and a new figure gets a content name; appendices, citations and figures/tables are
  renumbered by script at finalization (Section 11).

## 3. The working loop

1. **Start of session.** The agent reads `README.md`, the `TODO.md` data-state block and the
   block of the section in question, and the conventions files, and checks who owns that
   section (Section 8).
2. **Scope one item.** An instruction becomes one item: one section, one decision, one
   figure. A finding outside it is reported, not folded in.
3. **Edit.** Companion files change in the same edit as the draft: a symbol goes to
   `notation.md`, a term decision to `terminology.md`, a figure change to
   `figures/README.md`, the decision to `TODO.md`.
4. **Check.** `git diff --check`; the preflight; the renumber tools as dry runs when
   numbering is touched; `git ls-files --eol` on touched files; the word count when length
   matters.
5. **Report.** What changed and where, what the checks say, what is open, which points need
   the author's decision, and that the tree is uncommitted.
6. **Author review** of the diff (VS Code Source Control view) or of a rendered docx.
7. **Commit on the word.** One item per commit, staged on its own (Section 7).
8. **Record.** The decision goes into `TODO.md` and, if it is a lasting rule, into the
   conventions file it belongs to, with the date and its source.

**Work section by section.** Revise one section, get it approved, commit it alone; run the
mechanical checks once at the end of a pass.

## 4. The docx review loop

- **Render** with the bundled skill: preflight first, report, then `render.ps1` /
  `render.sh`. A review copy uses `-Jpg` (small file); a submission copy does not.
- **Share for review** by uploading a copy named with its date and time
  (`<draft name> YYYY-MM-DD HHmm.docx`) to the shared drive the co-authors use; render it
  outside the repository so the working docx is unchanged.
- **Port the review back.** A marked-up copy is referred to by its upload time and the
  reviewer's initials ("the 1649 AB docx"). Each section's edits become one commit:
  `text(fix): apply the review of the 1649 AB docx to Section 4.2 (...)`, with the
  substance of the changes in the parentheses.
- **Review rounds.** The reviewed docx and the marked-up copies are frozen in `archive/`.
  A `revision_todo_vX.Y.md` lists every item with a stable ID (Word comment IDs `C8`;
  tracked edits `T1`; points of a separate note `W1`; advisor-meeting items `AD1`;
  round-level decisions `D1`). Round-level decisions are settled before any section work;
  each item closes as applied or declined, with the reason and the commit hash; the closed
  round moves to `archive/`.
- **A benchmark section.** A section the advisor has revised and approved becomes the prose
  benchmark for the rest, recorded in `writing_conventions.md`.
- **Rules come out of reviews.** A recurring review comment becomes a rule in
  `writing_conventions.md` or `terminology.md`, with the comment ID and date, and the whole
  draft is then swept for it.

## 5. What is recorded where

**`TODO.md` is the decision log.**

- A dated **data-state block** at the top says which data the text uses and what is
  pending.
- Items are grouped by section or workstream: a checkbox, a bold title, then the state
  (`DONE YYYY-MM-DD`, `DECIDED`, `DRAFTED, awaiting author review`), the commit hash, and
  the original item kept below the resolution.
- Decisions carry their source ("(author, YYYY-MM-DD)", "(advisor meeting ...)", a
  reviewer's comment ID); the author's reasoning is quoted.
- Options considered and not chosen stay, with the reason, so the question is not raised
  again.
- A renumbering is recorded once with its old-to-new map.

**What stays out of the manuscript repository:** run and experiment bookkeeping (launch
commands, progress, archiving), which goes to a notes file next to the data, with a pointer
from TODO; campaign plans, which live with the data; scratch analysis, until it backs a
number in the text and becomes a `freeze_*` or `stats_*` script.

## 6. Writing rules in brief

The authority is the repository's `writing_conventions.md` and `terminology.md`.

- One idea per paragraph, topic sentence first; merge fragments; split at the seam.
- One function per sentence, ordered conclusion, evidence, explanation, significance; a
  claim may carry its immediate consequence, never through a colon or semicolon; about 30
  words at most.
- Plain engineering wording, one term per concept, conventional journal verbs, no
  em-dashes.
- Explain a figure before using it; cite it once; captions describe only.
- Rounded results are written bare; "approximately" only for real estimates.
- State causes qualitatively; no "explains N% of"; no closing "remains unexplained".
- No run bookkeeping in the text (re-runs, repeat runs, seeds); data appear as the case's.
- Smallest sufficient edit; a language pass changes no logic and answers no other review
  item; after a restructure, check the Abstract, roadmap and Conclusions for stale claims.
- Abstract and Conclusions are written last.

## 7. Commits

- **Only on an explicit instruction**, and only the edits that exist when it is given.
- **One item per commit, staged alone;** another session's uncommitted edits stay unstaged.
- **No AI-attribution trailer** unless the authors want one.
- **Message style:**

  | Prefix | For |
  |---|---|
  | `text(fix):` | A correction or a review edit in the draft |
  | `text(feat):` | New content in the draft |
  | `text(restructure):` | Content moved, merged or split |
  | `text(style):` | Wording or punctuation only |
  | `figures(feat):` / `figures(fix):` / `figures(data):` | A new figure, a figure change, frozen data |
  | `notation(fix):` | `notation.md` and the symbols it tracks |
  | `docs(todo):` | `TODO.md` only |
  | `docs:` | README and the other companion files |
  | `tools(...):` | Scripts under `tools/` |

  The subject says what the text now does, in the present tense, naming the section.
- Pushing, tagging and publishing are the author's acts.

## 8. Parallel sessions

- **One agent session per workstream** (a section, a figure set, a data campaign). When a
  section is handed off, its TODO heading says so with the date, and the handoff states
  what the receiving session owns.
- **Stay inside the owned scope.** A handoff note that lists edits elsewhere does not
  authorize them; findings about other sections go to the author.
- **Changes that touch other sessions** (a renumbering, a renamed term, a moved file) are
  recorded in TODO or README, and the author is told which sessions they affect; no
  broadcast messages between sessions.
- **Holds.** A section the author has put on hold (waiting for data, for example) is not
  edited until the hold is lifted.

## 9. Figures

- Content-named PNGs in `figures/`; `figures/README.md` maps each to its draft number,
  script and data.
- `figures/scripts/`: `freeze_*.py` extracts data read-only into `figdata/`; `fig_*.py`
  draws one figure from `figdata/`; `stats_*.py` prints numbers quoted in the text.
- House style in `figstyle.py`: at most 6.5 in wide (the docx column), 10 pt text (DejaVu
  Sans 10 pt matches a 12 pt Aptos body in x-height), 11 pt bold panel tags, 600 dpi;
  `save()` warns when a figure is wider than the column. Check the placed size in the
  rendered docx.
- Units in brackets only when the quantity has one; superseded figures move to
  `figures/retire/`.

## 10. Citations

- One `.bib` per cited paper, named like its PDF; PDFs gitignored; text sidecars for
  full-text claim checks.
- A reading list with DOIs goes into `references/download_list.md` (one line per paper,
  by priority); the `paper-download` skill verifies the DOIs on Crossref, downloads the
  open-access copies at a polite rate, lists the closed papers for the author to get through
  the library, names and files the PDFs, and ticks the list, which is the record of what is
  on disk.
- Only claim-matched citations, checked in the full text where the claim depends on detail;
  none for journal-name coverage.
- In-text citations are `\[N\]`; a new one takes the next free number until finalization.
- **Citation audit** (`references/citation_audit.md`): every entry gets a verdict (ACCURATE,
  ACCURATE-NUANCE, MISMATCH, NOT-FOUND) with the claim, the source location and a short
  quote. `tools/citation_usage_map.py` lists each entry's uses in the draft and writes one
  usage pack per batch, so batches of 10 to 15 entries can be audited by parallel agents
  that read the repository only. Usage is always checked anew, even for an entry a sibling
  manuscript has audited. The audit reports findings; the author decides each fix.
- **Related-work record** (`references/related_work_comparison.md`): a comparison table of
  the closest prior studies, the gap in one line, and per-paper rebuttal notes. It stays out
  of the draft; the Introduction carries the positioning in prose.

## 11. Finalization

In this order, each step a dry run first:

1. `python tools/renumber_appendices.py --write`
2. `python tools/renumber_citations.py --write`; reconcile the citation maps, record the
   old-to-new map in TODO
3. `python tools/renumber_figures_tables.py --write`; update `figures/README.md`
4. Reconcile `notation.md`; resolve every open issue
5. Preflight plus the judgment checks of the skill's `references/checklist.md`, reported
   before anything is fixed
6. Render and verify the docx

**Checks before each version.** A version (a git tag plus its rendered `.docx`, frozen in
`archive/`) is cut only after: the TODO items it needs are closed or deferred; notation and
terminology match the draft; the citation audit covers every citation added or changed
since the last version; the preflight shows no FAIL; and the render's figure placement is
checked. The list lives in the repository README.

**Journal variants.** A journal-adapted copy lives in `journal/<journal>/` and is generated
from the master draft by a script of exact-anchor replacements that stops when the master
drifts; it is never edited by hand. Content any journal benefits from goes into the master.

## 12. Provenance

- README names the code version behind every case (tag and commit), the executable or
  environment, a per-run acceptance check, and what changed in the code since. Trust a tag
  over a build-time version stamp, and keep the tags that anchor history a squash merge
  would orphan.
- A run that fails validation is discarded with a note next to the data, not described in
  the text.

## 13. Sibling manuscripts

- A sequel starts from this template with `--origin`, which records the origin manuscript
  and its commit as the reference baseline.
- Shared house-style files are kept in sync; a rule changed in one manuscript is ported to
  the other with a dated note.
- Sync audits are recorded in the sequel's TODO as "audit against <origin>
  `<from>..<to>`", one ported item per commit.
