"""Download the open-access copies the manifest lists, with a plain script (no browser).

Usage: python -I fetch_oa_pdfs.py <manifest.json> <staging_dir> [--dry-run]

For each entry OpenAlex calls open, tries the manifest's PDF URLs in order and keeps the first
response whose body starts with %PDF-, named from the manifest. Repositories (OSTI, IOP, HAL,
university repositories, arXiv) usually serve the file; many publisher sites answer a script
with HTML or 403, open access or not. Closed entries, entries without a PDF URL and failed
ones are printed at the end with their doi.org links, for the user to get through their
library. One request at a time, a pause between requests, nothing executed.
"""
import json
import os
import sys
import time
import urllib.request

UA = "paper-download-skill/1.0"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/pdf,*/*"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(60 * 1024 * 1024), r.headers.get("Content-Type", "")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    dry = "--dry-run" in sys.argv
    man_path, staging = [a for a in sys.argv[1:] if not a.startswith("--")][:2]
    os.makedirs(staging, exist_ok=True)
    man = json.load(open(man_path, encoding="utf-8"))
    ok, left = 0, []
    for m in man:
        dst = os.path.join(staging, m["file"])
        if os.path.exists(dst):
            print("have     ", m["doi"]); ok += 1; continue
        if m["status"].startswith(("closed", "ERR")) or not m["pdfs"]:
            why = m["status"] if m["status"].startswith(("closed", "ERR")) else "no PDF URL"
            print("skip     ", m["doi"], "(%s)" % why); left.append((m, why)); continue
        if dry:
            print("would try", m["doi"], m["pdfs"][0], "(+%d more)" % (len(m["pdfs"]) - 1)); continue
        why = ""
        for url in m["pdfs"]:
            try:
                data, ctype = fetch(url)
            except Exception as e:  # noqa: BLE001
                why = "%s %s" % (type(e).__name__, str(e)[:50])
                data = b""
            time.sleep(1.5)
            if data[:5] == b"%PDF-":
                with open(dst, "wb") as fh:
                    fh.write(data)
                print("OK       ", m["doi"], "%d kB" % (len(data) // 1024)); ok += 1
                break
            if data:
                why = "not a PDF (%s)" % ctype[:30]
        else:
            print("fail     ", m["doi"], why); left.append((m, why))
    print("saved or present: %d / %d" % (ok, len(man)))
    if left:
        print("left for the user: %d" % len(left))
        for m, why in left:
            print("    %s  %s  [%s]" % (m["file"][:-4][:70], m["landing"], why))


if __name__ == "__main__":
    main()
