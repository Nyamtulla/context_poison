"""Regenerate every number in pair_tally.md from the registries.

The point of this script is that the pair counts in the manuscript are
reconciled rather than hand-copied. Three numbers here have been wrong in
drafts at least once (the 332 composite, the defense-universe size, and the
episode count), all because they were transcribed from an earlier run.

Run: python3 scripts/pair_tally.py
"""
import collections
import json
import pathlib
import re

R = pathlib.Path(__file__).resolve().parent.parent / "data" / "registries"


def load(name):
    return json.loads((R / name).read_text())


def composite_pairs():
    """The 332. Four sources, deduplicated on (defense, attack).

    Sources 1/2/4 read defense papers; source 3 reads attack papers and is the
    only direction that can observe a defense losing to an attack published
    after it.
    """
    pairs, provenance = set(), collections.Counter()
    for m in load("rq5_coverage_matrix.json")["matches"]:
        pairs.add((m["defense_name"], m["mechanism_name"]))
        provenance["defense-paper read (RQ5 base)"] += 1
    for p in load("rq5_supplementary_pairs.json")["confirmed_pairs"]:
        pairs.add((p["defense"], p["mechanism"]))
        provenance["citation/full-text recovery"] += 1
    for p in load("benchmark_resolved_pairs.json")["confirmed_pairs"]:
        pairs.add((p["defense"], p["mechanism"]))
        provenance["benchmark-named resolution"] += 1
    for p in load("attack_paper_evaluations.json")["confirmed_pairs"]:
        pairs.add((p["defense"], p["mechanism"]))
        provenance["ATTACK-paper reverse scan (pass 1-2)"] += 1
    for p in load("attack_paper_evaluations_pass3.json")["confirmed_pairs"]:
        pairs.add((p["defense"], p["mechanism"]))
        provenance["ATTACK-paper reverse scan (pass 3)"] += 1
    return pairs, provenance


def attack_universe():
    """237 = 223 registry attacks + 14 that exist only inside a benchmark."""
    reg = load("rq3_pollution_registry.json")
    bench = load("rq3_benchmark_mechanisms.json")["mechanisms"]
    track = {m["name"]: m["regime"] for m in reg}
    for b in bench:
        # benchmark-only entries are all adversarial suites
        track.setdefault(b.get("name") or b.get("technique_name"), "security")
    return track


# --- the retrieval cell -------------------------------------------------
# Resolved by explicit token, longest first, never by fuzzy match: a silent
# mis-parse here would under-count the campaign, which is exactly how the
# "70 combinations" figure in CONTRIBUTOR_BRIEF.md went stale. Anything this
# table cannot classify raises, so a new run must be declared here to be
# counted.
# (token, label, literature-lookup key). Two implementations of RobustRAG are
# distinct runs but one registry entry, so they share a lookup key.
# Studies that are not (defense, attack) runs at all. The regime framing test
# varies the payload's provenance against an undefended model, so it has no
# defense arm to tally. Listing it here keeps the unclassified guard below
# doing its real job, which is catching a genuinely mis-named result file.
NOT_PAIR_RUNS = {"regime_framing_test"}

# the dose grid every native-protocol cell runs
GRID_DOSES = (0, 1, 2, 3, 5, 10)

