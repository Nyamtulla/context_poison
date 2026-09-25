# Evaluation-benchmark census spec

For each mechanism in your packet, classify **what its source paper actually
evaluated on**, and answer one question that the whole census exists to settle:

> Could another researcher take this paper's evaluation setup off the shelf and
> run a *different* attack or defense on it, to produce a comparable number?

That is `reusable_benchmark`. It is the crux. A paper can have a large, careful,
well-documented evaluation and still answer NO, because the setup is bespoke to
its own attack.

## Input / output

Packet: `data/registries/raw/benchmark_census_packet<N>.json` — a JSON array.
Each entry has `row` (carry through unchanged), `mechanism`, `track`, `channel`,
`paper_title`, `year`, `datasets_benchmarks`, `models_evaluated`, `key_result`.

Output: `data/registries/raw/benchmark_census_out<N>.jsonl` — ONE JSON object
per line, **appended after each item**. If the file exists, read it first and
skip `row`s already present.

Judge from `datasets_benchmarks` primarily; `key_result` and `models_evaluated`
are context. If the text is genuinely insufficient, say so via `confidence`
rather than guessing.

## Fields

- `row`, `mechanism` — copy unchanged.
- `benchmark_primary` — ONE of:
  - `own_purpose_built` — the paper constructed its own benchmark, dataset,
    testbed, simulated environment or scenario set for this attack. Includes
    "the authors construct", "no pre-existing benchmark", "new dataset
    introduced by this paper", and any bespoke harness.
  - `shared_security_benchmark` — an existing **security/injection** benchmark
    another paper could reuse: AgentDojo, InjecAgent, BIPIA, ASB, AdvBench,
    HarmBench, AgentHarm, SEP, CyberSecEval, Open-Prompt-Injection, HackAPrompt,
    Tensor Trust, JailbreakBench, AgentSafetyBench, R-Judge, ToolEmu, PINT...
  - `shared_generic_dataset` — standard NLP/QA/long-context corpora (Natural
    Questions, HotpotQA, MS-MARCO, TriviaQA, SQuAD, MMLU, GSM8K, LongBench,
    RULER, FEVER, needle-in-a-haystack...) used as raw material, with the
    attack setup built on top by this paper.
  - `live_system` — evaluated against a deployed product (ChatGPT, Bing Chat,
    Copilot, Claude, a real MCP server, a shipped agent) rather than a benchmark.
  - `none_qualitative` — no dataset: demonstrations, case studies, proofs of
    concept, disclosure write-ups.
  - `unclear` — the text does not say.
- `benchmark_all` — list of every category above that applies (a paper may use a
  shared benchmark AND build its own additions).
- `named_benchmarks` — list of the specific benchmarks/datasets named, verbatim
  as the text gives them. Empty list if none.
- `reusable_benchmark` — `"yes"` / `"no"` / `"partial"`.
  - `yes` — the evaluation runs on something another researcher could obtain and
    reuse to get a comparable number (a shared security benchmark; sometimes a
    standard corpus IF the attack setup is fully specified on top of it).
  - `partial` — a shared corpus or benchmark is used, but the attack
    construction layered on it is bespoke, so numbers are not directly
    comparable across papers.
  - `no` — bespoke environment, live-system demo, or no evaluation benchmark.
- `why` — one or two sentences, quoting or closely paraphrasing the text that
  decides it. This is the audit trail; "seems bespoke" is not acceptable.
- `confidence` — `high` / `medium` / `low`.

## Judgment guidance

- **The default is not `own_purpose_built`.** Read for a named, pre-existing
  benchmark first. Only conclude bespoke when the text says so or names nothing
  reusable.
- **A large dataset is not a shared benchmark.** PoisonedRAG uses Natural
  Questions — millions of passages — but the *poisoning setup* on top is its
  own, so `shared_generic_dataset` with `reusable_benchmark: partial`, not `yes`.
- **"Built on top of AgentDojo" is not the same as "used AgentDojo".** If a paper
  extends a shared benchmark with its own scenarios, record both categories in
  `benchmark_all` and judge `reusable_benchmark` on whether the extension is
  released/specified enough to reuse. Usually `partial`.
- Evaluating on a live product is `no` for reusability regardless of scale — the
  product changes and nobody else can reproduce the run.
- If `datasets_benchmarks` is empty, use `unclear` with `confidence: low`, not a
  guess.

## Report back

Counts per `benchmark_primary`; counts per `reusable_benchmark`; the named
benchmarks you saw most often; and the 8-10 calls you were least sure about
(mechanism + call + one line why).
