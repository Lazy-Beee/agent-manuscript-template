# Figures — {{NAME}} manuscript

Content-named PNGs, data-driven ones regenerated from `scripts/`. File names are decoupled
from the draft's "Figure N", so reordering the manuscript is a `.md`-only change.

> **Figure numbers live in ONE place: the provenance table below.** Everything else (TODO,
> README, script docstrings) refers to a figure by its content name. Update this table in
> the same commit as any figure renumbering (`tools/renumber_figures_tables.py`).

## Size rule (house style)

The docx places every figure at the text-column width, **6.5 in** (Letter page, 1 in
margins), and pandoc only scales images *down* to it, so a figure saved at most 6.5 in wide
is placed unscaled and every font size in it is the size the reader sees. All figure text is
**10 pt DejaVu Sans** (= the 12 pt Aptos body in x-height and letter width; 11 pt reads
larger than the body), panel tags **11 pt bold**, output **600 dpi**. `scripts/figstyle.py`
carries the knobs (`FIG_W_MAX`, `font.size`, `PANEL_LABEL_SIZE`, `DPI`) and `save()` warns
when a PNG overshoots the column. Check the placed size in the rendered docx, not in the PNG.
Axis and colorbar labels carry a unit in brackets only when the quantity has one.

## Scripts

| Kind | Name | Does |
|---|---|---|
| Freeze | `scripts/freeze_<content>.py` | Reads the raw data (simulation output, measurements) read-only and writes `scripts/figdata/<content>/` |
| Figure | `scripts/fig_<content>.py` | Draws one figure from `figdata/` into `figures/<content>.png` |
| Stats | `scripts/stats_<topic>.py` | Prints the numbers the text quotes, from `figdata/` |

Frozen data fall under the `*.csv` / `*.npz` ignore rules; force-add (`git add -f`) the
files a figure or a quoted number depends on.

## Provenance

Examples of the row format (shown as a list, to be replaced by real rows):

- `| process_schematic.png | Figure 1 | - (drawn by hand; source process_schematic.svg) | - |`
- `| temperature_history.png | Figure 4 | scripts/fig_temperature_history.py | scripts/figdata/temperature_history/ |`
- `| case_comparison.png | Figure 7 | scripts/fig_case_comparison.py | scripts/figdata/case_comparison/ |`

| File | Draft figure | Script | Data |
|------|--------------|--------|------|

## Retired figures

Superseded PNGs move to `retire/<reason-YYYY-MM-DD>/`; list them here with the reason.
