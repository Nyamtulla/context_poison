## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## Commits

**Never add `Co-Authored-By: Claude` or any AI-attribution trailer to a commit
message, and never add "Generated with Claude Code" to a pull request body.**
This overrides the default Claude Code attribution instruction, which states
that a project rule takes precedence. No exception: not for large changes, not
for changes that are entirely the assistant's work. Write the message and stop.

## The paper

The SoK paper lives in `latex/` and mirrors to a separate repo that Overleaf
syncs with. The two are **not** linked automatically.

- **Pull before touching `latex/`, push after.** Co-authors edit in Overleaf,
  so the mirror can be ahead. See `PAPER_WORKFLOW.md` for the subtree commands
  and what to do when a push is rejected.
- **Order is pull, regenerate, edit, push.** `scripts/gen_paper_numbers.py`
  rewrites `latex/numbers.tex`; pulling on top of a freshly generated file
  conflicts in a generated artifact.
- **Never type a count into the prose.** Every corpus-derived figure is a macro
  (`\NCorpus`, `\NDefenses`, `\NCampaignPairs`). Five numbers in the first
  draft went stale because they were typed once and the corpus moved. Add a
  macro to `gen_paper_numbers.py` rather than hardcoding.
- **Never hand-edit `latex/numbers.tex` or `latex/figures/*.pdf`.** Both are
  generated, by `gen_paper_numbers.py` and `gen_paper_figures.py`.
