"""
Context Integrity SoK — MCP server.

Exposes the distilled output of a ~1000-paper systematic review (LLM agent
context poisoning: adversarial attacks vs. incidental degradation) as
queryable tools: papers, named pollution mechanisms (RQ3), confirmed
defenses (RQ4), the defense x mechanism coverage matrix (RQ5), and
plain-language headline findings per research question (RQ1-RQ6).

All data is read from files already committed in this repo (data/exports/,
data/registries/, and the rq*.md writeups) — nothing is fetched over the
network and no API key is required to run this server.
"""
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# The joins that turn the three registry JSONs into "a mechanism, with the
# defenses tested against it" live in src/registry_source.py, shared with
# dashboard.py, so the two views of this data can't drift apart.
from src import registry_source  # noqa: E402

# ================================================================ DATA LOADING

PAPERS = registry_source.load_papers()
PAPERS_BY_ID = {p["paper_id"]: p for p in PAPERS}

_REG = registry_source.load_all()
MECHANISMS = _REG["mechanisms"]
DEFENSES = _REG["defenses"]
PAIRS = _REG["pairs"]
STATS = _REG["stats"]
UNCOVERED_NAMES = set(_REG["uncovered_mechanism_names"])
MECHS_BY_NAME = {m["mechanism_name"]: m for m in MECHANISMS}
DEFS_BY_NAME = {d["defense_name"]: d for d in DEFENSES}
RQ_FILES = registry_source.RQ_FILES


def _match(text, needle):
    return needle.lower() in (text or "").lower()


def _paper_summary(p):
    return {
        "paper_id": p.get("paper_id"),
        "title": p.get("title"),
        "year": p.get("year"),
        "venue": p.get("venue"),
        "track": p.get("track"),
        "channel": p.get("channel"),
        "consequence": p.get("consequence"),
        "defense_intervention_point": p.get("defense_intervention_point"),
        "citation_count": p.get("citation_count"),
    }


# ================================================================ SERVER

mcp = MCPServer("context-integrity-sok")


@mcp.tool()
def get_stats() -> dict:
    """Headline counts for the whole Context Integrity SoK corpus: how many
    papers, named pollution mechanisms, confirmed defenses, and confirmed
    (defense, mechanism) tested pairs. Good first call to orient yourself."""
    return {
        "papers_in_corpus": len(PAPERS),
        "named_mechanisms_rq3": STATS["n_mechanisms"],
        "confirmed_defenses_rq4": STATS["n_defenses"],
        "confirmed_defense_mechanism_pairs_rq5": STATS["n_pairs"],
        "defenses_with_confirmed_mechanism_match": STATS["n_defenses_matched"],
        "defenses_with_confirmed_mechanism_match_pct": round(100 * STATS["n_defenses_matched"] / STATS["n_defenses_total"], 1),
        "mechanisms_with_at_least_one_defense": STATS["n_mechs_covered"],
        "mechanisms_with_zero_defenses": STATS["n_mechs_uncovered"],
        "mechanisms_with_zero_defenses_pct": round(100 * STATS["n_mechs_uncovered"] / STATS["n_mechanisms"], 1),
        "cross_track_pairs": sum(1 for p in PAIRS if p["cross_track"]),
    }


@mcp.tool()
def list_papers(query: str = "", track: str = "", channel: str = "", consequence: str = "",
                defense_intervention_point: str = "", limit: int = 25) -> list[dict]:
    """Search the full 1008-paper corpus. `query` substring-matches title,
    key_result, and technical_summary (case-insensitive). `track` is
    'Security', 'ML/AI', or 'Both'. Returns compact summaries — use
    get_paper(paper_id) for the full extracted record (key_result,
    baselines_compared, technical_summary, etc)."""
    out = []
    for p in PAPERS:
        if track and str(p.get("track", "")).strip().lower() != track.strip().lower():
            continue
        if channel and str(p.get("channel", "")).strip().lower() != channel.strip().lower():
            continue
        if consequence and str(p.get("consequence", "")).strip().lower() != consequence.strip().lower():
            continue
        if defense_intervention_point and str(p.get("defense_intervention_point", "")).strip().lower() != defense_intervention_point.strip().lower():
            continue
        if query and not any(_match(p.get(f), query) for f in ("title", "key_result", "technical_summary")):
            continue
        out.append(_paper_summary(p))
        if len(out) >= limit:
            break
    return out


@mcp.tool()
def get_paper(paper_id: str) -> dict:
    """Full extracted record for one paper by paper_id (from list_papers or
    list_mechanisms/list_defenses' source_paper_id field) — includes
    abstract, key_result, baselines_compared, technical_summary,
    stated_limitations, models_evaluated, datasets_benchmarks, etc."""
    p = PAPERS_BY_ID.get(paper_id)
    if not p:
        return {"error": f"no paper with paper_id={paper_id!r}"}
    return dict(p)


@mcp.tool()
def list_mechanisms(query: str = "", track: str = "", channel: str = "", consequence: str = "",
                     covered_only: bool | None = None, limit: int = 50) -> list[dict]:
    """List named pollution/attack mechanisms from the RQ3 registry (183
    total: both deliberate attack techniques and incidental degradation
    mechanisms). Set covered_only=True for mechanisms with >=1 confirmed
    defense tested against them, or False for those with zero coverage."""
    out = []
    for m in MECHANISMS:
        if track and str(m.get("track", "")).strip().lower() != track.strip().lower():
            continue
        if channel and str(m.get("channel", "")).strip().lower() != channel.strip().lower():
            continue
        if consequence and str(m.get("consequence", "")).strip().lower() != consequence.strip().lower():
            continue
        if covered_only is not None and m["has_any_defense"] != covered_only:
            continue
        if query and not any(_match(m.get(f), query) for f in ("mechanism_name", "notes")):
            continue
        out.append({
            "mechanism_name": m["mechanism_name"],
            "track": m.get("track"),
            "channel": m.get("channel"),
            "consequence": m.get("consequence"),
            "n_defenses_tested_against": m["n_defenses_tested"],
            "source_paper_id": m.get("source_paper_id"),
            "source_paper_title": m.get("source_paper_title"),
            "notes": m.get("notes"),
        })
        if len(out) >= limit:
            break
    return out


