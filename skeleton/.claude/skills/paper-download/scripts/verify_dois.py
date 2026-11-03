"""Verify DOIs on Crossref and compare the registered title with the expected one.

Usage: python -I verify_dois.py <input.tsv> <output.tsv> [--mailto you@example.org]

input.tsv: one entry per line, "DOI<TAB>expected title" (the title may be empty; lines
starting with # are skipped). output.tsv: DOI, status, year, Crossref title, container,
volume, page or article number, first author, title similarity.

Status: OK (title matches), CHECK (partial match, read it), MISMATCH (another paper),
RESOLVES (no expected title given), FAIL (not resolved). Only the Crossref REST API is read;
nothing is downloaded. --mailto joins Crossref's polite pool; leave it out rather than
inventing an address.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request

STOP = {"a", "an", "the", "of", "in", "on", "for", "and", "to", "by", "with"}


def norm(s):
    return set(re.findall(r"[a-z0-9]+", (s or "").lower())) - STOP


def crossref(doi, ua):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["message"]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    mailto = args[args.index("--mailto") + 1] if "--mailto" in args else ""
    pos = [a for a in args if not a.startswith("--") and a != mailto]
    inp, out = pos[:2]
    ua = "paper-download-skill/1.0" + (" (mailto:%s)" % mailto if mailto else "")
    rows = []
    for line in open(inp, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        doi = parts[0].strip().replace("https://doi.org/", "")
        expected = parts[1].strip() if len(parts) > 1 else ""
        try:
            m = crossref(doi, ua)
            title = (m.get("title") or [""])[0]
            cont = (m.get("container-title") or [""])[0]
            year = ""
            for k in ("published-print", "published-online", "issued", "created"):
                dp = (m.get(k) or {}).get("date-parts")
                if dp and dp[0] and dp[0][0]:
                    year = str(dp[0][0])
                    break
            vol = m.get("volume", "")
            page = m.get("page") or m.get("article-number", "")
            au = m.get("author") or []
            first = au[0].get("family", "") if au else ""
            a, b = norm(expected), norm(title)
            sim = len(a & b) / max(1, min(len(a), len(b))) if expected else -1
            status = ("RESOLVES" if not expected else "OK" if sim >= 0.8 else
                      "CHECK" if sim >= 0.5 else "MISMATCH")
            rows.append([doi, status, year, title, cont, vol, page, first, "%.2f" % sim])
        except Exception as e:  # noqa: BLE001
            rows.append([doi, "FAIL %s %s" % (type(e).__name__, str(e)[:60]), "", "", "", "", "", "", ""])
        time.sleep(0.3)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("doi\tstatus\tyear\tcrossref_title\tcontainer\tvolume\tpage\tfirst_author\tsim\n")
        for r in rows:
            fh.write("\t".join(str(x).replace("\t", " ") for x in r) + "\n")
    for r in rows:
        print("%-45s %-10s %s %s | %s" % (r[0], r[1], r[2], r[7], r[3][:70]))
    n = len(rows)
    print("%d DOIs: %d OK, %d RESOLVES, %d other" % (
        n, sum(r[1] == "OK" for r in rows), sum(r[1] == "RESOLVES" for r in rows),
        sum(r[1] not in ("OK", "RESOLVES") for r in rows)))


if __name__ == "__main__":
    main()
