#!/usr/bin/env python3
"""Query data/paper_explorer.db from the terminal.

    python3 scripts/paper_db.py paper  "AgentDojo"
    python3 scripts/paper_db.py defense "SecAlign"
    python3 scripts/paper_db.py attack  "PoisonedRAG"
    python3 scripts/paper_db.py top
    python3 scripts/paper_db.py sql "SELECT ..."

Search is a case-insensitive substring match on title/name. If more than one
thing matches, the matches are listed instead of one being picked.
"""
from __future__ import annotations

import argparse
import pathlib
import sqlite3
import textwrap

DB = pathlib.Path(__file__).resolve().parent.parent / "data" / "paper_explorer.db"

# The distinction the whole database exists to preserve: a defense paper saying
# it won and an attack paper saying it lost are not the same kind of evidence.
DIRECTION_LABEL = {
    "defense_paper": "defense paper's own claim",
    "attack_paper": "reported by the ATTACK paper",
}
OUTCOME_LABEL = {
    "holds": "defense held",
    "loses": "DEFENSE BROKEN",
    "partial": "defense reduced but did not stop it",
    "undetermined": "ran it, no directional result",
}


def con():
    if not DB.exists():
        raise SystemExit("no database - run: python3 scripts/build_paper_db.py")
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def field(label, value, width=96):
    if value in (None, "", "nan"):
        return
    body = textwrap.fill(str(value), width, subsequent_indent=" " * 24)
    print(f"  {label:<21} {body}")


def pick(c, sql, term, label):
    rows = c.execute(sql, (f"%{term}%",)).fetchall()
    if not rows:
        raise SystemExit(f"no {label} matching {term!r}")
    if len(rows) > 1:
        print(f"{len(rows)} {label}s match {term!r}:\n")
        for r in rows[:40]:
            print(f"  - {r[0]}")
        if len(rows) > 40:
            print(f"  ... and {len(rows) - 40} more")
        raise SystemExit(0)
    return rows[0]


def show_pairs(c, column, value):
    rows = c.execute(
        f"SELECT * FROM pair WHERE {column} = ? "
        "ORDER BY outcome = 'loses' DESC, outcome", (value,)).fetchall()
    if not rows:
        print("  (no defense has ever been run against it, in either direction)"
              if column == "attack_name" else
              "  (never tested against any registry attack)")
        return
    other = "attack_name" if column == "defense_name" else "defense_name"
    for r in rows:
        print(f"  • {r[other]}")
        print(f"      {OUTCOME_LABEL[r['outcome']]}"
              f"  —  {DIRECTION_LABEL[r['direction']]}")
        if r["reported_by_title"]:
            print(f"      in: {r['reported_by_title'][:88]}")
        if r["evidence"]:
            print(textwrap.fill(r["evidence"][:400], 92,
                                initial_indent="      ", subsequent_indent="      "))


def cmd_paper(c, term):
    p = pick(c, "SELECT title FROM paper WHERE title LIKE ? ORDER BY title",
             term, "paper")
    row = c.execute("SELECT * FROM paper WHERE title = ?", (p[0],)).fetchone()
    pid = row["paper_id"]

    print("=" * 100)
    print(textwrap.fill(row["title"], 100))
    print("=" * 100)
    print(f"\n  ROLE: {row['role'].upper()} paper\n")

    for lab, key in [("authors", "authors"), ("year", "year"),
                     ("venue", "venue"), ("track", "track"),
                     ("screening", "screening"), ("citations", "citation_count"),
                     ("evidence grade", "evidence_grade"),
                     ("artifacts released", "artifacts_released"),
                     ("doi", "doi"), ("arxiv", "arxiv_id"), ("url", "url")]:
        field(lab, row[key])

    print()
    for lab, key in [("channel", "channel"), ("consequence", "consequence"),
                     ("intervention point", "defense_intervention_point"),
                     ("persistence", "temporal_persistence"),
                     ("threat model", "threat_model"),
                     ("models evaluated", "models_evaluated"),
                     ("benchmarks", "datasets_benchmarks"),
                     ("baselines", "baselines_compared"),
                     ("key result", "key_result"),
                     ("limitations", "stated_limitations"),
                     ("summary", "technical_summary")]:
        field(lab, row[key])

    for name, in c.execute("SELECT name FROM defense WHERE paper_id = ?", (pid,)):
        s = c.execute("SELECT * FROM v_defense_scorecard WHERE defense = ?",
                      (name,)).fetchone()
        print(f"\n{'-' * 100}\n  DEFENSE PROPOSED: {name}")
        print(f"  attacks it was tested against: {s['attacks_tested']}")
        print(f"      its own paper claims it stopped : {s['self_reported_win']}")
        print(f"      an attack paper later broke it  : {s['refuted']}")
        print(f"      reduced but did not stop        : {s['partial']}")
        print(f"      ran, no directional result      : {s['undetermined']}\n")
        show_pairs(c, "defense_name", name)

    for name, in c.execute("SELECT name FROM attack WHERE paper_id = ?", (pid,)):
        s = c.execute("SELECT * FROM v_attack_scorecard WHERE attack = ?",
                      (name,)).fetchone()
        print(f"\n{'-' * 100}\n  ATTACK PROPOSED: {name}")
        print(f"  defenses ever run against it: {s['defenses_tested']}")
        print(f"      it broke                        : {s['defenses_broken']}")
        print(f"      it only weakened                : {s['defenses_partial']}")
        print(f"      held (per the defense's paper)  : {s['defenses_held_claimed']}")
        print(f"      ran, no directional result      : {s['undetermined']}\n")
        show_pairs(c, "attack_name", name)

    if row["role"] == "neither":
        print("\n  This paper is in the corpus but introduced neither a named "
              "attack nor a named defense (background, survey, or its technique "
              "did not meet the registry's naming bar).")


