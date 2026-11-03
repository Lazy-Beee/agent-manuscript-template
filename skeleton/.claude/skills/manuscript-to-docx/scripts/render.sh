#!/usr/bin/env bash
# Render a manuscript Markdown file to .docx with the manuscript-to-docx Lua
# filters (mergecol.lua = merged group columns, eqnum.lua = right-aligned
# equation numbers, caption_style.lua = 10 pt figure/table captions with a bold
# label, refs_left.lua = left-aligned reference entries). Filters and the
# bundled reference doc are resolved relative to this script; pass
# --reference-doc to override the reference doc.
#
# --jpg converts the referenced PNG figures to JPG first (via jpgify.py) and
# renders from a rewritten copy, to shrink the .docx. The source .md and the
# original figures are left untouched. By default --jpg also caps figure width at
# 2600 px (~400 DPI at 6.5 in, print-quality); pass --jpg-max-width 0 to keep full
# resolution. The rendered document ends with a note stating that its figures are
# compressed JPEGs; pass --no-jpg-note to suppress it.
#
# Usage:
#   render.sh <manuscript.md> [output.docx]
#   render.sh <manuscript.md> [output.docx] --jpg [--jpg-quality N] [--jpg-max-width PX] [--no-jpg-note]
set -euo pipefail

md=""; out=""; jpg=0; quality=85; maxwidth=2600; refdoc=""; jpgnote=1
while [ $# -gt 0 ]; do
  case "$1" in
    --jpg) jpg=1; shift ;;
    --jpg-quality) quality="$2"; shift 2 ;;
    --jpg-max-width) maxwidth="$2"; shift 2 ;;
    --no-jpg-note) jpgnote=0; shift ;;
    --reference-doc) refdoc="$2"; shift 2 ;;
    -*) echo "unknown option: $1" >&2; exit 2 ;;
    *) if [ -z "$md" ]; then md="$1"; elif [ -z "$out" ]; then out="$1"; else echo "extra arg: $1" >&2; exit 2; fi; shift ;;
  esac
done
: "${md:?usage: render.sh <manuscript.md> [output.docx] [--jpg [--jpg-quality N] [--jpg-max-width PX] [--no-jpg-note]]}"
out="${out:-${md%.md}.docx}"

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
filters="$here/../filters"
dir="$(cd "$(dirname "$md")" && pwd)"

# Reference doc: caller-supplied template wins; otherwise the bundled one, which
# defines the caption style (Figure/Table captions at 10 pt via caption_style.lua).
refdoc="${refdoc:-$here/../assets/reference.docx}"

render_md="$md"
staging=""
cleanup() { if [ -n "$staging" ]; then rm -rf "$staging"; fi; }  # must return 0: it sets the exit code
trap cleanup EXIT

if [ "$jpg" -eq 1 ]; then
  staging="$(mktemp -d "${TMPDIR:-/tmp}/jpgify_XXXXXX")"
  jpg_args=("$here/jpgify.py" "$md" --quality "$quality" --staging "$staging")
  [ "$maxwidth" -gt 0 ] && jpg_args+=(--max-width "$maxwidth")
  [ "$jpgnote" -eq 0 ] && jpg_args+=(--no-note)
  render_md="$(python "${jpg_args[@]}" | tail -n 1)"
  [ -n "$render_md" ] || { echo "jpgify failed" >&2; exit 1; }
fi

pandoc "$render_md" \
  --from=markdown+tex_math_dollars-implicit_figures \
  --to=docx \
  --resource-path="$dir" \
  --lua-filter "$filters/mergecol.lua" \
  --lua-filter "$filters/eqnum.lua" \
  --lua-filter "$filters/caption_style.lua" \
  --lua-filter "$filters/refs_left.lua" \
  --reference-doc "$refdoc" \
  -o "$out"

# Word-only formatting of grouped tables (merged first column); a no-op without them.
python "$here/format_grouped_tables.py" "$out"

echo "OK -> $out"
