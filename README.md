# Manuscript template for writing with an AI agent

A ready-made git repository layout and working method for writing a journal manuscript
with an AI coding agent (Claude Code, Codex, Copilot agent mode, Cursor, ...). The agent
edits a Markdown draft and keeps the records; you read the draft in VS Code, review each
change as a diff, and decide what is committed. Co-authors get a Word file rendered from the
draft.

```
you ── instruction ──▶ agent ── edits draft.md + companion files ──▶ uncommitted diff
 ▲                                                                       │
 └──── review in VS Code (Source Control) ◀── report + checks ◀──────────┘
        accept → "commit"     reject → revert / ask for a redo
```

## What you need

- **git**, **Python 3.9+**, **VS Code**, and an AI agent that can run commands in a folder.
- **pandoc 3+** to render the `.docx` (pandoc.org/installing). Python packages `numpy`,
  `matplotlib`, `pandas` and `Pillow` for figure scripts and small review copies.
- PowerShell or bash for the render scripts (both versions are included).

## Quick start: let the agent build the repository

1. Put this folder where your manuscripts live, e.g. `papers/_manuscript_template/`.
2. Open the parent folder (`papers/`) in VS Code and start your agent there (in the
   integrated terminal, or the agent's VS Code panel).
3. Give it this prompt:

   > Read `_manuscript_template/AGENT_SETUP.md` and set up a new manuscript repository for
   > me from this template. Ask me what you need first. Do not commit anything.

4. Answer its questions (folder, title, draft name, target journals, origin manuscript if
   it is a sequel). It runs `new_manuscript.py`, fills in what it knows, runs the checks and
   reports.
5. Open the new folder in VS Code (**File > Open Folder**), look through the files, and tell
   the agent to make the first commit.

Without an agent, run the script yourself:

```
python _manuscript_template/new_manuscript.py "my-paper" --name "My paper" --title "Full title" --draft "my paper draft"
```

## Daily work

**Read the draft.** Open `<draft>.md` and press `Ctrl+K V` (`Cmd+K V` on macOS): the
preview opens beside the source and follows it as you scroll. Equations (`$...$`,
`$$...\tag{1}$$`) and figures render in the preview. A few pandoc-only marks (`^a^`
superscripts, `{width=60%}`) show as plain text; the rendered `.docx` is what co-authors
see.

**Ask for one thing at a time.** "Tighten Section 3.2", "add the new case to Table 2 and
the text that cites it", "apply my comments in the 1649 AB docx to Section 4". The agent
follows `AGENTS.md` in the repository: it edits, updates the companion files (symbols,
terms, figure list, TODO), runs the checks, and reports with the tree left **uncommitted**.

**Track and review the agent's changes in VS Code.**

- **Source Control** view (`Ctrl+Shift+G`): every file the agent touched is listed. Click a
  file to open its diff; changed words are highlighted inside each paragraph, and word wrap
  is on (set in `.vscode/settings.json`) so long paragraphs stay readable.
- **Keep everything:** tell the agent "commit". It commits that one item with a message
  that says what the text now does.
- **Keep part of it:** select the lines you do not want in the diff and run
  **Git: Revert Selected Ranges** from the Command Palette (or click the revert arrow
  beside a change), then tell the agent what you reverted so it does not reapply it.
  **Stage Selected Ranges** works the same way if you prefer to commit yourself.
- **Drop it all:** ask the agent to undo its change, or use **Discard Changes** on the file
  (cannot be undone).
- **History:** the **Timeline** view (bottom of the Explorer sidebar) lists every commit
  that touched the open file; click one to see what it changed. GitLens (recommended when
  VS Code first opens the folder) adds line blame and a full history view. Because every
  commit is one reviewed item, the history reads as the manuscript's revision record.

**Decisions are written down.** Every choice you make ("keep the old figure", "call it
the reference case") goes into `TODO.md` with its date, and lasting wording rules go into
`writing_conventions.md` or `terminology.md`. A later session reads them before touching
the draft, so the same question is not reopened.

**Several agents at once.** One session per section or workstream; `TODO.md` records which
session owns what. The agents do not edit each other's sections.

## Co-author review through Word

1. Ask the agent to render: it runs the preflight first, reports, then writes the `.docx`
   (`-Jpg` gives a small review copy).
2. Share the copy named with date and time, e.g. `my paper draft 2026-01-15 1649.docx`.
3. Co-authors comment or track changes in Word. Give the marked-up file back to the agent
   section by section; it ports the edits to the Markdown, one commit per section. The
   `.docx` itself is never edited as the source.

For a larger review round the agent keeps a `revision_todo_vX.Y.md` with one line per
comment (by its Word comment ID), each closed as applied or declined with the reason.

## What is in this folder

| Path | What it is |
|---|---|
| `AGENT_SETUP.md` | Step-by-step instructions the agent follows to build a new repository |
| `METHOD.md` | The method: roles, the working loop, review rounds, records, commits, parallel sessions, figures, citations, finalization |
| `new_manuscript.py` | The scaffold script (standard library only) |
| `skeleton/` | The files a new repository starts with |

A new repository contains:

| File | Role |
|---|---|
| `<draft>.md` | The manuscript (the only source; the `.docx` is rendered from it) |
| `AGENTS.md`, `CLAUDE.md` | Rules for AI agents (`CLAUDE.md` imports `AGENTS.md` for Claude Code) |
| `METHOD.md` | Copy of the method |
| `README.md` | Status, structure, provenance, how to render |
| `TODO.md` | Open items and the decision log |
| `writing_conventions.md` | Prose rules: paragraphs, sentences, figures, equations |
| `terminology.md` | One term per concept; checked automatically |
| `notation.md` | Symbol table; checked automatically |
| `known_inconsistencies.md` | Accepted differences between text and code, so they are not re-raised |
| `figures/` | Figures by content name, their scripts, and the figure-number map |
| `references/` | One `.bib` per cited paper, the citation map and audit, the related-work record |
| `tools/` | Renumber appendices, citations, figures and tables; citation usage map; word count; section extract |
| `.claude/skills/manuscript-to-docx/` | Pre-render checks, render scripts, Word styles, review checklist |
| `.claude/skills/paper-download/` | Turns `references/download_list.md` into named PDFs in `references/`: DOI verification on Crossref, the open-access copies found on OpenAlex fetched at a polite rate, a list of the closed papers for you to get through your library, a collector that names and files the PDFs you save, a finalizer that ticks the list |
| `.vscode/` | Word wrap for prose and diffs, LF line endings, recommended extensions |

## Adapting it

- **Wording rules:** `writing_conventions.md` and `terminology.md` hold the house style.
  Edit them freely; add a term to `terminology.md` the first time a reviewer flags a
  variant, and the checker enforces it from then on.
- **Word layout:** pass a journal's template with `-ReferenceDoc` (PowerShell) or
  `--reference-doc` (bash), or edit `assets/reference.docx` in the skill folder.
- **Agents other than Claude Code** read `AGENTS.md`; if yours uses another file name
  (e.g. `.github/copilot-instructions.md`), point that file at `AGENTS.md`.

## License

MIT No Attribution (MIT-0), see [`LICENSE`](LICENSE): use, copy and change the template
freely; the files it copies into a new manuscript repository need no notice. One file has
another origin: `skeleton/.claude/skills/manuscript-to-docx/assets/reference.docx` is
derived from pandoc's default reference document (pandoc is GPL-2.0-or-later) and holds
only page and paragraph styles.
