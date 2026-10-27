#!/bin/bash
# Compile the paper locally and report what a reviewer would notice.
#
# There was no TeX toolchain on this box for a long time, so several problems
# shipped that a single build would have caught: an unescaped ampersand in a
# generated bibliography entry that halted the compile outright, a caret left
# outside math mode by escaping the dollar signs around it, and a 40-digit
# corpus id printed on all 723 references. Build before pushing.
#
#   scripts/build_paper.sh            # build, report, leave the PDF in /tmp
#   scripts/build_paper.sh --open     # also render page 1 to PNG
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT=/tmp/paper_build
TECTONIC="${TECTONIC:-$HOME/.local/bin/tectonic}"

[ -x "$TECTONIC" ] || { echo "no tectonic at $TECTONIC"; exit 1; }
rm -rf "$OUT" && cp -r "$REPO/latex" "$OUT" && cd "$OUT" || exit 1

"$TECTONIC" -X compile main.tex 2>/tmp/paper_build.log >/dev/null
rc=$?
if [ $rc -ne 0 ]; then
    echo "BUILD FAILED"
    grep -E '^error' /tmp/paper_build.log | head -10
    exit 1
fi

pages=$(pdfinfo main.pdf | awk '/^Pages/{print $2}')
over=$(grep -oE 'Overfull \\hbox \([0-9.]+pt' /tmp/paper_build.log | grep -oE '[0-9.]+' | awk '$1>15' | wc -l)
# Underfull hboxes are loose lines a reader sees as rivers of white space.
# vbox cases come from float placement and are left to LaTeX.
under=$(grep -oE 'Underfull \\hbox \(badness [0-9]+' /tmp/paper_build.log | grep -oE '[0-9]+$' | awk '$1>3000' | sort -u | wc -l)
undef=$(grep -cE "Citation .* undefined|Reference .* undefined|undefined (reference|citation)" /tmp/paper_build.log)
# The log grep alone missed three dangling \ref that rendered as "??" on the
# page, so check the rendered text too. That is the thing a reader sees.
qq=$(pdftotext main.pdf - 2>/dev/null | grep -oE '\?\?|⁇' | wc -l)
undef=$(( undef + qq ))
echo "built  $OUT/main.pdf"
echo "  pages              $pages"
echo "  undefined cites/refs $undef   (must be 0)"
echo "  overfull boxes >15pt $over"
echo "  underfull lines      $under"
# Match the rendered headings on their own line. Matching loosely found
# "the full census" in a sentence on page 2 and reported the appendix there.
for p in $(seq 1 "$pages"); do
    t=$(pdftotext -f "$p" -l "$p" main.pdf - 2>/dev/null)
    # acmart prints REFERENCES, IEEEtran prints References. Match either,
    # or the report silently loses the body/references split on a class change.
    [ -z "${refp:-}" ] && echo "$t" | grep -qiE '^references[[:space:]]*$' \
        && { refp=$p; echo "  references start    p$p"; }
    [ -z "${appp:-}" ] && echo "$t" | grep -qiE '^the full census[[:space:]]*$' \
        && { appp=$p; echo "  appendix starts     p$p"; }
done
echo "  body                p1-$(( ${refp:-1} - 1 ))"
[ "${1:-}" = "--open" ] && pdftoppm -f 1 -l 1 -r 90 -png main.pdf /tmp/paper_p && echo "  page 1 -> /tmp/paper_p-01.png"
exit 0
