#!/usr/bin/env python3
"""Prose word count for the manuscript draft, broken down by section.

Approximates a Word-style count of the Markdown source. Excludes content that
does not count toward a journal's manuscript-text limit: display/inline LaTeX
($$...$$ and $...$), Markdown tables, image tags, Figure/Table caption lines
(numeric and appendix "Figure A.1" style), citation brackets (\\[n\\]), and
heading markers. A standalone ``Keywords:`` line is also excluded.

Usage:
    python tools/wordcount.py                 # counts the repo draft
    python tools/wordcount.py path/to/file.md
    python tools/wordcount.py --depth 3       # also break down level-3 subsections

Sections are discovered from the Markdown headings themselves (levels 1-3), so
adding/renaming sections needs no change here. "Main text" is the sum of the
Abstract and the numbered sections (1-4); the Title block, any Appendix, and the
References list are reported separately and excluded from the main-text total.
"""
import os
import re
import sys

DEFAULT_DRAFT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "{{DRAFT}}.md",
)


def clean(text, drop_captions=True):
    text = re.sub(r"\$\$.*?\$\$", " ", text, flags=re.S)
    text = re.sub(r"\$[^$]*\$", " ", text)
    text = re.sub(r"!\[.*?\]\([^)]*\)", " ", text)
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("|") or s.startswith("!["):
            continue
        if s.lower().startswith("keywords:"):
            continue
        # Drop caption lines only: "Figure 5. ...", "Table 1. ...", "Figure A.1. ..."
        # The trailing period after the number distinguishes a real caption from a
        # body paragraph that merely opens with a reference ("Figure 8 compares ...").
        if drop_captions and re.match(r"(Table|Figure)\s+(?:[A-Z]\.)?\d+\.", s):
            continue
        lines.append(ln)
    text = "\n".join(lines)
    text = re.sub(r"\\?\[[\d,\s\-]+\\?\]", " ", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.M)
    return text.replace("\\", " ")


def count(text):
    return sum(1 for t in text.split() if re.search(r"[A-Za-z0-9]", t))


def parse_headings(lines):
    """Return [(level, title, line_index), ...] for ATX headings, levels 1-3."""
    heads = []
    for i, ln in enumerate(lines):
        m = re.match(r"^(#{1,3})\s+(.*\S)\s*$", ln)
        if m:
            heads.append((len(m.group(1)), m.group(2).strip(), i))
    return heads


def span(lines, heads, k):
    """Raw text of section heads[k], up to the next heading of level <= its own."""
    level, _, start = heads[k]
    end = len(lines)
    for h in heads[k + 1:]:
        if h[0] <= level:
            end = h[2]
            break
    return "\n".join(lines[start:end])


def kind(title):
    if title.lower().startswith("title"):
        return "title"
    if title.lower().startswith("abstract") or re.match(r"\d", title):
        return "main"
    if title.lower().startswith("appendix"):
        return "appendix"
    if title.lower().startswith("reference"):
        return "references"
    return "other"


def main(argv):
    rest = list(argv[1:])
    depth = 2
    if "--depth" in rest:
        i = rest.index("--depth")
        depth = int(rest[i + 1])
        del rest[i:i + 2]
    args = [a for a in rest if not a.startswith("--")]
    path = args[0] if args else DEFAULT_DRAFT

    with open(path, encoding="utf-8") as f:
        txt = f.read()
    lines = txt.splitlines()
    heads = parse_headings(lines)

    print(f"file : {os.path.basename(path)}")
    print("prose words (excl. math, tables, captions, citations, headings)\n")

    WIDTH = 46
    main_total = appendix_total = 0
    for k, (level, title, _) in enumerate(heads):
        knd = kind(title) if level == 1 else None
        # track current top-level kind for indented children
        if level == 1:
            cur_kind = knd
        if level > depth:
            continue
        if level == 1 and cur_kind in ("title", "references"):
            continue  # skip Title block and References list entirely
        c = count(clean(span(lines, heads, k)))
        indent = "  " * (level - 1)
        label = f"{indent}{title}"
        dots = "." * max(3, WIDTH - len(label))
        print(f"{label} {dots} {c:>5}")
        if level == 1 and cur_kind == "main":
            main_total += c
        if level == 1 and cur_kind == "appendix":
            appendix_total += c

    # caption-inclusive main text, for journals that count captions
    main_incl_cap = 0
    for k, (level, title, _) in enumerate(heads):
        if level == 1 and kind(title) == "main":
            main_incl_cap += count(clean(span(lines, heads, k), drop_captions=False))

    print("-" * (WIDTH + 6))
    print(f"{'main text (Abstract-Conclusions)':<{WIDTH}} {main_total:>5}")
    print(f"{'  + with figure/table captions':<{WIDTH}} {main_incl_cap:>5}")
    if appendix_total:
        print(f"{'Appendix (separate)':<{WIDTH}} {appendix_total:>5}")
        print(f"{'main text + Appendix':<{WIDTH}} {main_total + appendix_total:>5}")


if __name__ == "__main__":
    main(sys.argv)
