"""Export the papers that contributed no named technique, for a recall pass.

223 of 929 included papers contribute neither a mechanism nor a defense. 80
of those are surveys, benchmarks, position or framework papers by title and
are expected to contribute nothing. The other 143 matched no pattern, and
nothing has checked them since the original extraction.

This is a RECALL check, not an accuracy check: the question is only whether
the paper names a technique we failed to register. The manual validation
study, whose `techniques_we_missed` column was meant to measure exactly
this, is on hold, so this is the only check standing.

Out: data/registries/raw/recheck_batchNN.json
"""
import argparse, json, pathlib, re
import openpyxl

REPO = pathlib.Path(__file__).resolve().parent.parent
PAT = (r"\b(survey|systemati[sz]ation|sok|review|taxonomy|landscape|benchmark"
       r"|evaluat|dataset|testbed|leaderboard|arena|position|towards|roadmap"
       r"|perspective|agenda|challenges|opportunit|framework|architecture"
       r"|platform|protocol|pipeline|system)\b")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-batch", type=int, default=48)
    ap.add_argument("--include-patterned", action="store_true",
                    help="also export the 80 survey/benchmark-looking papers")
    args = ap.parse_args()

    wb = openpyxl.load_workbook(
        REPO / "data/exports/paper_dashboard_source.xlsx", read_only=True)
    rows = list(wb["Papers"].iter_rows(values_only=True))
    h = {k: i for i, k in enumerate(rows[0]) if k}
    inc = [r for r in rows[1:]
           if str(r[h["screening"]]).strip() != "Exclude"]
    ids = {r[h["paper_id"]] for r in inc}

    reg = REPO / "data/registries"
    mech = {e["paper_id"] for e in json.loads(
        (reg / "rq3_pollution_registry.json").read_text())}
    deff = {e["paper_id"] for e in json.loads(
        (reg / "rq4_defense_registry.json").read_text())}
    neither = ids - mech - deff

    out = []
    for r in inc:
        pid = r[h["paper_id"]]
        if pid not in neither:
            continue
        title = str(r[h["title"]] or "")
        patterned = bool(re.search(PAT, title, re.I))
        if patterned and not args.include_patterned:
            continue
        txt = REPO / "data/cache/pdf_text" / f"{pid}.txt"
        out.append({"paper_id": pid, "title": title,
                    "year": r[h["year"]], "venue": r[h["venue"]],
                    "regime": r[h["regime"]],
                    "channel": r[h["channel"]],
                    "consequence": r[h["consequence"]],
                    "looks_like_survey_or_benchmark": patterned,
                    "text": str(txt.relative_to(REPO)),
                    "text_exists": txt.exists()})

    missing = sum(1 for o in out if not o["text_exists"])
    raw = reg / "raw"
    for i in range(0, len(out), args.per_batch):
        b = out[i:i + args.per_batch]
        p = raw / f"recheck_batch{i // args.per_batch + 1:02d}.json"
        p.write_text(json.dumps(b, indent=1))
        print(f"  {p.name}: {len(b)} papers")
    print(f"\n{len(out)} papers exported, {missing} with no cached text")


if __name__ == "__main__":
    main()
