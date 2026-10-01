# Can we actually run the deliberate causes? (2026-09-30)

Before booking GPU time on the incidental→deliberate transfer, a text-only
check of whether the target attacks can be reconstructed at all. The answer
changed which cell we should run.

## reasoning-corruption — the 7 deliberate causes

| # | cause | verdict | why |
|---|---|---|---|
| 1 | Oracle Poisoning | **substitute only** | Code released, but the evaluation targets a **proprietary 42M-node production knowledge graph** and nine closed models (GPT/Claude/Gemini). No public benchmark. The mechanism is reconstructable on a synthetic KG; the paper's result is not reproducible. |
| 2 | Reasoning Interruption Attack | **runnable** | No code, but fully specified. Dataset is 100 arithmetic prompts + GSM8K — trivially rebuilt. Targets DeepSeek-R1; open R1-distill works. |
| 3 | RAG-manipulation on multi-agent debate | **blocked** | **No PDF, no arXiv id, zero extracted text.** ICETES 2026. We cannot read it, so we cannot reconstruct it. |
| 4 | distraction effect | **not a distinct attack** | This is from **Attention Tracker**, a *defense* paper (`role='both'`). The "distraction effect" is the phenomenon it identifies to build its detector on, not an attack anyone proposed. A registry coding artifact — see below. |
| 5 | incidental prompt injection (pen mark on pathology slides) | **substitute only** | Code released, data public (TCGA/TCIA), but models are Claude 3 Opus / 3.5 Sonnet / GPT-4o. Needs an open VLM substitute. |
| 6 | preemptive answer attack | **already tested** | The 1 of 7 that has a confirmed pair. Trivially reconstructable anyway. |
| 7 | reasoning token overflow (RTO) | **runnable** | Same family as #2. API-only in the paper (R1-671B), reconstructable on open R1-distill. Datasets public. |

**Net: 2 cleanly runnable, 2 only with substitution, 1 blocked, 1 miscoded,
1 already done.** This is a case study, not a cell-wide result.

### The registry question raised by #4

`distraction effect (attention shift to injected instruction)` is registered
as a Security-track mechanism, but its paper is Attention Tracker — a defense
paper that also has a defense registry entry. Counting a defense paper's
explanatory phenomenon as a deliberate cause inflates the deliberate side of
reasoning-corruption from 6 to 7. **Not changed here**: removing a registry
entry moves published counts, and that is the project lead's call.

### A correction to the proposed pairing

The earlier suggestion was to run input-context compressors (ACON,
QwenLong-CPRS, TokenPilot) against #2 and #7. That match is weaker than it
looked: those defenses compress the **input context**, while #2 and #7 exhaust
the model's **own generated reasoning tokens**. Different quantity. Filtering
the 198 incidental reasoning-corruption defenses for ones that manage the
model's own reasoning leaves **7 with code**, and most are long-document or
memory systems rather than reasoning-budget managers. The defense side of this
pairing is thin.

## silent-corruption — the better target

The other way with both deliberate and incidental causes. Three deliberate
causes have never had a defense tested against them, and they check out far
better:

| cause | venue | artifacts | models | verdict |
|---|---|---|---|---|
| gradient-based corpus poisoning (adversarial passage injection) | **EMNLP 2023** | **released** | Contriever, Contriever-ms, DPR-nq, DPR-mul — all open | **runnable, fully local** |
| AGGD (Approximate Greedy Gradient Descent) | **ACL 2024** | none | same open retrievers | **reconstructable** — an improvement on the attack above, same setup |
| self-interpreting adversarial images | **USENIX Security 2024** | **released** | MiniGPT-4, LLaVA, InstructBLIP — all open-weight | **runnable, fully local** |

Three peer-reviewed attacks at top venues, two with released code, **none
requiring a closed model or private data**. Against 54 incidental-validated
silent-corruption defenses.

And the precedent is exact: RQ6's two completed transfer case studies,
**RobustRAG and FaithfulRAG, are both RAG/silent-corruption**, both found to
transfer *partially, at roughly half strength*. That is a real prior to test,
in the same cell, with the same harness.

## Recommendation

**Run silent-corruption, not reasoning-corruption.** Same experiment, same
claim, but 3 reconstructable targets instead of 2, all peer-reviewed, all on
open weights, and a published half-strength prior from our own RQ6 work to
confirm or break.

Reasoning-corruption is worth returning to only if #2 and #7 are run as a
deliberate pair — reasoning-budget exhaustion is a coherent story on its own,
but its defense side is too thin to call a cell result.
