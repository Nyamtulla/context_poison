"""One row per (defense, mechanism) pair we intend to test, with why it can or cannot run.

The transfer programme's credibility depends as much on the pairs we could NOT
run as the ones we could. A hit rate computed over a silently-filtered set is
not a hit rate. So every candidate pair gets a row, a status, and — when it
cannot run — a named blocker and the reason, in the same file.

Blockers are split into two kinds, because they have different futures:

  STRUCTURAL  the pair cannot produce evidence no matter what hardware we throw
              at it. Inherited from scripts/transfer_scenarios.py's TRIAGE:
              the payload is an optimizer's output, the carrier is an image or
              audio, or there is no single payload to place. Running these
              anyway would produce a number about our paraphrase, not the attack.

  OPERATIONAL the pair is testable in principle and blocked by our setup today:
              no released defense code, no agent-harness rebuild of the
              mechanism, or a victim model too weak to give a readable control.
              These have a route: better model, API model, more engineering.

That distinction is the point. "We could not test 40% of pairs" invites the
reader to assume the worst; "12 are structurally untestable and 28 are waiting
on a stronger victim model" is a different and honest claim.

    python3 scripts/build_pair_attempt_registry.py [-o out.xlsx]
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
REG = REPO / "data/registries"

STRUCTURAL = {"optimizer_is_the_attack", "channel_mismatch", "no_single_payload"}


def load_triage():
    """TRIAGE from transfer_scenarios without importing its heavy deps."""
    import ast
    src = (REPO / "scripts/transfer_scenarios.py").read_text()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "TRIAGE":
            return ast.literal_eval(node.value)
    return {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=str(REPO / "context_sok_pair_attempts.xlsx"))
    args = ap.parse_args()

    triage = load_triage()
    excluded = {}           # mechanism -> (category, why)
    for cat, block in triage.items():
        for m in block["mechanisms"]:
            excluded[m] = (cat, block["why"])

    preds = json.loads((REG / "stage2_transfer_predictions.json").read_text())
    raw3 = {m["name"]: m for m in json.loads((REG / "rq3_pollution_registry.json").read_text())}
    raw4 = {d["name"]: d for d in json.loads((REG / "rq4_defense_registry.json").read_text())}

    # which mechanisms have been rebuilt as AgentDojo attacks
    harnessed = {}
    try:
        sys.path.insert(0, str(REPO / "agentdojo_harness"))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "mech_attacks", REPO / "agentdojo_harness/mechanism_attacks.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        harnessed = {v: k for k, v in mod.MECHANISM_ATTACKS.items()}
    except Exception as e:                     # harness deps absent is not fatal here
        print(f"  (could not load mechanism_attacks: {e})")

    # current control state, if calibration has been run
    calib = {}
    cpath = REPO / "agentdojo_harness/control_calibration.json"
    if cpath.exists():
        c = json.loads(cpath.read_text())
        usable = [r for r in c["results"] if r["verdict"] == "USABLE"]
        calib = {"any_usable": bool(usable), "results": c["results"],
                 "floor": c["floor"]}

    control_ok = calib.get("any_usable", False)

    rows, log = [], []
    for p in preds:
        mech = p["mechanism"]
        cands = p.get("candidates") or []
        if not cands:
            cands = [{}]
        for rank, c in enumerate(cands[:1], start=1):     # top candidate per mechanism
            dname = c.get("defense", "")
            m3, d4 = raw3.get(mech, {}), raw4.get(dname, {})

            blocker = blocker_kind = blocker_detail = ""
            if mech in excluded:
                cat, why = excluded[mech]
                blocker, blocker_kind, blocker_detail = cat, "STRUCTURAL", why
            elif not dname:
                blocker, blocker_kind = "no_candidate_defense", "OPERATIONAL"
                blocker_detail = ("No defense in the RQ4 registry shares enough channel/"
                                  "consequence structure with this mechanism to generate a "
                                  "transfer hypothesis worth testing.")
            elif not c.get("code_released"):
                blocker, blocker_kind = "no_released_code", "OPERATIONAL"
                blocker_detail = (f"{dname} has no released implementation we can run. The "
                                  "project standard is to run the defense's own code, never "
                                  "to reimplement it and attribute the result to the authors.")
            elif mech not in harnessed:
                blocker, blocker_kind = "no_agent_harness", "OPERATIONAL"
                blocker_detail = (f"{mech} has not been rebuilt as an AgentDojo attack in "
                                  "agentdojo_harness/mechanism_attacks.py, so there is no "
                                  "agent-shaped victim to run it against. Bounded engineering, "
                                  "not a research obstacle.")
            elif not control_ok:
                blocker, blocker_kind = "control_underpowered", "OPERATIONAL"
                blocker_detail = ("No harness configuration currently reaches an undefended "
                                  "ASR that can resolve a reduction. At the rates measured "
                                  "(workspace 6.2%, banking 15.6% undefended, utility 31-38%) "
                                  "a two-proportion test cannot distinguish a perfect defense "
                                  "from no defense. Blocked on victim-model capability — an "
                                  "API model would likely clear it.")

            status = "BLOCKED" if blocker else "RUNNABLE"
            rows.append({
                "mechanism": mech,
                "defense": dname,
                "status": status,
                "blocker": blocker,
                "blocker_kind": blocker_kind,
                "blocker_detail": blocker_detail,
                "predicted_score": c.get("score", ""),
                "similarity": c.get("similarity", ""),
                "intervention_prior": c.get("intervention_prior", ""),
                "defense_intervention_point": c.get("defense_intervention_point", ""),
                "defense_validated_against": c.get("defense_validated_against", ""),
                "cross_track": c.get("cross_track", ""),
                "transfers_from": c.get("transfers_from", ""),
                "mechanism_track": p.get("mechanism_track", ""),
                "mechanism_channel": p.get("channel", ""),
                "mechanism_consequence": p.get("consequence", ""),
                "mechanism_citations": p.get("mechanism_citations", ""),
                "mechanism_paper": p.get("mechanism_paper", ""),
                "defense_paper": c.get("defense_paper_title", ""),
                "agent_harness_id": harnessed.get(mech, ""),
                "result_asr_undefended": "", "result_asr_defended": "",
                "result_utility": "", "result_verdict": "", "run_date": "",
            })

            log.append({
                "mechanism": mech,
                "defense": dname,
                "what_is_the_mechanism": (m3.get("notes") or "")[:800]
                    or f"{p.get('channel','')} / {p.get('consequence','')} attack; see {p.get('mechanism_paper','')}",
                "what_is_the_defense": (d4.get("notes") or "")[:800]
                    or f"{c.get('defense_intervention_point','')}-stage defense; see {c.get('defense_paper_title','')}",
                "why_this_pair": (
                    f"The transfer model scores this {c.get('score','')} "
                    f"(similarity {c.get('similarity','')} x {c.get('defense_intervention_point','')} "
                    f"prior {c.get('intervention_prior','')}). {dname} was validated against "
                    f"{c.get('transfers_from','')} but never against {mech}."
                ) if dname else "No candidate defense generated.",
                "how_we_would_run_it": (
                    f"AgentDojo victim agent; mechanism rebuilt as attack "
                    f"'{harnessed.get(mech,'(not yet built)')}'; run UNDEFENDED then DEFENDED "
                    f"over the same (user task, injection task) pairs, scored by the suite's own "
                    f"checker. Undefended ASR is reported alongside, so a miss on an inert "
                    f"payload is never counted as a defense success."
                ),
                "status": status,
                "blocker": blocker,
                "blocker_kind": blocker_kind,
                "blocker_detail": blocker_detail,
                "result": "not yet run",
            })

    # ---- write workbook
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    HDR_FILL = PatternFill("solid", fgColor="12253C")
    HDR_FONT = Font(bold=True, color="FFFFFF", size=10)

    wb = openpyxl.Workbook(); wb.remove(wb.active)

    def sheet(name, records, widths=None, wrap=()):
        if not records:
            return
        ws = wb.create_sheet(name[:31])
        cols = list(records[0].keys())
        ws.append(cols)
        for i in range(1, len(cols) + 1):
            c = ws.cell(1, i); c.fill, c.font = HDR_FILL, HDR_FONT
        for r in records:
            ws.append([r.get(k, "") for k in cols])
        for i, k in enumerate(cols, start=1):
            ws.column_dimensions[get_column_letter(i)].width = (widths or {}).get(k, 18)
            if k in wrap:
                for row in range(2, ws.max_row + 1):
                    ws.cell(row, i).alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        return ws

    sheet("Pair attempts", rows,
          widths={"mechanism": 46, "defense": 34, "blocker_detail": 70, "transfers_from": 40,
                  "mechanism_paper": 46, "defense_paper": 46, "blocker": 22, "status": 11},
          wrap=("blocker_detail",))
    sheet("Experiment log", log,
          widths={"mechanism": 40, "defense": 30, "what_is_the_mechanism": 70,
                  "what_is_the_defense": 70, "why_this_pair": 60,
                  "how_we_would_run_it": 70, "blocker_detail": 60, "result": 30},
          wrap=("what_is_the_mechanism", "what_is_the_defense", "why_this_pair",
                "how_we_would_run_it", "blocker_detail"))

    import collections
    bysum = collections.Counter((r["blocker_kind"] or "-", r["blocker"] or "runnable") for r in rows)
    summary = [{"blocker_kind": k, "blocker": b, "pairs": n,
                "route_forward": ("none — would not produce evidence about the attack"
                                  if k == "STRUCTURAL" else
                                  "stronger/API victim model" if b == "control_underpowered" else
                                  "build the AgentDojo attack" if b == "no_agent_harness" else
                                  "obtain or request the implementation" if b == "no_released_code" else
                                  "runnable now" if b == "runnable" else "n/a")}
               for (k, b), n in sorted(bysum.items(), key=lambda x: -x[1])]
    sheet("Blocker summary", summary, widths={"blocker": 26, "route_forward": 52, "blocker_kind": 14})

    if calib:
        sheet("Control calibration",
              [{k: (json.dumps(v) if isinstance(v, (list, dict)) else v)
                for k, v in r.items() if k != "per_pair"} for r in calib["results"]],
              widths={"model": 14, "served_model": 28, "attack": 26, "verdict": 18})

    wb.save(args.out)
    print(f"Wrote {args.out}")
    print(f"  pairs: {len(rows)}   runnable: {sum(1 for r in rows if r['status']=='RUNNABLE')}"
          f"   blocked: {sum(1 for r in rows if r['status']=='BLOCKED')}")
    for (k, b), n in sorted(bysum.items(), key=lambda x: -x[1]):
        print(f"    {n:>4}  [{k or '-'}] {b}")


if __name__ == "__main__":
    main()
