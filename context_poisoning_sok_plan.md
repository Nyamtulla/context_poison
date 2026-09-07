# SoK: Context Integrity — A Working Plan

**Working title:** *SoK: Context Integrity — Unifying Adversarial and Incidental Contamination of LLM Agent Context Windows*

**Core thesis:** The security literature (indirect prompt injection, tool poisoning, memory/RAG poisoning) and the ML-systems literature (context rot, distractor interference, semantic drift) study the *same underlying failure* — untrustworthy or low-quality content entering the context window and corrupting downstream behavior — as two disconnected fields with an attacker and without one. No existing survey treats these as one construct. That gap is the paper's contribution.

**Secondary organizing axis:** where in the pipeline a trust boundary is (or isn't) reconstructed — detection at ingestion, isolation during reasoning, or verification at execution — rather than organizing defenses by channel (memory defenses, RAG defenses, tool defenses) the way existing SoKs do.

---

## 1. Target venues and realistic timeline

| Venue | Cycle | Registration | Submission | Fit |
|---|---|---|---|---|
| USENIX Security '27 | Cycle 1 | Aug 18, 2026 | Aug 25, 2026 | Too tight — skip |
| IEEE S&P '27 | Cycle 2 | ~Nov 10, 2026 | Nov 17, 2026 | Tight but workable if we start now |
| USENIX Security '27 | Cycle 2 | Jan 19, 2027 | Jan 26, 2027 | **Recommended primary target** |
| ACM CCS '27 | TBA | — | — | Check CFP when posted (CCS '26 cycles already closed) |

Recommendation: write toward **USENIX Security '27 Cycle 2 (Jan 26, 2027)** as the primary deadline, with the S&P Nov 17, 2026 deadline as a stretch goal if the taxonomy and case study converge early. Always verify current dates against the official CFPs before committing — conference deadlines shift.

---

## 2. Proposed paper structure

1. **Introduction** — motivate via OWASP's ASI06 "Memory and Context Poisoning" entry (2026 Agentic AI Top 10) and the volume of 2026 top-venue attack papers as evidence of urgency; state the thesis (adversarial/incidental split is artificial) up front.
2. **Background** — MCP/agent architecture primer; define "context window as shared trust boundary."
3. **Unified taxonomy of contamination sources** (the core novel section) — organize *not* by channel but by two crossed dimensions:
   - **Intent**: adversarial vs. incidental
   - **Delivery vector**: direct input, web/document content, tool output, tool metadata, RAG/retrieval corpus, persistent memory, agent-to-agent/prior-output, cross-modal, skill/prompt-template, supply chain
   This produces a matrix — several cells (e.g., "incidental + tool metadata," "incidental + agent-to-agent") are effectively unstudied and worth flagging explicitly as gaps.
4. **Propagation and persistence** — one-shot vs. dormant/backdoor vs. self-propagating; blast-radius framing (one session vs. many users vs. unbounded spread via shared skills/servers).
5. **Defense landscape reorganized by trust-boundary reconstruction point** (not by channel):
   - *Ingestion-time*: classifiers, provenance tagging, cryptographic tool attestation (ETDI-style)
   - *Reasoning-time*: information-flow control, instruction hierarchies, masked re-execution/comparison (MELON-style)
   - *Execution-time*: capability sandboxing, action confirmation, execution isolation (IsolateGPT-style)
   Show that most current defenses cluster at ingestion-time and are channel-specific; argue (with evidence from the case study) that reconstruction-point defenses generalize better across the intent/vector matrix than channel-specific ones.
6. **Case study / validating evidence** (see Section 4 below) — the demonstrative piece that earns "compelling evidence," not a new-attack paper in miniature.
7. **Open problems** — cross-cell gaps from the matrix, benchmark consistency issues, lack of shared evaluation harness across the adversarial/incidental split.
8. **Conclusion.**

---

## 3. Literature map (papers already identified — expand during lit review)

