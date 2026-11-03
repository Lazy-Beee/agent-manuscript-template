# {{NAME}}: rules for AI agents

You are working in a manuscript repository. The author decides content and wording and
reviews every change; you edit, check, record and report. The background for these rules is
in `METHOD.md`.

## Never without the author's explicit word

- **Commit.** Leave your edits uncommitted and say so; the author reviews them first (for
  example in VS Code's Source Control view). A commit instruction covers only the edits
  that exist when it is given: "commit, then do X" means commit what is there, do X, and
  leave X uncommitted.
- Push, tag, upload, publish, send messages, or delete files.
- Edit anything under `archive/` (frozen history).
- Decide a content question that belongs to the author: list it instead.

## At the start of a session

1. Read `README.md` (status, structure, provenance) and, in `TODO.md`, the data-state
   block and the block of the section you are asked to work on. If TODO says that section
   is handed to another session or person, stay out of it and tell the author.
2. Authorities: `writing_conventions.md` (prose), `terminology.md` (words), `notation.md`
   (symbols), `known_inconsistencies.md` (accepted text-versus-code differences; never
   re-raise one), `figures/README.md` (the only figure-number map).

## While working

- **One item at a time:** one section, one decision, or one figure. A finding outside that
  item is reported, not folded in.
- **The working source is `{{DRAFT}}.md`.** The `.docx` is a render; never edit it.
- **Change the companion files in the same edit:** a symbol goes to `notation.md`, a term
  decision to `terminology.md`, a figure change to `figures/README.md`, the decision to
  `TODO.md`.
- **Smallest sufficient edit.** Keep numbers, conditions and qualifiers. Never invent a
  number or a citation to fill a gap; mark it and ask.
- **Line endings stay LF;** scripted edits write with `newline="\n"`. Files on disk are in
  English, whatever language the conversation uses.
- **Every number in the text has a source:** a frozen data file or a `stats_*.py` script in
  `figures/scripts/`.

## Before reporting

- `git diff --check`
- The preflight:
  `python .claude/skills/manuscript-to-docx/scripts/preflight_check.py "{{DRAFT}}.md" --terminology terminology.md --notation notation.md`
- The renumber tools as dry runs when numbering changed (`python tools/renumber_*.py`).
- `git ls-files --eol` on touched files (want `w/lf`).

## Report

What changed and where (`file:line`), what the checks say, what is still open, the points
that need the author's decision, and that the tree is **uncommitted**.

## Recording

- Each decision goes into `TODO.md` with its date and source: "(author, YYYY-MM-DD)", or a
  reviewer's comment ID. Options considered and not chosen stay, with the reason.
- A lasting rule goes to `writing_conventions.md` or `terminology.md` with its provenance.
- Run or experiment bookkeeping (launch commands, progress, archiving) goes to a notes file
  next to the data, not into this repository; TODO keeps a one-line pointer.

## Commits (when told)

One item per commit, staged alone; leave anyone else's uncommitted edits unstaged. No
AI-attribution trailer unless the author asks for one. Prefixes: `text(fix)`, `text(feat)`,
`text(restructure)`, `text(style)`, `figures(feat|fix|data)`, `notation(fix)`,
`docs(todo)`, `docs`, `tools(...)`. The subject says what the text now does, naming the
section: `text(fix): Section 5.4 cites Section 5.1 for the onset time, now that Section 4.2
no longer carries it`.

## Rendering

On request: preflight, report, then
`.claude/skills/manuscript-to-docx/scripts/render.ps1 "{{DRAFT}}.md"` (or `render.sh`);
`-Jpg` / `--jpg` for a small review copy. Full procedure:
`.claude/skills/manuscript-to-docx/SKILL.md`.
