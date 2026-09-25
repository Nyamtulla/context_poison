# Differentiation: this SoK against the five closest

Generated 2026-09-25. All five comparators are inside our own corpus, so their
scope, method and citation behaviour are coded by the same scheme applied to
every other paper — the comparison is drawn from the dataset, not from reading
impressions.

## The five closest

| # | paper | year | cites | scope |
|---|---|---|---:|---|
| 1 | **The Landscape of Prompt Injection Threats in LLM Agents** (2602.10453) | 2026 | 21 | prompt injection against agents |
| 2 | **SoK: The Attack Surface of Agentic AI** (2603.22928) | 2026 | 10 | tools, RAG, autonomy |
| 3 | **SoK: Security and Safety in the Model Context Protocol** (2512.08290) | 2025 | 17 | MCP ecosystem |
| 4 | **A Survey on Long-Term Memory Security in LLM Agents** (2604.16548) | 2026 | 8 | agent long-term memory |
| 5 | **Knowledge Conflicts for LLMs: A Survey** (2403.08319) | 2024 | **314** | context–memory conflict (ML side) |

## Comparison

| | 1. PI Landscape | 2. Attack Surface | 3. MCP | 4. Memory | 5. Knowledge Conflicts | **ours** |
|---|---|---|---|---|---|---|
| papers reviewed | 78 | ~40 | not stated | not stated | not stated | **1,026** |
| attacks catalogued | 37 | — | 7 categories | — | 3 conflict types | **223 named** |
| defenses catalogued | 41 | — | — | — | — | **534 named** |
| attack×defense pairs from the literature | — | — | — | — | — | **332** |
| runs its own experiments | **yes** (9 def × 5 atk) | no | no | no | no | **yes** |
| introduces a benchmark | yes (AgentPI) | no | no | no | no | no |
| covers the **incidental** literature | no | no | no | no | yes (only) | **yes (both)** |
| cites across the divide | **no** | no | yes | no | **no** | n/a |

## Where we are not different

**Comparator 1 is genuinely close and should be cited as such.** It is a
systematic review (78 papers), it builds a taxonomy, *and* it runs an empirical
evaluation of 9 defenses against 5 attacks, reporting a
trustworthiness–utility–latency trilemma. "We run experiments and surveys don't"
is not available to us as a distinction against this paper, and claiming it
would be false.

Our empirical work differs in question, not in existence: they ask *how do
defenses trade off against context-aware attacks* on a benchmark they built;
we ask *does a defense proven against one threat model transfer to another*,
selecting pairs from a coverage matrix rather than choosing them in advance.

## Where we are different, in order of strength

**1. Two literatures under one protocol.** Every comparator is single-track.
Four are security-only; comparator 5 is ML-only. Nobody has run one search,
screening and extraction protocol across both, which is the move the
central claim requires.

The evidence is the comparators' own citation behaviour, coded in our corpus:

| paper | cites security work | cites incidental-degradation work |
|---|---|---|
| Knowledge Conflicts (314 cites, ML side) | **no** | yes |
| PI Landscape (closest security competitor) | yes | **no** |
| Attack Surface SoK | yes | **no** |
| Memory Security survey | yes | **no** |
| MCP SoK | yes | yes |

**The most-cited survey of context–memory conflict does not cite the security
literature, and the closest security SoK does not cite the degradation
literature.** Four of five sit on one side of a divide they do not mention. That
is RQ2's claim, visible in the comparators themselves.

**2. Scale, and what scale buys.** 1,026 papers against 78 and ~40. The point is
not size for its own sake: a 78-paper review cannot produce a 223 × 534 coverage
matrix, and the coverage matrix is what makes "2.8% of defenses were ever
validated against both threat models" a measurement rather than an impression.

**3. Measurements nobody else has made.** Each is a number, reproducible from
the repo:
- **2.8%** of 534 defenses validated against both threat models — and unmoved
  when 55 defenses including the field's foundations were added.
- **131** named attacks with no defense ever tested against them.
- **42.6%** of attacks evaluated on a substrate no one else can reuse; the most
  shared substrate covers **11.7%**; **78%** of substrates are used once.
- **0 of 16** corpus mechanisms reach a readable control on the standard agent
  benchmark.

**4. A disconfirmed prediction of our own.** We predicted that recovering the
field's missing foundational papers would close the coverage gap, imported 164
of them, and it did not move. No comparator tests its own central claim against
a prediction that could have failed.

## How to use this

State comparator 1 as the nearest work early and precisely, including its
empirical component. Claiming novelty over it on "we ran experiments" invites
the obvious rebuttal. The defensible claims are the cross-literature protocol,
the scale that makes the coverage matrix possible, and the four measurements
above — none of which any comparator reports.

## Provenance

All five are corpus rows 45, 44, 39, 41 and 1003. Scope, citation counts and
cross-track citation flags come from the coded dataset
(`data/exports/paper_dashboard_source.xlsx`); our own figures from
`src/registry_source.py`. Cross-track flags are automated classifications and
carry the caveat recorded in RQ2's threats-to-validity.
