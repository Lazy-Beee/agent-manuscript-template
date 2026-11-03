---
name: paper-download
description: Download the open-access PDFs of a manuscript's reading list into its references/ folder from a DOI list (the manuscript template's download_list.md, or any list of DOIs) - verify the DOIs on Crossref, look up each paper's open copies on OpenAlex, fetch them with a plain script at a polite rate, name each file "<First author> - <Year> - <Title>.pdf", and list the papers without an open copy for the user to get through their library; PDFs the user saves by hand are then paired with their DOI and filed the same way. Use this whenever the user wants papers, PDFs or references downloaded, fetched, collected or pulled for a manuscript or a literature review, asks to check or verify DOIs or reference entries, or asks which papers are open access, even when the word "download" is not used.
---

# Paper download

Turns a reading list with DOIs into named PDFs in a manuscript repository's `references/`
folder, the way the template keeps them: one PDF per paper, named `<First author> - <Year> -
<Title>.pdf`, gitignored, with a `.bib` added only when the paper is cited. The scripts here
are the ones that run; every path is an argument.

The skill downloads **open-access copies only**, from the locations OpenAlex lists for each
paper (repositories, preprint servers, publisher pages). It does not drive a browser on
publisher sites and does not download through a subscription. A paper without an open copy
goes on a list for the user, who gets it through their library and saves it; the collector
then names and files it like the others.

## What it expects

- **The list.** The template's `references/download_list.md` format, one paper per line:
  `- [ ] First author (Year). Title. *Journal*. https://doi.org/DOI`, grouped under headings
  `## Priority A (N)`, `## Priority B (N)`, `## Priority C ...`. A plain list of DOIs is turned
  into this form first (`scripts/verify_dois.py` returns the first author, year, title and
  journal of each DOI from Crossref).
- **A staging folder** outside the repository (the session's scratch directory) where PDFs
  land before they are checked; `references/` receives only verified files.
- **Python 3.9+**, and PyMuPDF (`pip install pymupdf`) for the collector.

## Rules that come with the method

- **Open copies only.** Fetch only the URLs the manifest lists for papers OpenAlex marks open
  access: nothing behind a sign-in, no browser automation on publisher sites. If the user asks
  for subscription papers to be fetched in bulk, say that most licence terms forbid automated
  downloading, and point to their library and to the publishers' text-and-data-mining APIs.
- **Rate.** One request at a time with a pause between requests (the scripts' defaults). The
  metadata APIs get `--mailto` when the user gives an address; leave it out rather than
  inventing one.
- **One download run per machine.** The servers see one machine and one network, so the limit
  is per machine, not per session. `fetch_oa_pdfs.py` goes through `scripts/fetch_gate.py`, a
  machine-wide lease with a log of fetch slots (state in `%LOCALAPPDATA%\paper-download\`,
  `~/.local/state/paper-download/` elsewhere, or the `PAPER_DOWNLOAD_STATE` folder). When the
  script answers `BUSY` (exit code 3), another session is downloading: tell the user who it is
  and how far it got, run `python -I scripts/fetch_gate.py wait` in the background (it exits
  when the lease is free, after at most 3 h, without taking it), then run the fetch again.
  Never fetch around the gate. `fetch_gate.py status` shows the lease and the last log lines;
  `fetch_gate.py clear --run` removes a lease whoever holds it and is run only on the user's
  word.
- **Downloading needs the user's go.** The request to download the list is that go; say what
  will be fetched (the priority, the count, the destination) before starting, and report what
  landed and what did not.
- **PDFs are gitignored** in the repository; never force-add one. The `.bib` is written only
  when the citation goes into the draft (the repository's `references/README.md` rule).

## Steps

### 1. Verify the DOIs (once per list)

```
python -I scripts/verify_dois.py <in.tsv> <out.tsv> [--mailto you@example.org]
```

`in.tsv` has one `DOI<TAB>expected title` per line (title may be empty). The script resolves
each DOI on the Crossref REST API and compares the registered title with the expected one:
`OK` (match), `CHECK` (partial), `MISMATCH`, `RESOLVES` (no expected title), `FAIL`. Fix or
drop anything that is not `OK` or `RESOLVES` before downloading; a wrong DOI fetches the wrong
paper.

### 2. Build the manifest

```
python -I scripts/build_manifest.py "<repo>/references/download_list.md" <staging_dir> <manifest.json> --priority A [--mailto you@example.org]
```

For every unticked line of that priority whose file is not yet in staging, the script asks
OpenAlex for the open-access status (`gold`, `hybrid`, `bronze`, `green`, `closed`) and the
PDF URL of every open location, repository copies first, since repositories serve a plain
script more often than publisher sites do. It writes `manifest.json`, a list of `{doi, first,
year, file, status, landing, pdfs}` (`landing` is the doi.org link), and prints the counts per
status.

### 3. Fetch the open copies

```
python -I scripts/fetch_oa_pdfs.py <manifest.json> <staging_dir> [--dry-run]
```

For each open entry the script tries the listed URLs in order and keeps the first response
whose body starts with `%PDF-`, named from the manifest. Repositories (OSTI, IOP, HAL,
university repositories, arXiv) usually serve the file; many publisher sites answer a script
with an HTML page or 403 even for open-access papers, so some open papers join the closed ones
on the list the script prints at the end: the entries left for the user, with their doi.org
links and the reason.

The script first opens a run on the fetch gate. `GO` (after `TOOK-OVER` when it took over the
lease of a session that has exited or fell silent) means it fetches; `BUSY` means it requested
nothing (see the rule above). A `WARN` about PDFs in Downloads means files arrived there while
no gated run was open: another session fetching without the gate, or the user saving by hand;
tell the user. The run ends when the script exits (`ENDED`).

### 4. Papers the user gets

Give the user that list grouped by priority. They open each paper through their library's
normal access (or ask for an interlibrary loan or the author's copy) and save the PDFs in one
folder, usually Downloads, under any name. Then:

```
python -I scripts/collect_batch.py "<repo>/references/download_list.md" "<folder>" <staging_dir> --priority A [--since EPOCH]
```

moves every PDF in that folder whose first pages contain a pending DOI into staging under the
list name (a paper printed before DOIs, which carries none, is paired by its title and first
author). It looks only at files newer than `--since` (default: the last two hours); pass the
time the user started saving when that is earlier.

### 5. Finalize

```
python -I scripts/finalize_pdfs.py "<repo>" <staging_dir>
```

moves the staged files into `references/` without overwriting and ticks their lines in
`download_list.md`; the list is the record of what is on disk, so commit that change (and
nothing binary).

## Report

Say, in the language of the conversation: how many files landed per priority and where,
which entries are left for the user (closed, no PDF URL, or a page served instead of the PDF),
which files the collector left unmatched, any `BUSY`, `TOOK-OVER` or `WARN` line the gate
printed, and that the PDFs are gitignored and the list is ticked.
