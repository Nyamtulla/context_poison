"""Convert the Termes X .otf faces (CFF outlines) to .ttf (TrueType outlines).

matplotlib's PDF backend embeds a font as Type 42, which is TrueType. Given a
CFF-outline .otf it embeds the CFF data under a TrueType font type, and
pdffonts reports "Mismatch between font type and embedded font file"; a strict
checker such as IEEE PDF eXpress can reject that. TrueType outlines embed
cleanly. Outlines are converted with cu2qu at 1/1000 em tolerance, which is
not visible at print size.

    python3 third_party/fonts/termesx/otf2ttf.py
"""
import pathlib

from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable

HERE = pathlib.Path(__file__).resolve().parent


def convert(src, dst, max_err=1.0):
    f = TTFont(src)
    order = f.getGlyphOrder()
    gs = f.getGlyphSet()
    glyf = newTable("glyf")
    glyf.glyphOrder, glyf.glyphs = order, {}
    for name in order:
        pen = TTGlyphPen(gs)
        gs[name].draw(Cu2QuPen(pen, max_err, reverse_direction=True))
        glyf[name] = pen.glyph()
    f["loca"] = newTable("loca")
    f["glyf"] = glyf
    del f["CFF "]
    if "VORG" in f:
        del f["VORG"]
    glyf.compile(f)
    for name in order:                       # left side bearings follow the new outlines
        g = glyf[name]
        adv, _ = f["hmtx"][name]
        f["hmtx"][name] = (adv, getattr(g, "xMin", 0))
    maxp = newTable("maxp")
    maxp.tableVersion = 0x00010000
    maxp.numGlyphs = len(order)
    for k in ("maxZones", "maxTwilightPoints", "maxStorage", "maxFunctionDefs",
              "maxInstructionDefs", "maxStackElements", "maxSizeOfInstructions"):
        setattr(maxp, k, 0)
    maxp.maxZones = 1
    for k in ("maxPoints", "maxContours", "maxCompositePoints", "maxCompositeContours",
              "maxComponentElements", "maxComponentDepth"):
        setattr(maxp, k, 0)
    f["maxp"] = maxp
    f["head"].glyphDataFormat = 0
    post = f["post"]
    post.formatType = 2.0
    post.extraNames, post.mapping = [], {}
    post.glyphOrder = order
    f.sfntVersion = "\x00\x01\x00\x00"
    f.save(dst)                              # save() recomputes maxp and bounds


if __name__ == "__main__":
    for src in sorted(HERE.glob("*.otf")):
        convert(src, src.with_suffix(".ttf"))
        print("wrote", src.with_suffix(".ttf").name)
