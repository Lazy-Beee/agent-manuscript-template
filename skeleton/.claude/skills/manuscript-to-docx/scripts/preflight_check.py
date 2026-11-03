#!/usr/bin/env python3
"""Pre-conversion QA linter for a Markdown manuscript headed for .docx.

Read-only. Parses the manuscript and reports the mechanical issues that should be
resolved before a pandoc render: figure / table numbering, citation-reference
consistency, broken image links, AI-tell em-dashes, leftover placeholders and
Word -> pandoc artifacts, off-house-style terminology (from terminology.md),
optional context-aware bare-term rules, notation-table status, and common typos.

It never writes anything. The judgment checks a script cannot do reliably
(abstract / conclusion freshness, number consistency, hallucinations, sub-panel
cross-refs) live in ../references/checklist.md and are done by the model.

Usage:
    python preflight_check.py "path/to/manuscript.md" \
        [--terminology PATH] [--notation PATH]

If --terminology is omitted, a terminology.md next to the manuscript is used when
present; DEFAULT_FORBIDDEN below adds any built-in terms (empty by default). If
--notation is omitted, notation.md next to the manuscript is checked when present.

terminology.md format: every Markdown table row is read as
| Concept | Use | Do not use | Note |. Each comma- or semicolon-separated entry of the
"Do not use" column is flagged in the body. Multi-word entries are always flagged; a
single word is flagged only when the row's Note contains the marker [enforced], since
single words often have legitimate other senses and are better checked by hand.

Exit code: 1 if any FAIL-level issue is found, else 0. WARN / INFO never fail.
"""

import argparse
import os
import re
import sys

FAIL, WARN, INFO = "FAIL", "WARN", "INFO"

# Built-in off-house-style terms -> preferred form, applied on top of terminology.md.
# Empty by default: keep the house terms in terminology.md, where the authors see them.
# Example entry:  "utilize": "use",
DEFAULT_FORBIDDEN = {
}

# Context-aware rules for bare short forms that should be spelled out to the full house
# term, where a plain whole-word match would fire on legitimate uses. Each rule is
# (compiled pattern, message), matched case-insensitively on body text (reference titles
# are already excluded). Empty by default; add the manuscript's own. Example, flagging a
# bare "solidus" / "liquidus" used as a noun for the temperature while exempting hyphen
# compounds and "... temperature":
#   (re.compile(r"(?<![-\w])(?:solidus|liquidus)\b(?!\s+temperature)", re.IGNORECASE),
#    "bare 'solidus'/'liquidus' -> add 'temperature'"),
BARE_TERM_RULES = [
]

# Curated, high-confidence lexical errors -> correction. NOT a general spellchecker
# (that would drown in domain terms); only unambiguous typos and word-confusions. Add the
# ones your own drafts repeat. The full read-through (checklist.md section 9) covers the rest.
COMMON_TYPOS = [
    (r"\btunned\b", "tuned"),
    (r"\bgrinded\b", "ground"),
    (r"\bvender\b", "vendor"),
    (r"\bNavier-Stocks\b", "Navier-Stokes"),
    (r"\bdonates\b", "verify: 'denotes'?"),
    (r"\bwill\s+can\b", "double modal -> 'can' or 'will'"),
    (r"\bcan\s+will\b", "double modal -> 'can' or 'will'"),
    (r"\ba\s+choose\b", "a chosen"),
    (r"\boccured\b", "occurred"),
    (r"\bseperate\b", "separate"),
    (r"\bconsistant\b", "consistent"),
]


