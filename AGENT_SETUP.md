# Instructions for the AI agent: set up a new manuscript repository

The author has given you this template folder and asked you to set up a manuscript
repository from it. Work through the steps below in order. Do not commit, push or delete
anything at any step; the author reviews the result first.

## 1. Read

Read `README.md` and `METHOD.md` in this folder, and `skeleton/AGENTS.md` (the rules you
will follow inside the new repository).

## 2. Ask the author, in one message

1. **Where** the repository should go (parent folder) and its **folder name**.
2. The **full title** (a working title is fine) and a **short name** for headings.
3. The **draft file name** (without `.md`), e.g. `my paper draft`.
4. **Target journals**, in order of priority (can be left open).
5. Whether it is a **sequel** to an existing manuscript repository (its path), so that the
   origin commit is recorded and the house-style files can be copied from it.
6. If the author already has text (a Word draft, notes, an outline): where it is.

Offer sensible defaults where the author has none (for example the folder name from the
short name). Do not guess the title.

## 3. Check the tools

- `git --version` and `python --version` (Python 3.9 or later; the scaffold needs only the
  standard library).
- `pandoc --version` (3.0 or later) is needed for rendering the `.docx`; if it is missing,
  say how to install it (pandoc.org/installing) but continue: the repository works without
  it until the first render.
- For figures and `-Jpg` renders: `numpy`, `matplotlib`, `pandas`, `Pillow`. Report what is
  missing; do not install anything without the author's yes.

## 4. Create the repository

```
python new_manuscript.py "<folder>" --parent "<parent>" --name "<short name>" --title "<title>" --draft "<draft stem>" [--origin "<path of the origin repository>"] [--into-existing]
```

Run it with `--dry-run` first if anything about the paths is unclear. The script copies
the skeleton, fills the placeholders, and runs `git init` without committing.

If the manuscript grows out of a folder that already exists (an exploration or notes folder
that becomes the repository), pass `--into-existing` with that folder as `<folder>`: the
script writes only files that do not exist yet, keeps an existing `.git`, and stops without
writing anything if a skeleton file would overwrite one of the folder's own files (`README.md`,
`TODO.md`, `tools/`, ...). Move those aside first; see "Converting an existing folder" below.

## 5. Fill what is known

- `README.md`: target journals; the structure if the author gave one.
- `TODO.md`: the data-state block (what data exist and where); one item per section to
  draft; the open questions the author raised.
- Draft: the author line, if given. Leave every other placeholder as it is.
- For a sequel: compare the origin's `writing_conventions.md`, `terminology.md`,
  `notation.md` and `known_inconsistencies.md` with the new copies and list what could be
  carried over; carry over only what the author approves.
- If the author has an existing Word draft: convert it with
  `pandoc "<file>.docx" -t markdown+tex_math_dollars --wrap=none -o "<draft stem>.md"`
  only after the author agrees, then clean the result (equation tags to `\tag{N}`, captions
  as `Figure N.` paragraphs, images into `figures/` with content names). Report what the
  conversion lost.

### Converting an existing folder

When the repository is built on a folder that already holds work (`--into-existing`):

- **Old files go to one subfolder** (for example `exploration/`): plans, reviews, reading
  notes, superseded drafts, first-pass scripts, data and figures, and the folder's own old
  `README.md`, `TODO.md` and `notation.md`. Give the subfolder a `README.md` that lists them
  and maps old paths to new ones, and do not revise them: they are the record behind the
  numbers.
- **Scripts and data the draft's numbers depend on are not old.** Move them to
  `figures/scripts/` and `figures/scripts/figdata/`, update their path constants, and check
  that every script compiles, resolves its inputs and regenerates its figures unchanged.
- **An existing Markdown draft is converted to the template's source format**, with its
  wording unchanged: level-1 section headings, one paragraph per line, `\[N\]` citations,
  an `![](figures/<content>.png)` paragraph before each `Figure N.` caption, the author-line
  and keyword placeholders, the end-matter sections. What the conversion cannot place
  (references listed but not cited, a table without a lead sentence, off-house-style terms)
  goes to `TODO.md` for the author, not into the text.
- **The companion files are filled from the draft:** the notation table, the figure
  provenance table, one `.bib` per cited paper (from any combined candidate list), the
  references usage map, the terminology table (from the origin manuscript, when there is
  one).
- Decide nothing the author has not decided: record the defaults you chose (short name,
  draft file name) in `TODO.md` so they can be changed in one place.

## 6. Verify

From the new repository:

```
python .claude/skills/manuscript-to-docx/scripts/preflight_check.py "<draft stem>.md" --terminology terminology.md --notation notation.md
python -m unittest discover -s tools/tests
git status
```

The preflight should report FAIL=0, the tests should pass, and `git status` should list the
new files as untracked, among them
`.claude/skills/manuscript-to-docx/assets/reference.docx`: the skeleton's `.gitignore`
excepts it from the `*.docx` rule, so the first commit carries the render's reference
document and a clone can render the draft.

## 7. Report and hand over

Tell the author:

- the folder that was created and what you filled in;
- the check results;
- how to open it: **File > Open Folder** in VS Code (or `code "<path>"`), then open the
  draft and press `Ctrl+K V` (`Cmd+K V` on macOS) for the side-by-side preview;
- that the files are uncommitted, and the proposed first commit message
  (`docs: create the <short name> manuscript repository from the template`);
- that from now on you work by the rules in the repository's `AGENTS.md`: one item at a
  time, every change left uncommitted for review in VS Code's Source Control view, a
  commit only on the author's word.
