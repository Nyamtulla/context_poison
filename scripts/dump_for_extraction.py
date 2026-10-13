"""Pull the sections that carry the analysis columns, for the 30 unextracted papers.

The seven prose columns live in specific places: models and datasets in the
experimental setup, key_result in the abstract and results, baselines in the
comparison tables, threat_model in its own section or the setup, limitations
where the authors say so. Dumping those rather than the whole paper keeps the
read focused on where the answers actually are.
"""
from __future__ import annotations
import json, pathlib, re, sys
import pymupdf

REPO = pathlib.Path(__file__).resolve().parent.parent
NEED = REPO / "verification" / "needs_fulltext_extraction.json"

SECTS = {
 "abstract":    [r"abstract"],
 "setup":       [r"experimental set-?up", r"experiment(?:s|al)? (?:setup|settings|details)",
                 r"implementation details", r"evaluation setup", r"datasets?",
                 r"experiments?"],
 "threat":      [r"threat model", r"adversary model", r"attack model", r"problem (?:setting|formulation)"],
 "results":     [r"results?(?: and (?:analysis|discussion))?", r"evaluation", r"findings"],
 "limits":      [r"limitations?", r"discussion", r"conclusions?(?: and future work)?"],
}

def grab(txt, pats, limit):
    low = txt.lower()
    for p in pats:
        m = re.search(rf"\n[^\S\n]*(?:[IVXLC]+|\d+)?[.)]?[^\S\n]*{p}\b[^\n]{{0,60}}\n", low)
        if m:
            return txt[m.end(): m.end() + limit].strip()
    return ""

def main():
    idx = int(sys.argv[1]); n = int(sys.argv[2])
    papers = json.loads(NEED.read_text())["papers"][idx: idx + n]
    for p in papers:
        d = pymupdf.open(REPO / p["pdf"])
        full = "\n".join(d[i].get_text() for i in range(d.page_count)); d.close()
        print(f"\n{'='*110}\n### {p['title']}\n   {p['year']} | {p['venue']} | coded channel={p['channel']} consequence={p['consequence']}")
        for name, pats in SECTS.items():
            lim = {"abstract":700,"setup":1100,"threat":600,"results":1100,"limits":650}[name]
            s = grab(full, pats, lim)
            if s:
                clean = re.sub(r"[ \t]+", " ", s)[:lim]
                print("\n--[" + name + "]--\n" + clean)
        # tables often carry baselines/models as bare names
        names = set(re.findall(r"\b(GPT-[\w.]+|Llama-?[\d.]+\w*|Claude[\w\s.-]{0,12}|Gemini[\w.-]*|"
                               r"Mistral[\w.-]*|Qwen[\w.\-]*|DeepSeek[\w.-]*|Vicuna[\w.-]*|"
                               r"BERT[\w-]*|T5|Grok-?\d*|Gemma[\w.-]*)\b", full))
        if names:
            print(f"\n--[model names appearing anywhere]--\n{sorted(names)[:20]}")

if __name__ == "__main__":
    main()
