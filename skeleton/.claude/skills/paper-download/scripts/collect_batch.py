"""Pair the PDFs the user saved by hand with the download-list entries and move them to staging.

Usage: python -I collect_batch.py <download_list.md> <downloads_dir> <staging_dir> [--since EPOCH] [--priority A]

For every *.pdf in <downloads_dir> newer than --since (default: the last 2 hours): read the
text of its first three pages (PyMuPDF), look for the DOI of each list entry of the chosen
priority that is not yet in staging, and move the file to <staging_dir>/"<First author> -
<Year> - <Title>.pdf". A file that prints no DOI (papers from before the DOI era) is paired
by its title instead: every significant title word and the first author's name on the first
pages. Files that match no pending entry, or are not PDFs, stay where they are and are
reported. Needs PyMuPDF (pip install pymupdf).
"""
import os
import re
import shutil
import sys
import time

import fitz  # PyMuPDF


def safe_name(s, n=150):
    s = re.sub(r'[\\/:*?"<>|]', "-", s).replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n].rstrip(" .")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    since = float(args[args.index("--since") + 1]) if "--since" in args else time.time() - 7200
    prio = args[args.index("--priority") + 1] if "--priority" in args else "A"
    skip = set()
    for flag in ("--since", "--priority"):
        if flag in args:
            skip.add(args[args.index(flag) + 1])
    pos = [a for a in args if not a.startswith("--") and a not in skip]
    lst, ddir, staging = pos[:3]
    os.makedirs(staging, exist_ok=True)

    txt = open(lst, encoding="utf-8").read().replace("\r\n", "\n")
    sec = txt.split("## Priority %s" % prio)[1].split("\n## ")[0]
    entries = re.findall(r"- \[[ x]\] (.+?) \((\d{4})\)\. (.+?)\. \*(.+?)\*\. https://doi\.org/(\S+)", sec)
    pending, meta = {}, {}
    for first, year, title, journal, doi in entries:
        name = safe_name("%s - %s - %s" % (first, year, title)) + ".pdf"
        if not os.path.exists(os.path.join(staging, name)):
            pending[doi.lower()] = name
            meta[doi.lower()] = (first, title)

    new = [os.path.join(ddir, f) for f in os.listdir(ddir)
           if f.lower().endswith(".pdf") and os.path.getmtime(os.path.join(ddir, f)) > since]
    moved, left = [], []
    for src in sorted(new, key=os.path.getmtime):
        try:
            with open(src, "rb") as fh:
                if fh.read(5) != b"%PDF-":
                    left.append((os.path.basename(src), "not a PDF"))
                    continue
            doc = fitz.open(src)
            text = "".join(doc[i].get_text() for i in range(min(3, len(doc)))).lower()
            doc.close()
            text = re.sub(r"\s+", "", text)
        except Exception as e:  # noqa: BLE001
            left.append((os.path.basename(src), "unreadable: %s" % type(e).__name__))
            continue
        hit = [d for d in pending if d in text or d.replace("(", "%28").replace(")", "%29") in text]
        if not hit:   # no DOI printed: pair by title words and first author
            for d, (first, title) in meta.items():
                if d not in pending:
                    continue
                words = [w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) >= 4]
                enough = words and sum(w in text for w in words) >= 0.85 * len(words)
                if enough and re.sub(r"[^a-z]", "", first.lower()) in text:
                    hit.append(d)
        if len(hit) == 1:
            dst = os.path.join(staging, pending[hit[0]])
            shutil.move(src, dst)
            moved.append((hit[0], pending.pop(hit[0]), os.path.getsize(dst) // 1024))
        else:
            left.append((os.path.basename(src), "matches %d pending DOIs" % len(hit)))
    for d, n, kb in moved:
        print("moved  %-40s %5d kB  %s" % (d, kb, n[:70]))
    for f, why in left:
        print("left   %s: %s" % (f, why))
    print("pending after this pass: %d" % len(pending))
    for d in pending:
        print("    " + d)


if __name__ == "__main__":
    main()
