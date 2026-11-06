# TeX Gyre Termes X, the paper's text font

The four `.otf` faces (regular, bold, italic, bold italic) that `newtxtext`
uses for the paper's text, copied from TeX Live 2025
(`texmf-dist/fonts/opentype/public/newtx/`) on 2026-11-05. TeX Gyre fonts are
under the GUST Font License (`GUST-FONT-LICENSE.txt`, beside this file); the
newtx package is under the LaTeX Project Public License 1.3.

`otf2ttf.py` converts each to a `.ttf` with TrueType outlines, and
`scripts/paper_fonts.py` registers the `.ttf` files with matplotlib, so every
figure is set in the same face as the text. matplotlib embeds fonts as
TrueType (Type 42); given the `.otf` files it embedded CFF data under that
type, which `pdffonts` flags and a strict PDF checker can reject. The PDFs
embed the subset they use.
