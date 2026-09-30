"""Build data/paper_explorer.db - one queryable database of the whole SoK.

One row per paper, with its role (attack paper / defense paper / both / neither),
the techniques it introduced, and a scorecard of how those techniques fared
against the other side.

Three things this schema is careful about, because all three have caused wrong
claims in this project already:

1. **A pair is a claim, not a fact.** Every pair records WHO reported it.
   Defense papers report their own defense winning 193 times and losing 0
   times; attack papers report those same kinds of defense losing 40 times.
   So the scorecard never has a bare "wins" column - it has
   `self_reported_win` and `refuted_by_attack_paper`, which are different
   kinds of evidence and must not be summed.

2. **"Tested" is not "worked".** 58 benchmark-resolved pairs and 13 others
   record only that the run happened, with no directional result. Those land
   in `undetermined`, never in a win or loss column.

3. **Literature pairs and our own runs are separate tables.** `pair` is what
   papers reported. `our_run` is what we executed. They are never unioned.

Run: python3 scripts/build_paper_db.py
"""
from __future__ import annotations

import json
import pathlib
import sqlite3

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG = ROOT / "data" / "registries"
OUT = ROOT / "data" / "paper_explorer.db"
XLSX = ROOT / "data" / "exports" / "paper_dashboard_source.xlsx"

# Raw outcome strings -> the four classes the scorecards count.
# "partial" exists because collapsing "reduces ASR from 20.7% to 13.2%" into
# either win or loss would be a lie in one direction or the other.
HOLDS = {"defense_wins_claimed"}
LOSES = {
    "defense_loses_reported", "defense fails", "defense broken",
    "defense largely fails", "defense exploited", "defense assumption broken",
    "defense evaded after adaptation",
}
PARTIAL = {
    "defense insufficient", "defense degraded under adaptation",
    "defense partially effective",
}
UNDETERMINED = {
    "evaluated", "evaluated (transfer test)", "evaluated_no_directional_verdict",
    "no_reported_result_found", "",
}


def classify(raw: str) -> str:
    raw = (raw or "").strip()
    if raw in HOLDS:
        return "holds"
    if raw in LOSES:
        return "loses"
    if raw in PARTIAL:
        return "partial"
    if raw in UNDETERMINED:
        return "undetermined"
    raise ValueError(f"unmapped outcome {raw!r} - add it to the tables above "
                     "rather than letting it fall through to undetermined")


def load(name):
    return json.loads((REG / name).read_text())


