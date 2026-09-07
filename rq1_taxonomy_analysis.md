# RQ1 -- Taxonomy Analysis: channel x intent x consequence

Regenerated 2026-08-18 by `scripts/rq1_taxonomy.py` from the current Excel corpus state (886 included papers). Re-run this script any time screening/coding changes.

**RQ1:** Across the full landscape of LLM agent context contamination -- memory, RAG, tool output, tool metadata, skills, multi-agent, cross-modal, supply chain -- which channel x intent (adversarial/incidental) x consequence cells have been studied, and which are empty?

## Headline result

**63.6% of the channel x intent x consequence cube is empty** (103 of 162 cells: 9 channels x 3 intents x 6 consequences).

## Channel totals (both tracks combined)

| Channel | Papers | Share |
|---|---:|---:|
| tool-output | 335 | 37.8% |
| direct-input | 157 | 17.7% |
| RAG | 125 | 14.1% |
| memory | 107 | 12.1% |
| multi-agent | 63 | 7.1% |
| tool-metadata | 38 | 4.3% |
| cross-modal | 37 | 4.2% |
| skill | 18 | 2.0% |
| supply-chain | 6 | 0.7% |

## Consequence totals by track (intent)

| Consequence | Security (Track A) | ML/AI (Track B) | Both |
|---|---:|---:|---:|
| goal-hijack | 391 | 14 | 8 |
| data-exfiltration | 26 | 1 | 0 |
| persistence-backdoor | 19 | 2 | 3 |
| resource-abuse | 7 | 0 | 0 |
| silent-corruption | 9 | 73 | 2 |
| reasoning-corruption | 11 | 313 | 7 |

## Channel x Defense-intervention-point coverage

| Channel | Ingestion | Reasoning | Execution | None |
|---|---:|---:|---:|---:|
| memory | 7 | 49 | 3 | 48 |
| RAG | 22 | 43 | 0 | 60 |
| tool-output | 43 | 49 | 73 | 170 |
| tool-metadata | 5 | 1 | 4 | 28 |
| skill | 1 | 0 | 0 | 17 |
| multi-agent | 3 | 10 | 12 | 38 |
| cross-modal | 4 | 5 | 0 | 28 |
| supply-chain | 2 | 0 | 0 | 4 |
| direct-input | 41 | 53 | 2 | 61 |

## Full 3D cube

### Security

| channel | goal-hijack | data-exfiltration | persistence-backdoor | resource-abuse | silent-corruption | reasoning-corruption |
|---|---:|---:|---:|---:|---:|---:|
| memory | 3 | 1 | 11 | 0 | 0 | 1 |
| RAG | 32 | 7 | 2 | 0 | 7 | 3 |
| tool-output | 251 | 15 | 3 | 6 | 0 | 3 |
| tool-metadata | 28 | 0 | 0 | 1 | 0 | 1 |
| skill | 10 | 0 | 0 | 0 | 0 | 0 |
| multi-agent | 21 | 3 | 0 | 0 | 0 | 2 |
| cross-modal | 15 | 0 | 0 | 0 | 0 | 0 |
| supply-chain | 5 | 0 | 1 | 0 | 0 | 0 |
| direct-input | 26 | 0 | 2 | 0 | 2 | 1 |

### ML/AI

| channel | goal-hijack | data-exfiltration | persistence-backdoor | resource-abuse | silent-corruption | reasoning-corruption |
|---|---:|---:|---:|---:|---:|---:|
| memory | 1 | 1 | 2 | 0 | 5 | 77 |
| RAG | 1 | 0 | 0 | 0 | 49 | 23 |
| tool-output | 9 | 0 | 0 | 0 | 0 | 43 |
| tool-metadata | 1 | 0 | 0 | 0 | 0 | 5 |
| skill | 0 | 0 | 0 | 0 | 0 | 6 |
| multi-agent | 1 | 0 | 0 | 0 | 0 | 32 |
| cross-modal | 1 | 0 | 0 | 0 | 3 | 17 |
| supply-chain | 0 | 0 | 0 | 0 | 0 | 0 |
| direct-input | 0 | 0 | 0 | 0 | 16 | 110 |

### Both

| channel | goal-hijack | data-exfiltration | persistence-backdoor | resource-abuse | silent-corruption | reasoning-corruption |
|---|---:|---:|---:|---:|---:|---:|
| memory | 0 | 0 | 3 | 0 | 2 | 0 |
| RAG | 0 | 0 | 0 | 0 | 0 | 1 |
| tool-output | 5 | 0 | 0 | 0 | 0 | 0 |
| tool-metadata | 1 | 0 | 0 | 0 | 0 | 1 |
| skill | 1 | 0 | 0 | 0 | 0 | 1 |
| multi-agent | 1 | 0 | 0 | 0 | 0 | 3 |
| cross-modal | 0 | 0 | 0 | 0 | 0 | 1 |
| supply-chain | 0 | 0 | 0 | 0 | 0 | 0 |
| direct-input | 0 | 0 | 0 | 0 | 0 | 0 |

## Empty cells by channel

- **memory**: 7 of 18 empty
- **RAG**: 9 of 18 empty
- **tool-output**: 10 of 18 empty
- **tool-metadata**: 11 of 18 empty
- **skill**: 14 of 18 empty
- **multi-agent**: 11 of 18 empty
- **cross-modal**: 13 of 18 empty
- **supply-chain**: 16 of 18 empty
- **direct-input**: 12 of 18 empty

## Methodology / caveats

- `channel`, `consequence`, `track`, and `defense_intervention_point` are already-coded Excel columns (Week-2 batch classification); this script is a pure pivot over them, no new judgment is applied here.
- A corpus re-screening/deduplication pass should be run before this script if the underlying `screening` column may be stale -- see `scripts/dedupe_corpus.py` and `scripts/rescreen_corpus.py`.
