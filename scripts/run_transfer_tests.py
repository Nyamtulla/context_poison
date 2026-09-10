"""Transfer tests: DataSentinel vs. mechanisms it has never been tested against.

Every run carries three controls, so a result is interpretable rather than a
bare number:

  clean         the untouched example. Flags here are false positives.
  adversarial   CombineAttacker, the injection from DataSentinel's OWN paper.
                This is the positive control: if it does not read ~100%, the
                detector is not working and nothing else in the run means
                anything.
  incidental    an unrelated non-instructional sentence appended. Establishes
                the detector is keying on injection structure, not on "extra
                text".

Then one condition per mechanism, built by transfer_scenarios.py from that
mechanism's own paper.
"""
import argparse
import json
import random
import sys

sys.path.insert(0, ".")

import OpenPromptInjection as PI
from OpenPromptInjection.utils import open_config
from OpenPromptInjection.attackers.CombineAttacker import CombineAttacker

from transfer_scenarios import SCENARIOS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--ft_path", default="./checkpoints/detector_large/checkpoint-5000")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="transfer_results.json")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    target = PI.create_task(open_config("./configs/task_configs/sst2_config.json"), args.n)
    inject = PI.create_task(open_config("./configs/task_configs/sms_spam_config.json"),
                            args.n, for_injection=True)
    attacker = CombineAttacker(None, inject)

    cfg = open_config("./configs/model_configs/mistral_config.json")
    cfg["params"]["ft_path"] = args.ft_path
    cfg["params"]["gpus"] = ["0"]
    det = PI.DataSentinelDetector(cfg)

    clean = [target[i][0] for i in range(len(target))]
    conditions = {"clean": [], "adversarial_control": [], "incidental_control": []}
    for s in SCENARIOS:
        conditions[s["mechanism"] + (f" [{s['variant']}]" if s.get("variant") else "")] = []

    for i, text in enumerate(clean):
        print(f"[{i+1}/{len(clean)}]", flush=True)
        conditions["clean"].append(bool(det.detect(text)))
        conditions["adversarial_control"].append(
            bool(det.detect(attacker.inject(text, i, target_task="sentiment_analysis"))))
        donor = clean[rng.choice([j for j in range(len(clean)) if j != i])]
        conditions["incidental_control"].append(bool(det.detect(text + " " + donor)))
        for s in SCENARIOS:
            key = s["mechanism"] + (f" [{s['variant']}]" if s.get("variant") else "")
            conditions[key].append(bool(det.detect(s["build"](text))))

    summary = {k: {"n": len(v), "flagged_pct": round(100 * sum(v) / len(v), 1)}
               for k, v in conditions.items()}
    out = {"defense": "DataSentinel", "n": args.n,
           "strategies": {s["mechanism"] + (f" [{s['variant']}]" if s.get("variant") else ""):
                          s["strategy"] for s in SCENARIOS},
           "summary": summary, "raw": conditions}
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1)

    print("\n" + "=" * 78)
    for k, v in summary.items():
        print(f"  {v['flagged_pct']:6.1f}%  {k}")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