SCHEMA = """
DROP VIEW IF EXISTS v_defense_scorecard;
DROP VIEW IF EXISTS v_attack_scorecard;
DROP VIEW IF EXISTS v_paper_card;
DROP TABLE IF EXISTS pair;
DROP TABLE IF EXISTS our_run;
DROP TABLE IF EXISTS attack;
DROP TABLE IF EXISTS defense;
DROP TABLE IF EXISTS paper;

CREATE TABLE paper (
    paper_id TEXT PRIMARY KEY,
    title TEXT, authors TEXT, year INTEGER, venue TEXT,
    track TEXT,              -- Security | ML/AI | Both
    screening TEXT,          -- Include | Exclude
    role TEXT,               -- attack | defense | both | neither
    citation_count INTEGER, doi TEXT, arxiv_id TEXT, url TEXT,
    pdf_local_path TEXT, discovered_via TEXT, hop INTEGER,
    channel TEXT, consequence TEXT, defense_intervention_point TEXT,
    temporal_persistence TEXT, cites_track_a TEXT, cites_track_b TEXT,
    evidence_grade TEXT,     -- publication rigor, NOT evaluation quality
    artifacts_released TEXT, models_evaluated TEXT, datasets_benchmarks TEXT,
    key_result TEXT, baselines_compared TEXT, threat_model TEXT,
    stated_limitations TEXT, technical_summary TEXT, abstract TEXT
);

CREATE TABLE attack (
    name TEXT PRIMARY KEY,
    paper_id TEXT REFERENCES paper(paper_id),
    channel TEXT, consequence TEXT, track TEXT,
    is_extension_of TEXT, confidence TEXT, notes TEXT,
    benchmark_only INTEGER   -- 1 = exists only inside a benchmark suite
);

CREATE TABLE defense (
    name TEXT PRIMARY KEY,
    paper_id TEXT REFERENCES paper(paper_id),
    channel TEXT, consequence TEXT, intervention_point TEXT, track TEXT,
    validated_against TEXT,  -- adversarial | incidental | both
    is_extension_of TEXT, confidence TEXT, notes TEXT
);

CREATE TABLE pair (
    id INTEGER PRIMARY KEY,
    defense_name TEXT, attack_name TEXT,
    direction TEXT,          -- defense_paper | attack_paper
    reported_by_paper_id TEXT,
    reported_by_title TEXT,
    outcome_raw TEXT,
    outcome TEXT,            -- holds | loses | partial | undetermined
    source TEXT,             -- which recovery pass found it
    evidence TEXT
);

CREATE TABLE our_run (
    id INTEGER PRIMARY KEY,
    technique TEXT, technique_name TEXT, intervention_point TEXT,
    attack TEXT, suite TEXT, model TEXT,
    n INTEGER,
    undefended_asr REAL, defended_asr REAL,
    undefended_utility REAL, defended_utility REAL,
    drop_pp REAL, mdr_pp REAL,
    verdict TEXT
);

CREATE INDEX idx_pair_def ON pair(defense_name);
CREATE INDEX idx_pair_atk ON pair(attack_name);
CREATE INDEX idx_attack_paper ON attack(paper_id);
CREATE INDEX idx_defense_paper ON defense(paper_id);
"""

VIEWS = """
-- Per defense: how many attacks it has faced, and who said what about it.
-- self_reported_win and refuted_by_attack_paper are deliberately separate
-- columns; adding them together would merge two incompatible kinds of claim.
CREATE VIEW v_defense_scorecard AS
SELECT d.name AS defense,
       d.paper_id,
       d.intervention_point,
       d.validated_against,
       COUNT(p.id)                                            AS attacks_tested,
       SUM(p.outcome = 'holds'     AND p.direction = 'defense_paper') AS self_reported_win,
       SUM(p.outcome = 'loses')                               AS refuted,
       SUM(p.outcome = 'partial')                             AS partial,
       SUM(p.outcome = 'undetermined')                        AS undetermined,
       SUM(p.direction = 'attack_paper')                      AS tested_by_attack_paper
FROM defense d LEFT JOIN pair p ON p.defense_name = d.name
GROUP BY d.name;

-- Per attack: how many defenses have been run against it, and how they fared.
-- "broke" counts defenses this attack defeated; "held" counts defenses whose
-- own paper claimed a win against it - again, not the same evidence.
CREATE VIEW v_attack_scorecard AS
SELECT a.name AS attack,
       a.paper_id,
       a.channel,
       a.consequence,
       COUNT(p.id)                        AS defenses_tested,
       SUM(p.outcome = 'loses')           AS defenses_broken,
       SUM(p.outcome = 'partial')         AS defenses_partial,
       SUM(p.outcome = 'holds')           AS defenses_held_claimed,
       SUM(p.outcome = 'undetermined')    AS undetermined
FROM attack a LEFT JOIN pair p ON p.attack_name = a.name
GROUP BY a.name;

-- One row per paper: role, its techniques, and the rolled-up scorecard.
CREATE VIEW v_paper_card AS
SELECT pa.paper_id, pa.title, pa.year, pa.venue, pa.track, pa.role,
       pa.evidence_grade, pa.citation_count,
       (SELECT GROUP_CONCAT(name, ' | ') FROM attack  WHERE paper_id = pa.paper_id) AS attacks_introduced,
       (SELECT GROUP_CONCAT(name, ' | ') FROM defense WHERE paper_id = pa.paper_id) AS defenses_introduced,
       (SELECT COUNT(*) FROM pair p JOIN defense d ON d.name = p.defense_name
          WHERE d.paper_id = pa.paper_id)                       AS its_defense_attacks_tested,
       (SELECT COUNT(*) FROM pair p JOIN defense d ON d.name = p.defense_name
          WHERE d.paper_id = pa.paper_id AND p.outcome = 'holds')  AS its_defense_wins_claimed,
       (SELECT COUNT(*) FROM pair p JOIN defense d ON d.name = p.defense_name
          WHERE d.paper_id = pa.paper_id AND p.outcome = 'loses')  AS its_defense_refuted,
       (SELECT COUNT(*) FROM pair p JOIN attack a ON a.name = p.attack_name
          WHERE a.paper_id = pa.paper_id)                       AS its_attack_defenses_tested,
       (SELECT COUNT(*) FROM pair p JOIN attack a ON a.name = p.attack_name
          WHERE a.paper_id = pa.paper_id AND p.outcome = 'loses') AS its_attack_defenses_broken,
       (SELECT COUNT(*) FROM pair p JOIN attack a ON a.name = p.attack_name
          WHERE a.paper_id = pa.paper_id AND p.outcome = 'holds')  AS its_attack_defenses_held
FROM paper pa;
"""


