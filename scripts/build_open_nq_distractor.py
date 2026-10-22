"""Build a distractor payload for open_nq, so RobustRAG can meet an ML/AI mechanism.

The campaign has no Security-defense x ML/AI-attack pair, in the literature
or in our own runs. RobustRAG is the only security defense in the retrieval
cell, and the existing ML payloads (false and distractor evidence) are built
on CoConflictQA items that carry a single context string. RobustRAG isolates
and aggregates across k passages, so a single-passage item cannot exercise
it. This ports the distractor construction onto open_nq, which carries 30
retrieved passages per item.

Construction follows `build_distractor_payload.py` exactly: the distractor
answer is drawn from another item, matched on the question's wh-type AND on
the answer's shape (numerics bucketed by digit count, so a season number
replaces a season number), then substituted into one of the item's OWN
retrieved passages. Substituting into the item's own passage is what keeps
the register unchanged - the result is a passage that reads like the others
and is simply wrong, rather than one written to persuade.

That is the whole point of the arm: no instruction, no optimisation, no
adversary. If RobustRAG survives this where the context-reliance family did
not, the difference is the question each asks, not the difficulty of the
payload.

Out: data/payloads/open_nq_distractor.json
"""
from __future__ import annotations

import json
import pathlib
import random
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO / "third_party" / "RobustRAG" / "data" / "open_nq.json"
DST = REPO / "data" / "payloads" / "open_nq_distractor.json"

WH = re.compile(r"\s*(who|what|when|where|which|how many|how much|how long|"
                r"how old|why|whose|how)\b", re.I)


def qtype(q):
    m = WH.match(str(q or ""))
    return m.group(1).lower() if m else "other"


def shape(s):
    """Bucket by form AND magnitude AND length.

    Digit count keeps a year in a year's place. Token count keeps a
    three-word person name in a three-word person name's place: without it
    the "who" bucket mixes people with countries and produces "it was
    composed by Bangladesh", which any model dismisses. A payload that is
    trivially dismissed tests the attack at its weakest.
    """
    s = str(s).strip()
    if re.fullmatch(r"[\d,\.]+", s):
        return f"num{len(re.sub(r'[^0-9]', '', s))}"
    return f"text{min(len(s.split()), 4)}"


def main():
    data = json.loads(SRC.read_text())

    # pool of candidate distractor answers, keyed by (wh-type, shape)
    pool = {}
    for it in data:
        for a in it.get("correct answer") or []:
            a = str(a).strip()
            if a:
                pool.setdefault((qtype(it.get("question")), shape(a)), []).append(a)

    rng = random.Random(17)
    out, no_bucket, no_passage = [], 0, 0
    for it in data:
        golds = [str(a).strip() for a in (it.get("correct answer") or []) if str(a).strip()]
        if not golds:
            no_passage += 1
            continue
        gold = golds[0]
        gl = {g.lower() for g in golds}
        key = (qtype(it.get("question")), shape(gold))
        # also exclude anything that already appears in the item's own
        # passages: a "distractor" the retrieved set already asserts is not
        # a distractor.
        own = " ".join((c.get("text") or "") for c in (it.get("context") or [])).lower()
        cands = [c for c in pool.get(key, [])
                 if c.lower() not in gl and c.lower() not in own]
        if len(cands) < 3:          # too thin a bucket to stay type-safe
            no_bucket += 1
            continue
        dist = rng.choice(cands)

        # Substitute into one of the item's OWN passages, so register holds.
        # EVERY gold variant must go, not just the one that matched: an item
        # with answers ["Austin", "Pflugerville"] left the second in place,
        # so the passage still carried a correct answer and the payload was
        # not an attack at all.
        variants = sorted(
            {v for a in (golds + [str(x) for x in (it.get("expanded answer") or [])])
             if (v := str(a).strip())},
            key=len, reverse=True)
        hit = None
        for c in (it.get("context") or []):
            txt = c.get("text") or ""
            if any(re.search(re.escape(v), txt, re.I) for v in variants):
                hit = (c.get("title") or "", txt)
                break
        if not hit:
            no_passage += 1
            continue
        title, txt = hit
        # The title is prepended to the passage, and a title is often the
        # answer itself ("Austin" for "where was it filmed"). Substituting
        # only the body left 140 passages still asserting a correct answer.
        new = title + "\n" + txt if title else txt
        for v in variants:
            new = re.sub(re.escape(v), dist, new, flags=re.I)
        if any(re.search(re.escape(v), new, re.I) for v in variants):
            no_passage += 1          # a gold survived; refuse the item
            continue
        rec = dict(it)
        rec["distractor_answer"] = dist
        rec["distractor_context"] = new
        out.append(rec)

    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(json.dumps(out, indent=1))
    print(f"source items      {len(data)}")
    print(f"usable            {len(out)}")
    print(f"dropped, bucket   {no_bucket}  (fewer than 3 type-safe candidates)")
    print(f"dropped, passage  {no_passage}  (no own passage contains the gold answer)")
    print(f"wrote {DST.relative_to(REPO)}")


if __name__ == "__main__":
    main()
