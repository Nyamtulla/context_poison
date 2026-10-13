# Relevance pass over the 31 newly downloaded papers

Read 2026-10-13. Each paper's abstract, introduction and conclusion were read
and judged against `config.yaml`'s screening criteria, not against my own sense
of what belongs.

> **include:** peer-reviewed or arXiv (2023–2026), addresses LLM agents with
> tool use, RAG, memory or multi-step autonomy, AND presents an attack,
> defense, benchmark, or empirical measurement of context contamination or
> context-length/quality degradation.
> **exclude:** pure jailbreaking with no agentic/tool component,
> training-time-only poisoning, non-LLM systems.

## Verdict: 3 excluded, 1 flagged, 27 kept

### Exclude (3)

| paper | why |
|---|---|
| **Verlog: Context-lite Multi-turn RL** | An RL fine-tuning framework. Its customizable memory length is a *training-efficiency* device, not a study of context failure; the contribution is dual-discounting GAE and trajectory truncation. No attack, no defense, no measurement of context contamination. Training-time, not runtime. |
| **IEI-TIA (Industrial Embodied Intelligence)** | A supervisory agent for robotic sorting and palletizing. "Trustworthy" here means the VLA model's action correctness is interpretable, not that its context is protected. Nothing about contamination or degradation. |
| **LLM-PEA (Phishing Email Attacks)** | The LLM is a *classifier of emails*, not an agent with tool use, RAG or memory. Prompt injection appears as one robustness dimension of a phishing detector; there is no agentic context channel for anything to be injected into. |

### Flagged for the project lead (1)

**Evaluating and Exploiting Security Vulnerabilities in LLMs for Offensive
Penetration Testing.** Genuinely borderline. It is largely red-teaming of chat
models (recursive jailbreak, roleplay), which the criteria exclude — but two of
its five vectors are "Memory-Enabled Recursive Exploit" and "Hybrid Agent
Roleplay", which are agentic. It also cites **nothing** in our corpus. My read
is exclude; the call is yours because it turns on how strictly "no agentic/tool
component" is applied.

### Keep (27)

Twenty-three are unambiguous — a defense, attack, benchmark or measurement of
context contamination in an agentic or RAG setting. Highlights worth knowing
about:

- **RAG-Induced Failures in Multi-Agent LLM Debate** — this is the paper
  `reconstructability_check.md` recorded as *"no PDF, no arXiv id, zero
  extracted text. We cannot read it, so we cannot reconstruct it."* We can now
  read it. See the caution below before acting on its citation profile.
- **Temporal Dynamics of Memory Poisoning in Web3-Style LLM Agents** — memory
  poisoning with persistence across sessions; one of the few
  cross-session-dormant attacks in the corpus.
- **s42400-026-00628-w** — formal contagion model for MCP multi-agent swarms;
  a self-propagating mechanism, which the registry has almost none of.
- **Secure by Design (eBay)** — quantitative evaluation of architectural
  defenses against IPI, with an explicit "defense tax" measurement.

Four are **surveys or taxonomies** (Interaction-Centric Cybersecurity Risks;
Multimodal Prompt Injection 4D Taxonomy; Prompting for LLM Security and RAG;
TE009562). They are kept under the project's standing convention —
`rescreening_log.md` kept nine surveys and flagged the policy rather than
deciding it. **The same question applies here and I have not quietly answered
it:** a pure survey presents no attack, defense, benchmark or measurement of
its own. If the policy changes, it affects the whole corpus, not these four.

## Effect on the count

**1,026 → 1,023 included** (1,022 if the flagged paper is dropped).

**This does not get the corpus under 1,000, and reading more papers of this
kind will not either.** These 31 were the ones recovered from the missing-PDF
worklist — the paywalled, low-visibility tail. They were already the most
likely to fail screening, and 27 of 31 passed. A reduction to "well under
1,000" requires re-screening the corpus against *tighter criteria*, which is a
decision about the criteria, not an outcome of reading more carefully.

---

# The citation-outlier rule, and why it would delete real papers

The proposal is: if a paper cites nothing in our corpus, it is an outlier and
can be removed. Having now measured it on 31 papers where we hold the full
text, **the rule does not separate what it is meant to separate.**

Five of the 31 cite nothing in the corpus. Two of them are opposite cases:

**RAG-Induced Failures in Multi-Agent LLM Debate** — its reference list is spam
detection, phishing firewalls, bio-inspired feature selection, and the authors'
own prior work in a different field. A group from outside this literature wrote
a paper inside it without reading it. Here "cites nothing in our corpus" means
what the rule assumes it means.

**Failure-Gated Hierarchical Memory** — its reference list is ALFWorld,
WebShop, a survey of LLM-agent autonomy, a survey of agent memory mechanisms.
That is *exactly the right literature* for a paper about memory pollution in
long-horizon agents. It cites nothing in our corpus because **our corpus does
not contain agent benchmark environments** — ALFWorld and WebShop are not
context-contamination papers. Here "cites nothing in our corpus" is a fact
about our corpus boundary, not about the paper. And the paper is squarely in
scope: memory pollution is the memory × silent-corruption cell.

**One rule, two opposite meanings, no way to tell them apart from the edge
count.** Applied automatically it would delete the second kind.

There is a second, worse problem at corpus scale. `citation_graph_isolates.md`
flagged 118 papers as citing nothing in the corpus *from the Semantic Scholar
edge table*. Matching titles inside the actual PDFs showed **39 of them do cite
it**, one by 27 references. The API's edge coverage was the artifact. Every
measurement above was made from reference lists read out of the PDFs, which is
why it is trustworthy; the corpus-wide version would be made from API edges,
which have a known false-isolate rate of roughly a third.

## What to do instead

1. **Never auto-delete on edge count.** Use it to *rank a reading queue*, which
   is what it is good for.
2. **Read the reference list, not the API.** We hold 1,097 PDFs. Extracting
   reference lists from all of them and matching against corpus titles is cheap
   and gives the real network. The 118 isolates should be re-measured this way
   before anyone acts on them.
3. **Separate the two questions.** "Does it engage the literature?" is a
   *quality* signal. "Is it about our topic?" is a *relevance* signal. The
   first is a fine tie-breaker and a bad filter.
4. If the goal is a corpus small enough to cite, that is a **criteria**
   decision — tighten the inclusion rule and re-screen — not an outlier hunt.
