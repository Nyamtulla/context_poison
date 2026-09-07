"""Re-apply the current config.yaml inclusion/exclusion criteria to the
corpus using already-extracted full-text data (no new PDF reads).

This is the mechanical half of the screening step -- the AI judgment itself
(does this paper's technical_summary satisfy the current criteria) is done
by subagents driven by the rebuild-corpus skill, using the prompt template
this script generates. This script's job is: figure out WHICH papers need
(re-)judging, export them with the current criteria embedded, and apply
whatever decisions come back.

By default, only papers whose current screening decision came from an
automated process (screen_human is unset) are re-exported for judgment --
a paper a human already looked at and decided on (including a prior AI-
assisted re-screening pass, which this project treats as equivalent to a
human decision per its own established convention) is left alone unless
--all is passed. This is what makes repeated re-runs cheap: editing
config.yaml's criteria and re-running only re-judges the papers that were
never specifically adjudicated, not the whole corpus every time.

Usage:
    # 1. Export papers needing judgment against the CURRENT criteria
    python3 scripts/rescreen_corpus.py --export
    #    -> writes rescreen_batch_N.json (N papers each) + rescreen_prompt.md
    #       (the current criteria text, for a subagent to use)

    # 2. (subagent judges each batch, writes rescreen_decisions_batchN.csv)

    # 3. Apply the decisions
    python3 scripts/rescreen_corpus.py --apply data/registries/raw/rescreen_decisions_*.csv

    # Force a full re-screen of every paper, including previously-adjudicated ones:
    python3 scripts/rescreen_corpus.py --export --all
"""
import argparse
import csv
import datetime
import glob
import json
import sys
from pathlib import Path

import openpyxl

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.config import load_config  # noqa: E402
from src import db  # noqa: E402

EXCEL_PATH = REPO_ROOT / "data" / "exports" / "paper_dashboard_source.xlsx"
BATCH_SIZE = 150
EXPORT_DIR = REPO_ROOT / "data" / "registries" / "raw"


def get_screening_criteria():
    """Read the CURRENT include/exclude criteria text from config.yaml --
    never hardcode this text elsewhere, so editing config.yaml is the one
    place that changes screening behavior everywhere in the pipeline."""
    config = load_config()
    screening = config.screening
    return screening["include_criteria_text"].strip(), screening["exclude_criteria_text"].strip()


def rows_needing_judgment(include_all: bool):
    config = load_config()
    conn = db.connect(config.path("db_path"))
    human_reviewed = set()
    for row in conn.execute("SELECT paper_id FROM papers WHERE screen_human IS NOT NULL"):
        human_reviewed.add(row["paper_id"])

    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    ws = wb["Papers"]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    idx = {name: i for i, name in enumerate(header)}

    targets = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if row[idx["seed_category"]] == "seed":
            continue  # never re-screen hand-picked seeds
        paper_id = row[idx["paper_id"]]
        if not include_all and paper_id in human_reviewed:
            continue
        targets.append({
            "row": row_idx,
            "paper_id": paper_id,
            "title": row[idx["title"]],
            "abstract": row[idx["abstract"]],
            "technical_summary": row[idx["technical_summary"]],
            "key_result": row[idx["key_result"]],
            "threat_model": row[idx["threat_model"]],
            "current_screening": row[idx["screening"]],
        })
    wb.close()
    return targets