### Adversarial / security-framed
- Greshake et al. 2023 — foundational indirect prompt injection
- InjecAgent (Zhan et al., 2024) — benchmark, ReAct agents
- AgentDojo (Debenedetti et al., 2024) — realistic attack/defense environment
- MCPTox (Wang et al., AAAI 2026, arXiv:2508.14925) — 45 real MCP servers, 353 tools benchmarked
- MCP-SafetyBench (Zong et al., ICLR 2026, arXiv:2512.15163)
- MCP Security Bench / MSB (Zhang et al., ICLR 2026, arXiv:2510.15994)
- AgentPoison (Chen et al., NeurIPS 2024, arXiv:2407.12784) — memory/RAG backdoor poisoning
- MemoryGraft (Srivastava & He, 2025, arXiv:2512.16962)
- "Hidden in Memory" sleeper memory poisoning (Pulipaka et al., 2026, arXiv:2605.15338)
- Skill-Inject (Schmotz et al., 2026, arXiv:2602.20156) — skill file attacks
- Supply-chain poisoning of coding-agent skill ecosystems (Qu et al., 2026, arXiv:2604.03081)
- Oracle Poisoning — knowledge-graph corruption (arXiv:2605.09822)
- MELON defense (Zhu et al., arXiv:2502.05174)
- Depth-dependent IPI study (Rashidi, arXiv:2605.30686) — injection-depth as dominant variable
- MCP tool poisoning disclosure — Invariant Labs (2025)

### Non-adversarial / "context rot" framed
- Liu et al. 2023 — "lost in the middle," positional degradation
- Chroma research (2026) — context rot across 18 frontier models, coherent-vs-shuffled distractor findings
- Diagnosing/Mitigating Context Rot in Long-Horizon Search (arXiv:2606.29718)
- AttnComp (arXiv:2509.17486) — context compression against irrelevant retrieval noise
- Evaluating RAG under adversarial poisoning (arXiv:2412.16708) — notably already studies adversarial *and* "untouched" (non-adversarial wrong) contexts side by side; closest existing precedent for the unification move

### Existing adjacent SoKs/surveys (differentiate explicitly against each)
- SoK: MCP Ecosystem Security and Safety (arXiv:2512.08290)
- Layered Attack Surface SoK for LLM agents (arXiv:2604.23338)
- Survey on Long-Term Memory Security ("Mnemonic Sovereignty") (arXiv:2604.16548)
- Lifecycle/application-stack survey of LLM vulnerabilities (arXiv:2606.31639)
- Taxonomy and Consistency Analysis of Safety Benchmarks for AI Agents (arXiv:2605.16282)

---

## 4. Proposed case study (the "compelling evidence," not a standalone attack paper)

Design one demonstration that a **channel-specific defense fails to generalize across the intent/vector matrix** — e.g., take a defense built for adversarial tool-output injection (MELON-style re-execution comparison) and show it does *not* catch an incidental contamination case (stale/irrelevant retrieved memory causing the same downstream behavior change), or vice versa. This single experiment does double duty: it's the paper's differentiating empirical contribution *and* direct support for the central taxonomy claim, which is what the SoK format actually rewards (per IEEE S&P/EuroS&P CFP language: "support long-held beliefs... with compelling evidence").

Keep this contained — one clean comparison across 2–3 model families, not a full new benchmark. If it grows into a full benchmark, consider splitting it into a companion empirical paper for an ML venue (AAAI/ICLR/ACL-style), which is where this cluster of work has been landing.

---

## 5. Immediate next steps

1. **Expand the lit review** — target ~60–80 papers total; current list above is a strong start but underweights: cross-modal injection, agent-to-agent propagation empirics, and formal information-flow-control approaches (only loosely covered so far).
2. **Build the intent × vector matrix** as a literal table early — this becomes Figure 1 and the paper's organizing spine. Empty cells are your gap-analysis section for free.
3. **Draft the differentiation paragraph against the 5 adjacent SoKs first**, before writing anything else — if this paragraph doesn't feel convincing, the taxonomy needs more work before drafting begins.
4. **Scope and run the case study** in parallel with lit review, not after — its result may reshape which taxonomy cells you emphasize.
5. **Check official CFPs** for S&P '27 Cycle 2 and USENIX Security '27 Cycle 2 closer to the deadline for any date changes.