def read_lines(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read().splitlines()


def split_at_references(lines):
    """Return (body_lines, ref_lines) as (idx, text) pairs, 1-based line numbers.

    Everything from a '# References' / '# Bibliography' heading onward is the
    reference list; the rest is the body. Splitting matters so reference
    definitions are not counted as in-text citations and reference titles
    (which legitimately use other wording) are exempt from the
    terminology and em-dash scans.
    """
    head = re.compile(r"^#+\s*(references|bibliography)\s*$", re.IGNORECASE)
    split = len(lines)
    for i, text in enumerate(lines):
        if head.match(text.strip()):
            split = i
            break
    body = [(i + 1, t) for i, t in enumerate(lines[:split])]
    refs = [(i + 1, t) for i, t in enumerate(lines[split:], start=split)]
    return body, refs


def _label(word, key):
    """(group, num) -> display label, e.g. ('', 3) -> 'Figure 3', ('A', 1) -> 'Figure A.1'."""
    grp, num = key
    return "%s %s%s%d" % (word, grp, "." if grp else "", num)


def _numbered_captions(body, word):
    """Map caption key (group, num) -> line for 'Figure 3.' / 'Figure A.1.' / 'Table A.2.'.

    The optional leading letter is the appendix group ('' for body figures, 'A' for
    Appendix A). Body and appendix figures are separate sequences, each starting at 1."""
    pat = re.compile(r"^%s\s+(?:([A-Z])\.)?(\d+)\." % word)
    found = {}
    dups = []
    for ln, text in body:
        m = pat.match(text.strip())
        if m:
            key = (m.group(1) or "", int(m.group(2)))
            if key in found:
                dups.append((key, ln))
            else:
                found[key] = ln
    return found, dups


def check_numbered(body, word, ref_pat):
    """Check captions are sequential and that every in-text reference resolves. The body
    sequence (Figure 1..N) and each appendix sequence (Figure A.1..A.n) are checked
    independently, so an appendix restarting at A.1 is not read as a gap."""
    issues = []
    captions, dups = _numbered_captions(body, word)
    for key, ln in dups:
        issues.append((FAIL, ln, "%s caption appears more than once" % _label(word, key)))

    if captions:
        # gap + document-order checks run PER group (body '', appendix 'A', ...), since
        # each group numbers from 1. A caption whose number is larger than some later
        # caption's in the same group was appended out of order during drafting; it must be
        # renumbered by caption position at finalization, or the docx ships with Figure 35
        # appearing before Figure 5. WARN (not FAIL): the fix is deterministic +
        # author-approved, mirroring the citation first-appearance-order check.
        groups = {}
        for key, ln in captions.items():
            groups.setdefault(key[0], {})[key[1]] = ln
        for grp, members in sorted(groups.items()):
            for n in range(1, max(members) + 1):
                if n not in members:
                    issues.append((FAIL, 0, "%s caption is missing (gap in numbering)"
                                   % _label(word, (grp, n))))
            by_line = sorted(members.items(), key=lambda kv: kv[1])   # (num, line) in doc order
            displaced = [(n, ln) for i, (n, ln) in enumerate(by_line)
                         if any(m < n for m, _ in by_line[i + 1:])]
            if displaced:
                names = ", ".join(_label(word, (grp, n)) for n, _ in displaced[:6])
                more = " ..." if len(displaced) > 6 else ""
                issues.append((WARN, displaced[0][1],
                               "%d %s caption(s) numbered out of document order (%s%s); "
                               "run tools/renumber_figures_tables.py --write to renumber by appearance"
                               % (len(displaced), word, names, more)))

    refpat = re.compile(ref_pat)
    referenced = set()
    first_ref = {}
    for ln, text in body:
        if re.match(r"^%s\s+(?:[A-Z]\.)?\d+\." % word, text.strip()):
            continue  # the caption line itself is a definition, not a reference
        for m in refpat.finditer(text):
            key = (m.group(1) or "", int(m.group(2)))
            referenced.add(key)
            first_ref.setdefault(key, ln)
            if captions and key not in captions:
                issues.append((FAIL, ln, "in-text reference to %s, which has no caption"
                               % _label(word, key)))

    for key, ln in captions.items():
        if key not in referenced:
            issues.append((WARN, ln, "%s is captioned but never referenced in the text"
                           % _label(word, key)))
        elif ln < first_ref[key]:
            # the figure/table is placed before the paragraph that first mentions it;
            # a reader meets the artifact before it is introduced. Move it to just
            # after the first-mention paragraph.
            issues.append((WARN, ln, "%s appears before its first in-text mention (line %d); "
                                     "place it after the paragraph that first references it"
                                     % (_label(word, key), first_ref[key])))

    summary = "%d captioned, %d referenced" % (len(captions), len(referenced))
    return issues, summary


def check_images(all_lines, md_dir):
    issues = []
    pat = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
    count = 0
    for ln, text in all_lines:
        for m in pat.finditer(text):
            count += 1
            rel = m.group(1).split(" ")[0].strip()
            target = os.path.normpath(os.path.join(md_dir, rel))
            if not os.path.isfile(target):
                issues.append((FAIL, ln, "image link target not found: %s" % rel))
    return issues, "%d image link(s)" % count


def _parse_cite_numbers(text):
    out = []
    for m in re.finditer(r"\\?\[(\d+(?:\s*,\s*\d+)*)\\?\]", text):
        for part in m.group(1).split(","):
            out.append(int(part.strip()))
    return out


def check_citations(body, refs):
    issues = []
    defined = {}
    refdef = re.compile(r"^\\?\[(\d+)\\?\]")
    for ln, text in refs:
        m = refdef.match(text.strip())
        if m:
            defined[int(m.group(1))] = ln

    cited_order = []
    cited = set()
    for ln, text in body:
        for n in _parse_cite_numbers(text):
            cited.add(n)
            if n not in [c[0] for c in cited_order]:
                cited_order.append((n, ln))

    for n, ln in cited_order:
        if defined and n not in defined:
            issues.append((FAIL, ln, "citation [%d] has no entry in the reference list" % n))

    if defined:
        nums = sorted(defined)
        for n in range(1, max(nums) + 1):
            if n not in defined:
                issues.append((FAIL, 0, "reference list is missing entry [%d] (gap)" % n))
        for n, ln in defined.items():
            if n not in cited:
                issues.append((WARN, ln, "reference [%d] is listed but never cited in the text" % n))

    # First-appearance order: ideal first-cite sequence is 1, 2, 3, ...
    seq = [n for n, _ in cited_order]
    highest = 0
    for n, ln in cited_order:
        if n > highest + 1:
            issues.append((WARN, ln,
                           "citation [%d] appears before [%d]; numbering may not follow first-appearance order"
                           % (n, highest + 1)))
        highest = max(highest, n)

    summary = "%d cited, %d defined" % (len(cited), len(defined))
    return issues, summary


def check_em_dashes(body):
    issues = []
    n = 0
    table_rule = re.compile(r"^\s*\|?[\s|:\-]+\|?\s*$")  # markdown table delimiter row
    for ln, text in body:
        if "—" in text:  # em-dash, an AI tell in house prose
            col = text.index("—")
            snippet = text[max(0, col - 25):col + 26].strip()
            issues.append((WARN, ln, "em-dash (recast with comma/colon/parens): ...%s..." % snippet))
            n += 1
        elif "--" in text and not table_rule.match(text) and re.search(r"\S--\S", text):
            issues.append((INFO, ln, "double hyphen '--' (verify it is intended, not a stray em-dash)"))
    return issues, "%d em-dash line(s)" % n


def check_placeholders(all_lines):
    issues = []
    patterns = [
        (FAIL, re.compile(r"to be filled", re.IGNORECASE), "unfilled placeholder 'To Be Filled'"),
        (FAIL, re.compile(r"\\?\[\s*placeholder", re.IGNORECASE), "unfilled placeholder block"),
        (FAIL, re.compile(r"\\?\[citation[^\]]*\\?\]", re.IGNORECASE), "placeholder citation"),
        (FAIL, re.compile(r"\b(TODO|FIXME|TBD|XXX)\b"), "author TODO marker"),
        (WARN, re.compile(r"\\#"), "Word->pandoc equation-tag artifact '\\#' (verify number renders without a literal #)"),
        # Word->pandoc leftovers carry QUOTED width and height ({width="6.5in" height="4in"});
        # an unquoted {width=NN%} is a deliberate display width
        (WARN, re.compile(r"\{width=\"|\{height="), "leftover image size attribute"),
        (WARN, re.compile(r"AI-generated content", re.IGNORECASE), "leftover alt-text artifact"),
    ]
    counts = {}
    for ln, text in all_lines:
        for sev, pat, msg in patterns:
            if pat.search(text):
                issues.append((sev, ln, msg))
                counts[msg] = counts.get(msg, 0) + 1
    return issues, "%d marker(s)" % sum(counts.values())


def load_forbidden(terminology_path):
    terms = dict(DEFAULT_FORBIDDEN)
    if terminology_path and os.path.isfile(terminology_path):
        try:
            for line in read_lines(terminology_path):
                if not line.strip().startswith("|"):
                    continue
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) < 3:
                    continue
                preferred = re.sub(r"[*`]", "", cells[1]).strip()
                avoid = cells[2]
                note = cells[3] if len(cells) > 3 else ""
                if not preferred or avoid in ("", "-"):
                    continue
                if avoid.lower() == "do not use" or set(avoid) <= set("-: "):
                    continue  # header or separator row
                enforce_single = "[enforced]" in note.lower()
                for term in re.split(r"[,;]", avoid):
                    t = re.sub(r"[*`\"]", "", term).strip().lower()
                    # multi-word entries always; single words only when marked [enforced]
                    if t and (" " in t or enforce_single):
                        terms[t] = preferred
        except Exception:
            pass  # best-effort; the built-in defaults still apply
    return terms


