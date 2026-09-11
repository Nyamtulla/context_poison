"""What does each defense paper say it was evaluated against - in its own words?

RQ5 established coverage by matching a defense's evaluation target to a named
entry in the RQ3 mechanism registry. 302 of 479 defenses failed that match, and
the obvious reading is that those papers never evaluated against anything
nameable. Reading them shows something different and more useful:

**papers name a BENCHMARK, not a mechanism.** "We evaluate on AgentDojo" is the
normal form; "we evaluate against the important_instructions attack" is rare.
The benchmark is the unit of evaluation in this literature, and a benchmark
bundles many attacks under one name. So the registry match was asking a question
the papers do not answer, and the 302 are mostly not empty - they are
differently-shaped.

This pass records the target as the paper states it, decoupled from the
registry, with a `kind` saying what sort of thing it is. Matching benchmark ->
constituent mechanisms becomes a separate, later problem rather than a silent
failure inside the coverage number.

Two mistakes from the first version of this script, both caught by spot-checking
and both worth keeping in mind when reading the output:

  * a FIXED benchmark vocabulary is track-biased. The first list was built from
    Security-track papers and silently missed the entire ML/AI benchmark
    ecosystem - LOCOMO, LongMemEval, MemoryArena, KernelBench, NaVQA, LLM-SR -
    which dumped ~130 defenses into "unclear" that in fact name a benchmark
    plainly. Names are now extracted by SHAPE (CamelCase / ALLCAPS / "the X
    benchmark") and the curated list only supplies aliases, so a benchmark
    nobody thought to list still gets found.
  * "no defense baseline" is NOT "no evaluation". A paper can compare only
    against its own ablations while still evaluating on a real external
    dataset. Those are now separate fields (`has_defense_baseline`,
    `eval_target_kind`); conflating them mislabelled papers that had a
    perfectly good benchmark.

    python scripts/extract_eval_targets.py
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
OUT = REPO / "data/registries/defense_eval_targets.json"

# Named evaluation benchmarks. Each bundles attacks under one name, which is
# why matching a defense to a *mechanism* usually fails: the paper never names
# the constituent attack.
BENCHMARKS = [
    "AgentDojo", "InjecAgent", "InjectAgent", "BIPIA", "ASB", "Agent Security Bench",
    "AdvBench", "TensorTrust", "MobileSafetyBench", "AgentHarm", "Agent-SafetyBench",
    "LLMail-Inject", "NotInject", "deepset/prompt-injections", "SIREN", "TaintBench",
    "WildChat", "SQuAD", "HotpotQA", "NaturalQuestions", "TriviaQA", "WebQuestions",
    "ConflictQA", "ConFiQA", "MQuAKE", "GSM8K", "HumanEval", "MBPP", "ViQuAE",
    "AgentDyn", "AgentBench", "WebArena", "ToolBench", "MetaTool", "SafeAgentBench",
    "PoisonedRAG", "MS-MARCO", "NQ", "Natural Questions", "RGB", "CRAG",
]
# Attack families named generically rather than as a specific technique.
FAMILIES = [
    "indirect prompt injection", "direct prompt injection", "prompt injection",
    "goal hijacking", "tool misuse", "chained attacks", "jailbreak",
    "knowledge conflict", "context-memory conflict", "cross-modality",
    "data exfiltration", "data stealing", "direct harm", "memory poisoning",
    "knowledge poisoning", "backdoor", "skill poisoning", "tool poisoning",
    "denial of service", "context distraction", "lost in the middle",
    "counterfactual", "misinformation", "hallucination",
]
# Phrases that mark the paper as having run nothing external.
NO_EXTERNAL = re.compile(
    r"no (?:implemented |empirical |head-to-head |external )*(?:head-to-head |empirical )?"
    r"(?:baseline|comparison)|comparison is (?:analytical|argumentative|conceptual|qualitative)|"
    r"(?:internal ablation|internal comparison) rather than|no competing|"
    r"not (?:re-)?implemented|no datasets or benchmarks are used|"
    r"rather than (?:against )?(?:external|third-party)", re.I)
SELF_BUILT = re.compile(
    r"self-constructed|purpose-built|self-built|the authors(?:'|') own|authors construct|"
    r"we construct|own (?:new )?benchmark|novel benchmark|introduces? [A-Z]|"
    r"no (?:pre-existing |public )?benchmark is used|custom (?:pool|evaluation|dataset)", re.I)


# A benchmark or dataset name, by shape rather than by list: CamelCase
# (LongMemEval), ALLCAPS runs (LOCOMO, NQ), or hyphen/digit forms (GSM8K,
# Agent-SafetyBench). Ordinary sentence-initial capitals are excluded by
# requiring either an internal capital, a digit, or a benchmark-ish cue word.
NAME_SHAPE = re.compile(r"\b([A-Z][A-Za-z]*(?:[A-Z][A-Za-z0-9]*)+[A-Za-z0-9]*"
                        r"|[A-Z]{2,}(?:-[A-Za-z0-9]+)*"
                        r"|[A-Z][A-Za-z]+(?:-[A-Z][A-Za-z0-9]+)+"
                        r"|[A-Z][A-Za-z]+\d[A-Za-z0-9]*)\b")
CUE = re.compile(r"\b(benchmark|dataset|suite|corpus|testbed|task set)\b", re.I)
# Capitalised tokens that are never benchmark names in this corpus.
NOT_A_BENCHMARK = {
    "LLM", "LLMs", "GPT", "API", "APIs", "AI", "ASR", "FPR", "TPR", "FNR", "EM", "F1",
    "RAG", "IPI", "PI", "CoT", "QA", "MCP", "OWASP", "MIT", "CPU", "GPU", "JSON",
    "HTML", "DOM", "URL", "PII", "SOTA", "NLP", "RL", "RLHF", "LoRA", "SFT", "DPO",
    "OpenAI", "Anthropic", "Google", "Meta", "Qwen", "Llama", "LLaMA", "Mistral",
    "Claude", "Gemini", "DeepSeek", "GPT-4o", "GPT-4", "Phi", "Grok", "Pixtral",
    "TODO", "NOTE", "Table", "Figure", "Section", "Appendix", "No", "The", "This",
    "None", "Both", "Three", "Two", "Four", "Five", "Six", "Seven", "Ten",
    # metrics, not benchmarks
    "BLEU", "ROUGE", "METEOR", "BERTScore", "NDCG", "MRR", "AUC", "AUROC", "AUPRC",
    "MSE", "NMSE", "RMSE", "MAE", "Acc", "ACC", "SR", "UA", "TSR", "DSR", "FP", "FN",
    "TP", "TN", "PPL", "MAP", "Recall", "Precision",
    # numeric formats and hardware
    "FP32", "FP16", "FP8", "INT8", "INT4", "BF16", "H100", "A100", "A6000", "H800", "V100",
    # task-category labels that appear beside a benchmark but are not one
    "Multi-Hop", "Single-Hop", "Multi-Session", "Single-Session", "Open-Domain",
    "Cross-Domain", "Cross-Task", "Cross-Website", "Cross-Lingual", "Single-Assistant",
    "Single-Preference", "Single-User", "Temporal-Reasoning", "Knowledge-Update",
    "Direct-Harm", "Data-Steal", "In-Domain", "Out-of-Domain", "Zero-Shot", "Few-Shot",
    "Multi-Turn", "Single-Turn", "Long-Context", "Short-Form", "Long-Form",
}


def find_named(*texts: str, exclude: set[str] | None = None) -> list[str]:
    """Benchmark/dataset names by shape, from the datasets field primarily.

    `exclude` carries the defense's own name: a paper naming its own system in
    the datasets sentence ("MetaMem is evaluated on LongMemEval") would
    otherwise be recorded as having evaluated against itself.
    """
    ex = {e.lower() for e in (exclude or set())}
    out = set()
    for t in texts:
        if not t:
            continue
        for sent in re.split(r"(?<=[.;])\s+", t):
            cued = bool(CUE.search(sent))
            for m in NAME_SHAPE.finditer(sent):
                tok = m.group(1)
                if tok in NOT_A_BENCHMARK or len(tok) < 3:
                    continue
                # A shaped token in a sentence that mentions a benchmark/dataset
                # is taken as one; elsewhere require a strong shape (internal
                # capital or digit) to avoid picking up ordinary proper nouns.
                if tok.lower() in ex:
                    continue
                if cued or re.search(r"[a-z][A-Z]|\d", tok):
                    out.add(tok)
    return sorted(out)


def find_all(vocab: list[str], *texts: str) -> list[str]:
    blob = " \n ".join(t or "" for t in texts)
    hits = []
    for term in vocab:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", blob, re.I):
            hits.append(term)
    # drop a term fully contained in a longer hit ("NQ" inside "Natural Questions")
    return sorted({h for h in hits if not any(h != o and h.lower() in o.lower() for o in hits)})


def classify(named: list[str], fams: list[str], bc: str, ds: str) -> str:
    """What sort of thing the paper evaluated against.

    Note the ordering: an own-built benchmark still counts as a named target
    (the paper gives it a name and others can cite it), so `own_construction`
    is only reached when nothing nameable was found at all.
    """
    if not ds and not bc:
        return "nothing_extracted"
    if named:
        return "named_benchmark_or_dataset"
    if SELF_BUILT.search(bc + " " + ds):
        return "own_construction_unnamed"
    if fams:
        return "generic_family_only"
    if ds:
        return "dataset_described_not_named"
    return "no_external_evaluation"


def main() -> None:
    reg = registry_source.load_all()
    papers = {p["paper_id"]: p for p in registry_source.load_papers()}
    rows = []
    for d in reg["defenses"]:
        p = papers.get(d["source_paper_id"]) or {}
        bc = (p.get("baselines_compared") or "").strip()
        ds = (p.get("datasets_benchmarks") or "").strip()
        tm = (p.get("threat_model") or "").strip()
        # Names come primarily from the datasets field - that is where the
        # evaluation target lives. baselines_compared is mostly about competing
        # DEFENSES, which is a different question and tracked separately.
        own = {d["defense_name"], re.sub(r"\s*\(.*", "", d["defense_name"]).strip()}
        named = sorted(set(find_named(ds, exclude=own)) | set(find_all(BENCHMARKS, ds, bc)))
        fams = find_all(FAMILIES, ds, bc, tm)
        has_def_baseline = bool(bc) and not NO_EXTERNAL.search(bc)
        rows.append({
            "row": d["_row"], "defense_name": d["defense_name"], "track": d["track"],
            "stage": (d["intervention_point"] or "none"),
            "registry_matched": d["n_mechanisms_tested"] > 0,
            "mechanisms_matched": d["mechanisms_tested"],
            "eval_targets_named": named,
            "eval_families": fams,
            "has_defense_baseline": has_def_baseline,
            "eval_target_kind": classify(named, fams, bc, ds),
            "source_paper_title": d["source_paper_title"],
        })
    OUT.write_text(json.dumps(rows, indent=1) + "\n")

    print(f"defenses: {len(rows)}\n")
    print("=== what each paper names as its evaluation target ===")
    for k, v in Counter(r["eval_target_kind"] for r in rows).most_common():
        print(f"  {v:4d}  {k}")
    print()
    unmatched = [r for r in rows if not r["registry_matched"]]
    print(f"=== of the {len(unmatched)} with NO registry match ===")
    for k, v in Counter(r["eval_target_kind"] for r in unmatched).most_common():
        print(f"  {v:4d}  {k}")
    recovered = [r for r in unmatched if r["eval_target_kind"] in
                 ("named_benchmark_or_dataset", "generic_family_only",
                  "own_construction_unnamed", "dataset_described_not_named")]
    print(f"\n  -> now have a NAMED target (recovered): {len(recovered)}")
    print(f"  -> genuinely nothing external:            "
          f"{sum(1 for r in unmatched if r['eval_target_kind'] in ('no_external_evaluation','nothing_extracted'))}")
    print(f"\n=== defense baselines (a separate question) ===")
    print(f"  compared against >=1 competing defense: {sum(1 for r in rows if r['has_defense_baseline'])}")
    print(f"  ablations / argument only:              {sum(1 for r in rows if not r['has_defense_baseline'])}")
    print("\n=== most-used evaluation targets across all 479 ===")
    for k, v in Counter(b for r in rows for b in r["eval_targets_named"]).most_common(15):
        print(f"  {v:4d}  {k}")
    print("\nwrote", OUT)


if __name__ == "__main__":
    main()
