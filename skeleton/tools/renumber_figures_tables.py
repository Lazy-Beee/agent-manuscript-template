#!/usr/bin/env python3
"""Renumber a manuscript's figures and tables into document (caption) order.

Finalization companion to ``renumber_appendices.py`` and
``renumber_citations.py``; run this one last because moving appendix blocks can
change appendix caption order. Each figure is numbered by the position
of its caption in the document: the first caption becomes Figure 1, the next
Figure 2, and so on; tables likewise, in their own independent sequence. Every
in-text mention and every caption label is rewritten in place. This slots a
caption appended out of sequence (for example a resolution figure whose caption
sits in Section 2.1.8 but was numbered last) into its correct position and shifts
the rest, without touching the caption blocks physically.

Numbering by caption position (rather than by first citation, as the reference
tool does) is deliberate: figures have a fixed place in the document, and the
final numbering should match it. The journal rule "cite figures in order" is
instead checked and REPORTED: if a figure is first cited out of numerical order,
the tool warns so the prose (or the caption position) can be fixed by hand.

Reference forms handled (figures; tables are the same without panels/ranges):
  Figure 8            plain
  Figure 9a           panel-letter suffix (letter preserved: 9a -> Na)
  Figure 8a and 8b    panel join (same figure)
  Figures 8(a) and 8(d)  parenthesised panel join (same figure; suffix kept)
  Figures 30 and 31   figure join (two figures)
  Figures 24-32       en-dash / hyphen / "to" range (expanded, kept as a range)
  Fig. 6              abbreviation
A caption is a line beginning ``Figure N.`` / ``Table N.``.

Default is a DRY RUN: it prints the old->new map, flags anomalies, writes nothing.
Pass --write to apply in place. Idempotent (a no-op on an already-ordered file).

    python tools/renumber_figures_tables.py                 # dry-run on the draft
    python tools/renumber_figures_tables.py --write         # apply
    python tools/renumber_figures_tables.py other.md --write

Safety: refuses to --write if a mention has no caption, or if a range cannot be
preserved as a contiguous range after renumbering (that would silently change
which figures the range covers). Captioned figures/tables never mentioned in the
prose are numbered after all mentioned ones and reported.
"""
import argparse
import os
import re
import sys

# A number token, optionally carrying a panel suffix: a bare letter (9a, 23e) or a
# parenthesised panel spec as the house style writes it (9(a), 14(c), 15(d–e), 5(a, d)).
# The parenthesised branch is tried first, because the letter branch also matches "".
TOKEN_RE = re.compile(r"(\d+)(\([^()]{0,16}\)|[a-z]?)")
# Separator that denotes an inclusive range between two bare numbers.
RANGE_RE = re.compile(r"^\s*(?:–|—|-|to)\s*$")

# Self-references use the full word "Figure"/"Table"; the abbreviated "Fig." in
# the house style is reserved for EXTERNAL figures (e.g. "Fig. 6c therein" in a
# cited paper), so it is deliberately NOT a keyword -- matching it would corrupt
# the numbering with another work's figure numbers.
KINDS = {
    "figure": dict(caption="Figure", keywords=["Figures", "Figure"]),
    "table":  dict(caption="Table",  keywords=["Tables", "Table"]),
}


def default_md(repo_root):
    cand = os.path.join(repo_root, "{{DRAFT}}.md")
    if os.path.isfile(cand):
        return cand
    mds = [f for f in os.listdir(repo_root) if f.endswith(".md")
           and f not in ("README.md", "TODO.md", "AGENTS.md", "CLAUDE.md", "METHOD.md",
                         "terminology.md", "notation.md", "writing_conventions.md",
                         "known_inconsistencies.md")]
    if len(mds) == 1:
        return os.path.join(repo_root, mds[0])
    raise SystemExit("Could not auto-pick the manuscript .md; pass it explicitly.")


def ref_regex(keywords):
    kw = "(?:" + "|".join(keywords) + ")"      # plural forms listed first
    item = r"\d+(?:\([^()]{0,16}\)|[a-z]?)"     # also "N(x)" panel suffixes, so "Figures 10(a) and 10(d)" is one reflist
    conn = r"(?:\s*,\s*and\s*|\s*,\s*|\s*and\s*|\s*to\s*|\s*/\s*|\s*[–—-]\s*)"
    reflist = item + r"(?:" + conn + item + r")*"
    return re.compile(r"(" + kw + r")(\s*)(" + reflist + r")")


def caption_starts(text, caption_word):
    """{char offset: number} for every line beginning 'Figure N.' / 'Table N.',
    in document order."""
    rx = re.compile(r"(?m)^" + caption_word + r"\s+(\d+)\.")
    return [(m.start(), int(m.group(1))) for m in rx.finditer(text)]


def _tokens(reflist):
    return list(TOKEN_RE.finditer(reflist))


def mentioned_numbers(reflist):
    """Distinct-in-order numbers a reference names, expanding ranges."""
    toks = _tokens(reflist)
    nums = []
    for i, m in enumerate(toks):
        n = int(m.group(1))
        if i > 0:
            sep = reflist[toks[i - 1].end():m.start()]
            if RANGE_RE.match(sep) and not toks[i - 1].group(2) and not m.group(2):
                prev = int(toks[i - 1].group(1))
                step = 1 if n >= prev else -1
                for x in range(prev + step, n, step):
                    nums.append(x)
        nums.append(n)
    return nums


