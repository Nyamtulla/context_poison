"""Measure the paper against the structural rules of ASD-STE100.

Simplified Technical English has two halves. One is a controlled vocabulary of
roughly 900 approved words, which a research paper cannot adopt: "entropy",
"adversarial" and "retrieval-augmented" are not on it and no synonym exists.
STE handles this with Technical Names and Technical Verbs, which are permitted
additions, and that is the exemption this paper lives under.

The other half is structural, applies to any English, and is what actually
makes a page readable. That is what this measures:

  STE-1  a sentence says one thing          <= 25 words (descriptive text)
  STE-2  a paragraph stays short            <= 10 sentences
  STE-3  the actor comes first              active voice
  STE-4  noun clusters stay short           <= 3 nouns in a row
  STE-5  verbs stay simple                  no -ing where a finite verb works

The score is the share of sentences that break no structural rule. A research
paper will not reach 100: some claims need a subordinate clause, and some
passives are correct because the actor is genuinely unknown or irrelevant.
80 is a realistic target and is what the lead asked for.

    python3 scripts/check_ste.py            # score the paper
    python3 scripts/check_ste.py --worst 20 # the sentences to fix first
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
SEC = REPO / "latex" / "sections"
MAX_WORDS = 25
MAX_SENTENCES = 10
MAX_NOUNS = 3

PASSIVE = re.compile(
    r"\b(is|are|was|were|be|been|being)\s+(?:\w+ly\s+)?"
    r"(\w+ed|built|made|shown|given|taken|drawn|run|held|read|written|chosen"
    r"|known|seen|found|put|set|left|kept|told|brought)\b", re.I)
# -ing used as a verb, not as a noun or an adjective we cannot avoid
ING = re.compile(r"\b(?:is|are|was|were|be|been|being)\s+\w+ing\b", re.I)


def prose(t):
    t = re.sub(r"(?m)^\s*%.*$", "", t)
    t = re.sub(r"\\begin\{(tabular|table\*?|figure\*?|longtable|itemize|description)\}"
               r".*?\\end\{\1\}", " ", t, flags=re.S)
    t = re.sub(r"\$[^$]*\$", " MATH ", t)
    t = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^{}]*\})?", " ", t)
    return re.sub(r"[ \t]+", " ", t)


def sentences(par):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", par.strip()) if len(s.split()) > 2]


_NLP = None


def noun_cluster(s):
    """More than three nouns in a row is the STE limit.

    This needs a part-of-speech tagger. A first version guessed from word
    shape and counted verbs as nouns, so it flagged "Success means accuracy
    goes up" and reported 130 violations that were not violations. spaCy
    decides it properly now.

    A technical name is still a technical name: STE permits "large language
    model agent" as one, so a run is only a fault when it is not a term the
    paper has defined. We cannot detect that automatically, so this errs
    toward reporting and the worst-sentence list is read by a person.
    """
    global _NLP
    if _NLP is None:
        import spacy
        _NLP = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
    run = 0
    for tok in _NLP(s):
        if tok.pos_ in ("NOUN", "PROPN"):
            run += 1
            if run > MAX_NOUNS:
                return True
        elif tok.pos_ != "ADJ":
            run = 0
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worst", type=int, default=0)
    a = ap.parse_args()

    rows, long_par = [], []
    for p in sorted(SEC.glob("*.tex")):
        for par in re.split(r"\n\s*\n", prose(p.read_text())):
            ss = sentences(par)
            if len(ss) > MAX_SENTENCES:
                long_par.append((p.name, len(ss)))
            for s in ss:
                n = len(s.split())
                faults = []
                if n > MAX_WORDS:
                    faults.append(f"{n}w")
                if PASSIVE.search(s):
                    faults.append("passive")
                if ING.search(s):
                    faults.append("-ing")
                if noun_cluster(s):
                    faults.append("nouns")
                rows.append((p.name, s, faults))

    clean = sum(1 for _, _, f in rows if not f)
    total = len(rows)
    print(f"\nASD-STE100 structural compliance: "
          f"{100*clean/total:.1f}%  ({clean} of {total} sentences)\n")
    for k, lab in (("25w", "over 25 words"), ("passive", "passive voice"),
                   ("-ing", "progressive verb"), ("nouns", "noun cluster > 3")):
        n = sum(1 for _, _, f in rows
                if any(x.endswith("w") if k == "25w" else x == k for x in f))
        print(f"  {lab:<22}{n:>5}  ({100*n/total:.1f}%)")
    print(f"  {'paragraphs > 10 sent':<22}{len(long_par):>5}")

    print("\n  per section:")
    import collections
    per = collections.defaultdict(lambda: [0, 0])
    for f, _, flt in rows:
        per[f][0] += 1
        if not flt:
            per[f][1] += 1
    for f in sorted(per, key=lambda k: per[k][1] / per[k][0]):
        tot, ok = per[f]
        print(f"    {f:<24}{100*ok/tot:>6.0f}%   {tot-ok:>3} to fix of {tot}")

    if a.worst:
        print(f"\nworst {a.worst} sentences:\n")
        bad = sorted((r for r in rows if r[2]),
                     key=lambda r: -len(r[1].split()))[: a.worst]
        for f, s, flt in bad:
            print(f"  [{','.join(flt)}] {f}")
            print(f"    {s[:150]}\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