@mcp.tool()
def list_defenses(query: str = "", track: str = "", channel: str = "", consequence: str = "",
                   defense_intervention_point: str = "", validated_against: str = "",
                   has_mechanism_match: bool | None = None, limit: int = 50) -> list[dict]:
    """List confirmed defenses from the RQ4 registry (479 total).
    `defense_intervention_point` is 'ingestion', 'reasoning', or 'execution'.
    `validated_against` is 'adversarial' or 'incidental' (the threat model
    the defense's own paper tested it against). has_mechanism_match=False
    lists the 309 defenses NOT confirmed tested against any RQ3-named
    mechanism (see get_stats / RQ5 for why that isn't the same as "untested")."""
    out = []
    for d in DEFENSES:
        if track and str(d.get("track", "")).strip().lower() != track.strip().lower():
            continue
        if channel and str(d.get("channel", "")).strip().lower() != channel.strip().lower():
            continue
        if consequence and str(d.get("consequence", "")).strip().lower() != consequence.strip().lower():
            continue
        if defense_intervention_point and str(d.get("intervention_point", "")).strip().lower() != defense_intervention_point.strip().lower():
            continue
        if validated_against and str(d.get("validated_against", "")).strip().lower() != validated_against.strip().lower():
            continue
        if has_mechanism_match is not None and d["has_confirmed_match"] != has_mechanism_match:
            continue
        if query and not any(_match(d.get(f), query) for f in ("defense_name", "notes")):
            continue
        out.append({
            "defense_name": d.get("defense_name"),
            "track": d.get("track"),
            "channel": d.get("channel"),
            "consequence": d.get("consequence"),
            "defense_intervention_point": d.get("intervention_point"),
            "validated_against": d.get("validated_against"),
            "n_mechanisms_tested_against": d["n_mechanisms_tested"],
            "mechanisms_tested_against": d["mechanisms_tested"],
            "source_paper_id": d.get("source_paper_id"),
            "source_paper_title": d.get("source_paper_title"),
            "notes": d.get("notes"),
        })
        if len(out) >= limit:
            break
    return out


@mcp.tool()
def get_coverage_for_mechanism(mechanism_name: str) -> dict:
    """All confirmed defenses tested against one named mechanism (exact
    name, as returned by list_mechanisms), with the extracting agent's
    justification text for each match."""
    if mechanism_name not in MECHS_BY_NAME:
        return {"error": f"no mechanism named {mechanism_name!r} — call list_mechanisms(query=...) to find the exact name"}
    defenders = [
        {
            "defense_name": p["defense_name"],
            "defense_intervention_point": p.get("defense_intervention_point"),
            "validated_against": p.get("defense_validated_against"),
            "cross_track": p["cross_track"],
            "justification": p.get("justification", ""),
        }
        for p in PAIRS if p["mechanism_name"] == mechanism_name
    ]
    return {"mechanism_name": mechanism_name, "n_defenses": len(defenders), "defenses": defenders}


@mcp.tool()
def get_coverage_for_defense(defense_name: str) -> dict:
    """All mechanisms one named defense (exact name, as returned by
    list_defenses) was confirmed tested against, with justification text."""
    if defense_name not in DEFS_BY_NAME:
        return {"error": f"no defense named {defense_name!r} — call list_defenses(query=...) to find the exact name"}
    tested = [
        {
            "mechanism_name": p["mechanism_name"],
            "mechanism_track": p.get("mechanism_track"),
            "cross_track": p["cross_track"],
            "justification": p.get("justification", ""),
        }
        for p in PAIRS if p["defense_name"] == defense_name
    ]
    return {"defense_name": defense_name, "n_mechanisms": len(tested), "mechanisms": tested}


@mcp.tool()
def list_uncovered_mechanisms(track: str = "", channel: str = "", limit: int = 200) -> list[dict]:
    """The named mechanisms with ZERO confirmed defenses tested against
    them — a direct 'what's left to defend' list, useful for scoping new
    defense work or a related-work gap statement."""
    out = []
    for nm in sorted(UNCOVERED_NAMES):
        m = MECHS_BY_NAME.get(nm, {})
        if track and str(m.get("track", "")).strip().lower() != track.strip().lower():
            continue
        if channel and str(m.get("channel", "")).strip().lower() != channel.strip().lower():
            continue
        out.append({
            "mechanism_name": nm,
            "track": m.get("track"),
            "channel": m.get("channel"),
            "consequence": m.get("consequence"),
            "source_paper_title": m.get("source_paper_title"),
        })
        if len(out) >= limit:
            break
    return out


@mcp.tool()
def get_rq_summary(rq: str) -> str:
    """Plain-language headline finding for one research question. `rq` is
    one of RQ1 (taxonomy), RQ2 (citation network), RQ3 (pollution census),
    RQ4 (defense census), RQ5 (coverage matrix), RQ6 (defense
    generalization case studies), RQ7 (ranked open problems)."""
    text = registry_source.load_rq_summary(rq)
    if not text:
        return f"Unknown or missing RQ: {rq!r}. Valid values: {', '.join(RQ_FILES)}"
    return text


if __name__ == "__main__":
    mcp.run()
