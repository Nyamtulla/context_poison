"""What does each defense's EVALUATION section actually test it against?

Phase 1 showed the coded fields give a verified floor and an unreliable
middle. Phase 2a established authorship but not testing: RhinoInsight would
pass an origin check, because it genuinely proposes RhinoInsight. What it
fails is this test, and only this one. Its framing claims it combats context
rot; its evaluation is a report-quality score on DeepResearch Bench.

So: locate the paper's own evaluation section and look only inside it. An
introduction that says "we address context rot" is not evidence that context
rot was measured, and the whole point of this pass is to stop counting it as
such.

Three outputs per defense:
  eval_adversarial  an adversarial evaluation signal INSIDE the evaluation
                    section, with the sentence that carries it
  eval_present_non_adversarial  an evaluation section exists and shows no
                    adversarial signal
  no_eval_section   no evaluation section could be located

    python3 scripts/classify_defense_evaluation_section.py
"""
import collections
import json
import pathlib
import re

import openpyxl

REPO = pathlib.Path(__file__).resolve().parent.parent
R = REPO / "data" / "registries"

HEAD = re.compile(
    r"^\s*(?:[0-9IVX]+[\.\)]?\s*)?"
    r"(experiment\w*|evaluation\w*|empirical\w*|results?|"
    r"experimental (setup|evaluation|results)|"
    r"(evaluation|experimental) (setup|design|methodology))\s*$", re.I | re.M)
END = re.compile(
    r"^\s*(?:[0-9IVX]+[\.\)]?\s*)?"
    r"(related work|conclusion\w*|discussion|limitations?|references|"
    r"acknowledg\w*|appendix|future work|ethic\w*)\s*$", re.I | re.M)

# signals that an ADVERSARY was present in what was run
ADV = re.compile(
    r"attack success rate|\bASR\b|under attack|undefended|"
    r"without (any )?defen[cs]e|no[- ]defen[cs]e baseline|"
    r"(?<!non-)(?<!no )adversarial (attack|example|passage|input|prompt|suffix|"
    r"dataset|quer|corpus|benchmark|sample|document|payload|scenario|setting)|"
    r"\b(poisoned|injected|malicious|attacker-controlled) (passage|document|"
    r"context|input|prompt|tool|sample|corpus|memory|instruction)|"
    r"prompt injection (attack|experiment|success|rate)|"
    r"injection (attack|experiment|success rate)|jailbreak|"
    r"agentdojo|injecagent|bipia|poisonedrag|advbench|toolemu|agentharm|"
    r"open-?prompt-?injection|tensortrust|agentsafetybench|"
    r"attack (scenario|corpus|dataset|quer|payload|vector|budget)", re.I)


def load_text(path):
    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf
    try:
        d = pymupdf.open(path)
        t = "\n".join(p.get_text() for p in d)
        d.close()
        return t
    except Exception:
        return ""


def eval_section(txt):
    """The LAST evaluation-like heading that leaves a substantial tail.

    Last rather than first: a paper often lists "Experiments" in a contents
    block or forward-references it in the intro, and those hits leave the
    whole body as a tail, which defeats the point of narrowing.
    """
    best = None
    for m in HEAD.finditer(txt):
        start = m.end()
        e = END.search(txt, start)
        end = e.start() if e else min(len(txt), start + 40000)
        if end - start > 1200:
            best = (start, end)
    return txt[best[0]:best[1]] if best else ""


def main():
    r4 = json.loads((R / "rq4_defense_registry.json").read_text())
    wb = openpyxl.load_workbook(
        REPO / "data" / "exports" / "paper_dashboard_source.xlsx", read_only=True)
    ws = wb["Papers"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    hdr = list(rows[0])
    I = {k: hdr.index(k) for k in ("paper_id", "pdf_local_path")}
    meta = {r[I["paper_id"]]: r for r in rows[1:]}

    cache, out, counts = {}, [], collections.Counter()
    for i, e in enumerate(r4, 1):
        pid = e.get("paper_id")
        rec = {"defense_name": e.get("name"), "row": e.get("row"),
               "paper_id": pid, "track": e.get("track"),
               "claims": e.get("validated_against")}
        m = meta.get(pid)
        p = m[I["pdf_local_path"]] if m else None
        if not p or not pathlib.Path(p).exists():
            rec.update(eval_status="no_eval_section", evidence="no PDF")
            counts["no_eval_section"] += 1; out.append(rec); continue
        if pid not in cache:
            cache[pid] = eval_section(load_text(p))
        sec = cache[pid]
        if not sec:
            rec.update(eval_status="no_eval_section",
                       evidence="no evaluation section located")
            counts["no_eval_section"] += 1
        else:
            mm = ADV.search(sec)
            if mm:
                a = max(0, mm.start() - 130)
                rec.update(eval_status="eval_adversarial",
                           evidence=sec[a:mm.end() + 130].replace("\n", " ").strip())
                counts["eval_adversarial"] += 1
            else:
                rec.update(eval_status="eval_present_non_adversarial",
                           evidence=sec[:220].replace("\n", " ").strip())
                counts["eval_present_non_adversarial"] += 1
        out.append(rec)
        if i % 100 == 0:
            print(f"  ...{i}/{len(r4)}", flush=True)

    mismatch = [r for r in out
                if r["claims"] == "adversarial"
                and r["eval_status"] == "eval_present_non_adversarial"]
    (R / "defense_evaluation_section.json").write_text(json.dumps(
        {"generated": "2026-10-15",
         "method": __doc__.strip().split("\n\n")[0],
         "counts": dict(counts), "n_claim_evidence_mismatch": len(mismatch),
         "defenses": out}, indent=1))
    n = len(r4)
    print(f"\n{n} defenses")
    for k, v in counts.most_common():
        print(f"  {v:>4}  {100*v/n:>5.1f}%  {k}")
    print(f"\n  claims adversarial, evaluation section shows none: {len(mismatch)}")


if __name__ == "__main__":
    main()
