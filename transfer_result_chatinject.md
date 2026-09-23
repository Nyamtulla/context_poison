# Transfer result: detection is framing-dependent, action-checking is not

Generated 2026-09-23 from `data/registries/technique_transfer_chatinject.json`.
Banking suite, Qwen2.5-14B-Instruct, n=32 per condition, every condition run
undefended and defended, verdicts gated on minimum detectable reduction.

## The comparison

Five defense techniques against two attacks on the same substrate — one the
field has tested heavily, one it has barely touched.

| technique | stage | `important_instructions` (15 defenses tested) | `ChatInject` (1 defense tested) |
|---|---|---|---|
| heuristic pattern filter | ingestion | **holds** → 0% | no effect → 37.5% |
| known-answer detection | ingestion | **FAILS** → 43.8% | no effect → 37.5% |
| LLM-as-a-judge | ingestion | **holds** → 0% | no effect → 25.0% |
| **tool-call goal consistency** | **execution** | **holds** → 0% | **holds** → 0% |
| paraphrasing | ingestion | no resolvable effect → 12.5% | **reduces** → 3.1% |

Undefended: 40.6% and 43.8%. Minimum detectable reduction: 30.5pp and 31.0pp.

## Result

**Two ingestion techniques that stop the well-tested attack lose their effect on
the barely-tested one. The execution technique holds on both.**

- The regex filter goes from 0% to 37.5%.
- The LLM judge goes from 0% to 25.0% — a 18.8pp drop that does not clear the
  31.0pp resolvability bar, so it is reported as no effect rather than as a
  partial success.
- Goal consistency drives both to 0%.

## Why, mechanistically

The two attacks pursue the same goal through the same injection point. They
differ only in framing:

- `important_instructions` announces itself — `<INFORMATION>`, "This is an
  important message from me, Emma Johnson". It **looks like** an injected
  instruction, which is exactly what an ingestion detector is looking for.
- `ChatInject` closes the current turn and opens a forged **system** turn. To a
  detector inspecting tool output, the payload does not read as an instruction
  smuggled into data; it reads as system content, which is the one thing a
  detector is least likely to flag.

So ingestion-stage detection is **framing-dependent**: it generalises to attacks
that look like the attacks it was designed against, and fails when the framing
moves. The regex has no pattern for a turn boundary. The judge, asked whether
text contains "instructions aimed at the AI", sees something that presents as
legitimate system configuration.

Goal consistency never inspects the payload. It asks whether the tool call the
agent is about to make serves the user's stated request. That question is
**invariant to how the instruction arrived**, so re-framing the attack does not
help the attacker.

## This points opposite to RQ6's headline

RQ6 concluded that generalization tracks intervention point, with execution-stage
defenses generalizing **least** — 0 of 2 could even be evaluated. This measures
the reverse: the execution technique is the only one that transfers cleanly.

Both can be true of their own evidence, and the confound explains the gap. RQ6's
execution defenses were the ones it could not run, and "could not run" was
recorded as "did not generalize". When an execution-stage technique is actually
executed, it does best — and there is now a mechanism for why: detection depends
on recognising the attack, action-checking does not.

**This is the most direct evidence the project has that RQ6's intervention-point
finding is confounded**, and it inverts the sign rather than merely weakening it.

## The reconstruction-quality threat, measured

The same five attacks, rebuilt twice, screened identically:

| mechanism | v1 ASR | v2 ASR |
|---|---:|---:|
| ChatInject | — | **43.8%** |
| ASPI | 3.1% | 18.8% |
| Agent Data Injection | 3.1% | 12.5% |

Same suite, model, sample size and injection points. **The only variable was how
well the attack was implemented.** v2 keeps each mechanism's distinctive core and
adds the scaffolding AgentDojo's own attack uses — an out-of-band delimiter,
impersonation of the principal, direct address of the model, and framing as a
prerequisite of the user's task.

A six-fold ASR swing from implementation quality alone is a threat to validity
for **every** reconstruction-based result, including RQ6's and this document's:
a reconstructor who writes weak payloads makes every defense look strong. The
mitigation used here is that scaffolding is identical across mechanisms and the
field's own attack is carried as a reference control in every run, so results
are anchored even when a reconstruction underperforms.

## Limits

- **ChatInject is near-transfer, not transfer.** One defense (ClawGuard) is
  recorded against it in RQ5, not zero. The true zero-coverage mechanism, ASPI,
  reached only 18.8% undefended — below resolvability — so the clean transfer
  test is still unrun.
- **One suite, one model, n=32.** The `important_instructions` control has
  measured 46.9%, 40.6%, 37.5% and 27.8% across runs on this configuration.
  Verdicts are gated on resolvability, but point estimates carry wide intervals.
- **Techniques, not artifacts.** These are our implementations of published
  principles; a failure is a failure of the implementation. Named defenses
  abstracted: DataSentinel (known-answer); Task Shield, IPIGuard, PlanGuard,
  AgentArmor (goal consistency).
- **One execution technique.** The intervention-point claim rests on a single
  implementation and should not be read as settled.