DEFENSE_TOKENS = [
    ("robustrag_decoding", "RobustRAG-DecodingAgg", "robustrag"),
    ("robustrag", "RobustRAG-KeywordAgg", "robustrag"),
    ("faithfulrag", "FaithfulRAG", "faithfulrag"),
    ("parammute", "ParamMute", "parammute"),
    ("ckplug", "CK-PLUG", "ckplug"),
    ("coiecd", "COIECD", "coiecd"),
    ("dyprag", "DyPRAG", "dyprag"),
    ("spare", "SpARE", "spare"),
    ("shift", "SHIFT", "shift"),
    ("frag", "FaithfulRAG", "faithfulrag"),
    ("acd", "ACD", "adaptivecontrastivedecoding"),
    ("scr", "SCR", "selfguidedconfidencereasoning"),
    ("ck", "CK-PLUG", "ckplug"),
]
# false evidence and distractor evidence are both our instantiations of the
# registry's knowledge-conflict mechanism, so that is the name a literature
# pair would carry for either. They are separate ATTACK labels because they
# are separate payloads with separate results: false evidence plants the
# model's own prior answer, distractor evidence plants a third answer that is
# neither the gold nor the prior, which is what separates copying from
# remembering.
ATTACK_TOKENS = [
    ("badrag_sentiment", "BadRAG sentiment steering", "badrag"),
    ("badrag_dos", "BadRAG denial-of-service", "badrag"),
    ("corpus_poisoning", "corpus poisoning", "corpuspoisoning"),
    ("false_evidence", "false evidence", "knowledgeconflict"),
    ("distractor_evidence", "distractor evidence", "knowledgeconflict"),
    # our adaptive attack on ACD: the distractor payload in whichever form
    # minimises ACD's own ent_pos. Same registry key, because a literature
    # pair would still call it knowledge conflict, but its own label, because
    # it is a different payload with a different result.
    ("adaptive_evidence", "adaptive distractor", "knowledgeconflict"),
    # the gradient version of the same attack: a GCG-optimised suffix appended
    # to the best-of-K passage. Separate label for the same reason.
    ("gradient_evidence", "gradient distractor", "knowledgeconflict"),
    ("poisonedrag", "PoisonedRAG", "poisonedrag"),
]


def _sep(s):
    """Separators are not load-bearing: robustrag-decoding == robustrag_decoding."""
    return re.sub(r"[\s./-]+", "_", (s or "").lower())


def _tight(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())
# model/config variants of the same (defense, attack) pair - counted as runs,
# not as new pairs
VARIANTS = ("crossover", "mistral", "llama", "greedy", "pilot", "dose", "alpha")


def _token(stem, table):
    stem = _sep(stem)
    for tok, label, key in table:
        if tok in stem:
            return label, key
    return None, None


def retrieval_runs():
    """Every scored run in the RAG cell, keyed by (defense, attack).

    A run is a *transfer test* if any row carries a non-zero poison dose
    (`frac` for chunk-replacement dosing, `n_poison` for passage-count
    dosing). Everything else is a control: the defense reproducing its own
    published benefit on clean context, which gates whether a transfer number
    may be reported at all.
    """
    runs, unparsed = [], []
    for path in sorted(R.glob("*.json")):
        try:
            d = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        rows = d.get("results")
        if not (isinstance(rows, list) and rows
                and isinstance(rows[0], dict) and "arm" in rows[0]):
            continue
        stem = path.stem.lower()
        if stem in NOT_PAIR_RUNS:
            continue
        # A registry written incrementally says when it is finished. Files
        # that predate incremental writing carry no flag and were only ever
        # written complete, so absence means complete.
        if d.get("complete") is False:
            continue
        # Cells that began before the flag existed carry no marker, so
        # completeness is inferred from arm symmetry: a runner sweeps every
        # dose for one arm and then the next, so a run caught mid-flight has
        # one arm short. Dose sets differ between campaigns, which is why the
        # test compares the arms against each other rather than against a
        # fixed list.
        if d.get("complete") is None:
            _per_arm = {}
            for r in rows:
                _per_arm.setdefault(r.get("arm"), set()).add(
                    r.get("frac") if r.get("frac") is not None
                    else r.get("n_poison"))
            if len(_per_arm) > 1 and len(set(map(frozenset,
                                                 _per_arm.values()))) > 1:
                continue
        # metadata first where present, then the filename
        defense, dkey = _token(d.get("defense") or "", DEFENSE_TOKENS)
        if defense is None:
            defense, dkey = _token(stem, DEFENSE_TOKENS)
        attack, akey = _token(d.get("attack") or "", ATTACK_TOKENS)
        if attack is None:
            attack, akey = _token(stem, ATTACK_TOKENS)
        if defense is None:
            unparsed.append(path.name)
            continue

        doses = {r.get("frac") if r.get("frac") is not None else r.get("n_poison")
                 for r in rows}
        attacked = any(x not in (None, 0, 0.0) for x in doses)
        variant = next((v for v in VARIANTS if v in stem), "")
        if not attacked:
            role = "control"
        elif variant == "pilot":
            role = "pilot"          # smoke-scale, never a reportable pair
        else:
            role = "transfer"
        if role == "transfer" and attack is None:
            unparsed.append(f"{path.name} (attack token unresolved)")
            continue
        runs.append({
            "file": path.name, "defense": defense,
            "attack": attack if attacked else None,
            "role": role, "variant": variant,
            "dkey": dkey, "akey": akey if attacked else None,
            "rows": len(rows),
            "episodes": sum(r.get("n", 0) for r in rows),
        })
    if unparsed:
        raise SystemExit("pair_tally: unclassified result files, add them to "
                         "DEFENSE_TOKENS / ATTACK_TOKENS:\n  "
                         + "\n  ".join(unparsed))
    return runs


