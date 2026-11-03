#!/usr/bin/env python3
"""Renumber a manuscript's numeric citations into order of first appearance.

The manuscript body cites references as backslash-escaped brackets -- single
``\\[12\\]`` or comma groups ``\\[6, 7, 8, 9, 10\\]`` (no ranges) -- and the
``# References`` section lists one entry per number, ``\\[12\\] Author, ...``.
This tool rebuilds the numbering so the reference first cited earliest becomes
[1], the next new one [2], and so on, rewriting every in-text citation (inside
groups too) and reordering the reference list to match.

Default is a DRY RUN: it prints the old->new map, flags anomalies, and writes
nothing. Pass --write to apply the change in place. Running it on an
already-ordered manuscript is a no-op (idempotent).

Run ``renumber_appendices.py`` first: moving appendix blocks can change where a
reference first appears. Run ``renumber_figures_tables.py`` afterward.

    python tools/renumber_citations.py                 # dry-run on the default draft
    python tools/renumber_citations.py --write         # apply
    python tools/renumber_citations.py other.md --write # a different manuscript

Safety: if any in-text citation has no matching reference entry, it refuses to
--write (that would silently mangle a broken citation). Uncited reference
entries are kept, numbered after all cited ones, and reported as a warning.
"""
import argparse
import os
import re
import sys

# In-text citation group: \[ digits (, digits)* \]  (backslash-escaped brackets).
CITE_RE = re.compile(r"\\\[(\d+(?:\s*,\s*\d+)*)\\\]")
# Start of a reference-list entry: line beginning with \[N\].
REF_START_RE = re.compile(r"^\\\[(\d+)\\\]")
REF_HEADER = "# References"


def default_md(repo_root):
    """The manuscript draft, or the sole manuscript *.md at the repo root."""
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


def split_body_refs(text):
    """(body, refs_block, header_line). refs_block starts at the header."""
    idx = text.find("\n" + REF_HEADER)
    if idx == -1:
        raise SystemExit(f"No '{REF_HEADER}' section found.")
    cut = idx + 1  # keep the leading newline on the body side
    return text[:cut], text[cut:]


def parse_ref_entries(refs_block):
    """List of (old_num:int, entry_text:str) preserving multi-line entries."""
    lines = refs_block.splitlines(keepends=True)
    entries, cur, cur_num = [], [], None
    for ln in lines:
        m = REF_START_RE.match(ln)
        if m:
            if cur_num is not None:
                entries.append((cur_num, "".join(cur)))
            cur_num, cur = int(m.group(1)), [ln]
        elif cur_num is not None:
            cur.append(ln)
    if cur_num is not None:
        entries.append((cur_num, "".join(cur)))
    return entries


def appearance_order(body):
    """Distinct citation numbers in order of first appearance (groups scanned L-to-R)."""
    order = []
    for m in CITE_RE.finditer(body):
        for tok in m.group(1).split(","):
            n = int(tok.strip())
            if n not in order:
                order.append(n)
    return order


def build_map(order, ref_nums):
    """old->new for cited refs (appearance order), then uncited refs appended."""
    mapping = {n: i + 1 for i, n in enumerate(order)}
    nxt = len(order) + 1
    uncited = sorted(set(ref_nums) - set(order))
    for n in uncited:
        mapping[n] = nxt
        nxt += 1
    return mapping, uncited


def rewrite_body(body, mapping):
    def repl(m):
        nums = [int(t.strip()) for t in m.group(1).split(",")]
        newn = sorted(mapping[n] for n in nums)
        return "\\[" + ", ".join(str(n) for n in newn) + "\\]"
    return CITE_RE.sub(repl, body)


def rewrite_refs(refs_block, entries, mapping):
    header_end = refs_block.find("\n", refs_block.find(REF_HEADER)) + 1
    head = refs_block[:header_end]                       # "# References\n" (+ blank line kept below)
    # preserve a single blank line after the header if present
    rest = refs_block[header_end:]
    lead_blanks = len(rest) - len(rest.lstrip("\n"))
    ordered = sorted(entries, key=lambda e: mapping[e[0]])
    body_entries = []
    for old, txt in ordered:
        new = mapping[old]
        txt = REF_START_RE.sub(f"\\\\[{new}\\\\]", txt, count=1)
        body_entries.append(txt.rstrip("\n"))
    return head + ("\n" * lead_blanks) + "\n\n".join(body_entries) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Renumber citations to order of appearance.")
    ap.add_argument("mdfile", nargs="?", help="manuscript .md (default: the draft in the repo root)")
    ap.add_argument("--write", action="store_true", help="apply changes in place (default: dry run)")
    args = ap.parse_args(argv)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md = args.mdfile or default_md(repo_root)
    text = open(md, encoding="utf-8").read()

    body, refs_block = split_body_refs(text)
    entries = parse_ref_entries(refs_block)
    ref_nums = [n for n, _ in entries]
    order = appearance_order(body)

    # anomalies
    dup = sorted(n for n in set(ref_nums) if ref_nums.count(n) > 1)
    undefined = [n for n in order if n not in set(ref_nums)]
    mapping, uncited = build_map(order, ref_nums)

    print(f"manuscript: {md}")
    print(f"  in-text citations (distinct): {len(order)}   reference entries: {len(entries)}")
    changed = {o: n for o, n in mapping.items() if o != n}
    if changed:
        print(f"  renumbering {len(changed)} reference(s):")
        for o in sorted(changed, key=lambda k: mapping[k]):
            print(f"    [{o}] -> [{mapping[o]}]")
    else:
        print("  already in order of appearance (no change).")
    if uncited:
        print(f"  WARNING: {len(uncited)} reference(s) never cited (placed last): {uncited}")
    if dup:
        print(f"  WARNING: duplicate reference numbers in the list: {dup}")
    if undefined:
        print(f"  ERROR: cited but missing from the reference list: {undefined}")

    if not args.write:
        print("\n(dry run -- pass --write to apply)")
        return 1 if undefined else 0

    if undefined:
        print("\nRefusing to write: fix the missing reference entries first.")
        return 2
    if not changed:
        print("\nNothing to write.")
        return 0

    new_text = rewrite_body(body, mapping) + rewrite_refs(refs_block, entries, mapping)
    open(md, "w", encoding="utf-8", newline="\n").write(new_text)
    print(f"\nWrote renumbered citations to {md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
