#!/usr/bin/env python3
"""Map every reference-list entry to its uses in the draft, for the citation audit.

For each entry ``\\[N\\]`` (or plain ``[N]``) under ``# References``, wrapped over several
lines or not, it records every citation group in the body that names N (inside groups
too): the heading it sits under, the first line of its paragraph, and the sentence holding
the marker. It also matches each entry to a ``.bib`` in ``references/`` (first author and
year, then title similarity) and notes whether the PDF and the text sidecar
(``references/extracted_text/<stem>.txt``) exist.

Output (written to --out, default ``references/audit_work/``, gitignored):
  usage.json             all entries, machine-readable
  usage_<label>.md       one usage pack per batch, handed to whoever audits that batch

    python tools/citation_usage_map.py                              # one pack, all entries
    python tools/citation_usage_map.py --batches 1-12,13-25,26-40   # one pack per range
    python tools/citation_usage_map.py --override 14=none --override "17=Author - 2019 - Title"

Read-only on the draft. Check every match scored below about 0.7 by hand and fix it with
--override (``N=none`` for an entry with no .bib, e.g. a companion manuscript).
"""
import argparse
import difflib
import glob
import json
import os
import re
import sys

CITE_RE = re.compile(r"\\?\[(\d+(?:\s*,\s*\d+)*)\\?\]")      # \[N\] or [N], groups too
ENTRY_RE = re.compile(r"^\\?\[(\d+)\\?\]\s*(.*)$", re.M)
REF_HEADER = "# References"


def parse_entries(refs):
    """{N: entry text} from the reference list. An entry may be written ``\\[N\\]`` or
    ``[N]`` and may wrap over several lines; its lines are joined with one space."""
    joined = re.sub(r"\n(?!\s*\n|\\?\[\d+\\?\])", " ", refs)
    return {int(n): re.sub(r"\s+", " ", e.replace("\\", "")).strip()
            for n, e in ENTRY_RE.findall(joined)}


def split_body_refs(text):
    idx = text.find("\n" + REF_HEADER)
    if idx == -1:
        raise SystemExit(f"No '{REF_HEADER}' section found.")
    return text[:idx + 1], text[idx + 1:]


def collect_uses(body):
    """{N: [ {line, section, group, sentence}, ... ]} in body order."""
    uses = {}
    heading, para, start = "", [], None

    def flush():
        if not para:
            return
        p = " ".join(para)
        for m in CITE_RE.finditer(p):
            s0 = p.rfind(". ", 0, m.start())
            s0 = 0 if s0 < 0 else s0 + 2
            s1 = p.find(". ", m.end())
            s1 = len(p) if s1 < 0 else s1 + 1
            sentence = p[s0:s1].replace("\\[", "[").replace("\\]", "]").strip()
            group = m.group(0).replace("\\", "")
            for tok in m.group(1).split(","):
                uses.setdefault(int(tok), []).append(
                    {"line": start, "section": heading, "group": group, "sentence": sentence})

    for i, ln in enumerate(body.split("\n"), 1):
        if ln.startswith("#"):
            flush()
            para, start = [], None
            heading = ln.lstrip("#").strip()
        elif not ln.strip():
            flush()
            para, start = [], None
        else:
            if start is None:
                start = i
            para.append(ln.strip())
    flush()
    return uses


def bib_titles(ref_dir):
    out = {}
    for path in glob.glob(os.path.join(ref_dir, "*.bib")):
        stem = os.path.basename(path)[:-4]
        text = open(path, encoding="utf-8", errors="replace").read()
        m = re.search(r"\btitle\s*=\s*[{\"](.+?)[}\"]\s*,?\s*\n", text, re.I | re.S)
        title = m.group(1) if m else stem.split(" - ", 2)[-1]
        out[stem] = re.sub(r"[{}\s]+", " ", title).strip().lower()
    return out


def entry_title(entry):
    m = re.search(r'"(.+?),?"', entry.replace('\\"', '"'))
    return (m.group(1) if m else entry).lower()


STEM_RE = re.compile(r"^(?P<author>.+?) - (?P<year>\d{4}) - ")


def stem_author_year(stem):
    """First author's surname (lower case) and year from a '<Author> - <Year> - <Title>' stem;
    (None, None) when the stem is not of that form."""
    m = STEM_RE.match(stem)
    if not m:
        return None, None
    author = re.split(r"\s+(?:et al\.?|and)\s+|,", m.group("author"))[0].strip().lower()
    return (author or None), m.group("year")


def title_overlap(title, entry_tokens):
    """Share of the .bib title's words (four letters or more) that occur in the entry."""
    words = [w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) >= 4]
    return sum(1 for w in words if w in entry_tokens) / len(words) if words else 0.0


