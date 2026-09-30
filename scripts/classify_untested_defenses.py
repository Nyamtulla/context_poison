"""Answer "defends what?" for every defense with no confirmed pair.

`v_defense_scorecard` reports 320 of 534 defenses as tested against zero
registry attacks. Read literally that says the field publishes defenses that
defend nothing, which is false: a defense paper defends something by
definition, and 268 of the 320 state a formal threat model. What the zero
really means is that the thing they defend has no matching entry in the
attack registry - a naming and entity-resolution gap, not an evaluation gap.

This script reads each such defense's own paper (threat model, benchmarks,
baselines, key result, summary, registry notes) and sorts it into what it
actually defends:

  names_registry_attack  the text names an attack that IS in the registry.
                         A missed pair - send it to adjudication.
  names_benchmark        evaluates on a named suite (AgentDojo, BIPIA,
                         LLMail-Inject...) without naming its constituent
                         attacks. Real evaluation, unresolvable to a
                         specific attack without reading the suite.
  self_constructed       built and ran its own attacks, which nobody named,
                         so no shared entity exists to match on.
  threat_named_only      states an adversarial threat in generic terms
                         ("indirect prompt injection") with no named attack
                         or suite.
  non_adversarial        an incidental/context-degradation defense. "Which
                         attack was it tested against" is the wrong question.

It also records each defense's taxonomy-cell peers: the registry attacks
sharing its (channel, consequence) cell. That is a WEAK relation - the same
cell is not the same threat - so it is reported as "never run against each
other", never as coverage.

Run: python3 scripts/classify_untested_defenses.py
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "paper_explorer.db"
OUT = ROOT / "data" / "registries" / "untested_defense_classification.json"

# Suite names that stand in for a set of attacks. A defense evaluating here
# genuinely ran adversarial inputs; we just cannot say which attack without
# expanding the suite, and expanding it would manufacture coverage.
BENCHMARKS = [
    "AgentDojo", "BIPIA", "InjecAgent", "LLMail-Inject", "LLMail",
    "Open-Prompt-Injection", "OpenPromptInjection", "AdvBench", "HackAPrompt",
    "Tensor Trust", "CyberSecEval", "AgentHarm", "ASB", "AgentSecurityBench",
    "SafeAgentBench", "ToolEmu", "R-Judge", "PromptBench", "JailbreakBench",
    "StrongREJECT", "MMLU-PI", "Inj-SQuAD", "AgentDyn", "WASP", "DoomArena",
]

# Generic threat vocabulary. Not attack names - these say WHAT is defended
# when no specific attack is named.
THREATS = [
    ("indirect prompt injection", "indirect prompt injection"),
    ("prompt injection", "prompt injection"),
    ("jailbreak", "jailbreaking"),
    ("memory poisoning", "memory poisoning"),
    ("knowledge (base )?poisoning", "knowledge-base poisoning"),
    ("(rag|retrieval)[- ]poisoning", "RAG poisoning"),
    ("corpus poisoning", "corpus poisoning"),
    ("data poisoning", "data poisoning"),
    ("backdoor", "backdoor"),
    ("tool poisoning", "tool poisoning"),
    ("(mcp|tool)[- ]metadata", "tool-metadata manipulation"),
    ("goal hijack", "goal hijacking"),
    ("privilege escalation", "privilege escalation"),
    ("(exfiltrat|data leak)", "data exfiltration"),
    ("supply chain", "supply-chain compromise"),
    ("sybil|collusion|multi-agent attack", "multi-agent compromise"),
    ("adversarial (example|perturbation)", "adversarial perturbation"),
    ("hallucinat", "hallucination"),
    ("context (rot|degradation|dilution)", "context degradation"),
    ("lost in the middle|long[- ]context", "long-context degradation"),
]

SELF_BUILT = re.compile(
    r"\b(our own|we construct|we design|we build|we develop|self-constructed|"
    r"custom|purpose-built|newly constructed|authors'? own|developed by the "
    r"authors|specifically for this paper|the paper's own)\b", re.I)

STOPNAMES = {"unnamed", "none", "n/a", "attack", "injection", "poisoning",
             "backdoor", "jailbreak", "prompt injection", "baseline"}


def variants(name: str) -> list[str]:
    """Searchable forms of an attack name, minus anything too generic.

    Same rules as the reverse scan: drop the parenthetical expansion, keep a
    bracketed acronym, and never search a bare word on the stopname list -
    matching "injection" would hit every paper in the corpus.
    """
    if name.startswith("UNNAMED:"):
        return []
    base = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
    out = {base, re.sub(r"\s*\([^)]*\)\s*", " ", name).strip()}
    for m in re.finditer(r"\(([A-Z][A-Za-z0-9\-+ ]{1,24})\)", name):
        out.add(m.group(1).strip())
        if name[: m.start()].strip():
            out.add(name[: m.start()].strip())
    return sorted({v for v in out
                   if len(v) >= 4 and v.lower() not in STOPNAMES},
                  key=len, reverse=True)


def is_acronym(v: str) -> bool:
    return len(v) <= 8 and " " not in v and sum(1 for c in v if c.isupper()) >= 2


def main() -> None:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    attacks = [dict(r) for r in con.execute(
        "SELECT name, channel, consequence FROM attack")]
    cell = collections.defaultdict(list)
    for a in attacks:
        cell[(a["channel"], a["consequence"])].append(a["name"])
    # Pre-compile once: 237 attacks x 320 defenses is 76k regex builds otherwise.
    patterns = []
    for a in attacks:
        for v in variants(a["name"]):
            flags = 0 if is_acronym(v) else re.I
            patterns.append((a["name"], v,
                             re.compile(rf"\b{re.escape(v)}\b", flags)))

    rows = [dict(r) for r in con.execute("""
        SELECT d.name, d.channel, d.consequence, d.validated_against, d.track,
               d.intervention_point, d.notes,
               p.paper_id, p.title, p.year, p.threat_model,
               p.datasets_benchmarks, p.baselines_compared, p.key_result,
               p.technical_summary
        FROM defense d JOIN paper p ON p.paper_id = d.paper_id
        WHERE d.name IN (SELECT defense FROM v_defense_scorecard
                         WHERE attacks_tested = 0)
        ORDER BY d.name""")]

    out = []
    for d in rows:
        text = " ".join(str(d[f] or "") for f in (
            "threat_model", "datasets_benchmarks", "baselines_compared",
            "key_result", "technical_summary", "notes"))

        named = sorted({name for name, _v, pat in patterns if pat.search(text)})
        benches = sorted({b for b in BENCHMARKS
                          if re.search(rf"\b{re.escape(b)}\b", text, re.I)})
        threats = sorted({label for pat, label in THREATS
                          if re.search(pat, text, re.I)})

        if d["validated_against"] == "incidental" and not named and not benches:
            kind = "non_adversarial"
        elif named:
            kind = "names_registry_attack"
        elif benches:
            kind = "names_benchmark"
        elif SELF_BUILT.search(text) and threats:
            kind = "self_constructed"
        elif threats:
            kind = "threat_named_only"
        else:
            kind = "unclassified"

        peers = cell.get((d["channel"], d["consequence"]), [])
        out.append({
            "defense": d["name"], "paper_id": d["paper_id"],
            "paper_title": d["title"], "year": d["year"],
            "track": d["track"], "validated_against": d["validated_against"],
            "intervention_point": d["intervention_point"],
            "channel": d["channel"], "consequence": d["consequence"],
            "classification": kind,
            "defends_against": threats,
            "names_registry_attacks": named,
            "names_benchmarks": benches,
            "taxonomy_cell_peers": len(peers),
            "taxonomy_cell_peer_examples": peers[:8],
        })

    counts = collections.Counter(r["classification"] for r in out)
    missed = [r for r in out if r["classification"] == "names_registry_attack"]
    payload = {
        "generated": "2026-09-30",
        "purpose": __doc__.split("\n\n")[0],
        "n_defenses": len(out),
        "classification_counts": dict(counts),
        "n_missed_pair_candidates": sum(len(r["names_registry_attacks"])
                                        for r in missed),
        "caveat": (
            "names_registry_attack is a CANDIDATE list, not coverage. The name "
            "appearing in a defense paper's text does not mean the defense was "
            "run against that attack - it may be related work or motivation. "
            "Each one needs the same adjudication the reverse scan used before "
            "it can become a pair. taxonomy_cell_peers is weaker still: the "
            "same (channel, consequence) cell is not the same threat."),
        "rows": out,
    }
    OUT.write_text(json.dumps(payload, indent=1))

    # Write it back into the database too, so the dashboard can answer
    # "defends what?" without re-reading JSON. build_paper_db.py does not
    # create this table - it is produced here, after the scorecard views
    # exist, so a full rebuild is: build_paper_db.py then this script.
    con.executescript("""
        DROP TABLE IF EXISTS untested_defense;
        CREATE TABLE untested_defense (
            defense TEXT PRIMARY KEY REFERENCES defense(name),
            paper_id TEXT,
            classification TEXT,
            defends_against TEXT,       -- ' | '-joined threat labels
            names_registry_attacks TEXT,-- ' | '-joined candidate attack names
            names_benchmarks TEXT,
            taxonomy_cell_peers INTEGER,
            taxonomy_cell_peer_examples TEXT
        );""")
    con.executemany(
        "INSERT INTO untested_defense VALUES (?,?,?,?,?,?,?,?)",
        [(r["defense"], r["paper_id"], r["classification"],
          " | ".join(r["defends_against"]),
          " | ".join(r["names_registry_attacks"]),
          " | ".join(r["names_benchmarks"]),
          r["taxonomy_cell_peers"],
          " | ".join(r["taxonomy_cell_peer_examples"]))
         for r in out])
    con.commit()

    print(f"wrote {OUT.relative_to(ROOT)} and table `untested_defense` "
          f"({len(out)} defenses)\n")
    for k, v in counts.most_common():
        print(f"  {v:>4}  {k}")
    print(f"\n  {payload['n_missed_pair_candidates']} candidate "
          f"(defense, attack) pairs named in text across "
          f"{len(missed)} defenses")
    top = collections.Counter(t for r in out for t in r["defends_against"])
    print("\n  what they say they defend against:")
    for t, n in top.most_common(12):
        print(f"    {n:>4}  {t}")


if __name__ == "__main__":
    main()
