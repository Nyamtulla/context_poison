"""Build four 25-paper verification packets from the top 100, each a mixed slice.

Papers are dealt round-robin by rank (1->P1, 2->P2, 3->P3, 4->P4, 5->P1 ...)
so every packet gets an even spread of the top 100 rather than one person
getting all the most important papers and another getting the tail.

Each packet ships as a zip: one workbook plus the 25 PDFs.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import zipfile

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

REPO = pathlib.Path(__file__).resolve().parent.parent
RANK = REPO / "data" / "registries" / "paper_importance_ranking.json"
OUT = REPO / "verification" / "packets"
N_PACKETS, PER = 4, 25

CORE = ["track", "screening", "role", "channel", "consequence",
        "cites_track_a", "cites_track_b"]
SECONDARY = ["defense_intervention_point", "temporal_persistence",
             "evidence_grade", "artifacts_released"]
FREETEXT = ["models_evaluated", "datasets_benchmarks", "key_result",
            "baselines_compared", "threat_model", "stated_limitations",
            "technical_summary"]
FIELDS = CORE + SECONDARY + FREETEXT

GUIDE = {
 "paper_identity": ("check",
   "Is this PDF actually this paper? Compare title, authors and year on page 1.",
   "correct / wrong",
   "Page 1.",
   "If wrong, stop on this paper, mark the rest 'unclear', and say so in the note."),
 "track": ("core",
   "Which research community the paper belongs to.",
   "Security / ML-AI / Both",
   "Abstract; threat-model or problem-setup section.",
   "Security = an attacker deliberately places the bad content. ML-AI = the "
   "context degrades on its own. The word 'adversarial' appearing once is not "
   "enough - ask whether an attacker is actually modelled."),
 "screening": ("core",
   "Is the paper in scope: does it present an attack, defense, benchmark or "
   "measurement of LLM/agent context contamination?",
   "Include / Exclude",
   "Abstract; contributions list.",
   "An 'Exclude' that looks like it belongs is the most valuable thing you can find."),
 "role": ("core",
   "Does the paper PROPOSE an attack, a defense, both, or neither?",
   "attack / defense / both / neither",
   "Contributions list.",
   "Evaluating someone else's defense is not proposing one - that is usually "
   "'neither'. Surveys and benchmarks are usually 'neither'."),
 "channel": ("core",
   "HOW the bad content reaches the model - which route it travels.",
   "direct-input / RAG / tool-output / tool-metadata / memory / multi-agent / "
   "cross-modal / skill / supply-chain",
   "The attack or system setup.",
   "Ask: where did the text live before the model saw it? See the Glossary sheet."),
 "consequence": ("core",
   "WHAT GOES WRONG once the bad content is in the context.",
   "goal-hijack / reasoning-corruption / silent-corruption / data-exfiltration / "
   "persistence-backdoor / resource-abuse",
   "What the paper measures as the harm.",
   "Judge by what is MEASURED, not what is speculated about. See the Glossary sheet."),
 "cites_track_a": ("core",
   "Does the reference list contain at least one SECURITY paper on this topic?",
   "Y / N",
   "THE REFERENCE LIST - not the abstract.",
   "If you cannot see a bibliography, mark 'unclear' rather than guessing."),
 "cites_track_b": ("core",
   "Does the reference list contain at least one ML/AI reliability paper "
   "(retrieval noise, knowledge conflict, hallucination, context rot)?",
   "Y / N",
   "THE REFERENCE LIST.",
   "Same as above."),
 "defense_intervention_point": ("secondary",
   "Where in the pipeline the defense acts.",
   "ingestion / reasoning / execution / none",
   "Method section.",
   "'none' is correct for attack-only papers. See the Glossary sheet."),
 "temporal_persistence": ("secondary",
   "How long the contamination lasts.",
   "one-shot / session-persistent / cross-session-dormant / self-propagating",
   "Attack setup.",
   "one-shot is the default. Only mark otherwise if the paper SHOWS persistence."),
 "evidence_grade": ("secondary",
   "PUBLICATION RIGOR - not evaluation quality, not how good the paper is.",
   "B = peer-reviewed venue, C = credible preprint, D = no venue",
   "The venue, not the content.",
   "Easy to get backwards. An arXiv preprint is ALWAYS C however strong. A weak "
   "paper at a real venue is B or C, never D."),
 "artifacts_released": ("secondary",
   "Does the paper say code or data is released, and where?",
   "free text, usually Y/N plus a URL",
   "Abstract footnote, intro footnote, or an availability section.",
   "Record what the PAPER CLAIMS, not whether the link works."),
 "models_evaluated": ("freetext", "Which models the paper ran experiments on.",
   "free text", "Experimental setup.",
   "Models named only in related work do not count."),
 "datasets_benchmarks": ("freetext", "Which datasets or benchmarks the experiments used.",
   "free text", "Experimental setup.", "What was used, not what was cited."),
 "key_result": ("freetext", "The paper's main quantitative finding.",
   "free text", "Abstract and results.",
   "Check the numbers. Different wording is not an error; wrong numbers are."),
 "baselines_compared": ("freetext", "What the method was compared against.",
   "free text", "Results tables.", "'No baselines' is a legitimate value."),
 "threat_model": ("freetext", "What the attacker is assumed to control and know.",
   "free text", "Threat-model section, or the setup.",
   "If the paper never states one, 'not-in-paper' is correct - many ML/AI papers have none."),
 "stated_limitations": ("freetext", "Limitations the AUTHORS acknowledge.",
   "free text", "Limitations / discussion / conclusion.",
   "Only what the authors admit. Your own observations go in the note column."),
 "technical_summary": ("freetext", "Short description of what the paper does.",
   "free text", "The whole paper.", "Judge factual accuracy only."),
}

GLOSSARY = [
 ("CHANNEL - how the bad content reaches the model", "", ""),
 ("direct-input", "What the user (or attacker posing as the user) typed.", "channel"),
 ("RAG", "A passage pulled from a retrieval corpus or vector store.", "channel"),
 ("tool-output", "Content returned by a tool the agent called - a fetched web page, an API response, a file read.", "channel"),
 ("tool-metadata", "A tool's own name, description or schema, which the model reads to decide whether to call it.", "channel"),
 ("memory", "Something the agent stored earlier and retrieved later, within or across sessions.", "channel"),
 ("multi-agent", "A message from another agent.", "channel"),
 ("cross-modal", "An image, PDF, audio or video whose content the model parses.", "channel"),
 ("skill", "A plugin, skill file or extension loaded into the agent.", "channel"),
 ("supply-chain", "A model, dataset, package or dependency compromised before deployment.", "channel"),
 ("", "", ""),
 ("CONSEQUENCE - what goes wrong", "", ""),
 ("goal-hijack", "The agent does something it was not asked to do - calls the wrong tool, follows the injected instruction.", "consequence"),
 ("reasoning-corruption", "The reasoning degrades: distraction, wrong intermediate steps, lost-in-the-middle.", "consequence"),
 ("silent-corruption", "The answer is simply wrong and nothing warns you.", "consequence"),
 ("data-exfiltration", "Sensitive data leaves - secrets, PII, conversation history.", "consequence"),
 ("persistence-backdoor", "The contamination survives into later turns or sessions and fires later.", "consequence"),
 ("resource-abuse", "Compute, tokens or money are wasted - denial of service, inference bloat.", "consequence"),
 ("", "", ""),
 ("DEFENSE INTERVENTION POINT - where the defense acts", "", ""),
 ("ingestion", "Filters, rewrites or sanitises content BEFORE the model sees it.", "intervention"),
 ("reasoning", "Changes how the model processes the content - decoding, steering, prompting.", "intervention"),
 ("execution", "Constrains what the agent may DO with the output - permissions, confirmation, sandboxing.", "intervention"),
 ("none", "The paper proposes no defense (attack-only paper).", "intervention"),
 ("", "", ""),
 ("TEMPORAL PERSISTENCE", "", ""),
 ("one-shot", "Affects the current turn only. The default.", "persistence"),
 ("session-persistent", "Persists for the rest of the session.", "persistence"),
 ("cross-session-dormant", "Survives into a later session and can lie dormant.", "persistence"),
 ("self-propagating", "Spreads to other agents or contexts on its own.", "persistence"),
 ("", "", ""),
 ("ABBREVIATIONS", "", ""),
 ("LLM", "Large Language Model.", "abbrev"),
 ("RAG", "Retrieval-Augmented Generation - the model retrieves documents and answers from them.", "abbrev"),
 ("PI", "Prompt Injection - an instruction smuggled into the model's input.", "abbrev"),
 ("IPI", "Indirect Prompt Injection - the instruction arrives through content the agent fetched, not from the user.", "abbrev"),
 ("ASR", "Attack Success Rate - the share of attempts where the attack worked.", "abbrev"),
 ("FPR / FNR", "False Positive Rate / False Negative Rate.", "abbrev"),
 ("EM / F1", "Exact Match / F1 score - answer-accuracy metrics.", "abbrev"),
 ("CoT", "Chain of Thought - the model reasoning step by step before answering.", "abbrev"),
 ("MCP", "Model Context Protocol - a standard for agents to call shared tools.", "abbrev"),
 ("SoK", "Systematization of Knowledge - the kind of paper this project is writing.", "abbrev"),
 ("FFN", "Feed-Forward Network - a layer inside a transformer.", "abbrev"),
 ("SAE", "Sparse Autoencoder - used to find interpretable features inside a model.", "abbrev"),
 ("DPO / RLHF", "Preference-based training methods used to align models.", "abbrev"),
 ("top-k", "The k highest-ranked documents returned by retrieval.", "abbrev"),
 ("parametric knowledge", "What the model knows from training, as opposed to what it reads in the context.", "abbrev"),
 ("knowledge conflict", "The retrieved context and the model's own knowledge disagree.", "abbrev"),
 ("context rot / lost in the middle", "Long-context failure modes: quality degrades, or the middle of a long context is ignored.", "abbrev"),
]


def sheet_header(ws, head):
    ws.append(head)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="DDDDDD")


def build(packet_no, papers, pe):
    name = f"packet-{packet_no}"
    xlsx = OUT / f"{name}.xlsx"
    wb = openpyxl.Workbook()

    ws = wb.active
    ws.title = "Start here"
    lines = [
        (f"Verification packet {packet_no} of {N_PACKETS}", True),
        ("", False),
        (f"{len(papers)} papers. The PDFs are in pdfs/ in this zip, named by title", False),
        ("(a colon in a title becomes ' - ' in the filename).", False),
        ("", False),
        ("WHAT TO DO", True),
        ("For each paper we extracted 18 fields automatically. Check each one against", False),
        ("the paper and say whether it is right. You are measuring how accurate the", False),
        ("extraction is - you are not fixing the data.", False),
        ("", False),
        ("Work on the 'coding' sheet. One row per (paper, field).", False),
        ("", False),
        ("  Fill in these three columns only:", True),
        ("    verdict                  your judgement (see below)", False),
        ("    correct_value_if_wrong   what the paper actually says, if verdict = wrong", False),
        ("    note                     anything worth passing on", False),
        ("", False),
        ("  Do not change these - they are the record being tested:", True),
        ("    title, field, field_class, AI_extracted_value, paper_id", False),
        ("", False),
        ("THE FOUR VERDICTS", True),
        ("  correct        the value is right and the paper says so", False),
        ("  wrong          the paper says something different", False),
        ("                 -> put the real value in correct_value_if_wrong", False),
        ("  not-in-paper   the paper never states this at all.", False),
        ("                 Different from 'wrong': 'wrong' means we misread the paper,", False),
        ("                 'not-in-paper' means we made it up. Keep them apart.", False),
        ("  unclear        ambiguous, or you cannot tell from what you have", False),
        ("", False),
        ("IF YOU FIND AN ERROR", True),
        ("Write it down and move on. Do not go and correct the database or any other", False),
        ("spreadsheet - the point is to count how often the extraction is wrong.", False),
        ("If you think the FIELD DEFINITION is wrong rather than the value, say so in", False),
        ("the note.", False),
        ("", False),
        ("START EACH PAPER WITH 'paper_identity'", True),
        ("The first row of every paper asks whether the PDF is really that paper.", False),
        ("Check title, authors and year on page 1. If it is the wrong paper, stop", False),
        ("there, mark the remaining fields 'unclear', and say so in the note.", False),
        ("", False),
        ("FIELD CLASSES", True),
        ("  check      the paper-identity check. Do this first.", False),
        ("  core       the 7 fields the project's main numbers rest on. Spend your time", False),
        ("             here. If you only finish part of a paper, finish these.", False),
        ("  secondary  supporting fields. Still checked, lower stakes.", False),
        ("  freetext   prose summaries. Judge whether the paper supports the claim, not", False),
        ("             whether you would have worded it the same way.", False),
        ("", False),
        ("WHERE TO LOOK THINGS UP", True),
        ("  'field guide' sheet  - what each field means and where in the paper to find it", False),
        ("  'glossary' sheet     - what every allowed value means, plus abbreviations", False),
        ("  'papers' sheet       - the 25 papers at a glance", False),
        ("", False),
        ("Roughly 15-25 minutes per paper. You do not need to read the whole paper -", False),
        ("abstract, setup, results and the reference list carry almost everything.", False),
        ("", False),
        ("If in doubt, mark 'unclear' and write what confused you. An honest 'unclear'", False),
        ("is useful. A confident guess is not.", False),
    ]
    for i, (t, b) in enumerate(lines, start=1):
        c = ws.cell(row=i, column=1, value=t)
        if b:
            c.font = Font(bold=True)
    ws.column_dimensions["A"].width = 90

    wsg = wb.create_sheet("field guide")
    sheet_header(wsg, ["field", "class", "what it means", "allowed values",
                       "where to look", "watch out for"])
    for f in ["paper_identity"] + FIELDS:
        wsg.append(list((f,) + GUIDE[f]))
    for col, w in zip("ABCDEF", [28, 11, 56, 46, 34, 60]):
        wsg.column_dimensions[col].width = w
    for row in wsg.iter_rows():
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    for r in range(2, wsg.max_row + 1):
        wsg.row_dimensions[r].height = 76
    wsg.freeze_panes = "A2"

    wsgl = wb.create_sheet("glossary")
    sheet_header(wsgl, ["term", "meaning", "group"])
    for t, m, g in GLOSSARY:
        wsgl.append([t, m, g])
        if m == "" and t:
            wsgl.cell(row=wsgl.max_row, column=1).font = Font(bold=True)
    for col, w in zip("ABC", [34, 96, 14]):
        wsgl.column_dimensions[col].width = w
    for row in wsgl.iter_rows():
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    wsgl.freeze_panes = "A2"

    ws2 = wb.create_sheet("papers")
    sheet_header(ws2, ["#", "title", "year", "venue", "track", "role",
                       "channel", "consequence", "paper_id"])
    for i, p in enumerate(papers, 1):
        ws2.append([i, p["title"], p["year"], p["venue"], p["track"], p["role"],
                    p["channel"], p["consequence"], p["paper_id"]])
    for col, w in zip("ABCDEFGHI", [4, 78, 6, 36, 10, 9, 14, 22, 42]):
        ws2.column_dimensions[col].width = w
    ws2.freeze_panes = "B2"

    ws3 = wb.create_sheet("coding")
    sheet_header(ws3, ["#", "title", "field", "field_class", "AI_extracted_value",
                       "verdict", "correct_value_if_wrong", "note", "paper_id"])
    vals = {}
    for p in papers:
        row = pe.execute(f"select {', '.join(FIELDS)}, authors from paper "
                         f"where paper_id=?", (p["paper_id"],)).fetchone()
        vals[p["paper_id"]] = dict(zip(FIELDS + ["authors"], row))
    n = 0
    for i, p in enumerate(papers, 1):
        v = vals[p["paper_id"]]
        ws3.append([i, p["title"][:78], "paper_identity", "check",
                    f"{p['title']}  ({v['authors'] or '?'}, {p['year']})"[:500],
                    "", "", "", p["paper_id"]])
        n += 1
        for f in FIELDS:
            cls = ("core" if f in CORE else
                   "secondary" if f in SECONDARY else "freetext")
            x = v.get(f)
            ws3.append([i, p["title"][:78], f, cls,
                        "" if x is None else str(x)[:500], "", "", "",
                        p["paper_id"]])
            n += 1
    for col, w in zip("ABCDEFGHI", [4, 50, 28, 11, 74, 14, 32, 36, 42]):
        ws3.column_dimensions[col].width = w
    ws3.freeze_panes = "C2"
    ws3.auto_filter.ref = f"A1:I{n+1}"
    wb.save(xlsx)

    z = OUT / f"{name}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(xlsx, arcname=xlsx.name)
        for p in papers:
            src = REPO / p["pdf"]
            if src.exists():
                zf.write(src, arcname=f"pdfs/{src.name}")
    return xlsx, z, n


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = json.loads(RANK.read_text())["papers"][: N_PACKETS * PER]
    pe = sqlite3.connect(REPO / "data" / "paper_explorer.db")
    for r in rows:
        r["pdf"] = pe.execute("select pdf_local_path from paper where paper_id=?",
                              (r["paper_id"],)).fetchone()[0]
    # Greedy balanced deal, in rank order: each paper goes to whichever packet
    # still has room and holds the fewest papers of its track, ties broken by
    # the smaller packet. Dealing the flat ranking balanced rank but let track
    # drift (21 Security / 4 ML-AI in one packet against 15/10 in another);
    # dealing within track fixed that but gave packets of 26/25/25/24. This
    # holds every packet at exactly PER while keeping the track mix level.
    import collections as _c
    packets = [[] for _ in range(N_PACKETS)]
    tcount = [_c.Counter() for _ in range(N_PACKETS)]
    for r in rows:
        cand = [i for i in range(N_PACKETS) if len(packets[i]) < PER]
        i = min(cand, key=lambda j: (tcount[j][r["track"]], len(packets[j]), j))
        packets[i].append(r)
        tcount[i][r["track"]] += 1
    for pk in packets:
        pk.sort(key=lambda r: r["rank"])

    for i, pk in enumerate(packets, 1):
        xlsx, z, n = build(i, pk, pe)
        ranks = [p["rank"] for p in pk]
        import collections
        print(f"  packet-{i}: {len(pk)} papers, {n} coding rows, "
              f"{z.stat().st_size/1e6:.1f} MB | ranks {min(ranks)}-{max(ranks)} "
              f"| track {dict(collections.Counter(p['track'] for p in pk))} "
              f"| role {dict(collections.Counter(p['role'] for p in pk))}")
    print(f"\nwrote {N_PACKETS} packets to {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
