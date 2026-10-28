"""Run every paper-quality check that can be automated, in one command.

The paper will be revised for months. These rules come from four sources and
are too many to hold in a head between iterations, so the ones a machine can
test live here and the rest live in PAPER_CHECKLIST.md.

    python3 scripts/check_paper_style.py

Sources, and what each contributes:

  VUSEC, "Writing a System Security Paper (A Checklist)"
      American English, no defensive phrasing, no contractions, no section
      with exactly one subsection, figures and tables centered.
  McDaniel, "How to Write a Security Paper" (Penn State SIIS)
      Short sentences with defined scope. Novelty stated explicitly.
  van der Kouwe et al., "Benchmarking Crimes" (EuroS&P 2019)
      Platform specification, software versions, a stated baseline, a stated
      measure of significance.
  Roscoe, "Writing reviews for systems conferences"
      What a reviewer looks for in order: a summarisable claim, explicit
      contributions, explicit novelty, stated limitations.

A FAIL is a rule with no judgement in it. A WARN is a rule where the right
answer is sometimes no, so read the line before changing anything.
"""
from __future__ import annotations

import collections
import pathlib
import re
import statistics
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
SEC = REPO / "latex" / "sections"
TAB = REPO / "latex" / "tables"

BRIT = (r"\b(behaviour|favourable|modelled|modelling|organis\w*|centre|labelled"
        r"|summaris\w*|memoris\w*|synthesis\w*e\b|standardis\w*|minimis\w*|maximis\w*|optimis\w*|recognis\w*|analys(e|ed|ing)\b"
        r"|characteris\w*|generalis\w*|normalis\w*|utilis\w*|prioritis\w*"
        r"|defence|licence|towards|whilst|amongst|learnt|spelt)\b")
DEFENSIVE = (r"\b(we argue that|we believe|we feel|it should be noted"
             r"|it is worth noting|it is important to note|arguably"
             r"|in our opinion)\b")
CONTRACTION = r"\b(don't|won't|can't|isn't|aren't|doesn't|didn't|hasn't|haven't)\b"
FILLER = r"\b(very|clearly|obviously|of course|simply put|remarkably)\b"

fails = warns = 0


def say(ok, rule, detail="", warn=False):
    global fails, warns
    tag = "  ok  " if ok else ("  WARN" if warn else "  FAIL")
    if not ok:
        if warn:
            warns += 1
        else:
            fails += 1
    print(f"{tag}  {rule}" + (f"   {detail}" if detail else ""))


def body():
    out = {}
    for p in sorted(SEC.glob("*.tex")):
        t = re.sub(r"(?m)^\s*%.*$", "", p.read_text())
        out[p.name] = t
    return out


def prose(t):
    t = re.sub(r"\\begin\{(tabular|table\*?|figure\*?|longtable)\}.*?"
               r"\\end\{\1\}", "", t, flags=re.S)
    t = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^{}]*\})?", " ", t)
    return re.sub(r"\s+", " ", t)


def main():
    B = body()
    joined = "\n".join(B.values())
    # The presence checks below look for phrases, and the sources are hard
    # wrapped, so a phrase that straddles a line break reads as missing. The
    # novelty statement failed this way while sitting in the introduction.
    flow = re.sub(r"\s+", " ", joined)

    print("\n[style]  VUSEC + McDaniel")
    for name, pat, warn in (("American English", BRIT, False),
                            ("no defensive phrasing", DEFENSIVE, False),
                            ("no contractions", CONTRACTION, False),
                            ("no filler words", FILLER, True)):
        hits = collections.Counter(m.group(0).lower()
                                   for m in re.finditer(pat, joined, re.I))
        say(not hits, name, dict(hits.most_common(6)) if hits else "", warn)

    lens = [len(s.split()) for t in B.values()
            for s in re.split(r"(?<=[.!?]) ", prose(t)) if len(s.split()) > 3]
    long_ = sum(1 for x in lens if x > 40)
    say(statistics.mean(lens) < 22, "mean sentence under 22 words",
        f"mean {statistics.mean(lens):.1f}, median {statistics.median(lens):.0f}")
    say(long_ <= 12, "at most 12 sentences over 40 words", f"{long_} found", True)

    print("\n[structure]  VUSEC")
    bad = [f for f, t in B.items()
           if re.findall(r"(?m)^\\section\{", t)
           and len(re.findall(r"(?m)^\\subsection\{", t)) == 1]
    say(not bad, "no section with exactly one subsection", bad)
    rules = [f for f, t in list(B.items())
             + [(p.name, p.read_text()) for p in TAB.glob("*.tex")]
             if "\\hline" in t or re.search(r"\\begin\{tabular\}\{[^}]*\|", t)]
    say(not rules, "booktabs only, no vertical rules or hline", rules)
    uncentered = []
    for f, t in list(B.items()) + [(p.name, p.read_text()) for p in TAB.glob("*.tex")]:
        for m in re.finditer(r"\\begin\{(table\*?|figure\*?)\}.*?\\end\{\1\}", t, re.S):
            if "\\centering" not in m.group(0):
                uncentered.append(f)
    say(not uncentered, "every float centered", sorted(set(uncentered)))

    print("\n[benchmarking crimes]  van der Kouwe et al.")
    for name, pat in (("platform specified (F1)", r"A6000|GPU|NVIDIA"),
                      ("software versions given (F2)", r"transformers}? \d|PyTorch \d|Python \d"),
                      ("baseline stated (D1)", r"undefended arm|no-retrieval|closed-book"),
                      ("significance stated (B4)", r"detectab|Wilson|confidence interval|power")):
        say(bool(re.search(pat, flow, re.I)), name)

    print("\n[reviewer's eye]  Roscoe")
    for name, pat in (("contributions explicit", r"\\paragraph\{Contributions"),
                      ("novelty explicit", r"What is new here|first evaluation in which"),
                      ("scope/limits stated early", r"\\paragraph\{Scope"),
                      ("threat model present", r"\\(?:sub)?section\{(?:Threat model|System and threat model)")):
        say(bool(re.search(pat, flow)), name)

    # A float the prose never points at is a float the reader never looks
    # at. Two figures and two tables shipped unreferenced before this check
    # existed, each of them carrying an argument the text was making in
    # words a page away.
    print("\n[every float is pointed at]")
    labels = set(re.findall(r"\\label\{((?:fig|tab):[^}]+)\}", joined))
    for lab in sorted(labels):
        say(bool(re.search(r"\\(?:auto)?ref\{" + re.escape(lab) + r"\}",
                           joined)), f"{lab} referenced in the text")

    print(f"\n{fails} fail, {warns} warn")
    print("Judgement-based rules that no script can check are in "
          "PAPER_CHECKLIST.md; run through them before each submission.")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