def check_terminology(body, terms):
    issues = []
    n = 0
    for term, preferred in sorted(terms.items(), key=lambda kv: -len(kv[0])):
        pat = re.compile(r"(?<![\w-])" + re.escape(term) + r"(?![\w-])", re.IGNORECASE)
        for ln, text in body:
            if pat.search(text):
                issues.append((WARN, ln, "'%s' -> house term '%s'" % (term, preferred)))
                n += 1
    return issues, "%d hit(s)" % n


def check_bare_terms(body):
    """Bare short forms of full house terms, per the context-aware BARE_TERM_RULES
    (empty by default), so the accepted exceptions are not flagged.
    """
    issues = []
    n = 0
    for pat, msg in BARE_TERM_RULES:
        for ln, text in body:
            if pat.search(text):
                issues.append((WARN, ln, msg))
                n += 1
    return issues, "%d hit(s)" % n


def check_prose(body):
    """Curated typos, doubled words, and double spaces - a mechanical assist to the
    full read-through (checklist.md section 9), not a substitute for it."""
    issues = []
    typo_pats = [(re.compile(p, re.IGNORECASE), s) for p, s in COMMON_TYPOS]
    dup = re.compile(r"(?<![\w-])(\w{2,})\s+\1(?![\w-])", re.IGNORECASE)  # hyphen-aware: skip "multi-layer layer"
    dbl = re.compile(r"\w  +\w")
    table_rule = re.compile(r"^\s*\|?[\s|:\-]+\|?\s*$")
    n = 0
    for ln, text in body:
        if table_rule.match(text):
            continue
        for pat, sug in typo_pats:
            m = pat.search(text)
            if m:
                issues.append((WARN, ln, "'%s' -> %s" % (m.group(0).strip(), sug)))
                n += 1
        for m in dup.finditer(text):
            issues.append((WARN, ln, "doubled word '%s'" % m.group(1)))
            n += 1
        if dbl.search(text):
            issues.append((INFO, ln, "double space between words"))
    return issues, "%d prose flag(s)" % n


