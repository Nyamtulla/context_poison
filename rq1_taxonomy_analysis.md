# RQ1 -- Taxonomy Analysis: channel x intent x consequence

Regenerated 2026-10-23 by `scripts/rq1_taxonomy.py` from the current Excel corpus state (929 included papers). Re-run this script any time screening/coding changes.

**RQ1:** Across the full landscape of LLM agent context contamination -- memory, RAG, tool output, tool metadata, skills, multi-agent, cross-modal, supply chain -- which channel x intent (adversarial/incidental) x consequence cells have been studied, and which are empty?

## Headline result

**64.8% of the channel x intent x consequence cube is empty** (105 of 162 cells: 9 channels x 3 intents x 6 consequences).

## Channel totals (both tracks combined)

| Channel | Papers | Share |
|---|---:|---:|
| tool-output | 239 | 25.7% |
| direct-input | 223 | 24.0% |
| memory | 146 | 15.7% |
| RAG | 142 | 15.3% |
| cross-modal | 42 | 4.5% |
| multi-agent | 33 | 3.6% |
| tool-metadata | 24 | 2.6% |
| skill | 19 | 2.0% |
| supply-chain | 9 | 1.0% |

## Consequence totals by track (intent)

| Consequence | Security (Track A) | ML/AI (Track B) | Both |
|---|---:|---:|---:|
| goal-hijack | 419 | 7 | 0 |
| data-exfiltration | 56 | 4 | 0 |
| persistence-backdoor | 23 | 2 | 0 |
| resource-abuse | 1 | 0 | 0 |
| silent-corruption | 62 | 193 | 0 |
| reasoning-corruption | 6 | 121 | 0 |

## Channel x Defense-intervention-point coverage

| Channel | Ingestion | Reasoning | Execution | None |
|---|---:|---:|---:|---:|
| memory | 20 | 60 | 3 | 63 |
| RAG | 25 | 55 | 3 | 59 |
| tool-output | 43 | 36 | 53 | 107 |
| tool-metadata | 5 | 1 | 1 | 17 |
| skill | 1 | 0 | 3 | 15 |
| multi-agent | 2 | 6 | 8 | 17 |
| cross-modal | 8 | 5 | 1 | 28 |
| supply-chain | 2 | 0 | 2 | 5 |
| direct-input | 52 | 55 | 12 | 104 |

## Full 3D cube

### security

| channel | goal-hijack | data-exfiltration | persistence-backdoor | resource-abuse | silent-corruption | reasoning-corruption |
|---|---:|---:|---:|---:|---:|---:|
| memory | 2 | 0 | 14 | 0 | 0 | 2 |
| RAG | 23 | 13 | 2 | 0 | 28 | 0 |
| tool-output | 170 | 18 | 2 | 0 | 6 | 0 |
| tool-metadata | 17 | 1 | 0 | 0 | 0 | 0 |
| skill | 13 | 3 | 1 | 0 | 0 | 0 |
| multi-agent | 11 | 3 | 0 | 0 | 5 | 0 |
| cross-modal | 23 | 0 | 0 | 0 | 6 | 1 |
| supply-chain | 3 | 1 | 2 | 0 | 1 | 0 |
| direct-input | 122 | 15 | 2 | 1 | 16 | 2 |

### safety

| channel | goal-hijack | data-exfiltration | persistence-backdoor | resource-abuse | silent-corruption | reasoning-corruption |
|---|---:|---:|---:|---:|---:|---:|
| memory | 1 | 2 | 2 | 0 | 56 | 63 |
| RAG | 0 | 0 | 0 | 0 | 73 | 3 |
| tool-output | 2 | 1 | 0 | 0 | 8 | 21 |
| tool-metadata | 0 | 0 | 0 | 0 | 0 | 6 |
| skill | 1 | 0 | 0 | 0 | 1 | 0 |
| multi-agent | 1 | 0 | 0 | 0 | 4 | 9 |
| cross-modal | 1 | 0 | 0 | 0 | 7 | 4 |
| supply-chain | 0 | 0 | 0 | 0 | 1 | 0 |
| direct-input | 1 | 1 | 0 | 0 | 42 | 14 |

### Both

| channel | goal-hijack | data-exfiltration | persistence-backdoor | resource-abuse | silent-corruption | reasoning-corruption |
|---|---:|---:|---:|---:|---:|---:|
| memory | 0 | 0 | 0 | 0 | 0 | 0 |
| RAG | 0 | 0 | 0 | 0 | 0 | 0 |
| tool-output | 0 | 0 | 0 | 0 | 0 | 0 |
| tool-metadata | 0 | 0 | 0 | 0 | 0 | 0 |
| skill | 0 | 0 | 0 | 0 | 0 | 0 |
| multi-agent | 0 | 0 | 0 | 0 | 0 | 0 |
| cross-modal | 0 | 0 | 0 | 0 | 0 | 0 |
| supply-chain | 0 | 0 | 0 | 0 | 0 | 0 |
| direct-input | 0 | 0 | 0 | 0 | 0 | 0 |

## Empty cells by channel

- **memory**: 10 of 18 empty
- **RAG**: 12 of 18 empty
- **tool-output**: 10 of 18 empty
- **tool-metadata**: 15 of 18 empty
- **skill**: 13 of 18 empty
- **multi-agent**: 12 of 18 empty
- **cross-modal**: 12 of 18 empty
- **supply-chain**: 13 of 18 empty
- **direct-input**: 8 of 18 empty

## Methodology / caveats

- `channel`, `consequence`, `track`, and `defense_intervention_point` are already-coded Excel columns (Week-2 batch classification); this script is a pure pivot over them, no new judgment is applied here.
- A corpus re-screening/deduplication pass should be run before this script if the underlying `screening` column may be stale -- see `scripts/dedupe_corpus.py` and `scripts/rescreen_corpus.py`.
