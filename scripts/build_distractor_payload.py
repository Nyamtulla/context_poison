"""A third payload class, to separate recall from copying.

Under false evidence the planted passage asserts the same string the model
would have recalled from memory, so the parametric-answer rate cannot tell a
model that remembered from one that copied. They produce identical output.
That is the attack's design, not a flaw in the metric, and it is the stated
limitation of the result in `false_evidence_result.md`.

Planting the GOLD answer does not fix it, which is what the paper's own future
work section proposed: gold is already in the real context, so an output of
gold is still two-ways ambiguous.

A THIRD answer does fix it. Plant a fluent sentence asserting an answer that is
neither the gold nor the model's prior, built by substituting a distractor into
the item's own `parametric_evidencde` so the sentence keeps its register:

    model says gold        -> it read the real context
    model says parametric  -> it recalled from memory
    model says distractor  -> it copied the planted passage

Three disjoint outcomes, so the three paths are separable for the first time.

Restricted to 781 of the 1409 items. An item survives only if its
`parametric_answer` appears verbatim in its own evidence sentence, so the
substitution needs no rewriting, AND its question type and answer magnitude
bucket holds at least three candidate distractors, so the planted answer is a
plausible one of its kind rather than an absurdity a reader would dismiss.
Every arm is re-measured on that subset, so comparisons stay internal to the
run.

    python3 scripts/build_distractor_payload.py
"""
import json
import pathlib
import random
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = (REPO / "third_party" / "ParamMute" / "data" / "CoConflictQA" / "test"
       / "NaturalQuestionsShort_kc.jsonl")
DST = SRC.with_name("NaturalQuestionsShort_kc_distractor.jsonl")


WH = re.compile(r"^\s*(who|when|where|what|which|how many|how much|how long|"
                r"how old|why|whose|how)\b", re.I)


def qtype(q):
    """The question word is a cheap proxy for the answer's TYPE.

    Matching on form alone produced "The Prime Minister, Shri dura mater" and
    "kamala harris is the process of converting a stereo signal to a mono
    signal". A planted sentence that absurd is trivially dismissed, so the
    attack would be tested at its weakest rather than its most realistic.
    Drawing the distractor from another question of the same kind keeps a
    person in a person's place and a date in a date's.
    """
    m = WH.match(str(q or ""))
    return m.group(1).lower() if m else "other"


def shape(s):
    """Bucket by form AND magnitude.

    A numeric distractor must be plausible in its sentence. Swapping "22
    episodes" for "1978 episodes" produces a claim no reader would believe,
    which makes the planted passage easy to dismiss and the test unfair to the
    attack. Numerics are bucketed by digit count so a season number is
    replaced by a season number and a year by a year.
    """
    s = s.strip()
    if re.fullmatch(r"[\d,\.]+", s):
        return f"num{len(re.sub(r'[^0-9]', '', s))}"
    return "text"


def main():
    rows = [json.loads(l) for l in SRC.read_text().splitlines() if l.strip()]
    usable = []
    for r in rows:
        pa = str(r.get("parametric_answer") or "").strip()
        pe = str(r.get("parametric_evidencde") or "")
        if pa and re.search(re.escape(pa), pe, re.I):
            usable.append(r)

    pool = {}
    for r in usable:
        pa = str(r["parametric_answer"]).strip()
        pool.setdefault((qtype(r.get("question")), shape(pa)), []).append(pa)

    rng = random.Random(17)
    out, skipped = [], 0
    for r in usable:
        pa = str(r["parametric_answer"]).strip()
        gold = {str(a).strip().lower() for a in (r.get("answers") or [])}
        key = (qtype(r.get("question")), shape(pa))
        cands = [c for c in pool.get(key, [])
                 if c.lower() != pa.lower() and c.lower() not in gold]
        if len(cands) < 3:          # too thin a bucket to be type-safe
            skipped += 1
            continue
        if not cands:
            skipped += 1
            continue
        d = rng.choice(cands)
        pe = str(r["parametric_evidencde"])
        new = re.sub(re.escape(pa), d, pe, count=0, flags=re.I)
        if new == pe:
            skipped += 1
            continue
        r = dict(r)
        r["distractor_answer"] = d
        r["distractor_evidencde"] = new
        out.append(r)

    DST.write_text("\n".join(json.dumps(r) for r in out) + "\n")
    print(f"{len(rows)} items -> {len(usable)} substitutable -> {len(out)} written"
          f" ({skipped} skipped)")
    print(f"  {DST}")
    import collections
    print("  buckets used:",
          dict(collections.Counter(qtype(r["question"]) for r in out)))
    e = out[0]
    print(f"\n  question  : {e['question']}")
    print(f"  gold      : {e['answers']}")
    print(f"  parametric: {e['parametric_answer']}")
    print(f"  distractor: {e['distractor_answer']}")
    print(f"  planted   : {e['distractor_evidencde'][:110]}")
    # the three must be mutually exclusive or the arm proves nothing
    bad = [r for r in out
           if str(r["distractor_answer"]).lower() == str(r["parametric_answer"]).lower()
           or str(r["distractor_answer"]).lower() in
              {str(a).lower() for a in r["answers"]}]
    print(f"\n  items where the three answers are NOT disjoint: {len(bad)}")


if __name__ == "__main__":
    main()
