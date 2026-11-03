"""Shared plot style + helpers for the manuscript figure set.

Every fig_<content>.py imports this, so the whole set restyles from one place: change
the font sizes / line widths / DPI / panel aspect here and re-run the figure scripts.

Design intent: author each figure AT its final size in the manuscript docx (width
<= FIG_W_MAX = 6.5 in, the text-column width) so that every font size below is the
size the reader sees: 10 pt DejaVu Sans matches the 12 pt Aptos body text in x-height
and letter width (11 pt matched only the cap height and read visibly larger than the
body). Rendered at high DPI so it stays crisp when zoomed in.

Only the core style and save() are here; add shared helpers (scale bars, annotation
arrows, image stacking, series colours) to this module as figures need them, so every
script draws them the same way.
"""

import os
import matplotlib as mpl
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "figdata")

SAVE_PDF = False              # set True for vector copies alongside the PNGs
DPI = 600                     # main figures
OUT_DIR = os.path.dirname(HERE)   # the figures/ folder

PANEL_LABEL_SIZE = 11         # the a) b) c) ... panel tags (bold, one step above the 10 pt text)
PANEL_BOX_ASPECT = 3 / 4      # chart panel height/width = 3/4 -> 4:3 landscape
LINE_W = 1.6                  # data line / errorbar width

# The manuscript docx places every figure at the text-column width, 6.5 in (Letter page,
# 1 in margins; pandoc scales wider images down to it and leaves narrower ones at their
# native size). A figure saved wider than FIG_W_MAX is shrunk in the document and every
# font size is shrunk with it, so each script lays its panels out inside this width and
# save() warns when the tight-bbox output overshoots it.
FIG_W_MAX = 6.5


def _check_width(png_path, name):
    """Report the saved PNG width in inches at DPI and warn when it exceeds FIG_W_MAX."""
    try:
        from PIL import Image
        w_px, h_px = Image.open(png_path).size
    except Exception:
        return
    w_in, h_in = w_px / DPI, h_px / DPI
    flag = ("  <-- WIDER THAN %.2f in: shrunk in the docx, fonts shrink with it" % FIG_W_MAX
            if w_in > FIG_W_MAX + 0.01 else "")
    print(f"  {name}.png: {w_in:.2f} x {h_in:.2f} in{flag}")


def apply_style():
    """House style for the whole figure set. Tweak here to restyle everything."""
    mpl.rcParams.update({
        "figure.dpi": 110,
        "savefig.dpi": DPI,
        # every text element at 10 pt = the docx body size (12 pt Aptos) in x-height and
        # letter width; the figure is placed unscaled, so these are the sizes on the page
        "font.size": 10,
        "axes.titlesize": 10,
        "axes.titlelocation": "left",
        "axes.labelsize": 10,
        "legend.fontsize": 10,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "lines.linewidth": LINE_W,
        "lines.markersize": 6,
        "axes.linewidth": 0.9,
        "axes.grid": False,
        "savefig.bbox": "tight",
    })


def set_box(ax):
    """Give a chart panel the shared box aspect (PANEL_BOX_ASPECT)."""
    ax.set_box_aspect(PANEL_BOX_ASPECT)


def panel_label(ax, letter):
    """Bold upper-left panel tag, e.g. panel_label(ax, 'a') -> 'a)'."""
    ax.set_title(f"{letter})", loc="left", fontsize=PANEL_LABEL_SIZE, fontweight="bold")


def shared_legend(fig, ax, ncol=2, y=0.0, markerscale=1, loc="lower center"):
    """One figure-level legend (centred, bottom by default) built from `ax`'s handles,
    so the per-panel legends can be dropped. Reserve room with tight_layout(rect=...)."""
    handles, labels = ax.get_legend_handles_labels()
    return fig.legend(handles, labels, loc=loc, ncol=ncol,
                      frameon=False, bbox_to_anchor=(0.5, y), markerscale=markerscale)


def save(fig, name, into_figures=True):
    """Write <name>.png (and .pdf if SAVE_PDF) into the parent figures/ folder
    (overwriting the manuscript PNG). Pass into_figures=False to keep it in scripts/."""
    out_root = OUT_DIR if into_figures else HERE
    out = os.path.join(out_root, name)
    # matplotlib collapses the WIDTH of every axis label when it computes the tight bbox
    # (Axes.get_tightbbox -> for_layout_only), so an x-label wider than its panel that runs
    # past the figure edge is cut off; listing the labels as extra artists puts their full
    # extent back (a bare list REPLACES the default artist set, so start from that set)
    extra = (list(fig.get_default_bbox_extra_artists())
             + [lab for ax in fig.axes for lab in (ax.xaxis.label, ax.yaxis.label) if lab.get_text()])
    fig.savefig(out + ".png", dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.02,
                bbox_extra_artists=extra)
    if SAVE_PDF:
        fig.savefig(out + ".pdf", facecolor="white", bbox_inches="tight", pad_inches=0.02,
                    bbox_extra_artists=extra)
    plt.close(fig)
    print(f"  wrote {name}.png")
    _check_width(out + ".png", name)


def data_path(*parts):
    return os.path.join(DATA_DIR, *parts)
