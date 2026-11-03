"""Download the open-access copies the manifest lists, with a plain script (no browser).

Usage: python -I fetch_oa_pdfs.py <manifest.json> <staging_dir> [--dry-run]

For each entry OpenAlex calls open, tries the manifest's PDF URLs in order and keeps the first
response whose body starts with %PDF-, named from the manifest. Repositories (OSTI, IOP, HAL,
university repositories, arXiv) usually serve the file; many publisher sites answer a script
with HTML or 403, open access or not. Closed entries, entries without a PDF URL and failed
ones are printed at the end with their doi.org links, for the user to get through their
library. One request at a time, a pause between requests, nothing executed.

The run goes through the machine-wide fetch gate (fetch_gate.py in this folder): while another
session holds the lease it prints BUSY, exits with code 3 and requests nothing; inside this
session's own open run it runs under that run; otherwise it opens a run and ends it on exit.
Outside Claude Code, where there is no session id, the run is owned by this process. A dry run
does not touch the gate.
"""
import importlib.util
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


def load_gate():
    """fetch_gate.py from this folder (python -I keeps the script's folder off sys.path)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fetch_gate.py")
    spec = importlib.util.spec_from_file_location("fetch_gate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if os.environ.get("CLAUDE_CODE_HOST_SESSION_ID"):
        return mod.Gate()
    return mod.Gate(owner="fetch_oa_pdfs-%d" % os.getpid(), pid=os.getpid())


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    dry = "--dry-run" in sys.argv
    man_path, staging = [a for a in sys.argv[1:] if not a.startswith("--")][:2]
    os.makedirs(staging, exist_ok=True)
    man = json.load(open(man_path, encoding="utf-8"))
    gate, opened = None, False
    if not dry:
        gate = load_gate()
        code, lines, opened = gate.enter(man_path, "fetch_oa_pdfs " + os.path.basename(man_path))
        print("\n".join(lines), flush=True)
        if code:
            sys.exit(code)
    ok, left, lost = 0, [], False
    try:
        for m in man:
            dst = os.path.join(staging, m["file"])
            if os.path.exists(dst):
                print("have     ", m["doi"]); ok += 1; continue
            if m["status"].startswith(("closed", "ERR")) or not m["pdfs"]:
                why = m["status"] if m["status"].startswith(("closed", "ERR")) else "no PDF URL"
                print("skip     ", m["doi"], "(%s)" % why); left.append((m, why)); continue
            if dry:
                print("would try", m["doi"], m["pdfs"][0], "(+%d more)" % (len(m["pdfs"]) - 1)); continue
            why, got = "", False
            for url in m["pdfs"]:
                if not gate.touch():
                    lost = True
                    break
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
                    got = True
                    break
                if data:
                    why = "not a PDF (%s)" % ctype[:30]
            if lost:
                print("LOST another session took the fetch gate's lease over; stopping"); break
            if not got:
                print("fail     ", m["doi"], why); left.append((m, why))
        print("saved or present: %d / %d" % (ok, len(man)))
        if left:
            print("left for the user: %d" % len(left))
            for m, why in left:
                print("    %s  %s  [%s]" % (m["file"][:-4][:70], m["landing"], why))
    finally:
        if opened:
            print("\n".join(gate.end()[1]))


if __name__ == "__main__":
    main()
