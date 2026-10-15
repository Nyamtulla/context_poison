"""For every RQ4 defense, record what its paper actually evaluated it against.

The coverage matrix answers one question: was this defense tested against a
mechanism our RQ3 registry NAMES? For 313 of 527 defenses the answer is no,
and that number has been read as "the defense was never tested against an
attack". Those are not the same claim, and the gap between them is large
enough to matter.

A defense paper that runs on AgentDojo without naming which injection it used
IS evaluated adversarially. It is not a (defense, mechanism) pair, because
expanding a benchmark to all its constituent attacks would manufacture
coverage, and `benchmark_resolved_pairs.json` is deliberately strict about
that. But it is also not untested, and reporting it as untested overstates the
field's neglect.

So this script produces a second, coarser status per defense, and the paper
reports both:

  named_mechanism  appears in >=1 confirmed pair in the coverage matrix
  benchmark_only   evaluated on a known adversarial benchmark, specific
                   attack not named
  adversarial_prose  the evaluation describes attacked vs undefended runs
                   without naming a benchmark
  non_adversarial  real baselines, but on capability or quality benchmarks
                   (LoCoMo, ALFWorld, OSWorld, BrowseComp and the like). Not
                   untested. Its behaviour under attack is simply unknown,
                   which for an incidental-track fix is the normal state and
                   is exactly what this paper is about.
  no_baseline      the paper states it ran no real comparison
  unclear          the coded fields do not say

Precision over recall throughout: anything ambiguous lands in `unclear`.
"""
import collections
import json
import pathlib
import re
import sys

import openpyxl

REPO = pathlib.Path(__file__).resolve().parent.parent
R = REPO / "data" / "registries"
sys.path.insert(0, str(REPO / "scripts"))

BENCH = re.compile(
    r"agentdojo|injecagent|bipia|advbench|poisonedrag|open-?prompt-?injection|"
    r"toolemu|agentharm|tensortrust|agentsafetybench|\basb\b|safebench|"
    r"promptrobust|jailbreakbench|harmbench|agentsecuritybench|"
    r"inject\w*[ -](bench|suite|dataset)|(bench|suite|dataset)[ -]\w*inject", re.I)
# an evaluation that pits attacked runs against clean or undefended ones
# What the paper RAN, not what it assumed. A bare "adversar" token matched
# "non-adversarial" and "no adversarial threat model" 165 times, which is the
# same claim-versus-evidence confusion this whole pass exists to fix. Negated
# forms are excluded explicitly and the threat_model field is not searched.
PROSE = re.compile(
    r"undefended|without (any )?defense|no[- ]defense baseline|attack success rate|"
    r"\basr\b|under attack|attacked (runs|setting|condition)|"
    r"(?<!non-)(?<!no )adversarial (attack|example|passage|input|prompt|suffix|"
    r"setting|condition|robustness|evaluation|baseline|dataset|quer|corpus|"
    r"benchmark|test|sample|document|payload|scenario)|"
    r"attack (input|scenario|corpus|dataset|quer|payload|prompt|vector)|"
    r"unprotected baseline|without (the )?(defense|protection|filtering)|"
    r"red[- ]team|injection (experiment|success|attack)|jailbreak|"
    r"clean (vs|versus|and) (attacked|poisoned)|poisoned (vs|versus) clean|"
    r"poisoning (attack|experiment)", re.I)
# a real comparison, just not an adversarial one
HASBASE = re.compile(r"compared against|baselines?:|baseline categories|"
                     r"serve as (the )?baselines?|vs\.|versus|ablation|"
                     r"evaluated across|benchmarks?:|\bbenchmark\b", re.I)
NOBASE = re.compile(
    r"no implemented baseline|no implemented head-to-head|no head-to-head|"
    r"no empirical baseline|argumentative|rather than reproduced|no third-party|"
    r"not compared against|no external baseline|discussed rather than|"
    r"^\s*none[.\s]", re.I)


