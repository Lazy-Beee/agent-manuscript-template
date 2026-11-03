#!/usr/bin/env python3
"""Reorder manuscript appendices by first citation and repair dependent numbering.

The first appendix cited in the main text becomes Appendix A.1, the next new
appendix becomes A.2, and so on. Complete ``## A.n`` blocks are moved into that
order. The tool then rewrites:

* ``Appendix A.n`` / ``Appendices A.n and A.m`` references;
* appendix headings; and
* appendix equation tags and ``Eq. (A.n)`` references in physical equation order.

Figure A.1 / Table A.1 numbering is deliberately untouched; run
``renumber_figures_tables.py`` afterward because moving appendix blocks can
change caption order. Run ``renumber_citations.py`` afterward for the same reason.

Default is a dry run. ``--write`` applies the deterministic rewrite in place.
The tool refuses to write on duplicate/gapped appendix headings, references to
undefined appendices or appendix equations, or ranges whose meaning would change.

    python tools/renumber_appendices.py
    python tools/renumber_appendices.py --write
    python tools/renumber_appendices.py other.md --write
"""
import argparse
import os
import re
import sys


APPENDIX_HEADER_RE = re.compile(r"(?m)^#\s+Appendix\b.*$")
REFERENCES_HEADER_RE = re.compile(r"(?m)^#\s+(?:References|Bibliography)\s*$")
APPENDIX_HEADING_RE = re.compile(r"(?m)^##\s+A\.(\d+)\s+.+$")
APP_TOKEN_RE = re.compile(r"A\.(\d+)")
APP_ITEM = r"A\.\d+"
LIST_CONN = r"(?:\s*,\s*(?:and\s+)?|\s+and\s+|\s+to\s+|\s*[–-]\s*)"
APP_REF_RE = re.compile(
    r"\b(Appendix|Appendices)(\s+)(" + APP_ITEM + r"(?:" + LIST_CONN + APP_ITEM + r")*)"
)
RANGE_RE = re.compile(r"^\s*(?:–|-|to)\s*$")

EQ_TAG_RE = re.compile(r"\\tag\{A\.(\d+)\}")
EQ_TOKEN_RE = re.compile(r"A\.(\d+)")
EQ_ITEM = r"(?:\(A\.\d+\)|A\.\d+)"
EQ_REF_RE = re.compile(
    r"\b((?:Eq|Eqs|Equation|Equations)\.?)(\s+)("
    + EQ_ITEM + r"(?:" + LIST_CONN + EQ_ITEM + r")*)"
)


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


def _number_tokens(text, token_re):
    return list(token_re.finditer(text))


def _expand_numbers(text, token_re, dotted=False):
    """Expand explicit numeric ranges while preserving distinct appearance order."""
    toks = _number_tokens(text, token_re)
    out = []
    for i, tok in enumerate(toks):
        n = int(tok.group(1))
        if i:
            sep = text[toks[i - 1].end():tok.start()]
            if RANGE_RE.match(sep):
                prev = int(toks[i - 1].group(1))
                step = 1 if n >= prev else -1
                out.extend(range(prev + step, n, step))
        out.append(n)
    return out


def _ranges(text, token_re):
    toks = _number_tokens(text, token_re)
    out = []
    for i in range(1, len(toks)):
        sep = text[toks[i - 1].end():toks[i].start()]
        if RANGE_RE.match(sep):
            out.append((int(toks[i - 1].group(1)), int(toks[i].group(1))))
    return out


def _first_citation_order(main_text):
    order = []
    ranges = []
    for match in APP_REF_RE.finditer(main_text):
        span = match.group(3)
        ranges.extend(_ranges(span, APP_TOKEN_RE))
        for n in _expand_numbers(span, APP_TOKEN_RE):
            if n not in order:
                order.append(n)
    return order, ranges


def _appendix_parts(text):
    app = APPENDIX_HEADER_RE.search(text)
    if not app:
        raise ValueError("no '# Appendix ...' heading found")
    refs = REFERENCES_HEADER_RE.search(text, app.end())
    end = refs.start() if refs else len(text)
    matches = list(APPENDIX_HEADING_RE.finditer(text, app.end(), end))
    if not matches:
        raise ValueError("no '## A.n ...' appendix sections found")

    blocks = []
    for i, match in enumerate(matches):
        stop = matches[i + 1].start() if i + 1 < len(matches) else end
        blocks.append((int(match.group(1)), text[match.start():stop].rstrip()))
    return app, refs, matches[0].start(), end, blocks


def _rewrite_number_list(span, token_re, mapping, dotted=False):
    out = []
    last = 0
    for tok in token_re.finditer(span):
        out.append(span[last:tok.start()])
        n = mapping[int(tok.group(1))]
        out.append(("A." if dotted else "A") + str(n))
        last = tok.end()
    out.append(span[last:])
    return "".join(out)


def _rewrite_appendix_refs(text, mapping):
    def repl(match):
        return (match.group(1) + match.group(2)
                + _rewrite_number_list(match.group(3), APP_TOKEN_RE, mapping, dotted=True))
    return APP_REF_RE.sub(repl, text)


def _rewrite_equations(text, mapping):
    text = EQ_TAG_RE.sub(lambda m: r"\tag{A.%d}" % mapping[int(m.group(1))], text)

    def repl(match):
        span = _rewrite_number_list(match.group(3), EQ_TOKEN_RE, mapping, dotted=True)
        return match.group(1) + match.group(2) + span
    return EQ_REF_RE.sub(repl, text)


def _range_breaks(ranges, mapping):
    broken = []
    for a, b in ranges:
        lo, hi = sorted((a, b))
        if any(n not in mapping for n in range(lo, hi + 1)):
            broken.append((a, b))
            continue
        mapped = [mapping[n] for n in range(lo, hi + 1)]
        step = 1 if mapped[-1] >= mapped[0] else -1
        if mapped != list(range(mapped[0], mapped[-1] + step, step)):
            broken.append((a, b))
    return broken


