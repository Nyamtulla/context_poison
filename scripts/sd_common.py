"""What every second-direction runner shares: contexts in, a registry file out.

The second direction puts security-literature defenses in front of failures no
attacker wrote. Each defense runs in its own pinned environment, so the parts
that must be identical across them -- which passages an item gets, how an
answer is scored, what the result file looks like -- live here, and import
nothing heavier than the standard library and the scoring helpers.

A runner supplies three callables, all taking (question, passages) and
returning the model's answer as a string:

    undefended   the defense's own base pipeline with the defense switched off
    defended     the same pipeline with the defense on
    closedbook   the base model with no passage at all

and `run_cell` does the rest: every dose, every arm, the same schema as the
RobustRAG registries, and a per-prediction log so an interrupted cell resumes
where it stopped instead of starting over.
"""
from __future__ import annotations

import datetime
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from transfer_stats import min_detectable_change, wilson   # noqa: E402
from spare_vs_corpus_poisoning import acc_score            # noqa: E402
from poisonedrag_transfer import is_negative, is_refusal   # noqa: E402

CTX_DIR = REPO / "data" / "sd_contexts"


def load_contexts(failure, n=None, ctx_dir=None):
    """The shared contexts for one failure; `n` keeps the first n (smoke)."""
    d = json.loads(((ctx_dir or CTX_DIR) / f"{failure}.json").read_text())
    if n is not None:
        d["items"] = d["items"][:n]
    return d


def score(preds, rows, failure):
    """The RobustRAG registries' row schema, from a list of answers."""
    correct = attacked = refused = negative = 0
    for pred, row in zip(preds, rows):
        pred = str(pred)
        correct += acc_score(pred, row["gold"])
        attacked += acc_score(pred, row["target"])
        refused += is_refusal(pred)
        negative += is_negative(pred)
    n = len(rows)
    lo, hi = wilson(int(attacked), n)
    return {"n": n, "acc": round(correct / n * 100, 2),
            "asr": round(attacked / n * 100, 2),
            "refusal_rate": round(refused / n * 100, 2),
            "negative_framing_rate": round(negative / n * 100, 2),
            "wrong_answer_rate": round(attacked / n * 100, 2),
            "asr_ci_low": round(lo * 100, 1), "asr_ci_high": round(hi * 100, 1)}


class PredLog:
    """Append-only log of every answer, keyed by (arm, dose, item).

    A cell is hours of GPU time, and a session restart has killed runs here
    before. Reopening the log skips every answer already written.
    """

    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.done = {}
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    self.done[(r["arm"], r["dose"], r["idx"])] = r
        self.fh = self.path.open("a")

    def get(self, arm, dose, idx):
        r = self.done.get((arm, dose, idx))
        return None if r is None else r["pred"]

    def put(self, arm, dose, idx, pred, extra=None):
        r = {"arm": arm, "dose": dose, "idx": idx, "pred": str(pred)}
        if extra:
            r.update(extra)
        self.done[(arm, dose, idx)] = r
        self.fh.write(json.dumps(r) + "\n")
        self.fh.flush()


class Memo:
    """Persistent cache of one deterministic pipeline's answers.

    The wrapper defenses in sd_rag_base.py share their undefended and
    no-retrieval arms exactly: same model, same template, same passages,
    greedy decoding. Computing those arms once per defense would triple the
    GPU time for the same numbers, so each answer is cached under a hash of
    (question, passages) and reused by every defense on that pipeline.
    """

    def __init__(self, path):
        import hashlib
        self._h = hashlib
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.cache = {}
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    self.cache[r["k"]] = r["pred"]
        self.fh = self.path.open("a")

    def key(self, question, passages):
        blob = json.dumps([question, list(passages)]).encode()
        return self._h.sha256(blob).hexdigest()

    def wrap(self, fn):
        def cached(question, passages):
            k = self.key(question, passages)
            if k not in self.cache:
                self.cache[k] = str(fn(question, passages))
                self.fh.write(json.dumps({"k": k, "pred": self.cache[k]}) + "\n")
                self.fh.flush()
            return self.cache[k]
        return cached


def run_cell(*, defense, family, failure, model, undefended, defended,
             closedbook, out_path, log_path, n=None, doses=None, notes=None,
             arms=("closedbook", "undefended", "defended"), extra_fn=None):
    """Run every arm at every dose and write the registry file.

    `extra_fn(arm, dose, row, pred)` may return a dict stored beside the
    answer in the log -- the detectors use it to record which passages they
    flagged, so a reader can see what the filter removed and not only the
    accuracy that resulted.
    """
    ctx = load_contexts(failure, n)
    rows = ctx["items"]
    doses = doses or ctx["doses"]
    log = PredLog(log_path)
    results = []
    for arm in arms:
        fn = {"closedbook": closedbook, "undefended": undefended,
              "defended": defended}[arm]
        # the no-retrieval arm does not depend on the dose: measured once,
        # written against every dose, as in the RobustRAG registries.
        arm_doses = [doses[0]] if arm == "closedbook" else doses
        for j in arm_doses:
            preds = []
            for row in rows:
                pred = log.get(arm, j, row["idx"])
                if pred is None:
                    passages = ([] if arm == "closedbook"
                                else row["contexts"][str(j)])
                    pred = fn(row["question"], passages)
                    extra = extra_fn(arm, j, row, pred) if extra_fn else None
                    log.put(arm, j, row["idx"], pred, extra)
                preds.append(pred)
            r = score(preds, rows, failure)
            if arm == "closedbook":
                for jj in doses:
                    results.append(dict(r, arm=arm, n_poison=jj))
                print(f"  closedbook   acc {r['acc']:5.1f}%", flush=True)
            else:
                results.append(dict(r, arm=arm, n_poison=j))
                print(f"  {arm:10s} {j:>2}/{ctx['top_k']}  acc {r['acc']:5.1f}%"
                      f"   wrong {r['asr']:5.1f}%", flush=True)
    payload = {"generated": datetime.date.today().isoformat(),
               "defense": defense, "defense_family": family,
               "attack": failure, "placement": "retrieval",
               "dataset": "open_nq", "n": len(rows), "top_k": ctx["top_k"],
               "model": model, "contexts_sha256": ctx["sha256"],
               "mdr_pp_at_n": round(min_detectable_change(len(rows), 0.5), 1),
               "notes": notes or {}, "results": results}
    out = pathlib.Path(out_path)
    out.write_text(json.dumps(payload, indent=1))
    print(f"\nwrote {out}  (mdr {payload['mdr_pp_at_n']} pp)", flush=True)
    return payload