def check_sections(body):
    """Numbered headings: no duplicate section number, no sibling gaps.

    Restructuring a manuscript routinely leaves two headings with the same number
    (e.g. three subsections all labelled 3.2.1) or a skipped child. Duplicates are
    errors; gaps are flagged for a look.
    """
    issues = []
    pat = re.compile(r"^#{1,6}\s+(\d+(?:\.\d+)*)\b")
    seen = {}
    order = []
    for ln, text in body:
        m = pat.match(text.strip())
        if m:
            num = m.group(1)
            order.append((num, ln))
            if num in seen:
                issues.append((FAIL, ln, "duplicate section number %s (also at L%d)" % (num, seen[num])))
            else:
                seen[num] = ln
    children = {}
    for num, _ln in order:
        parent, last = num.rsplit(".", 1) if "." in num else ("", num)
        if last.isdigit():
            children.setdefault(parent, []).append(int(last))
    for parent, kids in sorted(children.items()):
        present = set(kids)
        for expect in range(1, max(present) + 1):
            if expect not in present:
                label = ("%s.%d" % (parent, expect)) if parent else str(expect)
                issues.append((INFO, 0, "section %s expected but not found (sibling gap)" % label))
    return issues, "%d numbered heading(s)" % len(order)


def check_appendices(body):
    """Appendix sections follow first-citation order; appendix equations resolve."""
    issues = []
    app_header = re.compile(r"^#\s+Appendix\b", re.IGNORECASE)
    heading = re.compile(r"^##\s+A\.(\d+)\s+")
    header_pos = next((i for i, (_ln, text) in enumerate(body)
                       if app_header.match(text.strip())), None)
    if header_pos is None:
        return issues, "0 appendix section(s)"

    main = body[:header_pos]
    appendix = body[header_pos + 1:]
    headings = []
    seen = {}
    for ln, text in appendix:
        match = heading.match(text.strip())
        if not match:
            continue
        num = int(match.group(1))
        headings.append((num, ln))
        if num in seen:
            issues.append((FAIL, ln, "duplicate Appendix A.%d heading (also at L%d)"
                           % (num, seen[num])))
        else:
            seen[num] = ln

    nums = [n for n, _ln in headings]
    if nums:
        missing = [n for n in range(1, max(nums) + 1) if n not in seen]
        for num in missing:
            issues.append((FAIL, 0, "Appendix A.%d heading is missing (gap in numbering)" % num))
        if nums != sorted(nums):
            issues.append((WARN, headings[0][1],
                           "appendix headings are out of physical order; "
                           "run tools/renumber_appendices.py --write"))

    # First-citation order in the main text. The manuscript normally uses singular
    # references, but tokenizing the whole Appendix/Appendices span also handles lists.
    app_ref = re.compile(
        r"\b(?:Appendix|Appendices)\s+(A\.\d+(?:(?:\s*,\s*(?:and\s+)?|\s+and\s+|"
        r"\s+to\s+|\s*[–-]\s*)A\.\d+)*)"
    )
    cited_order = []
    first_ref = {}
    for ln, text in main:
        for match in app_ref.finditer(text):
            span = match.group(1)
            token_matches = list(re.finditer(r"A\.(\d+)", span))
            tokens = []
            for i, token in enumerate(token_matches):
                num = int(token.group(1))
                if i:
                    sep = span[token_matches[i - 1].end():token.start()]
                    if re.match(r"^\s*(?:–|-|to)\s*$", sep):
                        prev = int(token_matches[i - 1].group(1))
                        step = 1 if num >= prev else -1
                        tokens.extend(range(prev + step, num, step))
                tokens.append(num)
            for num in tokens:
                if num not in cited_order:
                    cited_order.append(num)
                    first_ref[num] = ln
                if headings and num not in seen:
                    issues.append((FAIL, ln,
                                   "in-text reference to Appendix A.%d, which has no heading"
                                   % num))
    if cited_order != sorted(cited_order):
        first_bad = next((n for i, n in enumerate(cited_order, 1) if n != i),
                         cited_order[0])
        issues.append((WARN, first_ref[first_bad],
                       "appendices are not numbered by first citation (%s); "
                       "run tools/renumber_appendices.py --write"
                       % ", ".join("A.%d" % n for n in cited_order)))
    for num, ln in headings:
        if num not in first_ref:
            issues.append((WARN, ln, "Appendix A.%d is never cited in the main text" % num))

    tags = []
    tag_lines = {}
    for ln, text in appendix:
        for match in re.finditer(r"\\tag\{A\.(\d+)\}", text):
            num = int(match.group(1))
            tags.append(num)
            if num in tag_lines:
                issues.append((FAIL, ln, "duplicate appendix equation tag A.%d (also at L%d)"
                               % (num, tag_lines[num])))
            else:
                tag_lines[num] = ln
    if tags:
        for num in range(1, max(tags) + 1):
            if num not in tag_lines:
                issues.append((FAIL, 0, "appendix equation tag A.%d is missing" % num))
        if tags != sorted(tags):
            issues.append((WARN, tag_lines[tags[0]],
                           "appendix equation tags are out of physical order; "
                           "run tools/renumber_appendices.py --write"))

    eq_ref = re.compile(r"\b(?:Eq|Eqs|Equation|Equations)\.?\s+"
                        r"((?:\(A\.\d+\)|A\.\d+)(?:(?:\s*,\s*(?:and\s+)?|\s+and\s+|"
                        r"\s+to\s+|\s*[–-]\s*)(?:\(A\.\d+\)|A\.\d+))*)")
    for ln, text in body:
        for match in eq_ref.finditer(text):
            for token in re.findall(r"A\.(\d+)", match.group(1)):
                num = int(token)
                if num not in tag_lines:
                    issues.append((FAIL, ln,
                                   "reference to Eq. (A.%d), which has no appendix equation tag"
                                   % num))

    return issues, "%d appendix section(s), %d appendix equation(s)" % (len(headings), len(tags))


