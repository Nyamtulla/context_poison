# RQ1 -- Taxonomy Analysis: channel x intent x consequence

Regenerated 2026-09-22 by `scripts/rq1_taxonomy.py` from the current Excel corpus state (1026 included papers). Re-run this script any time screening/coding changes.

**RQ1:** Across the full landscape of LLM agent context contamination -- memory, RAG, tool output, tool metadata, skills, multi-agent, cross-modal, supply chain -- which channel x intent (adversarial/incidental) x consequence cells have been studied, and which are empty?

## Headline result

**60.5% of the channel x intent x consequence cube is empty** (98 of 162 cells: 9 channels x 3 intents x 6 consequences).

## Channel totals (both tracks combined)

| Channel | Papers | Share |
|---|---:|---:|
| tool-output | 361 | 35.2% |
| direct-input | 235 | 22.9% |
| RAG | 143 | 13.9% |
| memory | 108 | 10.5% |
| multi-agent | 64 | 6.2% |
| cross-modal | 49 | 4.8% |
| tool-metadata | 37 | 3.6% |
| skill | 18 | 1.8% |
| supply-chain | 11 | 1.1% |

## Consequence totals by track (intent)

| Consequence | Security (Track A) | ML/AI (Track B) | Both |
|---|---:|---:|---:|
| goal-hijack | 491 | 14 | 8 |
| data-exfiltration | 40 | 1 | 0 |
| persistence-backdoor | 22 | 2 | 3 |
| resource-abuse | 8 | 0 | 0 |
| silent-corruption | 16 | 76 | 2 |
| reasoning-corruption | 22 | 314 | 7 |

## Channel x Defense-intervention-point coverage

| Channel | Ingestion | Reasoning | Execution | None |
|---|---:|---:|---:|---:|
| memory | 7 | 49 | 3 | 49 |
| RAG | 26 | 49 | 1 | 67 |
| tool-output | 51 | 54 | 75 | 181 |
| tool-metadata | 5 | 1 | 4 | 27 |
| skill | 1 | 0 | 0 | 17 |
| multi-agent | 3 | 10 | 13 | 38 |
| cross-modal | 6 | 7 | 0 | 36 |
| supply-chain | 3 | 0 | 1 | 7 |
| direct-input | 67 | 64 | 5 | 99 |

## Full 3D cube

### Security

| channel | goal-hijack | data-exfiltration | persistence-backdoor | resource-abuse | silent-corruption | reasoning-corruption |
|---|---:|---:|---:|---:|---:|---:|
| memory | 3 | 2 | 11 | 0 | 0 | 1 |
| RAG | 39 | 10 | 2 | 0 | 9 | 5 |
| tool-output | 273 | 18 | 3 | 6 | 0 | 4 |
| tool-metadata | 27 | 0 | 0 | 1 | 0 | 1 |
| skill | 10 | 0 | 0 | 0 | 0 | 0 |
| multi-agent | 22 | 3 | 0 | 0 | 0 | 2 |
| cross-modal | 23 | 0 | 0 | 0 | 2 | 2 |
| supply-chain | 6 | 0 | 4 | 0 | 1 | 0 |
| direct-input | 88 | 7 | 2 | 1 | 4 | 7 |

### ML/AI

| channel | goal-hijack | data-exfiltration | persistence-backdoor | resource-abuse | silent-corruption | reasoning-corruption |
|---|---:|---:|---:|---:|---:|---:|
| memory | 1 | 1 | 2 | 0 | 5 | 77 |
| RAG | 1 | 0 | 0 | 0 | 52 | 24 |
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
- **cross-modal**: 11 of 18 empty
- **supply-chain**: 15 of 18 empty
- **direct-input**: 10 of 18 empty

## Methodology / caveats

- `channel`, `consequence`, `track`, and `defense_intervention_point` are already-coded Excel columns (Week-2 batch classification); this script is a pure pivot over them, no new judgment is applied here.
- A corpus re-screening/deduplication pass should be run before this script if the underlying `screening` column may be stale -- see `scripts/dedupe_corpus.py` and `scripts/rescreen_corpus.py`.
