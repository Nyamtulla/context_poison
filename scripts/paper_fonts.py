"""Give every paper figure the paper's own text font.

main.tex loads newtxtext, whose text face is TeX Gyre Termes X. Until
2026-11-05 the figure scripts asked matplotlib for plain "serif", found no
Times on this box, and fell back to DejaVu Serif, so every figure was set in
a different, wider face from the text around it. The font files are vendored
in third_party/fonts/termesx so the figures build the same on any machine;
we load the .ttf copies, because matplotlib embeds the .otf (CFF) files under
the wrong font type (see otf2ttf.py there).
"""
import pathlib

from matplotlib import font_manager

FONTS = pathlib.Path(__file__).resolve().parent.parent / "third_party" / "fonts" / "termesx"
FAMILY = "TeX Gyre TermesX"


def use_paper_font(rc):
    """Register the four Termes X faces and make them the default family."""
    files = sorted(FONTS.glob("*.ttf"))
    if len(files) != 4:
        raise SystemExit(f"paper font missing: expected 4 .ttf files in {FONTS};"
                         " run third_party/fonts/termesx/otf2ttf.py")
    for f in files:
        font_manager.fontManager.addfont(str(f))
    rc.update({"font.family": FAMILY})
