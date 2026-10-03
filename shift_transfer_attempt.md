# SHIFT: the mechanism runs, and does nothing measurable here

**SHIFT (arXiv 2026, `validated_against: incidental`) vs corpus poisoning.**
Llama3.1-8B-Instruct checkpoint from `ITcoder/SHIFT`, CoConflictQA /
NaturalQuestions, **n = 150**, threshold **16.2 pp**. 2026-10-03.

## Result: control does not fire

| arm | ctx_acc | pm_acc | `mr` |
|---|---:|---:|---:|
| `ffn_output_gate=False` | 68.0 % | 12.0 % | 15.0 % |
| `ffn_output_gate=True` (SHIFT) | 69.3 % | 14.0 % | 16.8 % |
| **gate effect** | **+1.3 pp** | +2.0 pp | +1.8 pp |

Nowhere near threshold, and small enough that no feasible sample size would
rescue it: resolving 1.3 pp needs n ≈ 23,000. **No transfer verdict is
reportable from this**, on the same rule that made the FaithfulRAG attempt
unreportable.

## But the reason is different, and worth separating

FaithfulRAG's control failed because the method was **ablated** — its CoT path
needs OpenAI JSON mode and only the reduced `wo_cot` variant runs on open
weights. SHIFT's full method runs. Three checks establish that:

1. **The flag applies.** The harness prints the resolved config on load:
   `ffn_output_gate=False` then `True`.
2. **The trained gate is really loaded.** The checkpoint carries 64 `ffn_gate`
   tensors (32 layers × weight + bias), and layer 0's weight norm is
   **0.0049** — a trained value. Random initialisation at this shape would be
   on the order of 1.0, so the weights are not silently re-initialised, which
   is the failure mode that would have produced exactly this null.
3. **The gate changes generation.** On 5 held-out items, 4 of 5 outputs differ
   between gate on and off.

The differences are **cosmetic**: `'23'` → `'23 episodes.'`,
`'Patrick Walter Brown MPP'` → `'Patrick Walter Brown MPP.'`,
`'Panning straight up'` → `'Panning a stereo signal straight up.'`. Trailing
punctuation and slightly fuller phrasing. The substantive answer is unchanged,
which is why accuracy does not move.

**So this is a verified-active mechanism with no measurable effect on this
benchmark** — not a reconstruction failure.

## The most likely explanation, stated as a limitation

SHIFT is evaluated in its own paper on **MRQA**, standard reading
comprehension. It was run here on CoConflictQA, the knowledge-conflict
benchmark the other three defenses were measured on, because comparability
across the cell is worth more than each defense on its own home dataset.

That choice has a cost, and this is it. Running SHIFT on MRQA instead would
very likely show its benefit — but MRQA has no parametric-vs-contextual
conflict, so corpus poisoning's whole premise (context that contradicts what
the model knows) does not map onto it, and the result would not be comparable
to the other three. **The honest report is a null on the shared benchmark, not
a verdict on the defense.**

## Setup: six obstacles

All recorded in the campaign defect table. The shipped
`src/evaluation/eval.py` is unusable — `TEST_DATA_DIR` is
`/your/path/to/datasets/mrqa`, every `MODELS` entry is `/your/path/to/...`,
the listed models are Qwen3-only though `models/` ships Llama3.1, and
`datasets/{train,valid}/*.jsonl` are **1-byte placeholders**. Beyond that:

- **No tokenizer in the checkpoint.** `ITcoder/SHIFT` ships weights, config and
  modeling code but zero tokenizer files; loaded from the ungated
  Llama-3.1-8B-Instruct mirror, whose vocabulary the checkpoint fine-tunes.
- **Absolute sibling import.** `modeling_llama.py` does
  `from configuration_llama import ...`; `trust_remote_code` reads the bare
  name as a missing PyPI package and raises
  *"Run `pip install configuration_llama`"*. Fixed by putting the checkpoint
  directory on `sys.path`.
- **A two-sided transformers constraint.** The modeling code needs
  `transformers.modeling_layers.GradientCheckpointingLayer`, added around
  4.52, *and* `transformers.utils.LossKwargs`, removed in v5. Only a narrow
  window satisfies both; **4.53.3** does, 4.56.2 and 5.18 do not.

## Reproduce

```bash
python3 scripts/shift_vs_corpus_poisoning.py --n 150 --clean_only
```

Raw: `data/registries/shift_control.json`.