def main():
    r4 = json.loads((R / "rq4_defense_registry.json").read_text())
    from pair_tally import composite_pairs
    pairs, _ = composite_pairs()
    matched = {d for d, _ in pairs}

    wb = openpyxl.load_workbook(
        REPO / "data" / "exports" / "paper_dashboard_source.xlsx", read_only=True)
    ws = wb["Papers"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    hdr = list(rows[0])
    I = {k: hdr.index(k) for k in
         ("paper_id", "baselines_compared", "datasets_benchmarks", "key_result",
          "threat_model")}
    meta = {r[I["paper_id"]]: r for r in rows[1:]}

    out, counts = [], collections.Counter()
    for e in r4:
        name = e.get("name")
        m = meta.get(e.get("paper_id"))
        # the evaluation fields only. threat_model states the assumed model,
        # not what was executed, and searching it conflates the two.
        blob = ""
        if m:
            blob = " | ".join(str(m[I[k]] or "") for k in
                              ("baselines_compared", "datasets_benchmarks",
                               "key_result"))
        if name in matched:
            status, why = "named_mechanism", "appears in a confirmed coverage pair"
        elif BENCH.search(blob):
            status = "benchmark_only"
            why = "names an adversarial benchmark: " + BENCH.search(blob).group(0)
        elif NOBASE.search(blob):
            status = "no_baseline"
            why = "paper states no real comparison: " + NOBASE.search(blob).group(0)[:40]
        elif PROSE.search(blob):
            status = "adversarial_prose"
            why = "evaluation describes attacked vs undefended: " + PROSE.search(blob).group(0)
        elif HASBASE.search(blob) and len(blob.strip()) > 60:
            status = "non_adversarial"
            why = "real baselines, no adversarial signal in the coded fields"
        else:
            status, why = "unclear", "coded fields do not say"
        counts[status] += 1
        out.append({"defense_name": name, "paper_id": e.get("paper_id"),
                    "row": e.get("row"), "track": e.get("track"),
                    "validated_against": e.get("validated_against"),
                    "status": status, "evidence": why})

    n = len(r4)
    adversarial = counts["named_mechanism"] + counts["benchmark_only"] + counts["adversarial_prose"]
    (R / "defense_evaluation_status.json").write_text(json.dumps({
        "generated": "2026-10-15",
        "purpose": __doc__.strip().split("\n\n")[0],
        "n_defenses": n,
        "counts": dict(counts),
        "n_evaluated_adversarially": adversarial,
        "pct_evaluated_adversarially": round(100 * adversarial / n, 1),
        "defenses": out}, indent=1))

    print(f"{n} defenses")
    for k, v in counts.most_common():
        print(f"  {v:>4}  {100*v/n:>5.1f}%  {k}")
    print(f"\n  tested against a NAMED registry mechanism : "
          f"{counts['named_mechanism']} ({100*counts['named_mechanism']/n:.1f}%)")
    print(f"  evaluated adversarially in SOME form      : "
          f"{adversarial} ({100*adversarial/n:.1f}%)")
    print(f"  evaluated, but never against an adversary : "
          f"{counts['non_adversarial']} ({100*counts['non_adversarial']/n:.1f}%)")
    print(f"  states it ran no baseline at all          : "
          f"{counts['no_baseline']} ({100*counts['no_baseline']/n:.1f}%)")
    print(f"  still unclear from the coded fields       : "
          f"{counts['unclear']} ({100*counts['unclear']/n:.1f}%)")
    print()
    by = collections.Counter((d["validated_against"], d["status"]) for d in out)
    print("  status by the threat model the paper claims:")
    for (va, stt), c in sorted(by.items(), key=lambda x: -x[1])[:9]:
        print(f"    {c:>4}  claims {va or '(none)':<12} -> {stt}")


if __name__ == "__main__":
    main()
