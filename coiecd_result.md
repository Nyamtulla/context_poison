# A defense that is invisible on accuracy and active on the failure mode

**COIECD vs corpus poisoning, n=400, Llama-3-8B-Instruct, CoConflictQA.**
Prediction committed in `scripts/coiecd_vs_corpus_poisoning.py` before the run.

Sixth defense in the RAG x silent-corruption cell, and the best-cited
context-reliance method run so far (37 citations against ParamMute's 8).
COIECD detects parametric-vs-contextual conflict with an information-entropy
constraint and, where it fires, moves the next-token distribution toward the
context.

## The control fires

| poison | base_rag ctx_acc |
|---|---:|
| clean | 44.0 % |
| 10 % | 26.5 % |
| 50 % | 19.0 % |
| 100 % | 3.8 % |

Clean vs 100 %: Fisher p = 2.5e-45. The attack works on the undefended arm, so
the defended arm is reportable.

## The prediction was wrong

Committed before the run: *same family as ParamMute and CK-PLUG, so COIECD
should lose ground under poisoning, and lose more as the fraction grows.*

| poison | metric | base_rag | COIECD | Δ | Fisher p |
|---|---|---:|---:|---:|---:|
| clean | ctx_acc | 44.0 | 43.2 | −0.8 | 0.89 |
| 10 % | ctx_acc | 26.5 | 27.2 | +0.8 | 0.87 |
| 50 % | ctx_acc | 19.0 | 18.5 | −0.5 | 0.93 |
| 100 % | ctx_acc | 3.8 | 2.0 | −1.8 | 0.20 |

**Inert at every dose.** Nothing approaches the 9.9 pp threshold at n=400.
COIECD neither helps nor hurts accuracy. It is not in the "makes it worse"
bucket that ParamMute and CK-PLUG occupy, and not in the "stops the attack"
bucket either.

## But it is firing, and harder as the attack grows

| poison | base_rag pm_acc | COIECD pm_acc | Δ | Fisher p |
|---|---:|---:|---:|---:|
| clean | 7.8 | 7.0 | −0.8 | 0.79 |
| 10 % | 12.0 | 8.2 | −3.8 | 0.10 |
| 50 % | 11.8 | 7.5 | −4.2 | 0.055 |
| 100 % | 20.2 | 13.2 | **−7.0** | **0.010** |

The parametric-answer rate falls monotonically with dose and resolvably at
saturation. The defense does exactly what it was designed to do - pull the
model off memory and toward the context - and gains nothing, because the
context *is* the attack.

## Where the mass goes

Every generation at clean and 100 % was dumped and classified
(`data/registries/coiecd_generations.json`, 800 rows).

| poison 100 % | gold | parametric | abstain | other |
|---|---:|---:|---:|---:|
| base_rag | 3.5 % | 19.5 % | 38.5 % | 38.5 % |
| COIECD | 2.0 % | 12.8 % | **46.0 %** | 39.2 % |

Paired, on the 78 items where base_rag answered from memory:

| COIECD did | n | share |
|---|---:|---:|
| still parametric | 46 | 59.0 % |
| **abstain** | **25** | **32.1 %** |
| other | 6 | 7.7 % |
| gold | 1 | 1.3 % |

On clean context the same pairing moves almost nothing - 21 of 25 memory
answers stay parametric, abstention is flat at 1.5 %, and accuracy is
unchanged. **The conversion happens only under attack.**

## Why this is a result and not a null

COIECD converts about a third of memory-fallback answers into abstentions
when the context is adversarial, costs nothing in accuracy at any dose, and
does not fire on clean conflicts. In CoConflictQA the parametric answer is in
conflict with gold by construction, so what it suppresses were confident wrong
answers, and what it produced instead was "not mentioned".

Silent corruption is dangerous *because it is silent*: the harm is a confident
wrong answer the user has no reason to question. A defense that converts a
third of silent failures into loud ones is acting directly on the property
that defines the consequence class - while scoring zero on the accuracy column
that every paper in this family reports.

**A reader scanning accuracy deltas would record COIECD as a no-op.** That is
the wrong lesson. It is working as specified; the specification is what fails.
This argues the cell needs a second reported axis - abstention rate, or any
loud-vs-silent split - because accuracy alone cannot distinguish "did nothing"
from "changed how it breaks".

## What it does to the design rule

The campaign's rule is *do not suppress parametric memory*. COIECD suppresses
parametric memory by 7.0 pp at saturation and causes no harm, so the rule as
worded over-predicts.

The reason is visible in the data: in CoConflictQA the parametric answer is
wrong against gold by construction, so suppressing it costs nothing. The rule's
real content is narrower than its wording - **suppressing memory hurts only
where memory held the right answer.** ParamMute and CK-PLUG were measured on
items where it sometimes did. That is a scope condition on the rule, found by a
defense that was predicted to confirm it.

## Integration notes

COIECD's own `model_answer` is used unchanged - their prompts, their
`coiecd_constraint`, their generation loop, their oracle-length `tgt_len` - so
the control arm (`cond_answer`) and the defended arm (`coiecd_answer`) come out
of the same forward passes. Scored with the cell's existing rubric
(`eval_NQ.get_score`), unchanged.

Two environment fixes were required. **Neither touches the method, and the
first is a silent-wrong-answer bug for anyone running this repo on a
right-padding tokenizer:**

1. **`padding_side`.** COIECD tokenises `[context_prompt, no_context_prompt]`
   as a padded batch, then reads `logits[:, -1, :]` for both rows. Llama-3
   defaults to **right** padding, which makes the shorter no-context row's last
   position a PAD - so `logits_uncond` is read off padding and the entropy
   constraint computes on noise, with no error raised. Set to left, which is
   what their loop assumes.
2. **`pad_token`.** Llama-3 ships none and their `tokenizer.pad_token_id = 0`
   line is commented out, so the padded batch cannot be built at all.

## Limits

- One model, one dataset, one attack. The abstention finding is a within-run
  paired comparison, not a claim about abstention rates in general.
- Abstention was classified by pattern match over the generated text. The
  pattern is in the analysis above and errs toward under-counting - anything
  unrecognised falls into "other", which is flat across arms (38.5 vs 39.2 %).
- Corpus poisoning fills the context with the attack's optimised passage, which
  carries no planted answer. A false-fact attack such as PoisonedRAG gives the
  model something to copy, and the destination split would likely differ.
- Deterministic: both runs returned 44.0/7.8 and 3.8/20.2 to the decimal.