def transform(text):
    app, refs, first_section, appendix_end, blocks = _appendix_parts(text)
    old_order = [n for n, _ in blocks]
    errors = []
    warnings = []

    duplicates = sorted(n for n in set(old_order) if old_order.count(n) > 1)
    if duplicates:
        errors.append("duplicate appendix heading(s): %s" % duplicates)
    if old_order:
        missing = [n for n in range(1, max(old_order) + 1) if n not in old_order]
        if missing:
            errors.append("appendix heading gap(s): %s" % missing)

    main_text = text[:app.start()]
    cited, app_ranges = _first_citation_order(main_text)
    undefined = [n for n in cited if n not in old_order]
    if undefined:
        errors.append("main text cites undefined appendix section(s): %s" % undefined)

    uncited = [n for n in old_order if n not in cited]
    if uncited:
        warnings.append("appendix section(s) never cited in the main text: %s" % uncited)
    desired = cited + uncited
    mapping = {old: new for new, old in enumerate(desired, 1)}

    broken_ranges = _range_breaks(app_ranges, mapping)
    if broken_ranges:
        errors.append("appendix range(s) would change meaning after reorder: %s" % broken_ranges)

    tags = [int(m.group(1)) for m in EQ_TAG_RE.finditer(text)]
    duplicate_tags = sorted(n for n in set(tags) if tags.count(n) > 1)
    if duplicate_tags:
        errors.append("duplicate appendix equation tag(s): %s" % duplicate_tags)

    eq_refs = []
    eq_ranges = []
    for match in EQ_REF_RE.finditer(text):
        span = match.group(3)
        eq_refs.extend(_expand_numbers(span, EQ_TOKEN_RE))
        eq_ranges.extend(_ranges(span, EQ_TOKEN_RE))
    undefined_eq = sorted(set(eq_refs) - set(tags))
    if undefined_eq:
        errors.append("undefined appendix equation reference(s): %s" % undefined_eq)

    if errors:
        return dict(errors=errors, warnings=warnings, old_order=old_order,
                    desired=desired, mapping=mapping, eq_mapping={}, text=text)

    by_number = dict(blocks)
    reordered_blocks = []
    for old in desired:
        new = mapping[old]
        block = re.sub(r"(?m)^##\s+A\.%d\b" % old, "## A.%d" % new,
                       by_number[old], count=1)
        reordered_blocks.append(block)

    prefix = text[:first_section].rstrip()
    suffix = text[appendix_end:].lstrip("\n")
    new_text = prefix + "\n\n" + "\n\n".join(reordered_blocks)
    if suffix:
        new_text += "\n\n" + suffix
    else:
        new_text += "\n"
    new_text = _rewrite_appendix_refs(new_text, mapping)

    reordered_tags = [int(m.group(1)) for m in EQ_TAG_RE.finditer(new_text)]
    eq_mapping = {old: new for new, old in enumerate(reordered_tags, 1)}
    broken_eq_ranges = _range_breaks(eq_ranges, eq_mapping)
    if broken_eq_ranges:
        errors.append("appendix equation range(s) would change meaning: %s" % broken_eq_ranges)
        return dict(errors=errors, warnings=warnings, old_order=old_order,
                    desired=desired, mapping=mapping, eq_mapping=eq_mapping, text=text)
    new_text = _rewrite_equations(new_text, eq_mapping)

    return dict(errors=errors, warnings=warnings, old_order=old_order,
                desired=desired, mapping=mapping, eq_mapping=eq_mapping, text=new_text)


def _changed(mapping):
    return {old: new for old, new in mapping.items() if old != new}


def report(result):
    print("  current appendix order: %s" %
          ", ".join("A.%d" % n for n in result["old_order"]))
    print("  first-citation order : %s" %
          ", ".join("A.%d" % n for n in result["desired"]))
    changed = _changed(result["mapping"])
    if changed:
        print("  appendix renumbering:")
        for old in result["desired"]:
            if old in changed:
                print("    Appendix A.%d -> A.%d" % (old, changed[old]))
    else:
        print("  appendices already follow first-citation order.")

    eq_changed = _changed(result["eq_mapping"])
    if eq_changed:
        print("  appendix equation renumbering:")
        for old, new in sorted(eq_changed.items(), key=lambda item: item[1]):
            print("    Eq. (A.%d) -> Eq. (A.%d)" % (old, new))
    elif result["eq_mapping"]:
        print("  appendix equations already follow physical order.")

    for warning in result["warnings"]:
        print("  WARNING: " + warning)
    for error in result["errors"]:
        print("  ERROR: " + error)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Reorder appendices by first citation and renumber appendix equations.")
    parser.add_argument("mdfile", nargs="?",
                        help="manuscript .md (default: the draft in the repo root)")
    parser.add_argument("--write", action="store_true",
                        help="apply changes in place (default: dry run)")
    args = parser.parse_args(argv)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md = args.mdfile or default_md(repo_root)
    with open(md, encoding="utf-8") as handle:
        text = handle.read()

    print("manuscript: %s" % md)
    try:
        result = transform(text)
    except ValueError as exc:
        print("  ERROR: %s" % exc)
        return 2
    report(result)

    if result["errors"]:
        print("\nRefusing to write: resolve the ERROR(s) above first.")
        return 2
    if not args.write:
        print("\n(dry run -- pass --write to apply)")
        return 0
    if result["text"] == text:
        print("\nNothing to write.")
        return 0

    with open(md, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(result["text"])
    print("\nWrote reordered appendices to %s" % md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
