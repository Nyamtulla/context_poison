"""Quantify benchmark standardization across the RQ3 mechanism registry.

The census (data/registries/raw/benchmark_census_out*.jsonl) records, for every
named attack mechanism, what its source paper evaluated on and whether another
researcher could reuse that setup to produce a comparable number.

This turns those per-paper judgments into the claim the SoK needs: how much of
this field's evaluation happens on ground anyone else can stand on.

    python3 scripts/analyze_benchmark_census.py
"""
from __future__ import annotations
import collections, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data/registries/raw"


def norm_benchmark(s: str) -> str:
    """Collapse surface variants so counts are not split across spellings."""
    t = re.sub(r"\s+", " ", (s or "").strip())
    t = re.sub(r"^(the|a|an)\s+", "", t, flags=re.I)
    # Strip a trailing parenthetical gloss: "ASB (Agent Security Bench)" and
    # "ASB" are the same benchmark and must not be counted as two. Keep the
    # parenthetical only when it IS the name, e.g. "Agent Security Bench (ASB)"
    # -> prefer the acronym so both spellings collapse together.
    m = re.match(r"^(.*?)\s*\(([^)]{2,40})\)\s*$", t)
    if m:
        outer, inner = m.group(1).strip(), m.group(2).strip()
        t = inner if (inner.isupper() and len(inner) <= 12) else outer
    # Only strip a trailing descriptor when it is a separate word -- without the
    # space requirement this turns "NFCorpus" into "NF".
    stripped = re.sub(r"\s+(benchmark|dataset|corpus|suite)$", "", t, flags=re.I).strip()
    if len(stripped) >= 3:
        t = stripped
    key = t.lower()
    ALIASES = {
        "ms marco": "MS-MARCO", "ms-marco": "MS-MARCO",
        "natural questions": "Natural Questions", "nq": "Natural Questions",
        "hotpotqa": "HotpotQA", "hotpot qa": "HotpotQA",
        "agentdojo": "AgentDojo", "agent dojo": "AgentDojo",
        "injecagent": "InjecAgent", "injectagent": "InjecAgent",
        "agent security bench": "ASB", "asb": "ASB",
        "agent security bench (asb)": "ASB",
        "open-prompt-injection": "Open-Prompt-Injection",
        "openpromptinjection": "Open-Prompt-Injection",
        "tensortrust": "Tensor Trust", "tensor trust": "Tensor Trust",
        "advbench": "AdvBench", "harmbench": "HarmBench",
        "bipia": "BIPIA", "cyberseceval": "CyberSecEval",
        "longbench": "LongBench", "triviaqa": "TriviaQA",
    }
    return ALIASES.get(key, t)


def main() -> None:
    rows, seen = [], set()
    for fp in sorted(RAW.glob("benchmark_census_out*.jsonl")):
        for line in fp.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("row") in seen:
                continue
            seen.add(r.get("row"))
            rows.append(r)

    n = len(rows)
    if not n:
        print("no census rows found"); return
    print("=" * 72)
    print(f"EVALUATION-BENCHMARK CENSUS  —  {n} named attack mechanisms")
    print("=" * 72)

    prim = collections.Counter(r.get("benchmark_primary") for r in rows)
    print("\nWhat each paper evaluated on (primary):")
    for k, v in prim.most_common():
        print(f"   {v:>4}  {100*v/n:>5.1f}%  {k}")

    reuse = collections.Counter(str(r.get("reusable_benchmark")).lower() for r in rows)
    print("\nCould another researcher reuse that setup for a comparable number?")
    for k in ("yes", "partial", "no", "none", "unclear"):
        if reuse.get(k):
            print(f"   {reuse[k]:>4}  {100*reuse[k]/n:>5.1f}%  {k}")
    not_reusable = reuse.get("no", 0)
    print(f"\n   NOT reusable: {not_reusable}/{n} = {100*not_reusable/n:.1f}%")
    print(f"   reusable or partially so: {n-not_reusable}/{n} = {100*(n-not_reusable)/n:.1f}%")

    # --- the concentration question: how many distinct benchmarks, how shared?
    named = collections.Counter()
    for r in rows:
        for s in (r.get("named_benchmarks") or []):
            ns = norm_benchmark(s)
            if ns:
                named[ns] += 1
    print(f"\nDistinct named benchmarks across the whole registry: {len(named)}")
    print("Most-reused:")
    for k, v in named.most_common(15):
        print(f"   {v:>4}  {k}")
    singles = sum(1 for v in named.values() if v == 1)
    print(f"\n   benchmarks used by exactly ONE paper: {singles}/{len(named)} "
          f"= {100*singles/len(named):.1f}%")
    top = named.most_common(1)
    if top:
        print(f"   most-shared benchmark ({top[0][0]}) appears in {top[0][1]}/{n} "
              f"= {100*top[0][1]/n:.1f}% of mechanisms")

    # --- by track and by year
    # Agents were not asked to echo `track`, so join it back from the registry
    # rather than silently reporting nothing.
    reg = json.loads((REPO / "data/registries/rq3_pollution_registry.json").read_text())
    track_of = {int(m["row"]): m.get("track") for m in reg}
    year_of = {}
    try:
        import openpyxl
        wb = openpyxl.load_workbook(REPO / "data/exports/paper_dashboard_source.xlsx", read_only=True)
        ws = wb["Papers"]; hdr = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        yi = hdr.index("year")
        for i, rr in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            year_of[i] = rr[yi]
        wb.close()
    except Exception:
        pass
    for r in rows:
        r.setdefault("track", track_of.get(r.get("row")))
        r.setdefault("year", year_of.get(r.get("row")))

    print("\nBy track:")
    for tr in sorted({r.get("track") for r in rows if r.get("track")}):
        sub = [r for r in rows if r.get("track") == tr]
        no_ = sum(1 for r in sub if str(r.get("reusable_benchmark")).lower() == "no")
        print(f"   {tr:<10} n={len(sub):>3}   not reusable {no_:>3} = {100*no_/len(sub):.1f}%")

    print("\nBy year (is benchmark sharing improving?):")
    by_year = collections.defaultdict(list)
    for r in rows:
        if r.get("year"):
            by_year[r["year"]].append(r)
    for y in sorted(by_year):
        sub = by_year[y]
        if len(sub) < 5:
            continue
        no_ = sum(1 for r in sub if str(r.get("reusable_benchmark")).lower() == "no")
        shared = sum(1 for r in sub if r.get("benchmark_primary") == "shared_security_benchmark")
        print(f"   {y}  n={len(sub):>3}   not reusable {100*no_/len(sub):>5.1f}%"
              f"   on a shared security benchmark {100*shared/len(sub):>5.1f}%")

    conf = collections.Counter(r.get("confidence") for r in rows)
    print(f"\nConfidence: " + "  ".join(f"{k}={v}" for k, v in conf.most_common()))

    out = REPO / "data/registries/benchmark_census.json"
    out.write_text(json.dumps({
        "generated": "2026-09-23",
        "n_mechanisms": n,
        "benchmark_primary": dict(prim),
        "reusable_benchmark": dict(reuse),
        "not_reusable_pct": round(100 * not_reusable / n, 1),
        "distinct_named_benchmarks": len(named),
        "benchmarks_used_once": singles,
        "named_benchmark_counts": dict(named.most_common()),
        "rows": rows,
    }, indent=1) + "\n")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