def check_notation(notation_path, manuscript_lines):
    """Check the external notation table's mechanically verifiable state.

    Semantic symbol coverage and meaning still require the judgment checklist.
    This pass catches the two safe deterministic failures: unresolved rows left
    under "Open notation issues" and equation locations that no longer resolve
    after renumbering.
    """
    if not notation_path or not os.path.isfile(notation_path):
        return [(WARN, 0, "notation.md not found; update and review the external symbol table")], \
               "no notation table found"

    notation_lines = read_lines(notation_path)
    issues = []

    open_heading = None
    for idx, text in enumerate(notation_lines):
        if re.match(r"^##\s+Open notation issues\s*$", text.strip(), re.IGNORECASE):
            open_heading = idx
            break

    open_rows = []
    if open_heading is None:
        issues.append((WARN, 0, "missing 'Open notation issues' section"))
    else:
        for idx in range(open_heading + 1, len(notation_lines)):
            text = notation_lines[idx].strip()
            if text.startswith("## "):
                break
            if not text or re.fullmatch(r"None\.?", text, re.IGNORECASE):
                continue
            if text.startswith("|"):
                cells = [cell.strip() for cell in text.strip("|").split("|")]
                if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                    continue
                if cells and cells[0].lower() in {"symbol", "notation", "item"}:
                    continue
            open_rows.append((idx + 1, text))
        for ln, text in open_rows:
            label = text.strip("|").split("|", 1)[0].strip() or "unresolved item"
            issues.append((WARN, ln, "open notation issue remains: %s" % label))

    manuscript_tags = set()
    for text in manuscript_lines:
        manuscript_tags.update(re.findall(r"\\tag\{((?:[A-Z]\.)?\d+)\}", text))

    checked_refs = 0
    for idx, text in enumerate(notation_lines):
        if not re.search(r"\bEqs?\.", text):
            continue
        refs = re.findall(r"\(((?:[A-Z]\.)?\d+)\)", text)
        checked_refs += len(refs)
        for ref in refs:
            if ref not in manuscript_tags:
                issues.append((FAIL, idx + 1,
                               "notation location Eq. (%s) has no matching manuscript tag" % ref))

    return issues, "%d line(s), %d open issue(s), %d equation reference(s) checked" % (
        len(notation_lines), len(open_rows), checked_refs)


