"""Read the three stage-D checks of the second-direction campaign.

Stage D asks why two results came out as they did, from the answer logs the
runs already wrote:

  * AttnTrace (tracing only). When the model gives the planted answer, is
    the passage AttnTrace ranks first one of the planted ones? Every grid
    context puts its planted passages at the bottom of the ranked list
    (positions 10-j..9), so the check reruns 100 stale-document items with
    the same passages in a shuffled order, and reads both.
  * Position. The same shuffled items, undefended, say how much of the stale
    document's effect came from sitting at the end of the context.
  * ReliabilityRAG at five stale passages of ten. Its trace records every
    per-passage answer and the set it kept, so the outvoting explanation is
    counted rather than inferred.

Answers are scored with the campaign's own scorer (sd_common's acc_score).
A traced or isolated answer is "stale" if it contains the planted answer and
not the gold one, "correct" the other way round.

    python3 scripts/analyze_stage_d.py

Out: data/registries/check_stage_d.json
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from spare_vs_corpus_poisoning import acc_score   # noqa: E402

LOGS = REPO / "data" / "sd_logs"
CTX = REPO / "data" / "sd_contexts"
OUT = REPO / "data" / "registries" / "check_stage_d.json"


def items(name):
    return {it["idx"]: it for it in
            json.loads((CTX / f"{name}.json").read_text())["items"]}


def log(name):
    return [json.loads(l) for l in (LOGS / name).read_text().splitlines()
            if l.strip()]


def kind(pred, it):
    g, t = acc_score(pred, it["gold"]), acc_score(pred, it["target"])
    return "stale" if t and not g else "correct" if g and not t else "other"


def attntrace(logname, ctxname, shuffled):
    """Share of answers whose top-traced passage is planted, by answer kind."""
    I = items(ctxname)
    top1, recall = collections.defaultdict(list), collections.defaultdict(list)
    for r in log(logname):
        if r["arm"] != "defended" or r["dose"] == 0 or "traced_ranked" not in r:
            continue
        it, j = I[r["idx"]], r["dose"]
        bad = set(it["bad"][str(j)]) if shuffled else set(range(10 - j, 10))
        k = kind(r["first_answer"], it)
        top1[k].append(r["traced_ranked"][0] in bad)
        recall[(k, j)].append(len(bad & set(r["traced_ranked"])) / len(bad))
    return ({k: {"n": len(v), "top1_planted": round(100 * sum(v) / len(v), 1)}
             for k, v in top1.items()},
            {f"{k}@{j}": round(100 * sum(v) / len(v), 1)
             for (k, j), v in recall.items()})


def position():
    """Stale-answer rate, undefended, same 100 items: end of list vs shuffled."""
    I = items("incidental_stale_shuffled")
    out = {}
    for lbl, name in (("end", "attntrace_incidental_stale_qwen2.5-7b.jsonl"),
                      ("shuffled",
                       "attntrace_incidental_stale_shuffled_qwen2.5-7b.jsonl")):
        c = collections.Counter()
        for r in log(name):
            if r["arm"] == "undefended" and r["idx"] in I and r["dose"] in (1, 3, 5):
                c[r["dose"]] += acc_score(r["pred"], I[r["idx"]]["target"])
        out[lbl] = {j: c[j] for j in (1, 3, 5)}
    out["n"] = len(I)
    return out


def reliabilityrag():
    """What MISBasedRRAG kept, and when the stale answer won, at dose 5."""
    I = items("incidental_stale")
    stale_pos, honest_pos = range(5, 10), range(5)
    kept, by_size, honest, n_skip = collections.Counter(), collections.Counter(), collections.Counter(), 0
    rows = log("reliabilityrag_incidental_stale_mistral7b_trace.jsonl")
    for r in rows:
        # A handful of items record fewer than ten per-passage answers: the
        # wrapper keeps the last batch_query call, and for these their code
        # issued a later one. Those traces cannot be read per passage.
        if len(r["responses"]) != 10:
            n_skip += 1
            continue
        it = I[r["idx"]]
        K = [kind(x, it) for x in r["responses"]]
        for i in honest_pos:
            x = r["responses"][i].lower()
            honest["idk" if "know" in x and ("don't" in x or "do not" in x)
                   else K[i]] += 1
        sel = set(r["selected"])
        kept["all_stale" if sel and sel <= set(stale_pos) else
             "all_honest" if sel and sel <= set(honest_pos) else
             "mixed" if sel else "empty"] += 1
        n_stale = sum(K[i] == "stale" for i in stale_pos)
        n_gold = sum(K[i] == "correct" for i in honest_pos)
        grp = "stale_larger" if n_stale > n_gold else "not_larger"
        by_size[(grp, kind(r["pred"], it) == "stale")] += 1
    n = sum(kept.values())
    size = {g: {"n": by_size[(g, True)] + by_size[(g, False)],
                "stale_answer": round(100 * by_size[(g, True)]
                                      / max(1, by_size[(g, True)] + by_size[(g, False)]), 1)}
            for g in ("stale_larger", "not_larger")}
    return {"n": n, "skipped_incomplete_trace": n_skip,
            "kept_all_stale_pct": round(100 * kept["all_stale"] / n, 1),
            "kept": dict(kept),
            "honest_passage_answers_pct": {k: round(100 * v / (5 * n), 1)
                                           for k, v in honest.items()},
            "by_group_size": size}


def main():
    sh_top1, sh_recall = attntrace(
        "attntrace_incidental_stale_shuffled_qwen2.5-7b.jsonl",
        "incidental_stale_shuffled", True)
    end_top1, end_recall = attntrace(
        "attntrace_incidental_stale_qwen2.5-7b.jsonl", "incidental_stale", False)
    out = {"attntrace_shuffled_top1": sh_top1,
           "attntrace_shuffled_recall": sh_recall,
           "attntrace_end_top1": end_top1,
           "attntrace_end_recall": end_recall,
           "position_stale_answers": position(),
           "reliabilityrag_dose5": reliabilityrag()}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