def export(include_all: bool):
    include_text, exclude_text = get_screening_criteria()
    targets = rows_needing_judgment(include_all)
    print(f"Papers needing (re-)judgment: {len(targets)}"
          + ("" if include_all else " (human-reviewed papers skipped -- pass --all to force everyone)"))

    if not targets:
        print("Nothing to do -- every non-seed paper already has a human/AI-adjudicated screening "
              "decision. Pass --all to re-screen everyone against the current criteria anyway.")
        return

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    n_batches = max(1, (len(targets) + BATCH_SIZE - 1) // BATCH_SIZE)
    batch_size = (len(targets) + n_batches - 1) // n_batches
    batches = [targets[i:i + batch_size] for i in range(0, len(targets), batch_size)]
    for i, batch in enumerate(batches, 1):
        path = EXPORT_DIR / f"rescreen_batch{i}.json"
        with open(path, "w") as f:
            json.dump(batch, f, indent=1)
        print(f"  wrote {path} ({len(batch)} papers)")

    prompt_path = EXPORT_DIR / "rescreen_prompt.md"
    prompt = f"""# Screening criteria (live from config.yaml, generated {datetime.date.today().isoformat()})

**Include** if: {include_text}

**Exclude** if: {exclude_text}

For each paper, judge INCLUDE or EXCLUDE against these criteria using its
`title`/`abstract`/`technical_summary`/`key_result`/`threat_model` fields
(fall back to `abstract` if `technical_summary` is blank). Be genuinely
discriminating -- err toward EXCLUDE for papers that are centrally about
something else even if they mention a relevant term in passing; err toward
INCLUDE for papers centrally about the phenomena these criteria describe
even if unconventionally framed. See rescreening_log.md in the repo root
for worked examples of both directions from the last screening pass.

Output one row per paper to a CSV with columns:
`row,paper_id,title,decision,reason` (`decision` is exactly `INCLUDE` or
`EXCLUDE`, `reason` is one short phrase).
"""
    prompt_path.write_text(prompt)
    print(f"  wrote {prompt_path}")
    print(f"\n{len(batches)} batch(es) ready. Have a subagent judge each batch against "
          f"{prompt_path.name}, writing decisions to rescreen_decisions_batchN.csv, "
          f"then run: python3 scripts/rescreen_corpus.py --apply data/registries/raw/rescreen_decisions_*.csv")


def apply_decisions(decision_files):
    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb["Papers"]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    idx = {name: i for i, name in enumerate(header)}
    screening_col = idx["screening"] + 1
    seed_col = idx["seed_category"] + 1

    config = load_config()
    conn = db.connect(config.path("db_path"))

    n_include = n_exclude = n_skipped_seed = n_unchanged = 0
    for pattern in decision_files:
        for fname in sorted(glob.glob(pattern)):
            with open(fname) as f:
                for r in csv.DictReader(f):
                    row_idx = int(r["row"])
                    decision = r["decision"].strip().upper()
                    if ws.cell(row=row_idx, column=seed_col).value == "seed":
                        n_skipped_seed += 1
                        continue
                    new_val = "Include" if decision == "INCLUDE" else "Exclude"
                    old_val = ws.cell(row=row_idx, column=screening_col).value
                    if old_val == new_val:
                        n_unchanged += 1
                    ws.cell(row=row_idx, column=screening_col).value = new_val
                    screen_human = "auto_include" if decision == "INCLUDE" else "auto_exclude"
                    conn.execute("UPDATE papers SET screen_human = ? WHERE paper_id = ?",
                                 (screen_human, r["paper_id"]))
                    if decision == "INCLUDE":
                        n_include += 1
                    else:
                        n_exclude += 1

    wb.save(EXCEL_PATH)
    conn.commit()
    print(f"Applied: {n_include} INCLUDE, {n_exclude} EXCLUDE "
          f"({n_unchanged} unchanged from prior decision, {n_skipped_seed} seed rows skipped)")
    print("Excel and DB updated. Next: re-run scripts/dedupe_corpus.py, then rq1/rq2 scripts, "
          "then build_registry.py for any papers whose inclusion status flipped.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--export", action="store_true", help="Export papers needing judgment")
    parser.add_argument("--all", action="store_true", help="With --export: include already-adjudicated papers too")
    parser.add_argument("--apply", nargs="+", metavar="DECISIONS_CSV_GLOB",
                         help="Apply decision CSV(s) (glob patterns ok) to Excel + DB")
    args = parser.parse_args()

    if args.export:
        export(include_all=args.all)
    elif args.apply:
        apply_decisions(args.apply)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
