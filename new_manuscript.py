#!/usr/bin/env python3
"""Create a new manuscript repository from this template.

Copies skeleton/ (plus METHOD.md) into a new folder, fills the placeholders, renames the
draft, and runs `git init`. It does NOT commit: the first commit is made after the author
has looked at the result, like every other commit.

    python new_manuscript.py "my-paper" \
        --name "Short name" \
        --title "Full manuscript title" \
        --draft "my paper draft" \
        [--parent DIR] [--origin DIR] [--into-existing] [--no-git] [--dry-run]

--parent   where the new folder goes (default: the folder that contains this template)
--origin   an existing manuscript repository this one is modeled on; its HEAD commit is
           recorded in the new README as the reference baseline (by a relative path, or by
           its absolute path when it sits on another drive)
--into-existing
           scaffold into a folder that already exists (an exploration or notes folder that
           becomes the manuscript repository). Only files that do not exist yet are written;
           if any skeleton file would overwrite an existing one, nothing is written and the
           collisions are listed, so move the old files aside first (for example into a
           subfolder). An existing .git is kept.

Placeholders filled in every text file of the skeleton:
    {{NAME}}      short manuscript name used in headings
    {{TITLE}}     full title (draft title line, README)
    {{DRAFT}}     draft file stem; the draft becomes "<DRAFT>.md"
    {{DATE}}      creation date (today)
    {{BASELINE}}  origin manuscript and its commit, or "none"

Files are written byte-for-byte with LF line endings. Needs only the Python standard
library (and git, unless --no-git).
"""
import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKELETON = os.path.join(HERE, "skeleton")
EXTRA_FILES = {"METHOD.md": os.path.join(HERE, "METHOD.md")}   # copied to the repo root
DRAFT_PLACEHOLDER_FILE = "__DRAFT__.md"
TEXT_EXT = {".md", ".py", ".ps1", ".sh", ".lua", ".json", ".txt",
            ".gitignore", ".gitattributes", ".gitkeep"}
PLACEHOLDER_RE = re.compile(rb"\{\{(?:NAME|TITLE|DRAFT|DATE|BASELINE)\}\}")


def origin_commit(origin_dir):
    try:
        out = subprocess.run(["git", "-C", origin_dir, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return None


def is_text(path):
    name = os.path.basename(path)
    ext = os.path.splitext(name)[1] or name   # ".gitignore" has no stem
    return ext in TEXT_EXT


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", help="name of the new repository folder")
    ap.add_argument("--name", required=True, help="short manuscript name for headings")
    ap.add_argument("--title", required=True, help="full manuscript title")
    ap.add_argument("--draft", required=True, help='draft file stem, e.g. "my paper draft"')
    ap.add_argument("--parent", default=os.path.dirname(HERE),
                    help="directory to create the folder in (default: next to this template)")
    ap.add_argument("--origin", help="path of an existing manuscript repository this one follows")
    ap.add_argument("--into-existing", action="store_true",
                    help="scaffold into an existing folder; never overwrites a file")
    ap.add_argument("--no-git", action="store_true", help="skip git init")
    ap.add_argument("--dry-run", action="store_true", help="list what would be written")
    args = ap.parse_args()

    parent = os.path.abspath(args.parent)
    target = os.path.join(parent, args.folder)
    if os.path.exists(target) and not args.into_existing:
        sys.exit(f"refusing: {target} already exists (pass --into-existing to scaffold into it)")
    if args.into_existing and not os.path.isdir(target):
        sys.exit(f"--into-existing: {target} is not an existing folder")

    today = datetime.date.today().isoformat()
    if args.origin:
        odir = args.origin if os.path.isabs(args.origin) else os.path.join(parent, args.origin)
        if not os.path.isdir(odir):
            sys.exit(f"origin not found: {odir}")
        try:
            rel = os.path.relpath(odir, target).replace(os.sep, "/")
        except ValueError:   # Windows: no relative path between drives
            rel = os.path.abspath(odir).replace(os.sep, "/")
        sha = origin_commit(odir)
        baseline = (f"modeled on `{rel}/` at commit `{sha}` (its HEAD when this repository "
                    f"was created, {today})." if sha else
                    f"modeled on `{rel}/` ({today}; commit not resolved).")
    else:
        baseline = "none (created from the manuscript template without an origin manuscript)."

    subs = {
        b"{{NAME}}": args.name.encode("utf-8"),
        b"{{TITLE}}": args.title.encode("utf-8"),
        b"{{DRAFT}}": args.draft.encode("utf-8"),
        b"{{DATE}}": today.encode("utf-8"),
        b"{{BASELINE}}": baseline.encode("utf-8"),
    }

    plan = []
    for root, dirs, files in os.walk(SKELETON):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        rel_root = os.path.relpath(root, SKELETON)
        out_root = target if rel_root == "." else os.path.join(target, rel_root)
        plan.append(("dir", None, out_root))
        for f in files:
            if f.endswith(".pyc"):
                continue
            src = os.path.join(root, f)
            out_name = args.draft + ".md" if (rel_root == "." and f == DRAFT_PLACEHOLDER_FILE) else f
            plan.append(("file", src, os.path.join(out_root, out_name)))
    for name, src in EXTRA_FILES.items():
        plan.append(("file", src, os.path.join(target, name)))

    # never overwrite: with --into-existing the folder may hold files of the same name
    collisions = [dst for kind, src, dst in plan if kind == "file" and os.path.exists(dst)]

    if args.dry_run:
        for kind, src, dst in plan:
            flag = "  <-- exists" if dst in collisions else ""
            print(f"{kind:4s} {os.path.relpath(dst, parent)}{flag}")
        if collisions:
            print(f"\n{len(collisions)} file(s) already exist; a real run stops without writing.")
        return
    if collisions:
        sys.exit("refusing to overwrite existing files (move them aside first):\n  "
                 + "\n  ".join(os.path.relpath(c, target) for c in collisions))

    leftovers = []
    for kind, src, dst in plan:
        if kind == "dir":
            os.makedirs(dst, exist_ok=True)
            continue
        if is_text(src):
            data = open(src, "rb").read().replace(b"\r\n", b"\n")
            for key, val in subs.items():
                data = data.replace(key, val)
            if PLACEHOLDER_RE.search(data):
                leftovers.append(os.path.relpath(dst, target))
            with open(dst, "wb") as fh:
                fh.write(data)
        else:
            shutil.copy2(src, dst)

    print(("scaffolded into " if args.into_existing else "created ") + target)
    if leftovers:
        print("WARNING: unfilled {{...}} placeholders in: " + ", ".join(leftovers))
    if not args.no_git:
        if os.path.isdir(os.path.join(target, ".git")):
            print("existing .git kept (no git init)")
        else:
            subprocess.run(["git", "-C", target, "init"], check=True)
    print("\nNext: fill README (target journals), TODO (data state), the terminology table and")
    print("the end matter; run the preflight on the draft; open the folder in VS Code; make the")
    print("first commit once the author has looked at it, e.g.")
    print(f'  docs: create the {args.name} manuscript repository from the template')


if __name__ == "__main__":
    main()
