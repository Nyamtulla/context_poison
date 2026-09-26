# The full defense × attack matrix

Generated 2026-09-25 from `data/registries/technique_transfer_full_banking.json`.
8 defenses × 7 attacks = **56 conditions, 1,440 agent episodes**. Banking suite,
Qwen2.5-14B-Instruct, n=32 per condition, every condition run undefended and
defended, verdicts gated on the minimum detectable reduction at n=32.

The 7 attacks are every attack, of 21 screened, that reached an undefended
attack-success rate strong enough for a defense verdict to be resolvable
(`benchmark_coverage` for the screen).

## The matrix

`HOLD` drove ASR to 0 with a resolvable drop · `red.` resolvable reduction ·
`FAIL` no reduction at all · `--` drop too small to resolve at n=32

| defense | stage | II | II no-names | II no-model | II no-user | II wrong-model | II wrong-user | **ChatInject** |
|---|---|---|---|---|---|---|---|---|
| **goal consistency** | execution | HOLD | HOLD | HOLD | HOLD | HOLD | HOLD | **HOLD** |
| heuristic filter | ingestion | HOLD | HOLD | HOLD | HOLD | HOLD | HOLD | -- |
| LLM-as-a-judge | ingestion | HOLD | HOLD | HOLD | HOLD | HOLD | HOLD | -- |
| paraphrasing | ingestion | -- | HOLD | HOLD | red. | -- | HOLD | red. |
| transformers PI detector | ingestion | red. | -- | red. | -- | -- | HOLD | **HOLD** |
| known-answer detection | ingestion | FAIL | FAIL | -- | FAIL | FAIL | FAIL | -- |
| Spotlighting | ingestion | -- | -- | -- | -- | FAIL | FAIL | FAIL |
| repeat user prompt | reasoning | -- | -- | -- | -- | -- | -- | FAIL |

Across all 56 conditions: 24 hold, 4 reduce, 19 show no resolvable effect,
9 fail outright.

## Result 1 — one defense works everywhere, and it is the one that ignores the payload

**Goal consistency holds on 7 of 7.** It is the only technique that does.

It is also the only technique that never inspects the attack text. It asks
whether the tool call the agent is about to make serves the user's stated
request. Every other technique on this list is trying to recognise an attack;
this one is checking an action.

That distinction predicts the whole table. The two best detectors — the regex
filter and the LLM judge — hold on **6 of 7** and fail on exactly one: ChatInject,
the attack whose framing was designed to not look like an attack. They generalise
across everything that *resembles* what they were built for, and stop at the
thing that does not.

## Result 2 — three of eight defenses never worked on anything

**Known-answer detection: 0 of 7.** Five outright failures. This is
DataSentinel's principle, which RQ6 rated *full generalization*.

**Spotlighting: 0 of 7.** A published, well-known defense and an RQ4 registry
entry. Three outright failures, four unresolvable. Worth stating carefully: this
is AgentDojo's implementation, which does not run at all in stock 0.1.33 (see
`agentdojo_defense_compat.py`) — these are the first numbers it has produced
here, and a different implementation could do better.

**Repeat-user-prompt: 0 of 7.** The sandwich baseline. No resolvable effect on
any attack.

Three of eight published defense ideas, measured on a benchmark they can all run
on, produced nothing measurable against any attack that lands.

## Result 3 — detectors have complementary blind spots

The trained classifier (`transformers_pi_detector`, ProtectAI DeBERTa) runs
**opposite** to the prompt-based detectors:

| | 6 `important_instructions` variants | ChatInject |
|---|---|---|
| heuristic filter | holds 6/6 | no effect |
| LLM judge | holds 6/6 | no effect |
| **trained classifier** | **holds 1/6** | **holds** |

The prompt-based detectors catch the polite authority framing and miss the forged
system turn. The trained classifier does the reverse. Neither is strictly better,
and a deployment running only one has a blind spot the other would cover — which
is an argument for composition that the single-defense evaluation convention
cannot surface.

## Result 4 — impersonation detail does not matter, to attacker or defender

The six ablations remove or corrupt the attack's impersonation: the model's name,
the user's name, or both. For every defense, behaviour is near-identical across
all six (goal consistency 6/6, heuristic filter 6/6, LLM judge 6/6, known-answer
0/6, Spotlighting 0/6, repeat-user 0/6).

So the names are not what makes the attack work, and not what the detectors key
on. The **authority structure** — an out-of-band delimiter and a claim that the
instruction is a prerequisite of the user's own task — carries the effect. An
attacker does not need to know who the user is.

## Limits

- **One suite, one model, n=32.** `important_instructions` has measured 46.9%,
  40.6%, 37.5%, 34.4% and 27.8% undefended across five runs on this exact
  configuration. Verdicts are gated on resolvability precisely because point
  estimates move this much; `HOLD` means "reduction larger than n=32 can
  resolve", not "zero in general".
- **Five of eight defenses are our implementations** of published principles.
  A failure is a failure of the implementation. Spotlighting, the PI detector
  and repeat-user-prompt are AgentDojo's own code.
- **`tool_filter` could not be run at all** — it requires an OpenAI model. A
  ninth defense, excluded for a reason unrelated to whether it works.
- **One execution-stage technique.** The strongest claim in this document rests
  on a single implementation and should not be read as settled.
- **19 of 56 cells are unresolvable at n=32.** They are reported as such rather
  than as successes or failures.
