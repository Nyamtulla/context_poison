"""Resolve "evaluated on benchmark B" into "evaluated against attack A".

The problem this closes: 67 defenses report evaluating on AgentDojo, 37 on
InjecAgent, 17 on ASB - and RQ3 extracted ZERO mechanisms from all three
benchmark papers, so every one of those evaluations pointed at something the
registry treated as empty. That is the single largest cause of RQ5's apparent
coverage gap, and it is a coding artefact rather than a fact about the field.

The trap this avoids: a defense "evaluated on AgentDojo" is almost never
evaluated against all 23 of AgentDojo's attacks. Most use `important_instructions`
alone. Expanding benchmark -> every constituent attack would manufacture
coverage on a large scale and would be worse than the gap it claims to fix.

So resolution is only granted when the paper NAMES the attack it used inside the
benchmark. Three outcomes per defense:

  mechanism_level   the paper names the specific attack -> a real pair
  benchmark_level   the paper names only the benchmark -> coverage of the
                    benchmark, explicitly NOT of any mechanism
  unresolved        no benchmark in our inventory

    python scripts/resolve_benchmark_mechanisms.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import registry_source

REPO = Path(__file__).resolve().parent.parent
INVENTORY = REPO / "data/registries/benchmark_mechanism_inventory.json"
TARGETS = REPO / "data/registries/defense_eval_targets.json"
OUT = REPO / "data/registries/benchmark_resolution.json"

# How each benchmark's attack families appear in prose. Keys must match the
# inventory's family names; the patterns are what a defense paper actually
# writes when it says which attack it ran.
ATTACK_PATTERNS = {
    "AgentDojo": {
        "important_instructions": r"important[\s_-]?instruction",
        "ignore_previous": r"ignore[\s_-]?previous",
        "direct": r"\bdirect attack\b|\bdirect injection\b",
        "system_message": r"system[\s_-]?message attack|###\s*\(?system_message",
        "tool_knowledge": r"tool[\s_-]?knowledge",
        "neural_exec": r"neural[\s_-]?exec",
        "injecagent": r"injecagent[\s-]?style|injecagent attack string",
        "dos": r"\bdos attack|denial[\s-]?of[\s-]?service attack",
    },
    "InjecAgent": {
        "Direct Harm": r"direct harm",
        "Data Stealing": r"data steal",
    },
    "ASB (Agent Security Bench)": {
        "DPI (Direct Prompt Injection)": r"\bDPI\b",
        "OPI (Observation Prompt Injection)": r"\bOPI\b",
        "Memory Poisoning": r"memory poison",
        "Plan-of-Thought (PoT) Backdoor": r"\bPoT\b|plan[\s-]of[\s-]thought backdoor",
        "Mixed attack": r"\bmixed attack\b",
    },
}
ALIASES = {"AgentDojo": ["AgentDojo"], "InjecAgent": ["InjecAgent", "InjectAgent"],
           "ASB (Agent Security Bench)": ["ASB", "Agent Security Bench"]}


def main() -> None:
    inv = json.loads(INVENTORY.read_text())["benchmarks"]
    targets = {r["row"]: r for r in json.loads(TARGETS.read_text())}
    papers = {p["paper_id"]: p for p in registry_source.load_papers()}
    reg = registry_source.load_all()

    rows = []
    for d in reg["defenses"]:
        t = targets.get(d["_row"], {})
        p = papers.get(d["source_paper_id"]) or {}
        # Everything the paper said about its evaluation, in one blob.
        blob = " ".join(str(p.get(f) or "") for f in
                        ("datasets_benchmarks", "baselines_compared", "key_result",
                         "technical_summary", "threat_model"))
        found_benches, named_attacks = [], []
        for bench, aliases in ALIASES.items():
            if not any(re.search(rf"(?<![A-Za-z0-9]){re.escape(a)}(?![A-Za-z0-9])", blob, re.I)
                       for a in aliases):
                continue
            found_benches.append(bench)
            for fam, pat in ATTACK_PATTERNS.get(bench, {}).items():
                if re.search(pat, blob, re.I):
                    named_attacks.append(f"{bench}::{fam}")
        level = ("mechanism_level" if named_attacks
                 else "benchmark_level" if found_benches else "unresolved")
        rows.append({
            "row": d["_row"], "defense_name": d["defense_name"], "track": d["track"],
            "stage": d["intervention_point"] or "none",
            "registry_matched": d["n_mechanisms_tested"] > 0,
            "benchmarks_used": found_benches,
            "named_attacks_within_benchmark": sorted(set(named_attacks)),
            "resolution_level": level,
        })
    OUT.write_text(json.dumps({"generated": "2026-09-11", "resolution": rows}, indent=1) + "\n")

    print(f"defenses: {len(rows)}\n")
    for k, v in Counter(r["resolution_level"] for r in rows).most_common():
        print(f"  {v:4d}  {k}")
    print()
    unmatched = [r for r in rows if not r["registry_matched"]]
    print(f"=== of the {len(unmatched)} with NO RQ5 registry match ===")
    for k, v in Counter(r["resolution_level"] for r in unmatched).most_common():
        print(f"  {v:4d}  {k}")
    gain = [r for r in unmatched if r["resolution_level"] == "mechanism_level"]
    print(f"\n  -> resolvable to a SPECIFIC attack (real new pairs): {len(gain)}")
    print(f"  -> benchmark-level only (NOT new coverage):          "
          f"{sum(1 for r in unmatched if r['resolution_level'] == 'benchmark_level')}")
    print("\n=== which benchmark attacks defense papers actually name ===")
    for k, v in Counter(a for r in rows for a in r["named_attacks_within_benchmark"]).most_common(14):
        print(f"  {v:4d}  {k}")
    print("\nwrote", OUT)


if __name__ == "__main__":
    main()
