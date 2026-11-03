# {{NAME}} — manuscript

**Manuscript:** {{TITLE}}

**Reference baseline:** {{BASELINE}}

## Target journals

Submission priority:

1. *(to be decided)*

**Status ({{DATE}}):** repository created from the manuscript template. Nothing is drafted
yet; open work is tracked in `TODO.md`.

**Working source:** `{{DRAFT}}.md` (Markdown, equations as LaTeX with `\tag{N}`,
hand-numbered reference list, content-named figures in `figures/`). Rendered to `.docx`
with the bundled `manuscript-to-docx` skill (preflight first, then render). The `.docx` is
the deliverable for co-authors and journals; re-render after each committed change before
sharing.

**Structure:**

- **Abstract** — *(to be written last)*.
- **§1 Introduction** — *(to be written)*.
- **§2 Methodology** — 2.1 Model; 2.2 Experiment design.
- **§3 Validation** — *(to be written)*.
- **§4 Results** — *(sections to be planned)*.
- **§5 Limitations** — *(to be written; renumbered as results sections are added)*.
- **§6 Conclusions** — *(to be written last)*.
- **Appendix A** — *(supplementary details)*.
- **References** — none yet; new citations take the next free number until the
  finalization renumbering.

> **Repo rule: do not modify `archive/` without explicit permission.** It is a frozen
> record (reviewed docx versions, closed review rounds) and is gitignored.

**Versions.** *(None yet. Each version is a git tag on the commit it was rendered from;
its `.docx` is frozen in `archive/` by the author. Record: version, date, purpose, tag and
commit, render options and page count.)*

**Checks before each version** (tag and render):

1. Open `TODO.md` items that the version needs are closed or deferred with the author.
2. `notation.md` and `terminology.md` match the draft; no open notation issues.
3. Citation audit (`references/citation_audit.md`): every citation added or whose usage
   changed since the last version is source-checked, every entry is cited, and the labels
   follow the current numbering. The first version audits every entry.
4. Preflight (below) with no FAIL; each WARN accepted or fixed.
5. Render to `.docx` and check the figure placement in the exported PDF.

## Computational and data provenance

Fill this in when the case set is fixed: the code version (tag and commit) behind every
case, the executable, a per-run acceptance check, and which tags must not be deleted. Run
bookkeeping lives next to the data, not here.

| Case set | Code tag | Commit | Executable / environment | Status |
|---|---|---|---|---|

## Layout

| Path | Role |
|------|------|
| `{{DRAFT}}.md` | **Working source** (edit this) |
| `TODO.md` | **Decision log and open items**; data-state block at the top |
| `AGENTS.md`, `CLAUDE.md` | Rules for AI agents working here (`CLAUDE.md` imports `AGENTS.md`) |
| `METHOD.md` | The writing-interaction method behind these rules |
| `writing_conventions.md` | **Prose standard**: paragraphs, sentences, figures, equations, source format |
| `terminology.md` | **Wording standard**: one preferred term per concept; feeds the preflight |
| `notation.md` | **Symbol table**: meaning, unit, location, open issues, accepted reuse |
| `known_inconsistencies.md` | **Accepted text-versus-implementation differences**; do not re-raise |
| `figures/` | Content-named PNGs (gitignored); `figures/README.md` holds the only figure-number map; `figures/scripts/` the generators |
| `references/` | One `.bib` per cited paper; PDFs gitignored; text sidecars in `extracted_text/`; the usage map (`README.md`), the citation audit and the related-work record |
| `tools/` | Renumbering (appendices, citations, figures/tables), citation usage map, word count, section extract |
| `.claude/skills/manuscript-to-docx/` | Preflight checker, render scripts, Lua filters, reference doc, judgment checklist |
| `.claude/skills/paper-download/` | DOI verification, the open-access lookup and download, and the collector and finalizer scripts for `references/download_list.md` |
| `.vscode/` | Editor settings for reading the draft and reviewing diffs |
| `archive/` | Frozen history (gitignored, read-only) |

## Reading and reviewing in VS Code

- Open this folder in VS Code. Open `{{DRAFT}}.md` and press `Ctrl+K V` (`Cmd+K V` on
  macOS) for the preview beside it; equations and figures render there. Pandoc-only syntax
  (`^a^` superscripts, `{width=60%}`) shows as plain text; the docx is the faithful render.
- An agent's edits appear in the **Source Control** view (`Ctrl+Shift+G`) as uncommitted
  changes. Click a file to see the diff; word wrap is on, so long paragraphs stay readable.
- Accept: tell the agent to commit (or commit from that view yourself). Reject a part:
  select the lines in the diff and run **Git: Revert Selected Ranges** from the Command
  Palette (or use the revert arrow beside a change block), then tell the agent what you
  reverted. Reject all of a file: **Discard Changes** (cannot be undone).
- History: the **Timeline** view (Explorer sidebar) lists the commits that touched the open
  file; GitLens (recommended in `.vscode/extensions.json`) adds blame and history views.

## Render command

Needs pandoc 3 or later on `PATH` (and Python with Pillow for `-Jpg`).

```
python .claude/skills/manuscript-to-docx/scripts/preflight_check.py "{{DRAFT}}.md" --terminology terminology.md --notation notation.md
.claude/skills/manuscript-to-docx/scripts/render.ps1 "{{DRAFT}}.md"          # PowerShell
.claude/skills/manuscript-to-docx/scripts/render.ps1 "{{DRAFT}}.md" -Jpg     # small review copy
bash .claude/skills/manuscript-to-docx/scripts/render.sh "{{DRAFT}}.md"      # bash
```

Do not keep the output `.docx` open in Word while rendering; Word locks the file.

## Word count

```
python tools/wordcount.py
```

Reports the Abstract, the body (§1 to Conclusions), body with captions, and the main-text
total, approximating Word (equations, tables, captions, references and citation brackets
excluded).

## Conventions

- **Figures** are content-named and authored at most 6.5 in wide with 10 pt text
  (`figures/README.md`, `figures/scripts/figstyle.py`); reordering touches only the `.md`.
- **Terminology and punctuation** follow `terminology.md` (no em-dashes in prose).
- **Git policy** (`.gitignore`): version the text (`.md`) and scripts (`.py`) only;
  binaries and derived data are regenerable and untracked. `git add -f` force-tracks a
  frozen data file that must be kept.
