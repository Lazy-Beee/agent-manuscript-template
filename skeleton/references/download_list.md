# Papers to download

The papers this manuscript's literature work needs on disk, by reading priority (A: likely
cited, read first; B: supporting; C: optional), one per line in this exact form, which the
`paper-download` skill's scripts parse:

`- [ ] First author (Year). Title. *Journal volume, pages*. https://doi.org/DOI`

A ticked box (`[x]`) means the PDF is in this folder as `<First author> - <Year> -
<Title>.pdf` (PDFs are gitignored; this list is the record). Verify every DOI on Crossref
before it goes here (`verify_dois.py` in the skill); add the `.bib` beside the PDF when the
citation is written into the draft (`README.md`, rule for adding a reference).

## Priority A (0)

## Priority B (0)

## Priority C (optional) (0)

## Already on disk, not to download

*(Papers whose PDF a sibling manuscript's `references/` already holds; copy the PDF and `.bib`
when the citation is written.)*
