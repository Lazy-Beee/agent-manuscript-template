"""Move the staged PDFs into the repository's references/ folder and tick them in download_list.md.

Usage: python -I finalize_pdfs.py <repo> <staging_dir> [--dry-run]

For every "- [ ] First (Year). Title. *Journal*. https://doi.org/DOI" line of
<repo>/references/download_list.md whose "<First> - <Year> - <Title>.pdf" (file-name-safe
form) exists in staging: move it to <repo>/references/ (never overwriting) and change "[ ]"
to "[x]". PDFs are gitignored there; the ticked list is the record. Prints the counts per
section and the staged files that matched no line.
"""
import os
import re
import shutil
import sys


def safe_name(s, n=150):
    s = re.sub(r'[\\/:*?"<>|]', "-", s).replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n].rstrip(" .")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    dry = "--dry-run" in sys.argv
    repo, staging = [a for a in sys.argv[1:] if not a.startswith("--")][:2]
    lst = os.path.join(repo, "references", "download_list.md")
    dst_dir = os.path.join(repo, "references")
    text = open(lst, encoding="utf-8").read().replace("\r\n", "\n")
    staged = {f for f in os.listdir(staging) if f.lower().endswith(".pdf")}
    used, out, counts, section = set(), [], {}, ""
    for line in text.split("\n"):
        if line.startswith("## "):
            section = line[3:].split(" (")[0]
        m = re.match(r"- \[ \] (.+?) \((\d{4})\)\. (.+?)\. \*(.+?)\*\. https://doi\.org/(\S+)$", line)
        if m:
            name = safe_name("%s - %s - %s" % (m.group(1), m.group(2), m.group(3))) + ".pdf"
            if name in staged:
                used.add(name)
                counts[section] = counts.get(section, 0) + 1
                if not dry:
                    dst = os.path.join(dst_dir, name)
                    if not os.path.exists(dst):
                        shutil.move(os.path.join(staging, name), dst)
                line = line.replace("- [ ] ", "- [x] ", 1)
        out.append(line)
    if not dry:
        with open(lst, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(out))
    print(("dry run, would tick: " if dry else "ticked: ") + str(counts))
    print("staged files matching no list line:", sorted(staged - used) or "none")


if __name__ == "__main__":
    main()