def ranges_in(reflist):
    """List of (a, b) bare-number endpoints joined by a range separator."""
    toks = _tokens(reflist)
    out = []
    for i in range(1, len(toks)):
        sep = reflist[toks[i - 1].end():toks[i].start()]
        if RANGE_RE.match(sep) and not toks[i - 1].group(2) and not toks[i].group(2):
            out.append((int(toks[i - 1].group(1)), int(toks[i].group(1))))
    return out


def rewrite_reflist(reflist, mapping):
    out, last = [], 0
    for m in _tokens(reflist):
        out.append(reflist[last:m.start()])
        out.append(str(mapping[int(m.group(1))]) + m.group(2))
        last = m.end()
    out.append(reflist[last:])
    return "".join(out)


def analyze(text, kind):
    cfg = KINDS[kind]
    rx = ref_regex(cfg["keywords"])
    caps = caption_starts(text, cfg["caption"])
    cap_start_offsets = {off for off, _ in caps}
    cap_nums = [n for _, n in caps]                         # document order

    # primary numbering: caption position in the document
    mapping = {n: i + 1 for i, n in enumerate(cap_nums)}

    # scan mentions for the citation-order / coverage checks (not for numbering)
    cited, seen = [], set()
    range_pairs = []
    for m in rx.finditer(text):
        reflist = m.group(3)
        range_pairs += ranges_in(reflist)
        if m.start() in cap_start_offsets:                 # a caption line
            lead = _tokens(reflist)[0]                      # its leading 'N.' defines
            nums = mentioned_numbers(reflist[lead.end():])  # only trailing cross-refs count
        else:
            nums = mentioned_numbers(reflist)
        for n in nums:
            if n not in seen:
                seen.add(n); cited.append(n)

    undefined = [n for n in cited if n not in mapping]      # mentioned, no caption
    orphans = [n for n in cap_nums if n not in seen]        # captioned, never mentioned
    dup = sorted(n for n in set(cap_nums) if cap_nums.count(n) > 1)

    # ranges that cannot stay contiguous after renumbering
    broken = []
    for a, b in set(range_pairs):
        if a in mapping and b in mapping:
            lo, hi = sorted((a, b))
            new = sorted(mapping[x] for x in range(lo, hi + 1) if x in mapping)
            if new != list(range(new[0], new[-1] + 1)) or len(new) != hi - lo + 1:
                broken.append((a, b))

    # citation order (journal rule): first-citation sequence as NEW numbers
    new_cite_seq = [mapping[n] for n in cited if n in mapping]
    inversions = [(new_cite_seq[i], new_cite_seq[i + 1])
                  for i in range(len(new_cite_seq) - 1)
                  if new_cite_seq[i] > new_cite_seq[i + 1]]

    return dict(rx=rx, caps=caps, mapping=mapping, undefined=undefined,
                orphans=orphans, dup=dup, broken=broken, inversions=inversions)


def rewrite(text, kind, mapping):
    rx = ref_regex(KINDS[kind]["keywords"])
    def repl(m):
        return m.group(1) + m.group(2) + rewrite_reflist(m.group(3), mapping)
    return rx.sub(repl, text)


def report(kind, a):
    print(f"[{kind}s]")
    print(f"  captions: {len(a['caps'])}")
    changed = {o: n for o, n in a["mapping"].items() if o != n}
    if changed:
        print(f"  renumbering {len(changed)}:")
        for o in sorted(changed, key=lambda k: a["mapping"][k]):
            print(f"    {kind.capitalize()} {o} -> {a['mapping'][o]}")
    else:
        print("  already in order of appearance (no change).")
    if a["orphans"]:
        print(f"  WARNING: captioned but never cited in the prose: {a['orphans']}")
    if a["dup"]:
        print(f"  WARNING: duplicate caption numbers: {a['dup']}")
    if a["inversions"]:
        pairs = ", ".join(f"{kind.capitalize()} {x} before {y}" for x, y in a["inversions"])
        print(f"  WARNING: cited out of order (new numbers): {pairs}. "
              f"Renumbering still applies, but consider reordering the prose so figures "
              f"are first cited in ascending order.")
    if a["broken"]:
        print(f"  ERROR: range(s) cannot stay contiguous after renumbering: {a['broken']}")
    if a["undefined"]:
        print(f"  ERROR: mentioned but no caption: {a['undefined']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Renumber figures and tables to order of appearance.")
    ap.add_argument("mdfile", nargs="?", help="manuscript .md (default: the draft in the repo root)")
    ap.add_argument("--write", action="store_true", help="apply changes in place (default: dry run)")
    ap.add_argument("--only", choices=["figure", "table"], help="restrict to one kind")
    args = ap.parse_args(argv)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md = args.mdfile or default_md(repo_root)
    text = open(md, encoding="utf-8").read()
    kinds = [args.only] if args.only else ["figure", "table"]

    print(f"manuscript: {md}")
    analyses, fatal = {}, False
    for kind in kinds:
        a = analyze(text, kind)
        analyses[kind] = a
        report(kind, a)
        if a["undefined"] or a["broken"]:
            fatal = True

    if not args.write:
        print("\n(dry run -- pass --write to apply)")
        return 1 if fatal else 0
    if fatal:
        print("\nRefusing to write: resolve the ERROR(s) above first.")
        return 2

    new_text = text
    wrote = False
    for kind in kinds:
        a = analyses[kind]
        if any(o != n for o, n in a["mapping"].items()):
            new_text = rewrite(new_text, kind, a["mapping"]); wrote = True
    if not wrote:
        print("\nNothing to write.")
        return 0
    open(md, "w", encoding="utf-8", newline="\n").write(new_text)
    print(f"\nWrote renumbered figures/tables to {md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
