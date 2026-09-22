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

    # ---- executed runs, if any. Keyed (defense, mechanism) -> outcome.
    # Written by agentdojo_harness/run_mechanism_transfer.py; every *.json there
    # matching the shape is ingested, so results appear in the registry as they
    # are produced rather than needing a separate merge step.
    attack_to_mech = {aid: mname for mname, aid in harnessed.items()}
    executed = {}
    screened = {}
    for rp in sorted((REPO / "agentdojo_harness").glob("*.json")):
        try:
            r = json.loads(rp.read_text())
        except Exception:
            continue
        if not isinstance(r, dict) or "results" not in r:
            continue

        # Undefended-only screens (calibrate_control.py) carry `results` as a
        # LIST of per-attack measurements and have no `defense`. They establish
        # whether a mechanism lands on a suite AT ALL, which decides whether a
        # defended run would buy anything -- so they are ingested as a
        # defense-independent property of the (mechanism, suite) pair.
        if isinstance(r["results"], list):
            for res in r["results"]:
                mech_name = attack_to_mech.get(res.get("attack", ""), "")
                if not mech_name:
                    continue
                screened[mech_name] = {
                    "suite": res.get("suite", ""), "model": res.get("served_model", ""),
                    "attack_id": res.get("attack", ""),
                    "asr_undefended": res.get("asr_pct"),
                    "utility_undefended": res.get("utility_pct"),
                    "n": res.get("n_pairs"),
                    "mdr_pp": res.get("min_detectable_reduction_pp"),
                    "verdict": res.get("verdict", ""),
                    "harness_error": res.get("harness_error", ""),
                    "source_file": rp.name,
                }
            continue

        if "defense" not in r:
            continue
        for attack, res in r["results"].items():
            mech_name = res.get("mechanism", "")
            key = (r["defense"], mech_name)
            u, d = res.get("undefended"), res.get("defended")
            executed[key] = {
                "suite": r.get("suite", ""), "model": r.get("model", ""),
                "attack_id": attack,
                "asr_undefended": (u or {}).get("asr_pct", ""),
                "asr_defended": (d or {}).get("asr_pct", ""),
                "utility_undefended": (u or {}).get("utility_pct", ""),
                "n": (u or {}).get("n", ""),
                "mdr_pp": res.get("min_detectable_reduction_pp", ""),
                "verdict": res.get("verdict", ""),
                "blocker": res.get("blocker", ""),
                "blocker_detail": res.get("blocker_detail", ""),
                "source_file": rp.name,
            }
    if executed:
        print(f"  ingested {len(executed)} executed (defense, mechanism) outcome(s)")
    if screened:
        print(f"  ingested {len(screened)} undefended screen result(s)")

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

            # An actual run supersedes any predicted blocker.
            ex = None
            for (dn_k, mech_k), v in executed.items():
                if mech_k == mech:
                    ex = v
                    break
            sc = screened.get(mech)
            if not ex and sc:
                if sc.get("harness_error"):
                    blocker, blocker_kind = "harness_error", "OPERATIONAL"
                    blocker_detail = (
                        f"Rebuilt as AgentDojo attack '{sc['attack_id']}', the pair crashes the "
                        f"harness rather than producing a number: {str(sc['harness_error'])[:260]} "
                        "The injected text collides with AgentDojo's own environment "
                        "serialisation. Not a defense result and not an attack result.")
                elif sc.get("asr_undefended") is not None and sc["asr_undefended"] <= 6.2 and \
                     (sc.get("mdr_pp") in (None, "")):
                    blocker, blocker_kind = "mechanism_inert_on_suite", "OPERATIONAL"
                    blocker_detail = (
                        f"Screened UNDEFENDED on the {sc['suite']} suite as "
                        f"'{sc['attack_id']}': ASR {sc['asr_undefended']}% over n={sc['n']}, too "
                        f"low for any defense verdict to be resolvable, while agent utility was "
                        f"{sc['utility_undefended']}% (so the agent was working) and AgentDojo's "
                        "own attack reached 37.5% on the same victim. The mechanism assumes "
                        "context this suite does not provide. See "
                        "agent_benchmark_representability.md.")

            if ex:
                if ex["blocker"] == "harness_error":
                    blocker, blocker_kind = "harness_error", "OPERATIONAL"
                    blocker_detail = ("The pair crashed the harness rather than producing a "
                                      "number. " + str(ex["blocker_detail"])[:400])
                elif ex["asr_undefended"] == 0:
                    blocker, blocker_kind = "mechanism_inert_on_suite", "OPERATIONAL"
                    blocker_detail = (
                        f"Rebuilt as AgentDojo attack '{ex['attack_id']}' on the "
                        f"{ex['suite']} suite, this mechanism's framing never hijacked the "
                        f"agent even UNDEFENDED (ASR 0% over n={ex['n']}). A defense cannot "
                        "be credited with stopping a payload that does nothing, so the pair "
                        "yields no evidence. Usually means the mechanism assumes a context "
                        "the suite does not provide (persistent memory, a planner, multiple "
                        "agents, skills) rather than that the attack is weak.")
                elif ex["mdr_pp"] in ("", None):
                    blocker, blocker_kind = "control_underpowered", "OPERATIONAL"
                    blocker_detail = (
                        f"Ran on {ex['suite']} at n={ex['n']} with undefended ASR "
                        f"{ex['asr_undefended']}%, too low for a two-proportion test to "
                        "resolve any reduction. Needs a larger n or a stronger control.")
                else:
                    blocker = blocker_kind = blocker_detail = ""

            status = ("RUN" if ex and not blocker else
                      "BLOCKED" if blocker else "RUNNABLE")
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
                "result_suite": (ex or {}).get("suite", ""),
                "result_model": (ex or {}).get("model", ""),
                "result_n": (ex or {}).get("n", ""),
                "result_asr_undefended": (ex or {}).get("asr_undefended", ""),
                "result_asr_defended": (ex or {}).get("asr_defended", ""),
                "result_utility_undefended": (ex or {}).get("utility_undefended", ""),
                "result_mdr_pp": (ex or {}).get("mdr_pp", ""),
                "result_verdict": (ex or {}).get("verdict", ""),
                "result_source": (ex or sc or {}).get("source_file", ""),
                "screen_asr_undefended": (sc or {}).get("asr_undefended", ""),
                "screen_utility": (sc or {}).get("utility_undefended", ""),
                "screen_suite": (sc or {}).get("suite", ""),
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
                "result": (
                    f"{ex['suite']}/{ex['model']} n={ex['n']}: undefended ASR "
                    f"{ex['asr_undefended']}% -> defended {ex['asr_defended']}% "
                    f"(utility {ex['utility_undefended']}%, mdr {ex['mdr_pp']}pp). "
                    f"{ex['verdict']}" if ex else
                    (f"UNDEFENDED SCREEN on {sc['suite']} as '{sc['attack_id']}': "
                     f"ASR {sc['asr_undefended']}% (n={sc['n']}, utility "
                     f"{sc['utility_undefended']}%). {sc['verdict']}" if sc else "not yet run")),
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
                                  "runnable now" if b == "runnable" else
                                  "none on this suite - the framing is inert here; needs a "
                                  "suite providing the context it assumes"
                                  if b == "mechanism_inert_on_suite" else
                                  "fix the attack/harness format collision"
                                  if b == "harness_error" else "n/a")}
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