def report_retrieval():
    runs = retrieval_runs()
    transfer = [r for r in runs if r["role"] == "transfer"]
    control = [r for r in runs if r["role"] == "control"]
    pilot = [r for r in runs if r["role"] == "pilot"]
    pairs = {(r["defense"], r["attack"]) for r in transfer}

    print("\n== what we ran ourselves: the RAG cell ==")
    print(f"  {len(pairs)} distinct (defense, attack) pairs over "
          f"{len(transfer)} transfer runs")
    print(f"  {len(control)} control runs, {len(pilot)} pilots, "
          f"{len({r['defense'] for r in runs})} defense implementations")
    print(f"  {sum(r['rows'] for r in runs)} scored arm-conditions, "
          f"{sum(r['episodes'] for r in runs)} episodes")
    by_def = collections.defaultdict(set)
    for d, a in pairs:
        by_def[d].add(a)
    for d in sorted(by_def):
        print(f"    {d:22s} vs {', '.join(sorted(by_def[d]))}")
    return pairs, transfer, control, runs


def main():
    pairs, provenance = composite_pairs()
    track = attack_universe()
    defenses = load("rq4_defense_registry.json")
    per_attack = collections.Counter(a for _, a in pairs)
    per_defense = collections.Counter(d for d, _ in pairs)

    print("== pair provenance ==")
    for k, v in provenance.items():
        print(f"  {v:>4}  {k}")
    print(f"  {sum(provenance.values()):>4}  raw    ->  {len(pairs)} unique")

    print("\n== the two threat models are separate problems ==")
    n_def = collections.Counter(d["validated_against"] for d in defenses)
    for label, va, tr in [("adversarial", "adversarial", "security"),
                          ("incidental", "incidental", "safety")]:
        targets = [n for n, t in track.items() if t == tr]
        covered = sum(1 for n in targets if per_attack.get(n, 0))
        print(f"  {label:12s} {n_def[va]:>4} defenses vs {len(targets):>4} targets "
              f"= {n_def[va]/len(targets):.1f}:1, {covered}/{len(targets)} "
              f"({covered/len(targets):.1%}) covered")
    print(f"  both         {n_def['both']:>4} defenses")

    print("\n== defenses tested against each attack ==")
    buckets = {"0": 0, "1": 0, "2": 0, "3-5": 0, "6-10": 0, "11+": 0}
    for name in track:
        c = per_attack.get(name, 0)
        key = ("0" if c == 0 else "1" if c == 1 else "2" if c == 2
               else "3-5" if c <= 5 else "6-10" if c <= 10 else "11+")
        buckets[key] += 1
    for k, v in buckets.items():
        print(f"  {k:>5}: {v:>4}")
    heavy = sum(v for v in per_attack.values() if v >= 11)
    print(f"  the 11+ attacks absorb {heavy}/{len(pairs)} pairs "
          f"({heavy/len(pairs):.1%})")
    print("  top:", per_attack.most_common(7))

    print("\n== attacks tested against each defense ==")
    universe = {d["name"] for d in defenses} | set(per_defense)
    hist = collections.Counter(per_defense.get(n, 0) for n in universe)
    print(f"  universe {len(universe)} (534 registry + strays)")
    for k in sorted(hist)[:6]:
        print(f"  {k:>5}: {hist[k]:>4}")
    print(f"    4+: {sum(v for k, v in hist.items() if k >= 4):>4}")

    print("\n== who reports what ==")
    outcomes = load("pair_outcomes.json")
    by_src = collections.defaultdict(collections.Counter)
    for o in outcomes:
        by_src[o["reported_by"]][o["reported_verdict"]] += 1
    for src, c in by_src.items():
        print(f"  {src:16s} n={sum(c.values()):>4}  "
              f"wins={c['defense_wins_claimed']:>4}  "
              f"loses={c['defense_loses_reported']:>4}")

    print("\n== what we ran ourselves ==")
    full = load("technique_transfer_full_banking.json")
    scored = [r for r in full["results"] if not r.get("error")]
    episodes = sum(r["undefended"]["n"] + r["defended"]["n"] for r in scored)
    print(f"  {len(scored)} scored conditions, {episodes} episodes, "
          f"{len(full['results']) - len(scored)} harness errors excluded")
    print(" ", collections.Counter(r["verdict"].split("(")[0].strip()
                                   for r in scored))
    zero_cov = sum(1 for r in scored if r.get("is_transfer_test"))
    near = sum(1 for r in scored if r.get("is_near_transfer"))
    print(f"  conditions against a zero-coverage attack: {zero_cov}")
    print(f"  conditions on a pair no paper had run: {near}")
    agent_pairs = {(r["technique_name"], r["attack"]) for r in scored}
    agent_eps = episodes

    rag_pairs, rag_transfer, rag_control, rag_runs = report_retrieval()

    print("\n== campaign total (both cells) ==")
    print(f"  {len(agent_pairs) + len(rag_pairs)} distinct (defense, attack) pairs "
          f"= {len(agent_pairs)} agent + {len(rag_pairs)} RAG")
    print(f"  {len({r['defense'] for r in rag_runs})} RAG defense implementations, "
          f"{len({r['technique_name'] for r in scored})} agent techniques")
    print(f"  {agent_eps + sum(r['episodes'] for r in rag_runs)} episodes "
          f"= {agent_eps} agent + {sum(r['episodes'] for r in rag_runs)} RAG")
    lit = [(_tight(d), _tight(a)) for d, a in pairs]
    keyed = {(r["dkey"], r["akey"]) for r in rag_transfer}
    already, novel = [], []
    for dk, ak in sorted(keyed):
        hit = any(dk in ld and ak in la for ld, la in lit)
        (already if hit else novel).append((dk, ak))
    print(f"  at registry-name level these {len(rag_pairs)} RAG pairs collapse to "
          f"{len(keyed)} (the two RobustRAG implementations share one entry)")
    print(f"  {len(novel)}/{len(keyed)} are absent from the {len(lit)} pairs "
          f"the literature reports")
    if already:
        print("  NOT novel - the literature already reports these:")
        for dk, ak in already:
            print(f"    {dk} x {ak}")

    print("\n== reverse-scan freshness ==")
    p3 = load("attack_paper_evaluations_pass3.json")
    n_reg = len(load("rq3_pollution_registry.json"))
    rej = sum(len(v) for v in p3["rejected"].values())
    print(f"  pass 3 ({p3['generated']}) covered the full registry ({n_reg} + "
          f"benchmark-only)")
    print(f"  {p3['candidates_adjudicated']} adjudicated -> "
          f"{len(p3['confirmed_pairs'])} confirmed, {rej} rejected/pending")


if __name__ == "__main__":
    main()
