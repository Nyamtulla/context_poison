# RQ1 -- Taxonomy Analysis: channel x intent x consequence

Regenerated 2026-10-16 by `scripts/rq1_taxonomy.py` from the current Excel corpus state (929 included papers). Re-run this script any time screening/coding changes.

**RQ1:** Across the full landscape of LLM agent context contamination -- memory, RAG, tool output, tool metadata, skills, multi-agent, cross-modal, supply chain -- which channel x intent (adversarial/incidental) x consequence cells have been studied, and which are empty?

## Headline result

**63.6% of the channel x intent x consequence cube is empty** (103 of 162 cells: 9 channels x 3 intents x 6 consequences).

## Channel totals (both tracks combined)

| Channel | Papers | Share |
|---|---:|---:|
| tool-output | 325 | 35.0% |
| direct-input | 226 | 24.3% |
| RAG | 134 | 14.4% |
| memory | 102 | 11.0% |
| multi-agent | 46 | 5.0% |
| cross-modal | 39 | 4.2% |
| tool-metadata | 33 | 3.6% |
| skill | 14 | 1.5% |
| supply-chain | 10 | 1.1% |

## Consequence totals by track (intent)

| Consequence | Security (Track A) | ML/AI (Track B) | Both |
|---|---:|---:|---:|
| goal-hijack | 476 | 12 | 7 |
| data-exfiltration | 39 | 1 | 0 |
| persistence-backdoor | 20 | 2 | 3 |
| resource-abuse | 8 | 0 | 0 |
| silent-corruption | 15 | 73 | 1 |
| reasoning-corruption | 22 | 248 | 2 |

## Channel x Defense-intervention-point coverage

| Channel | Ingestion | Reasoning | Execution | None |
|---|---:|---:|---:|---:|
| memory | 6 | 47 | 3 | 46 |
| RAG | 25 | 48 | 1 | 60 |
| tool-output | 49 | 53 | 70 | 153 |
| tool-metadata | 5 | 1 | 4 | 23 |
| skill | 1 | 0 | 0 | 13 |
| multi-agent | 3 | 8 | 13 | 22 |
| cross-modal | 6 | 6 | 0 | 27 |
| supply-chain | 3 | 0 | 1 | 6 |
| direct-input | 65 | 60 | 5 | 96 |

## Full 3D cube

### Security

| channel | goal-hijack | data-exfiltration | persistence-backdoor | resource-abuse | silent-corruption | reasoning-corruption |
|---|---:|---:|---:|---:|---:|---:|
| memory | 3 | 2 | 9 | 0 | 0 | 1 |
| RAG | 37 | 10 | 2 | 0 | 8 | 5 |
| tool-output | 264 | 17 | 3 | 6 | 0 | 4 |
| tool-metadata | 27 | 0 | 0 | 1 | 0 | 1 |
| skill | 10 | 0 | 0 | 0 | 0 | 0 |
| multi-agent | 21 | 3 | 0 | 0 | 0 | 2 |
| cross-modal | 23 | 0 | 0 | 0 | 2 | 2 |
| supply-chain | 5 | 0 | 4 | 0 | 1 | 0 |
| direct-input | 86 | 7 | 2 | 1 | 4 | 7 |

### ML/AI

| channel | goal-hijack | data-exfiltration | persistence-backdoor | resource-abuse | silent-corruption | reasoning-corruption |
|---|---:|---:|---:|---:|---:|---:|
| memory | 1 | 1 | 2 | 0 | 5 | 74 |
| RAG | 1 | 0 | 0 | 0 | 49 | 21 |
| tool-output | 8 | 0 | 0 | 0 | 0 | 18 |
| tool-metadata | 0 | 0 | 0 | 0 | 0 | 4 |
| skill | 0 | 0 | 0 | 0 | 0 | 3 |
| multi-agent | 1 | 0 | 0 | 0 | 0 | 18 |
| cross-modal | 1 | 0 | 0 | 0 | 3 | 7 |
| supply-chain | 0 | 0 | 0 | 0 | 0 | 0 |
| direct-input | 0 | 0 | 0 | 0 | 16 | 103 |

### Both

| channel | goal-hijack | data-exfiltration | persistence-backdoor | resource-abuse | silent-corruption | reasoning-corruption |
|---|---:|---:|---:|---:|---:|---:|
| memory | 0 | 0 | 3 | 0 | 1 | 0 |
| RAG | 0 | 0 | 0 | 0 | 0 | 1 |
| tool-output | 5 | 0 | 0 | 0 | 0 | 0 |
| tool-metadata | 0 | 0 | 0 | 0 | 0 | 0 |
| skill | 1 | 0 | 0 | 0 | 0 | 0 |
| multi-agent | 1 | 0 | 0 | 0 | 0 | 0 |
| cross-modal | 0 | 0 | 0 | 0 | 0 | 1 |
| supply-chain | 0 | 0 | 0 | 0 | 0 | 0 |
| direct-input | 0 | 0 | 0 | 0 | 0 | 0 |

## Empty cells by channel

- **memory**: 7 of 18 empty
- **RAG**: 9 of 18 empty
- **tool-output**: 10 of 18 empty
- **tool-metadata**: 14 of 18 empty
- **skill**: 15 of 18 empty
- **multi-agent**: 12 of 18 empty
- **cross-modal**: 11 of 18 empty
- **supply-chain**: 15 of 18 empty
- **direct-input**: 10 of 18 empty

## Methodology / caveats

- `channel`, `consequence`, `track`, and `defense_intervention_point` are already-coded Excel columns (Week-2 batch classification); this script is a pure pivot over them, no new judgment is applied here.
- A corpus re-screening/deduplication pass should be run before this script if the underlying `screening` column may be stale -- see `scripts/dedupe_corpus.py` and `scripts/rescreen_corpus.py`.
