#!/usr/bin/env python3
"""Convert a manuscript's referenced PNG figures to JPG and emit a rewritten
Markdown file whose image links point at the JPGs, to shrink the rendered
.docx (JPEG is far smaller than PNG for photographic / rendered figures).

Each PNG is only switched to JPG when the JPG actually comes out smaller;
line-art plots (flat background, sharp text) often compress better as PNG and
would also lose quality under JPEG, so those keep their original PNG. This
makes the pass strictly a size win, never a regression. Use --force to convert
every PNG regardless.

The source Markdown and the original figures are never modified. Converted
JPGs and the rewritten .md are written to a staging directory (a fresh temp
dir by default); JPGs are referenced by absolute path and kept PNGs keep their
original relative link (resolved by pandoc's --resource-path at render time).

Alpha/transparency is flattened onto white (JPEG has no alpha channel).

When at least one figure is converted, a note is appended to the end of the
rewritten .md recording that the rendered document carries compressed JPEG
figures (with the quality and width cap used), so a reader of the .docx can
tell it is not the full-resolution deliverable. Pass --no-note to suppress it.

Prints the path of the rewritten .md to stdout (the only stdout line). A
per-image and total size summary goes to stderr.

Usage:
  python jpgify.py <manuscript.md> [--quality N] [--max-width PX] [--force]
                   [--staging DIR] [--out-md PATH] [--no-note]
"""
import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required (pip install Pillow)")

# ![alt](<path> "title")  -- angle-bracket and title parts are optional
IMG_RE = re.compile(r'(!\[[^\]]*\]\()(<?)([^)>\s]+)(>?)(\s+"[^"]*")?(\))')

# raster extensions worth converting to JPEG
CONVERT_EXTS = {".png"}


def note_text(quality: int, max_width, n_converted: int, n_kept: int) -> str:
    """End-of-document note stating that the figures are compressed JPEGs."""
    size = f", downscaled to a maximum width of {max_width} px" if max_width else ""
    mixed = (f" The remaining {n_kept} figure{'s are' if n_kept > 1 else ' is'} kept as "
             f"the original PNG." if n_kept else "")
    return (f"*Figure note: to reduce the file size, {n_converted} figure"
            f"{'s' if n_converted > 1 else ''} in this document "
            f"{'are' if n_converted > 1 else 'is a'} compressed JPEG image"
            f"{'s' if n_converted > 1 else ''} (quality {quality}{size}) rather than the "
            f"original figure file{'s' if n_converted > 1 else ''}.{mixed}*")


def convert_one(src: Path, dst: Path, quality: int, max_width):
    im = Image.open(src)
    src_dpi = im.info.get("dpi")     # read before flattening: a new RGB canvas has no info
    # flatten alpha / palette transparency onto a white background
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    # keep the physical size: pandoc places an image at pixels / dpi and only scales it
    # DOWN to the page width, so a JPG without a density tag counts as 96 dpi, comes out
    # ~27 in wide and is scaled to exactly the column width, which stretches figures that
    # were authored narrower than the column. Scale the source dpi with the
    # resize so the JPG keeps the PNG's width in inches.
    dpi = src_dpi
    if max_width and im.width > max_width:
        scale = max_width / im.width
        h = round(im.height * scale)
        im = im.resize((max_width, h), Image.LANCZOS)
        if dpi:
            dpi = (dpi[0] * scale, dpi[1] * scale)
    dst.parent.mkdir(parents=True, exist_ok=True)
    kw = dict(quality=quality, optimize=True, progressive=True)
    if dpi and dpi[0] > 0:
        kw["dpi"] = (round(dpi[0]), round(dpi[1]))
    im.save(dst, "JPEG", **kw)