def cmd_defense(c, term):
    name = pick(c, "SELECT name FROM defense WHERE name LIKE ? ORDER BY name",
                term, "defense")[0]
    s = c.execute("SELECT * FROM v_defense_scorecard WHERE defense = ?",
                  (name,)).fetchone()
    t = c.execute("SELECT title, year, venue FROM paper WHERE paper_id = ?",
                  (s["paper_id"],)).fetchone()
    print("=" * 100)
    print(f"DEFENSE: {name}")
    print("=" * 100)
    field("from", f"{t['title']} ({t['year']}, {t['venue'] or 'no venue'})")
    field("intervention point", s["intervention_point"])
    field("validated against", s["validated_against"])
    print(f"\n  attacks tested against it       : {s['attacks_tested']}")
    print(f"    own paper claims it stopped   : {s['self_reported_win']}")
    print(f"    an attack paper broke it      : {s['refuted']}")
    print(f"    reduced but did not stop      : {s['partial']}")
    print(f"    ran, no directional result    : {s['undetermined']}\n")
    show_pairs(c, "defense_name", name)


def cmd_attack(c, term):
    name = pick(c, "SELECT name FROM attack WHERE name LIKE ? ORDER BY name",
                term, "attack")[0]
    s = c.execute("SELECT * FROM v_attack_scorecard WHERE attack = ?",
                  (name,)).fetchone()
    t = c.execute("SELECT title, year, venue FROM paper WHERE paper_id = ?",
                  (s["paper_id"],)).fetchone()
    print("=" * 100)
    print(f"ATTACK: {name}")
    print("=" * 100)
    field("from", f"{t['title']} ({t['year']}, {t['venue'] or 'no venue'})")
    field("channel", s["channel"])
    field("consequence", s["consequence"])
    print(f"\n  defenses ever run against it    : {s['defenses_tested']}")
    print(f"    it broke                      : {s['defenses_broken']}")
    print(f"    it only weakened              : {s['defenses_partial']}")
    print(f"    held (per the defense's paper): {s['defenses_held_claimed']}")
    print(f"    ran, no directional result    : {s['undetermined']}\n")
    show_pairs(c, "attack_name", name)


def cmd_top(c, _term=None):
    def table(title, sql, cols):
        print(f"\n{title}\n" + "-" * 100)
        for r in c.execute(sql):
            print("  " + "  ".join(
                f"{str(r[k]):>{w}}" if w else str(r[k])[:58].ljust(58)
                for k, w in cols))

    table("Defenses broken by the most attacks",
          "SELECT defense, attacks_tested, refuted FROM v_defense_scorecard "
          "WHERE refuted > 0 ORDER BY refuted DESC, attacks_tested DESC LIMIT 15",
          [("defense", 0), ("attacks_tested", 4), ("refuted", 4)])
    table("Attacks that broke the most defenses",
          "SELECT attack, defenses_tested, defenses_broken FROM v_attack_scorecard "
          "WHERE defenses_broken > 0 ORDER BY defenses_broken DESC LIMIT 15",
          [("attack", 0), ("defenses_tested", 4), ("defenses_broken", 4)])
    table("Attacks nobody has ever defended",
          "SELECT attack, channel FROM v_attack_scorecard WHERE defenses_tested = 0 "
          "ORDER BY attack LIMIT 20",
          [("attack", 0), ("channel", 14)])
    n = c.execute("SELECT COUNT(*) FROM v_attack_scorecard "
                  "WHERE defenses_tested = 0").fetchone()[0]
    print(f"  ... {n} attacks in total have never been defended")


def cmd_sql(c, query):
    rows = c.execute(query).fetchall()
    if rows:
        print(" | ".join(rows[0].keys()))
    for r in rows[:200]:
        print(" | ".join(str(v)[:60] for v in r))
    print(f"\n({len(rows)} rows)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["paper", "defense", "attack", "top", "sql"])
    ap.add_argument("term", nargs="?", default="")
    a = ap.parse_args()
    with con() as c:
        {"paper": cmd_paper, "defense": cmd_defense, "attack": cmd_attack,
         "top": cmd_top, "sql": cmd_sql}[a.command](c, a.term)


if __name__ == "__main__":
    main()