def best_match(entry, titles):
    """Best .bib stem for a reference-list entry: (score, stem).

    Stems whose first author and year both occur in the entry are the candidates; only
    when none does are all stems ranked. The score of a candidate is the larger of the
    title similarity (difflib, for entries with a quoted title) and the share of the
    .bib title's words found in the entry (for entries written as 'Authors, Title,
    Journal ...'), so an unquoted entry can reach a trusted score too."""
    tokens = set(re.findall(r"[a-z0-9]+", entry.lower()))
    t = entry_title(entry)[:100]
    guarded = []
    for stem in titles:
        author, year = stem_author_year(stem)
        if author and year and year in tokens and author in tokens:
            guarded.append(stem)
    pool = guarded or list(titles)
    scored = sorted(((max(difflib.SequenceMatcher(None, t, titles[k][:100]).ratio(),
                          title_overlap(titles[k], tokens)), k) for k in pool), reverse=True)
    return scored[0] if scored else (0.0, None)


def parse_batches(spec, numbers):
    if not spec:
        return [("all", numbers)]
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        lo, hi = int(a), int(b or a)
        out.append((f"{lo}-{hi}", [n for n in numbers if lo <= n <= hi]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("draft", nargs="?", help="the draft .md (default: the only draft at the repo root)")
    ap.add_argument("--refs", default="references", help="references directory")
    ap.add_argument("--out", default=os.path.join("references", "audit_work"))
    ap.add_argument("--batches", help="comma-separated ranges, e.g. 1-12,13-25")
    ap.add_argument("--override", action="append", default=[],
                    help="N=<bib stem> or N=none; repeatable")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")   # .bib stems may hold characters outside the console code page
    except Exception:
        pass

    draft = args.draft
    if draft is None:
        skip = {"README.md", "TODO.md", "AGENTS.md", "CLAUDE.md", "METHOD.md",
                "writing_conventions.md", "terminology.md", "notation.md",
                "known_inconsistencies.md"}
        mds = [f for f in os.listdir(".") if f.endswith(".md") and f not in skip]
        if len(mds) != 1:
            raise SystemExit("Could not pick the draft; pass it explicitly.")
        draft = mds[0]

    body, refs = split_body_refs(open(draft, encoding="utf-8").read())
    entries = parse_entries(refs)
    uses = collect_uses(body)
    titles = bib_titles(args.refs)
    overrides = dict(o.split("=", 1) for o in args.override)

    data = {}
    for n in sorted(entries):
        score, stem = best_match(entries[n], titles)
        if str(n) in overrides:
            stem, score = (None if overrides[str(n)].lower() == "none" else overrides[str(n)]), 1.0
        has = lambda p: bool(stem) and os.path.isfile(p)
        data[n] = {
            "entry": entries[n], "stem": stem, "match": round(score, 2),
            "pdf": has(os.path.join(args.refs, f"{stem}.pdf")),
            "txt": has(os.path.join(args.refs, "extracted_text", f"{stem}.txt")),
            "uses": uses.get(n, []),
        }

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "usage.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    for label, nums in parse_batches(args.batches, sorted(data)):
        with open(os.path.join(args.out, f"usage_{label}.md"), "w", encoding="utf-8", newline="\n") as f:
            for n in nums:
                d = data[n]
                files = "none"
                if d["stem"]:
                    files = (f"`{d['stem']}` .bib" + (" + .pdf" if d["pdf"] else " (no PDF)")
                             + (" + text sidecar" if d["txt"] else " (no text sidecar)"))
                f.write(f"## [{n}]\n\nEntry: {d['entry']}\n\nFiles: {files}\n\n"
                        f"Uses in the draft ({len(d['uses'])}):\n\n")
                for u in d["uses"]:
                    f.write(f"- line {u['line']}, \"{u['section']}\", {u['group']}: {u['sentence']}\n")
                f.write("\n")

    uncited = [n for n in data if not data[n]["uses"]]
    missing = sorted(set(uses) - set(entries))
    for n, d in data.items():
        flag = "" if d["match"] >= 0.7 or str(n) in overrides else "  <-- check match"
        print(f"[{n}] {d['match']:.2f} {'pdf' if d['pdf'] else '---'} "
              f"{'txt' if d['txt'] else '---'} {len(d['uses']):2d} uses  {d['stem'] or 'NO .bib'}{flag}")
    print(f"\n{len(data)} entries; uncited: {uncited or 'none'}; cited but not listed: {missing or 'none'}")
    print(f"Written to {args.out}")


if __name__ == "__main__":
    main()
