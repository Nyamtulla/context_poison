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
     python3 scripts/classify_untested_defenses.py   # adds `untested_defense`

The second script is a separate step because it reads the scorecard views this
one creates. A rebuild drops its table, so always run both.
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
    n_poison INTEGER,        -- dose, NULL for the single-dose IPI suite
    undefended_asr REAL, defended_asr REAL,
    undefended_utility REAL, defended_utility REAL,
    drop_pp REAL, mdr_pp REAL,
    verdict TEXT,            -- what happened to attack success
    utility_verdict TEXT,    -- what happened to accuracy, control permitting
    baseline_kind TEXT,      -- 'vanilla' | 'counter_intervention'
    campaign TEXT            -- 'ipi_banking' | 'rag_transfer'
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


# ---------------------------------------------------------------------------
# The RAG transfer campaign
# ---------------------------------------------------------------------------
# Every cell we ran against a RAG defense writes a dose-response registry:
# both arms (undefended / defended) at several poison levels. Those were living
# only as JSON and as prose in the result documents, so the database said we had
# run 56 episodes when the transfer campaign is far larger. This loads them.
#
# Two disciplines are enforced here rather than left to the reader:
#
#   control-fires-first - if the two arms already differ by more than the
#   minimum detectable change at poison 0, the defense is changing accuracy for
#   reasons that have nothing to do with the attack, and no accuracy delta in
#   that cell is attributable. Those rows get `control_failed`, not a verdict.
#
#   mdr gating - a delta smaller than the minimum detectable change at that n is
#   not a result, whatever its sign. It gets `not_resolvable`.

# The runner's `defense` field changed name mid-campaign: the first RobustRAG
# cells wrote "robustrag", later ones write "robustrag-keyword" for the same
# defense. Left alone that splits one cell in two, and the half without a
# poison-0 arm then has no control to fire. Canonicalise before grouping.
DEFENSE_ALIAS = {"robustrag-keyword": "robustrag"}

DEFENSE_META = {
    # registry name -> (display name, family)
    "parammute":          ("ParamMute", "context-reliance"),
    "ckplug":             ("CK-PLUG", "context-reliance"),
    "spare":              ("SpARE", "context-reliance"),
    "robustrag":          ("RobustRAG / KeywordAgg", "isolate-then-aggregate"),
    "robustrag-decoding": ("RobustRAG / DecodingAgg", "isolate-then-aggregate"),
}

# Two early registries predate the fields they needed. The values are not
# guesses: they are the run configuration recorded in the result documents.
REGISTRY_FIXUPS = {
    "poisonedrag_parammute":       {"attack": "poisonedrag"},
    "poisonedrag_parammute_pilot": {"attack": "poisonedrag"},
}
DEFAULT_MODEL = {"parammute": "meta-llama/Meta-Llama-3-8B-Instruct",
                 "ckplug":    "meta-llama/Meta-Llama-3-8B-Instruct"}

# Registries name their arms after the defense. Mapping them to a common pair is
# bookkeeping for most defenses - but not for SpARE, whose two arms are *both*
# steered, in opposite directions, because `generate_two_answers` returns both
# from one model on one prompt. Its comparison is internal and has no unsteered
# model in it, so the row is flagged `counter_intervention` rather than being
# silently read as defended-versus-vanilla.
ARM_MAP = {
    "spare":     {"steer_to_use_context": "defended",
                  "steer_to_use_parameter": "undefended"},
    "ckplug":    {"ck": "defended", "base_rag": "undefended"},
    "parammute": {"parammute": "defended", "base": "undefended"},
    "shift":     {"shift": "defended", "gate_off": "undefended"},
    "faithfulrag": {"faithfulrag": "defended", "vanilla": "undefended"},
}
COUNTER_INTERVENTION_BASELINE = {"spare"}


def load_rag_transfer_runs():
    """Read every dose-response registry into flat (undefended, defended) rows.

    Registries are grouped into cells by (defense, attack) before anything is
    judged. A cell is often split across files - a base run sampling poison
    0/1/5/9/10 plus a `_crossover` run filling 6/7/8 - and the crossover file
    carries no poison 0 arm. Judging files separately would leave those doses
    with no control to fire first, which is how the 8/10 onset went unnoticed.
    """
    cells = {}
    for path in sorted(REG.glob("*.json")):
        if path.stem.endswith("_pilot"):
            continue              # superseded by the full-n run of the same cell
        try:
            d = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(d, dict):
            continue              # some registries are a bare list of records
        results = d.get("results")
        if not isinstance(results, list) or not results:
            continue
        if not (isinstance(results[0], dict)
                and "arm" in results[0] and "n_poison" in results[0]):
            continue              # not a dose-response registry

        d.update(REGISTRY_FIXUPS.get(path.stem, {}))
        defense, attack = d.get("defense"), d.get("attack")
        if not defense or not attack:
            continue
        defense = DEFENSE_ALIAS.get(defense, defense)
        cell = cells.setdefault((defense, attack), {
            "arms": {}, "dataset": d.get("dataset"),
            "model": d.get("model") or DEFAULT_MODEL.get(defense),
            "n": d.get("n"), "mdr": d.get("mdr_pp_at_n")})
        amap = ARM_MAP.get(defense, {})
        for r in results:
            cell["arms"][(amap.get(r["arm"], r["arm"]), r["n_poison"])] = r

    rows = []
    for (defense, attack), cell in sorted(cells.items()):
        name, family = DEFENSE_META.get(defense, (defense, "unclassified"))
        arms, mdr = cell["arms"], cell["mdr"]

        # control-fires-first, evaluated once per cell
        zero_u, zero_d = arms.get(("undefended", 0)), arms.get(("defended", 0))
        control_ok = None
        if zero_u and zero_d and mdr:
            control_ok = abs(zero_d["acc"] - zero_u["acc"]) < mdr

        for level in sorted({k[1] for k in arms}):
            u, v = arms.get(("undefended", level)), arms.get(("defended", level))
            if not (u and v):
                continue
            d_asr = v["asr"] - u["asr"]
            d_acc = v["acc"] - u["acc"]
            if mdr is None:
                verdict = utility = "ungated"
            else:
                verdict = ("reduces_attack_success" if d_asr <= -mdr else
                           "increases_attack_success" if d_asr >= mdr else
                           "not_resolvable")
                if control_ok is False:
                    utility = "control_failed"
                elif control_ok is None:
                    utility = "no_control_arm"
                else:
                    utility = ("harms_accuracy" if d_acc <= -mdr else
                               "helps_accuracy" if d_acc >= mdr else
                               "not_resolvable")
            rows.append((defense, name, family, attack,
                         cell["dataset"], cell["model"], cell["n"], level,
                         u["asr"], v["asr"], u["acc"], v["acc"],
                         d_asr, mdr, verdict, utility,
                         "counter_intervention"
                         if defense in COUNTER_INTERVENTION_BASELINE
                         else "vanilla"))
    return rows


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
        "undefended_utility, defended_utility, drop_pp, mdr_pp, verdict, "
        "campaign) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'ipi_banking')", runs)

    con.executemany(
        "INSERT INTO our_run (technique, technique_name, intervention_point, "
        "attack, suite, model, n, n_poison, undefended_asr, defended_asr, "
        "undefended_utility, defended_utility, drop_pp, mdr_pp, verdict, "
        "utility_verdict, baseline_kind, campaign) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'rag_transfer')",
        load_rag_transfer_runs())

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