def render_section(title, issues, summary):
    """Group identical (severity, message) issues so repeated artifacts (e.g. the
    same '\\#' equation tag on 21 lines) collapse to one row with a line list."""
    order = {FAIL: 0, WARN: 1, INFO: 2}
    grouped = {}
    for sev, ln, msg in issues:
        grouped.setdefault((sev, msg), []).append(ln)
    rows = sorted(grouped.items(), key=lambda kv: (order[kv[0][0]], min(kv[1])))
    out = ["[%s]  %s" % (title, summary)]
    if not issues:
        out.append("    OK")
    for (sev, msg), lns in rows:
        lns = sorted({n for n in lns if n})
        if len(lns) <= 1:
            loc = ("L%d" % lns[0]) if lns else "-"
            out.append("    %-4s %-9s %s" % (sev, loc, msg))
        else:
            shown = ",".join("L%d" % n for n in lns[:10])
            if len(lns) > 10:
                shown += ",... (+%d more)" % (len(lns) - 10)
            out.append("    %-4s x%-8d %s" % (sev, len(lns), msg))
            out.append("    %-4s %-9s %s" % ("", "", shown))
    return "\n".join(out)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # em-dash snippets are non-ASCII
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Pre-conversion QA linter for a Markdown manuscript.")
    ap.add_argument("manuscript", help="path to the manuscript .md")
    ap.add_argument("--terminology", default=None, help="path to terminology.md (house style)")
    ap.add_argument("--notation", default=None, help="path to notation.md (external symbol table)")
    args = ap.parse_args()

    if not os.path.isfile(args.manuscript):
        print("error: manuscript not found: %s" % args.manuscript, file=sys.stderr)
        return 2

    md_dir = os.path.dirname(os.path.abspath(args.manuscript))
    term_path = args.terminology or os.path.join(md_dir, "terminology.md")
    term_path = term_path if os.path.isfile(term_path) else None
    notation_path = args.notation or os.path.join(md_dir, "notation.md")

    lines = read_lines(args.manuscript)
    all_lines = [(i + 1, t) for i, t in enumerate(lines)]
    body, refs = split_at_references(lines)
    terms = load_forbidden(term_path)

    sections = []
    all_issues = []

    def run(title, result):
        issues, summary = result
        all_issues.extend(issues)
        sections.append(render_section(title, issues, summary))

    run("SECTIONS", check_sections(body))
    run("APPENDICES", check_appendices(body))
    run("FIGURES", check_numbered(body, "Figure", r"Figures?\s+(?:([A-Z])\.)?(\d+)"))
    run("TABLES", check_numbered(body, "Table", r"Tables?\s+(?:([A-Z])\.)?(\d+)"))
    run("IMAGES", check_images(all_lines, md_dir))
    run("CITATIONS", check_citations(body, refs))
    run("EM-DASHES", check_em_dashes(body))
    run("PLACEHOLDERS", check_placeholders(all_lines))
    run("TERMINOLOGY", check_terminology(body, terms))
    run("NOTATION", check_notation(notation_path, lines))
    run("BARE-TERMS", check_bare_terms(body))
    run("PROSE", check_prose(body))

    n_fail = sum(1 for s, _, _ in all_issues if s == FAIL)
    n_warn = sum(1 for s, _, _ in all_issues if s == WARN)
    n_info = sum(1 for s, _, _ in all_issues if s == INFO)

    print("=" * 64)
    print("manuscript-to-docx preflight")
    print("manuscript : %s" % os.path.abspath(args.manuscript))
    print("terminology: %s" % (term_path or "(none found - using built-in defaults)"))
    print("notation   : %s" % (notation_path if os.path.isfile(notation_path)
                              else "(none found)"))
    print("=" * 64)
    print("\n\n".join(sections))
    print("\n" + "-" * 64)
    print("summary: FAIL=%d  WARN=%d  INFO=%d" % (n_fail, n_warn, n_info))
    if n_fail:
        print("verdict: FAIL-level issues present - resolve before rendering.")
    elif n_warn:
        print("verdict: no blockers; review WARN items (house style / freshness) before rendering.")
    else:
        print("verdict: clean on mechanical checks. Still run the judgment checklist.")
    print("note: mechanical checks only. Run ../references/checklist.md judgment checks too.")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