def main():
    ap = argparse.ArgumentParser(description="Convert referenced PNGs to JPG and rewrite the .md.")
    ap.add_argument("manuscript")
    ap.add_argument("--quality", type=int, default=85, help="JPEG quality 1-95 (default 85)")
    ap.add_argument("--max-width", type=int, default=None,
                    help="downscale images wider than this many pixels (default: no downscale)")
    ap.add_argument("--force", action="store_true",
                    help="use JPG even when it is larger than the source PNG")
    ap.add_argument("--staging", default=None,
                    help="dir for JPGs + rewritten md (default: a fresh temp dir)")
    ap.add_argument("--out-md", default=None,
                    help="path for the rewritten md (default: <staging>/<manuscript name>)")
    ap.add_argument("--no-note", action="store_true",
                    help="do not append the compressed-JPEG note at the end of the document")
    args = ap.parse_args()

    md_path = Path(args.manuscript).resolve()
    if not md_path.exists():
        sys.exit(f"manuscript not found: {md_path}")
    text = md_path.read_text(encoding="utf-8")
    src_dir = md_path.parent

    staging = Path(args.staging).resolve() if args.staging else Path(tempfile.mkdtemp(prefix="jpgify_"))
    staging.mkdir(parents=True, exist_ok=True)

    seen = {}  # src -> jpg Path (converted) or None (kept as PNG)
    stats = {"n": 0, "kept": 0, "before": 0, "after": 0}

    def repl(m):
        pre, lb, path, rb, title, close = m.groups()
        title = title or ""
        if re.match(r"^[a-z][a-z0-9+.-]*://", path, re.I):  # leave URLs alone
            return m.group(0)
        if Path(path).suffix.lower() not in CONVERT_EXTS:
            return m.group(0)
        src = (src_dir / path).resolve()
        if not src.exists():
            print(f"  MISSING (left as-is): {path}", file=sys.stderr)
            return m.group(0)
        if src not in seen:
            rel = os.path.relpath(src, src_dir)
            if rel.startswith(".."):  # figure outside the manuscript folder (a journal
                rel = os.path.join("_ext", src.name)  # branch under journal/<j>/): keep it inside staging
            jpg = (staging / rel).with_suffix(".jpg")
            convert_one(src, jpg, args.quality, args.max_width)
            b, a = src.stat().st_size, jpg.stat().st_size
            if a < b or args.force:
                stats["n"] += 1
                stats["before"] += b
                stats["after"] += a
                print(f"  {rel}: {b // 1024} KB -> {a // 1024} KB", file=sys.stderr)
                seen[src] = jpg
            else:
                jpg.unlink(missing_ok=True)  # PNG was smaller; keep it
                stats["kept"] += 1
                print(f"  {rel}: kept PNG ({b // 1024} KB; JPG would be {a // 1024} KB)",
                      file=sys.stderr)
                seen[src] = None
        return m.group(0) if seen[src] is None else f"{pre}{lb}{seen[src].as_posix()}{rb}{title}{close}"

    new_text = IMG_RE.sub(repl, text)

    if stats["n"] and not args.no_note:
        note = note_text(args.quality, args.max_width, stats["n"], stats["kept"])
        new_text = new_text.rstrip("\n") + "\n\n---\n\n" + note + "\n"

    out_md = Path(args.out_md).resolve() if args.out_md else staging / md_path.name
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(new_text, encoding="utf-8")

    if stats["n"]:
        b, a = stats["before"], stats["after"]
        pct = 100 * (b - a) // b if b else 0
        extra = f", max-width {args.max_width}px" if args.max_width else ""
        kept = f"; {stats['kept']} kept as PNG" if stats["kept"] else ""
        print(f"Converted {stats['n']} PNG -> JPG (q{args.quality}{extra}){kept}: "
              f"{b // 1024} KB -> {a // 1024} KB on the converted set "
              f"({pct}% smaller)", file=sys.stderr)
    elif stats["kept"]:
        print(f"No PNG converted: all {stats['kept']} were already smaller as PNG "
              f"(use --force to convert anyway).", file=sys.stderr)
    else:
        print("No PNG images converted (none referenced or all missing).", file=sys.stderr)

    print(out_md)


if __name__ == "__main__":
    main()
