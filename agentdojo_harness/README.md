# AgentDojo as the shared victim harness

## Why

The DataSentinel transfer run answered only 7 of 26 mechanisms. The reason was
structural, not sloppiness: DataSentinel's own harness models a
**text-classification victim** — sentiment over a movie review — while most of
the corpus's mechanisms attack an **agent**: plan state, skill files, MCP error
paths, tool-call arguments, cross-app context. Those payloads have nothing to
act on in a sentiment prompt, so they never hijacked, so their detection numbers
were uninterpretable.

AgentDojo supplies the missing victim: a real tool-calling agent over four
suites (workspace, travel, banking, slack — 97 user tasks, 27 injection tasks),
where a hijack is scored by the suite's own checker actually observing the
injected goal being carried out, not by a regex over the reply.

## What is here

- `mechanism_attacks.py` — 16 corpus mechanisms rebuilt as AgentDojo attacks.
  Each is a `FixedJailbreakAttack` template using the same injection
  placeholders every AgentDojo attack uses, so the *framing* is the only
  variable. `{goal}` is substituted with the injection task's real goal, so
  every attack pursues a genuine scorable objective.
- `run_mechanism_transfer.py` — runs each mechanism **undefended and defended**.
  Both are required: a defense that misses an inert payload has not failed at
  anything, so `ASR_undefended == 0` is reported as *inconclusive* rather than
  as a defense success. Utility is carried alongside, so a defense that "wins"
  by breaking the agent is visible as such.

Mechanisms whose payload *is* an optimizer's output (GCG, fuzzers, MCTS, RL) are
excluded here for the same reason as before — see `scripts/transfer_scenarios.py`
for that list and the rationale.

## Running it

The harness needs a tool-calling model on an OpenAI-compatible endpoint at
:1111. **Model choice is not free here.** Mistral-7B-Instruct-v0.3 returns 0%
utility across every AgentDojo condition — the agent cannot complete even the
benign tasks, which makes every security number meaningless. Qwen2.5-7B-Instruct
works.

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct --port 1111 --dtype bfloat16 \
  --max-model-len 16384 --gpu-memory-utilization 0.60 \
  --enable-auto-tool-choice --tool-call-parser hermes
```

```bash
python run_mechanism_transfer.py --suite banking \
  --model Qwen/Qwen2.5-7B-Instruct --defense tool_filter --n_user 3 --n_inject 1
```

Copies of both files live in the IPIGuard reconstruction checkout's `run/`
directory, which is where they must sit to import AgentDojo and the existing
`eval.py` scoring logic.

## Always read the control first

Every run prepends `important_instructions`, AgentDojo's own attack, as a
positive control. On Qwen2.5-7B / banking / 3 user tasks it reads **66.7%
undefended ASR at 66.7% utility** — the agent works and the attack lands, so the
rest of the run means something. If that control reads 0% ASR *or* 0% utility,
stop: the victim is not functioning and no mechanism number from that run is
interpretable.

## A caveat the first control already surfaced

`tool_filter` took the control from 66.7% ASR to **0% — and utility from 66.7%
to 0% as well.** The defense stopped the attack by stopping the agent. Any
"defense holds" verdict has to be read against its utility column; this is the
same failure mode RQ6 was built to catch, and it shows up immediately here.

## Defenses available in-harness

AgentDojo's own six: `tool_filter`, `transformers_pi_detector`,
`repeat_user_prompt`, `spotlighting_with_delimiting`, `reflection`, `ipiguard`.

Plus this project's two, added in `corpus_defenses.py` and selectable as
`--defense datasentinel` / `--defense robustrag`. They sit in the tools-execution
loop at exactly the point AgentDojo puts its own `transformers_pi_detector`, so
the only difference between those pipelines is which detector is in the loop.

**They are not equally faithful, and the results must not be reported as if they
were.**

| | fidelity | what is actually running |
|---|---|---|
| `datasentinel` | **genuine reconstruction** | the authors' released LoRA checkpoint, called through their own unmodified `detect()` |
| `robustrag` | **a port** | the authors' keyword extraction and `min(beta, alpha*k)` filtering, applied to a substrate they did not design for |

### Why sidecars

Both defenses run as small local HTTP services rather than imports:
`datasentinel_service.py` (:1112) and `robustrag_service.py` (:1113). DataSentinel
needs `peft`, `bitsandbytes` and transformers 4.42; RobustRAG needs spaCy and
`en_core_web_sm`; the AgentDojo venv has transformers 4.46 and none of the rest.
Installing into any of these environments risks the reconstructions that
currently work — and those working reconstructions *are* RQ6's evidence base. A
process boundary keeps all three intact and changes nothing about either defense.

Each service refuses to start unless its controls reproduce: DataSentinel must
read clean=0 and the paper's own CombineAttacker=1; RobustRAG must keep five
corroborating items and drop an injected outlier.

### What RobustRAG's port does and does not preserve

RobustRAG answers a question over *k* independently retrieved passages, and its
certifiable-robustness guarantee rests on those passages being interchangeable
evidence for one question. An agent trajectory violates that: tool outputs are
sequential and dependent, so isolating them destroys the task rather than
protecting it.

What does satisfy the assumption is a **single tool output returning k
independent items** — a search over emails, files or messages. That is where
this element applies, filtering items whose content is not corroborated across
the others. Consequences to state whenever reporting from it:

- **no certificate.** Certified robustness is not being measured.
- it is a filter over multi-item outputs, not an answer aggregator.
- on single-item tool outputs it is a **no-op by construction**, and those runs
  must never be read as the defense holding. The element counts
  `skipped_single_item` so this is checkable rather than assumed.

### First result, and how it was verified

On banking / Qwen2.5-7B / 3 user tasks, `important_instructions` reads
**66.7% undefended → 66.7% defended** with DataSentinel in the loop. The defense
does not fire on AgentDojo's canonical IPI attack at all.

That claim was checked before being believed, because identical defended and
undefended numbers are exactly what a *disconnected* element also produces.
Instrumenting `detect()` shows **4 calls on real tool outputs (793, 712, 69 and
67 characters), 0 flagged** — the element is in the loop and genuinely misses.

The mechanism is the same one the text-classification run surfaced: DataSentinel
detects by wrapping data in a canary instruction and checking whether the model
still repeats a secret key. An injection aimed at an *agent mid-task* does not
stop a bare classification prompt from repeating that key, so it reads as clean.
**Its published generalization was established on a text-classification victim,
and against agent-shaped attacks in this harness it does not fire.**
