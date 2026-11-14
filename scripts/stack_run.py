"""RQ4, measured: a security filter in front of a safety fix, on both regimes.

RQ4 asks whether the two communities, taken together, cover context
poisoning. The census says their fixes act at different stages and nothing
joins them; this runs the join. Stage one is a security filter that acts where
text enters: it drops the retrieved passages its detector flags. Stage two is
a safety fix that acts where the model reasons: it answers from the passages
that survive. Each runs unmodified -- the filter's flags come from its own
detector (sd_detect_classifier.py, sd_detect_datasentinel.py, computed once per
passage), the fix from its own released code through defenses.py -- so the
stack composes two published methods without changing either.

Every item and dose is answered in five arms on the same contexts:

    closedbook   no passage at all
    undefended   all passages, fix off
    filter       the passages the filter keeps, fix off
    fix          all passages, fix on
    stack        the passages the filter keeps, fix on

and on both regimes: the attacks' planted passages and the honest mistakes,
from the same context files the second direction used (data/sd_contexts).
Each answer is scored as correct, the planted answer, or a refusal. The filter's
own behaviour is recorded too: how many passages it dropped, and how often it
dropped a planted one.

    PYTHONPATH=envs/acd-libs python3 scripts/stack_run.py --fix acd \
        --mechanism incidental_stale

Out: data/registries/stack_<fix>_<mechanism>.json, with a per-answer log in
data/stack_logs/ so an interrupted run resumes where it stopped.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from sd_common import PredLog, load_contexts, score         # noqa: E402
from transfer_stats import min_detectable_change, wilson    # noqa: E402

FLAG_DIR = REPO / "data" / "sd_flags"
FILTERS = ["piguard", "datasentinel"]
# CoConflictQA, where ACD's control ran; its five shots are drawn from just past
# the control's evaluation slice, exactly as scripts/control_gate.py draws them
COCQ = (REPO / "third_party" / "ParamMute" / "data" / "CoConflictQA"
        / "test" / "NaturalQuestionsShort_kc.jsonl")


def sha(text):
    return hashlib.sha1(text.encode()).hexdigest()


def acd_shots(n_eval=400, max_chars=2000):
    rows = [json.loads(l) for l in COCQ.open()]
    kept = [r for r in rows if len(r["context"]) <= max_chars]
    shots = kept[n_eval:n_eval + 5]
    if len(shots) < 5:
        raise SystemExit("not enough held-out items for ACD's few-shots")
    return shots


def load_flags(name):
    path = FLAG_DIR / f"{name}.json"
    if not path.exists():
        raise SystemExit(f"no flags for {name}: run its detector first")
    return json.loads(path.read_text())["flags"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", default="acd")
    ap.add_argument("--mechanism", required=True,
                    help="a context file in data/sd_contexts, e.g. incidental_stale")
    ap.add_argument("--filters", nargs="+", default=FILTERS)
    ap.add_argument("--doses", nargs="+", type=int, default=[0, 1, 5])
    ap.add_argument("--n", type=int, default=None, help="smoke: first n items")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    ctx = load_contexts(a.mechanism, a.n)
    rows = ctx["items"]
    doses = [z for z in a.doses if str(z) in rows[0]["contexts"]]
    flags = {f: load_flags(f) for f in a.filters}
    # every passage must have a verdict from every filter before anything runs
    for row in rows:
        for z in doses:
            for p in row["contexts"][str(z)]:
                for f, fl in flags.items():
                    if sha(p) not in fl:
                        raise SystemExit(f"{f} has not flagged a passage of "
                                         f"{a.mechanism}; run its detector "
                                         "with --attacks")

    import defenses
    kw = {"shots": acd_shots()} if a.fix == "acd" else {}
    d = defenses.load(a.fix, **kw)
    off, on = d.arms[0], d.name               # e.g. "rag" and "acd"

    tag = f"{a.fix}_{a.mechanism}" + (f"_n{a.n}" if a.n else "")
    log = PredLog(REPO / "data" / "stack_logs" / f"stack_{tag}.jsonl")
    out = pathlib.Path(a.out or REPO / "data" / "registries" / f"stack_{tag}.json")

    preds = {}                                 # (arm, dose) -> [pred per row]
    fstats = {(f, z): {"dropped": 0, "passages": 0, "planted": 0,
                       "planted_dropped": 0, "items_all_planted_dropped": 0}
              for f in a.filters for z in doses}
    for z in doses:
        for i, row in enumerate(rows):
            q, idx = row["question"], row["idx"]
            ps = row["contexts"][str(z)]
            clean = set(row["contexts"]["0"]) if "0" in row["contexts"] else set()
            planted = [p for p in ps if p not in clean] if z else []
            cache = {}

            def ask(passages):
                key = tuple(passages)
                if key not in cache:
                    cache[key] = d.answer(q, list(passages))
                return cache[key]

            # the all-passage arms, computed once and shared by both filters
            arms_all = {"closedbook": "closedbook", "undefended": off, "fix": on}
            if any(log.get(arm, z, idx) is None for arm in arms_all):
                r = ask(ps)
                for arm, k in arms_all.items():
                    if log.get(arm, z, idx) is None:
                        log.put(arm, z, idx, r[k])
            for arm in arms_all:
                preds.setdefault((arm, z), []).append(log.get(arm, z, idx))

            for f in a.filters:
                kept = [p for p in ps if not flags[f][sha(p)]["flag"]]
                st = fstats[(f, z)]
                st["passages"] += len(ps)
                st["dropped"] += len(ps) - len(kept)
                st["planted"] += len(planted)
                pd = sum(1 for p in planted if p not in kept)
                st["planted_dropped"] += pd
                st["items_all_planted_dropped"] += int(bool(planted) and pd == len(planted))
                for arm, k in ((f"filter:{f}", off), (f"stack:{f}", on)):
                    if log.get(arm, z, idx) is None:
                        if kept == ps:            # nothing dropped: same answer
                            pred = log.get("undefended" if k == off else "fix", z, idx)
                        else:
                            pred = ask(kept)[k]
                        log.put(arm, z, idx, pred, {"dropped": len(ps) - len(kept)})
                    preds.setdefault((arm, z), []).append(log.get(arm, z, idx))
            if (i + 1) % 50 == 0:
                print(f"  dose {z}: {i + 1}/{len(rows)}", flush=True)
        print(f"dose {z} done {datetime.datetime.now():%m-%d %H:%M}", flush=True)

    results = []
    for (arm, z), ps in sorted(preds.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        s = score(ps, rows, a.mechanism)
        lo, hi = wilson(round(s["acc"] * s["n"] / 100), s["n"])
        s.update({"arm": arm, "n_poison": z,
                  "acc_ci_low": round(lo * 100, 1), "acc_ci_high": round(hi * 100, 1)})
        results.append(s)
    filt = [{"filter": f, "n_poison": z, **st,
             "drop_rate": round(100 * st["dropped"] / max(st["passages"], 1), 2),
             "planted_drop_rate": (round(100 * st["planted_dropped"] / st["planted"], 2)
                                   if st["planted"] else None)}
            for (f, z), st in fstats.items()]
    out.write_text(json.dumps({
        "generated_by": "scripts/stack_run.py",
        "question": "RQ4: does a security filter in front of a safety fix hold "
                    "where each alone does not?",
        "fix": a.fix, "model": defenses.BASE, "mechanism": a.mechanism,
        "filters": a.filters, "doses": doses, "n": len(rows),
        "contexts_sha256": ctx.get("sha256"),
        "mdr_pp_at_n": round(min_detectable_change(len(rows), 0.5), 1),
        "arms": ["closedbook", "undefended", "fix"]
                + [f"{k}:{f}" for f in a.filters for k in ("filter", "stack")],
        "results": results, "filter_stats": filt,
        "finished": f"{datetime.datetime.now():%Y-%m-%d %H:%M}"}, indent=1) + "\n")
    print(f"wrote {out.relative_to(REPO)}")
    for z in doses:
        line = "  ".join(f"{r['arm']}={r['acc']:.0f}/{r['asr']:.0f}"
                         for r in results if r["n_poison"] == z)
        print(f"  dose {z} (correct/planted %): {line}")


if __name__ == "__main__":
    main()