def main():
    con = sqlite3.connect(OUT)
    con.executescript(SCHEMA)

    # ---- papers -------------------------------------------------------
    x = pd.read_excel(XLSX)
    x["paper_id"] = x["paper_id"].astype(str)
    cols = [c for c in [
        "paper_id", "title", "authors", "year", "venue", "track", "screening",
        "citation_count", "doi", "arxiv_id", "url", "pdf_local_path",
        "discovered_via", "hop", "channel", "consequence",
        "defense_intervention_point", "temporal_persistence", "cites_track_a",
        "cites_track_b", "evidence_grade", "artifacts_released",
        "models_evaluated", "datasets_benchmarks", "key_result",
        "baselines_compared", "threat_model", "stated_limitations",
        "technical_summary", "abstract"] if c in x.columns]
    x[cols].where(pd.notna(x[cols]), None).to_sql(
        "paper", con, if_exists="append", index=False)

    # ---- attacks ------------------------------------------------------
    rows = []
    for e in load("rq3_pollution_registry.json"):
        rows.append((e["name"], str(e["paper_id"]), e.get("channel"),
                     e.get("consequence"), e.get("track"),
                     e.get("is_extension_of"), e.get("confidence"),
                     e.get("notes"), 0))
    have = {r[0] for r in rows}
    for e in load("rq3_benchmark_mechanisms.json")["mechanisms"]:
        name = e.get("name") or e["technique_name"]
        if name in have:
            continue
        rows.append((name, str(e["paper_id"]), e.get("channel"),
                     e.get("consequence"), e.get("track"), None,
                     e.get("confidence"), e.get("notes"), 1))
    con.executemany("INSERT INTO attack VALUES (?,?,?,?,?,?,?,?,?)", rows)

    # ---- defenses -----------------------------------------------------
    con.executemany(
        "INSERT OR IGNORE INTO defense VALUES (?,?,?,?,?,?,?,?,?,?)",
        [(e["name"], str(e["paper_id"]), e.get("channel"), e.get("consequence"),
          e.get("defense_intervention_point"), e.get("track"),
          e.get("validated_against"), e.get("is_extension_of"),
          e.get("confidence"), e.get("notes"))
         for e in load("rq4_defense_registry.json")])

    # ---- pairs --------------------------------------------------------
    # pair_outcomes.json is the adjudicated verdict layer over the RQ5 base,
    # the supplementary recovery and reverse-scan passes 1-2, so it wins
    # wherever it has an entry. The source files fill in the rest.
    verdict = {}
    for o in load("pair_outcomes.json"):
        verdict[(o["defense_name"], o["mechanism_name"])] = o

    pairs, seen = [], set()

    def add(defense, attack, direction, source, raw, paper_id, title, evidence):
        key = (defense, attack)
        if key in seen:
            return
        seen.add(key)
        v = verdict.get(key)
        if v:
            raw = v["reported_verdict"]
            paper_id = v.get("claim_source_paper_id") or paper_id
            title = v.get("claim_source_paper_title") or title
            direction = ("attack_paper" if v["reported_by"] == "attack_paper"
                         else "defense_paper")
            evidence = v.get("evidence") or evidence
        pairs.append((defense, attack, direction, paper_id, title,
                      raw, classify(raw), source, evidence))

    for m in load("rq5_coverage_matrix.json")["matches"]:
        add(m["defense_name"], m["mechanism_name"], "defense_paper",
            "rq5_base", "", None, None, None)
    for p in load("benchmark_resolved_pairs.json")["confirmed_pairs"]:
        add(p["defense"], p["mechanism"], "defense_paper",
            "benchmark_resolution", p.get("outcome", ""), None, None,
            p.get("evidence"))
    for p in load("rq5_supplementary_pairs.json")["confirmed_pairs"]:
        add(p["defense"], p["mechanism"], "defense_paper",
            "citation_recovery", p.get("verdict", ""), None,
            p.get("defense_paper_title"), p.get("evidence"))
    for p in load("attack_paper_evaluations.json")["confirmed_pairs"]:
        add(p["defense"], p["mechanism"], "attack_paper",
            "reverse_scan_p12", p.get("outcome", ""), None,
            p.get("source_paper"), p.get("evidence"))
    for p in load("attack_paper_evaluations_pass3.json")["confirmed_pairs"]:
        add(p["defense"], p["mechanism"], "attack_paper",
            "reverse_scan_p3", p.get("outcome", ""), None,
            p.get("source_paper"), p.get("evidence"))

    con.executemany(
        "INSERT INTO pair (defense_name, attack_name, direction, "
        "reported_by_paper_id, reported_by_title, outcome_raw, outcome, "
        "source, evidence) VALUES (?,?,?,?,?,?,?,?,?)", pairs)

    # ---- our own runs (kept apart from `pair` on purpose) -------------
    full = load("technique_transfer_full_banking.json")
    runs = []
    for r in full["results"]:
        if r.get("error"):
            continue
        u, d = r["undefended"], r["defended"]
        runs.append((r["technique"], r.get("technique_name"),
                     r.get("intervention_point"), r["attack"],
                     full["suite"], full["model"], u["n"],
                     u["asr_pct"], d["asr_pct"],
                     u.get("utility_pct"), d.get("utility_pct"),
                     r.get("drop_pp"), r.get("mdr_pp"), r.get("verdict")))
    con.executemany(
        "INSERT INTO our_run (technique, technique_name, intervention_point, "
        "attack, suite, model, n, undefended_asr, defended_asr, "
        "undefended_utility, defended_utility, drop_pp, mdr_pp, verdict) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", runs)

    # ---- role ---------------------------------------------------------
    con.executescript("""
        UPDATE paper SET role = CASE
            WHEN paper_id IN (SELECT paper_id FROM attack)
             AND paper_id IN (SELECT paper_id FROM defense) THEN 'both'
            WHEN paper_id IN (SELECT paper_id FROM attack)  THEN 'attack'
            WHEN paper_id IN (SELECT paper_id FROM defense) THEN 'defense'
            ELSE 'neither' END;
    """)
    con.executescript(VIEWS)
    con.commit()

    q = lambda s: con.execute(s).fetchone()[0]
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  papers   {q('SELECT COUNT(*) FROM paper')}",
          dict(con.execute("SELECT role, COUNT(*) FROM paper GROUP BY role")))
    print(f"  attacks  {q('SELECT COUNT(*) FROM attack')}")
    print(f"  defenses {q('SELECT COUNT(*) FROM defense')}")
    print(f"  pairs    {q('SELECT COUNT(*) FROM pair')}",
          dict(con.execute("SELECT outcome, COUNT(*) FROM pair GROUP BY outcome")))
    print(f"  our_runs {q('SELECT COUNT(*) FROM our_run')}")
    con.close()


if __name__ == "__main__":
    main()
