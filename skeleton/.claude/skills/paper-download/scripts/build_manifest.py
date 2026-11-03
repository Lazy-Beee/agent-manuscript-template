"""Build the fetch manifest for one priority of a download list.

Usage: python -I build_manifest.py <download_list.md> <staging_dir> <manifest.json> [--priority A] [--mailto you@example.org]

Reads the unticked lines "- [ ] First (Year). Title. *Journal*. https://doi.org/DOI" under the
heading "## Priority <P>", skips those whose "<First> - <Year> - <Title>.pdf" is already in
<staging_dir>, and asks OpenAlex for the open-access status and the PDF URL of every open
location, repository copies first (they serve a plain script more often than publisher sites).
Writes a JSON list of {doi, first, year, file, status, landing, pdfs} and prints the counts per
status. Only the OpenAlex API is read.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request


def safe_name(s, n=150):
    s = re.sub(r'[\\/:*?"<>|]', "-", s).replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n].rstrip(" .")


def get_json(url, ua):
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def openalex(doi, ua):
    url = "https://api.openalex.org/works/https://doi.org/" + urllib.parse.quote(doi, safe="/().-")
    m = get_json(url, ua)
    # "locations" with an is_oa flag; older records of the API had "oa_locations" instead
    locs = [loc for loc in m.get("locations") or m.get("oa_locations") or []
            if loc.get("is_oa") and loc.get("pdf_url")]
    locs.sort(key=lambda loc: (loc.get("source") or {}).get("type") != "repository")
    pdfs = []
    for loc in locs:
        if loc["pdf_url"] not in pdfs:
            pdfs.append(loc["pdf_url"])
    return (m.get("open_access") or {}).get("oa_status", ""), pdfs


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    prio = args[args.index("--priority") + 1] if "--priority" in args else "A"
    mailto = args[args.index("--mailto") + 1] if "--mailto" in args else ""
    pos = [a for a in args if not a.startswith("--") and a not in (prio, mailto)]
    lst, staging, out = pos[:3]
    ua = "paper-download-skill/1.0" + (" (mailto:%s)" % mailto if mailto else "")

    txt = open(lst, encoding="utf-8").read().replace("\r\n", "\n")
    if "## Priority %s" % prio not in txt:
        sys.exit("no heading '## Priority %s' in %s" % (prio, lst))
    sec = txt.split("## Priority %s" % prio)[1].split("\n## ")[0]
    entries = re.findall(r"- \[ \] (.+?) \((\d{4})\)\. (.+?)\. \*(.+?)\*\. https://doi\.org/(\S+)", sec)
    staged = set(os.listdir(staging)) if os.path.isdir(staging) else set()
    man = []
    for first, year, title, journal, doi in entries:
        fn = safe_name("%s - %s - %s" % (first, year, title)) + ".pdf"
        if fn in staged:
            continue
        try:
            status, pdfs = openalex(doi, ua)
        except Exception as e:  # noqa: BLE001
            status, pdfs = "ERR " + type(e).__name__, []
        man.append(dict(doi=doi, first=first, year=year, file=fn, status=status,
                        landing="https://doi.org/" + doi, pdfs=pdfs))
        time.sleep(0.3)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(man, fh, indent=1, ensure_ascii=False)
    from collections import Counter
    print("%d pending in priority %s; open-access status: %s" % (len(man), prio, dict(Counter(m["status"] for m in man))))
    for m in man:
        print("%-8s %d url  %-42s %s" % (m["status"][:8], len(m["pdfs"]), m["doi"], m["file"][:60]))


if __name__ == "__main__":
    main()
