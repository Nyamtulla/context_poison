"""Build a self-contained verification pack for one teammate: xlsx + PDFs, zipped.

This selects PURPOSIVELY - the highest-cited Security papers that contribute an
attack or defense - which is a different thing from the 100-paper random sample
in verification/. The distinction is not pedantry and is stated on the README
sheet: an accuracy measured on the most-cited papers in the field cannot be
generalised to the corpus, because heavily-cited work is better known, better
written and almost certainly better extracted. This pack answers "are our
load-bearing papers coded right", the random sample answers "how good is the
extraction overall", and the two numbers must never be pooled.

Surveys and SoKs are excluded by title, and papers coded role='neither' are
excluded because they contribute no registry entry.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sqlite3
import zipfile

REPO = pathlib.Path(__file__).resolve().parent.parent
DB = REPO / "data" / "paper_explorer.db"

SURVEY = re.compile(
    r"\b(survey|systemati[sz]ation|sok|systematic review|literature review|"
    r"a review|overview of|taxonomy of|landscape|state of the art)\b", re.I)


# field -> (class, what it means, allowed values, where to look, watch out for)
FIELD_GUIDE = {
 "paper_identity": ("check",
   "Is the PDF actually this paper? Compare the title, authors and year on page 1.",
   "correct / wrong",
   "Page 1 of the PDF.",
   "If this is wrong, STOP on this paper and mark the rest 'unclear' - every other "
   "field is being judged against the wrong document."),

 "track": ("core",
   "Which literature the paper belongs to. Security = the bad content is placed "
   "deliberately by an adversary. ML/AI = the context degrades on its own "
   "(retrieval noise, knowledge conflict, long-context drift). Both = the paper "
   "genuinely does both.",
   "Security / ML/AI / Both",
   "Abstract and the threat-model or problem-setup section.",
   "The word 'adversarial' appearing once does not make it Security. Ask whether an "
   "ATTACKER IS MODELLED - someone with a goal, choosing the input."),

 "screening": ("core",
   "Is the paper in scope for this SoK - does it present an attack, a defense, a "
   "benchmark, or an empirical measurement of LLM/agent context contamination?",
   "Include / Exclude",
   "Abstract and the contributions list.",
   "An 'Exclude' that looks like it belongs is the single most valuable thing you "
   "can find - a wrongly excluded paper is invisible everywhere else."),

 "role": ("core",
   "Does the paper PROPOSE an attack, a defense, both, or neither?",
   "attack / defense / both / neither",
   "Contributions list; what the paper claims as new.",
   "Evaluating or benchmarking someone else's defense is not proposing one - that "
   "is usually 'neither'. A paper proposing an attack AND a mitigation is 'both'."),

 "channel": ("core",
   "HOW the bad content reaches the model - which route it travels.",
   "direct-input / RAG / tool-output / tool-metadata / memory / multi-agent / "
   "cross-modal / skill / supply-chain",
   "The attack or system setup: where does the text physically come from?",
   "Ask 'where did the poisoned text live before the model saw it?' A web page the "
   "agent fetched is tool-output; a retrieved passage is RAG; a tool's description "
   "is tool-metadata; what the user typed is direct-input."),

 "consequence": ("core",
   "WHAT GOES WRONG once the bad content is in the context.",
   "goal-hijack / reasoning-corruption / silent-corruption / data-exfiltration / "
   "persistence-backdoor / resource-abuse",
   "What the paper measures as the harm.",
   "goal-hijack = the agent does something it was not asked to. silent-corruption = "
   "the answer is simply wrong and nothing warns you. reasoning-corruption = the "
   "reasoning degrades. Judge by what is MEASURED, not what is speculated about."),

 "cites_track_a": ("core",
   "Does the reference list contain at least one SECURITY paper on this topic "
   "(prompt injection, poisoning, adversarial attacks on LLMs)?",
   "Y / N",
   "THE REFERENCE LIST. Not the abstract.",
   "This needs the bibliography. If you cannot see one, mark 'unclear' rather than "
   "guessing - a wrong Y/N here moves one of the paper's headline numbers."),

 "cites_track_b": ("core",
   "Does the reference list contain at least one ML/AI reliability paper "
   "(retrieval noise, knowledge conflict, hallucination, context rot, "
   "lost-in-the-middle)?",
   "Y / N",
   "THE REFERENCE LIST.",
   "Same as above. These two fields produce the cross-citation result, so they "
   "matter more than their size suggests."),

 "defense_intervention_point": ("secondary",
   "Where in the pipeline the defense acts.",
   "ingestion / reasoning / execution / none",
   "The method section of a defense paper.",
   "'none' is correct for attack-only papers. ingestion = filters or rewrites input "
   "before the model; reasoning = changes how the model processes it; execution = "
   "constrains what the agent may DO with the output."),

 "temporal_persistence": ("secondary",
   "How long the contamination lasts.",
   "one-shot / session-persistent / cross-session-dormant / self-propagating",
   "The attack setup - does the poison survive past the current turn?",
   "one-shot is the default and by far the most common. Only mark something else if "
   "the paper SHOWS persistence, not merely mentions it as future work."),

 "evidence_grade": ("secondary",
   "PUBLICATION RIGOR - not evaluation quality, not how good the paper is.",
   "B = peer-reviewed venue, C = credible preprint, D = no venue (thesis, "
   "unpublished)",
   "The venue, not the content.",
   "This one is easy to get backwards and the original extraction did exactly that. "
   "An arXiv preprint is ALWAYS C, however strong. A weak paper at a real venue is "
   "C or B, never D. D means there is no venue at all."),

 "artifacts_released": ("secondary",
   "Does the paper say code or data is released, and where?",
   "free text, usually starting Y/N and a URL",
   "Abstract footnote, intro footnote, or a reproducibility/availability section.",
   "Record what the PAPER CLAIMS, not whether the link works. 'Will be released' "
   "counts as a claim - note that wording if you see it."),

 "models_evaluated": ("freetext",
   "Which models the paper actually ran experiments on.",
   "free text",
   "Experimental setup / implementation details.",
   "Models mentioned in related work do not count. Only what was run."),

 "datasets_benchmarks": ("freetext",
   "Which datasets or benchmarks the experiments used.",
   "free text",
   "Experimental setup.",
   "Same rule - what was used, not what was cited."),

 "key_result": ("freetext",
   "The paper's main quantitative finding.",
   "free text",
   "Abstract and results section.",
   "Judge whether the paper SUPPORTS this claim, not whether you would have phrased "
   "it the same way. Wrong numbers are a real error; different wording is not."),

 "baselines_compared": ("freetext",
   "What the method was compared against.",
   "free text",
   "Results tables.",
   "'No baselines' is a legitimate value and worth recording when true."),

 "threat_model": ("freetext",
   "What the attacker is assumed to control and know.",
   "free text",
   "Threat model section, or the setup if there is no dedicated section.",
   "If the paper never states a threat model, 'not-in-paper' is the right verdict - "
   "many ML/AI papers genuinely have none."),

 "stated_limitations": ("freetext",
   "Limitations the AUTHORS acknowledge.",
   "free text",
   "Limitations / discussion / conclusion.",
   "Only what the authors admit. Limitations you noticed yourself are not this "
   "field - put those in the note column."),

 "technical_summary": ("freetext",
   "A short description of what the paper does.",
   "free text",
   "The whole paper.",
   "Judge factual accuracy only. Do not mark it wrong for being terse."),
}

CORE = ["track", "screening", "role", "channel", "consequence",
        "cites_track_a", "cites_track_b"]
SECONDARY = ["defense_intervention_point", "temporal_persistence",
             "evidence_grade", "artifacts_released"]
FREETEXT = ["models_evaluated", "datasets_benchmarks", "key_result",
            "baselines_compared", "threat_model", "stated_limitations",
            "technical_summary"]
FIELDS = CORE + SECONDARY + FREETEXT
META = ["paper_id", "title", "authors", "year", "venue", "citation_count",
        "doi", "arxiv_id", "url"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--track", default="Security")
    ap.add_argument("--who", default="teammate-1")
    ap.add_argument("--out", default="verification/packs")
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    rows = con.execute(f"""
        select {', '.join(META + FIELDS + ['pdf_local_path'])}
        from paper
        where screening='Include' and track=?
          and role in ('attack','defense','both')
          and pdf_local_path is not null and trim(pdf_local_path)!=''
        order by coalesce(citation_count,0) desc limit 200""", (args.track,)).fetchall()
    cols = META + FIELDS + ["pdf_local_path"]
    recs = [dict(zip(cols, r)) for r in rows]
    recs = [r for r in recs if not SURVEY.search(r["title"] or "")]
    recs = [r for r in recs if (REPO / r["pdf_local_path"]).exists()][: args.n]
    print(f"selected {len(recs)} papers", flush=True)

    overlap = set()
    sd = REPO / "verification" / "sample_design.json"
    if sd.exists():
        rand = {s["paper_id"] for s in json.loads(sd.read_text())["sample"]}
        overlap = {r["paper_id"] for r in recs} & rand

    outdir = REPO / args.out
    outdir.mkdir(parents=True, exist_ok=True)
    xlsx = outdir / f"{args.who}_assignment.xlsx"

    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = openpyxl.Workbook()

    ws = wb.active
    ws.title = "How to code"
    lines = [
        ("How to verify these papers", True),
        ("", False),
        (f"You have {len(recs)} papers. The PDFs are in pdfs/ in this zip, named by title", False),
        ("(a colon in the title becomes ' - ' in the filename).", False),
        ("", False),
        ("THE JOB", True),
        ("For each paper we extracted 18 fields automatically. Your job is to check each", False),
        ("one against the paper and say whether it is right. You are measuring how good", False),
        ("the extraction is - you are NOT fixing the data.", False),
        ("", False),
        ("WHERE TO WORK", True),
        ("Use the 'coding' sheet. One row per (paper, field).", False),
        ("", False),
        ("  EDIT these three columns only:", True),
        ("    verdict                  your judgement (see below)", False),
        ("    correct_value_if_wrong   what the paper actually says, if verdict=wrong", False),
        ("    note                     anything the next person needs to know", False),
        ("", False),
        ("  LEAVE these alone - they are the record being tested:", True),
        ("    title, field, field_class, AI_extracted_value, paper_id", False),
        ("", False),
        ("THE FOUR VERDICTS", True),
        ("  correct        the value is right and the paper says so", False),
        ("  wrong          the paper says something different.", False),
        ("                 -> put the real value in correct_value_if_wrong", False),
        ("  not-in-paper   the paper never states this at all.", False),
        ("                 This is NOT the same as 'wrong'. 'wrong' means we misread", False),
        ("                 the paper; 'not-in-paper' means we made it up. Those have", False),
        ("                 different causes and different fixes, so keep them apart.", False),
        ("  unclear        the paper is ambiguous, or you cannot tell from what you have.", False),
        ("                 Use it honestly - a guess is worse than an 'unclear'.", False),
        ("", False),
        ("IF YOU FIND SOMETHING WRONG", True),
        ("Write it down and move on. Do NOT go and correct the database or the", False),
        ("spreadsheet the value came from. The whole point is to count how often the", False),
        ("extraction is wrong; a silently corrected cell destroys the measurement.", False),
        ("If you think the FIELD DEFINITION is wrong rather than the value, say so in", False),
        ("the note - that is a different and more important finding.", False),
        ("", False),
        ("START EACH PAPER WITH 'paper_identity'", True),
        ("The first row for every paper asks whether the PDF is really that paper.", False),
        ("Check the title, authors and year on page 1. If it is the wrong paper, stop", False),
        ("there, mark the remaining fields 'unclear', and say so in the note - every", False),
        ("other field would be judged against the wrong document.", False),
        ("", False),
        ("FIELD CLASSES", True),
        ("  check      the paper-identity check above. Do this first.", False),
        ("  core       the 7 fields the project's headline numbers rest on. Spend your", False),
        ("             time here. If you only finish part of a paper, finish these.", False),
        ("  secondary  supporting taxonomy fields. Still checked, lower stakes.", False),
        ("  freetext   prose summaries. Judge whether the paper SUPPORTS the claim, not", False),
        ("             whether you would have worded it the same way. Wrong facts and", False),
        ("             wrong numbers are errors; different phrasing is not.", False),
        ("", False),
        ("WHAT EACH FIELD MEANS", True),
        ("See the 'field guide' sheet: what the field is, its allowed values, where in", False),
        ("the paper to look for it, and the mistake most likely to be made on it.", False),
        ("Read the field guide row before coding a field for the first time.", False),
        ("", False),
        ("HOW LONG", True),
        ("Expect roughly 15-25 minutes per paper once you are warmed up. You do not", False),
        ("need to read the whole paper - abstract, setup, results and the reference", False),
        ("list carry almost everything.", False),
        ("", False),
        ("IF IN DOUBT", True),
        ("Mark 'unclear' and write what confused you. An honest 'unclear' is useful", False),
        ("data. A confident guess is not.", False),
    ]
    wsg = wb.create_sheet("field guide")
    gh = ["field", "class", "what it means", "allowed values",
          "where to look in the paper", "watch out for"]
    wsg.append(gh)
    for c in wsg[1]:
        c.font = Font(bold=True); c.fill = PatternFill("solid", fgColor="DDDDDD")
    wsg.freeze_panes = "A2"
    for f in ["paper_identity"] + FIELDS:
        cls, meaning, allowed, where, watch = FIELD_GUIDE[f]
        wsg.append([f, cls, meaning, allowed, where, watch])
    for col, w in zip("ABCDEF", [28, 11, 62, 46, 42, 64]):
        wsg.column_dimensions[col].width = w
    for row in wsg.iter_rows(min_row=1, max_row=wsg.max_row):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    for r in range(2, wsg.max_row + 1):
        wsg.row_dimensions[r].height = 86

    ws2 = wb.create_sheet("papers")
    head2 = ["#", "title", "year", "venue", "citations", "role", "channel",
             "consequence", "doi", "arxiv_id", "paper_id"]
    ws2.append(head2)
    for c in ws2[1]:
        c.font = Font(bold=True); c.fill = PatternFill("solid", fgColor="DDDDDD")
    ws2.freeze_panes = "A2"
    for i, r in enumerate(recs, start=1):
        ws2.append([i, r["title"], r["year"], r["venue"], r["citation_count"],
                    r["role"], r["channel"], r["consequence"], r["doi"] or "",
                    r["arxiv_id"] or "", r["paper_id"]])
    for col, w in zip("ABCDEFGHIJK", [4, 78, 6, 38, 10, 10, 14, 22, 32, 12, 42]):
        ws2.column_dimensions[col].width = w
    ws2.auto_filter.ref = f"A1:K{len(recs)+1}"

    ws3 = wb.create_sheet("coding")
    head3 = ["#", "title", "field", "field_class", "AI_extracted_value",
             "verdict", "correct_value_if_wrong", "note", "paper_id"]
    ws3.append(head3)
    for c in ws3[1]:
        c.font = Font(bold=True); c.fill = PatternFill("solid", fgColor="DDDDDD")
    ws3.freeze_panes = "C2"
    n = 0
    for i, r in enumerate(recs, start=1):
        # identity check first: everything else is worthless if the PDF is
        # a different paper
        ws3.append([i, r["title"][:78], "paper_identity", "check",
                    f"{r['title']}  ({r['authors'] or '?'}, {r['year']})"[:500],
                    "", "", "", r["paper_id"]])
        n += 1
        for f in FIELDS:
            cls = "core" if f in CORE else "secondary" if f in SECONDARY else "freetext"
            v = r.get(f)
            v = "" if v is None else str(v)
            ws3.append([i, r["title"][:78], f, cls, v[:500], "", "", "", r["paper_id"]])
            n += 1
    for col, w in zip("ABCDEFGHI", [4, 54, 28, 11, 74, 14, 32, 36, 42]):
        ws3.column_dimensions[col].width = w
    for row in ws3.iter_rows(min_row=2, min_col=5, max_col=5):
        for c in row:
            c.alignment = Alignment(wrap_text=False, vertical="top")
    ws3.auto_filter.ref = f"A1:I{n+1}"
    wb.save(xlsx)

    zpath = outdir / f"{args.who}_assignment.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(xlsx, arcname=xlsx.name)
        for r in recs:
            src = REPO / r["pdf_local_path"]
            z.write(src, arcname=f"pdfs/{src.name}")
    size = zpath.stat().st_size / 1e6
    print(f"wrote {xlsx.relative_to(REPO)}  ({n} coding rows)")
    print(f"wrote {zpath.relative_to(REPO)}  ({len(recs)} PDFs, {size:.1f} MB)")
    if overlap:
        print(f"  NOTE: {len(overlap)} also in the random sample: "
              f"{sorted(x[:8] for x in overlap)}")

    (outdir / f"{args.who}_manifest.json").write_text(json.dumps(
        {"who": args.who, "selection": "purposive: most-cited Security papers "
         "presenting an attack or defense; surveys/SoKs excluded",
         "generalisable": False,
         "overlap_with_random_sample": sorted(overlap),
         "papers": [{"paper_id": r["paper_id"], "title": r["title"],
                     "citations": r["citation_count"],
                     "pdf": pathlib.Path(r["pdf_local_path"]).name} for r in recs]},
        indent=1))


if __name__ == "__main__":
    main()
