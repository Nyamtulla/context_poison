# Context Integrity SoK — MCP server

Query the distilled output of this project's ~1000-paper systematic review
(1,008 screened papers, 183 named pollution mechanisms, 479 confirmed
defenses, 190 confirmed defense×mechanism test pairs) conversationally, from
your own Claude — no need to open the Excel workbook or the JSON registries
by hand.

Runs entirely offline against files already committed in this repo
(`data/exports/`, `data/registries/`, the `rq*.md` writeups). No API key,
no network access, and no write access to the repo.

## Setup

```bash
cd mcp_server
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

## Add it to your Claude

**Claude Code** — add to `.mcp.json` at the repo root (create it if it
doesn't exist):

```json
{
  "mcpServers": {
    "context-integrity-sok": {
      "command": "/absolute/path/to/context_sok/mcp_server/.venv/bin/python3",
      "args": ["/absolute/path/to/context_sok/mcp_server/server.py"]
    }
  }
}
```

**Claude Desktop** — add the same block under `mcpServers` in your
`claude_desktop_config.json` (Settings → Developer → Edit Config), then
restart the app.

Use absolute paths in both cases — replace `/absolute/path/to/context_sok`
with wherever you cloned this repo.

## What you can ask it

- `get_stats` — headline counts, a good first call.
- `list_papers(query=..., track=..., channel=..., consequence=...)` — search
  the full corpus; `get_paper(paper_id)` for the full extracted record
  (key result, baselines compared, technical summary, stated limitations).
- `list_mechanisms(...)` / `list_defenses(...)` — the RQ3/RQ4 registries,
  each already annotated with how many defenses/mechanisms it's confirmed
  matched against.
- `get_coverage_for_mechanism(name)` / `get_coverage_for_defense(name)` —
  the RQ5 matrix, one entity at a time, with the original justification
  text for each match.
- `list_uncovered_mechanisms(...)` — the 116 mechanisms nothing has ever
  been tested against; a ready-made gap list.
- `get_rq_summary("RQ1"..."RQ6")` — the plain-language headline finding for
  any research question, pulled straight from the corresponding writeup.

In practice: just ask your Claude something like *"what mechanisms has
DataFilter been tested against?"* or *"what's the RQ6 finding?"* — it will
call the right tool.

## Data freshness

The server loads everything into memory once at startup from the repo's
`data/` files. If those files change (e.g. after re-running the
`rebuild-corpus` skill), restart the server / restart your Claude session
for the update to take effect.
