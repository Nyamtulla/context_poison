# The headline test could not be run — and why that is the finding

**FaithfulRAG (ACL 2025, `validated_against: incidental`) vs corpus poisoning
(EMNLP 2023, deliberate).** Attempted 2026-10-02. Qwen2.5-7B-Instruct,
FaithEval, **n = 400**, threshold **9.9 pp**.

## What this was meant to test

Everything before it tested *deliberate → deliberate*: RobustRAG is
adversarial-validated, so its failure against a second attack says nothing
about the two-literatures thesis. FaithfulRAG is the other kind — one of the
**54 incidental-validated** defenses in the silent-corruption cell. The
question the whole SoK rests on: **does work built for context going bad by
accident survive context made bad on purpose?**

## Result: the control failed, so the question stays open

| condition | vanilla | FaithfulRAG | difference | verdict |
|---|---:|---:|---:|---|
| **clean (its own native task)** | **76.8 %** | **71.8 %** | **−5.0 pp** | **no resolvable effect** |
| corpus poisoning, 10 % of context | 79.5 % | 76.8 % | −2.8 pp | no resolvable effect |
| corpus poisoning, 50 % of context | 75.0 % | 67.5 % | −7.5 pp | no resolvable effect |
| corpus poisoning, 100 % of context | 7.2 % | 7.5 % | +0.2 pp | no resolvable effect |

**FaithfulRAG produced no measurable benefit on its own benchmark.** Not a
negative result — a *non-result*: −5.0 pp is below the 9.9 pp threshold, so it
is not resolvable in either direction.

That makes every other row uninterpretable. **You cannot report that a defense
fails to transfer when you could not show it working at home.** The RobustRAG
study is readable precisely because its control *did* fire (+11.0 pp against
PoisonedRAG); this one does not earn that licence.

An n=20 pilot showed +5.0 pp and we did not act on it. At n=400 it is −5.0 pp.
The pilot's threshold was ~44 pp; it never supported a sign.

## What the run does establish

**Corpus poisoning replicates, on a different model, dataset and framework.**
Saturating the context drops accuracy **76.8 % → 7.2 %, −69.5 pp**, far above
threshold. Against RobustRAG (Mistral-7B, NQ, top-k passages) the same attack
gave 60.6 % → 3.4 %. Two independent reconstructions, same collapse.

**And the same saturation-dependence.** At 10 % and 50 % of the context, attack
damage is +2.8 and −1.8 pp — neither resolvable. The attack does nothing until
it owns nearly everything. That now holds across both experiments and is the
more robust finding about corpus poisoning than either collapse number.

## Why the control probably failed

**The method is ablated on open weights, and not by choice.** `get_predictions`
sets `response_format={"type": "json_object"}` for `normal_cot` and
`scheduled_cot`. That is an OpenAI JSON-mode flag; the HuggingFace backend
forwards it into `model.generate`, which rejects it outright. Stripping it —
exactly as the authors already strip `max_tokens` one line above — makes the
CoT paths *run* and score **0.0 % on both arms**, because OpenAI's JSON mode
was doing work the prompt alone cannot.

So on open-weight models only `wo_cot` is usable, and `wo_cot` is FaithfulRAG
**with Self-Think's reasoning disabled**. Every local reconstruction of this
defense — ours and RQ6's — has been testing the ablation.

**It also discards most of the context.** `chunk_topk=5 × chunk_size=20` keeps
~100 words of a median 319-word FaithEval context: about **31 %**. The vanilla
arm sees all of it. If the supporting sentence falls outside the selected
chunks, selection is pure loss. That is the method as implemented, not a
misconfiguration — but it is where a −5 pp would come from.

## What to do about it

1. **Run it through the OpenAI backend.** The defense's full method needs
   JSON mode. One API key turns this from an ablation into the real test.
   `.env.example` already documents the path.
2. **Or pick a different incidental defense.** 53 others remain in the cell;
   this one is not uniquely required.
3. **Do not report a transfer verdict from this run.** The attack numbers are
   solid. The defense numbers are not.

## The finding worth keeping

The SoK's central claim — defenses for accidental context failure will not
hold against deliberate ones — **could not be tested here, because the
incidental defense could not be reconstructed in working form on open
weights.** That is not a null result about transfer. It is a result about the
ML/AI literature's artifacts: a defense whose headline configuration silently
requires a commercial API, and whose open-weight path is an ablation the paper
never reports separately.

It belongs next to the project's reproducibility findings, not its transfer
findings.

## Reproduce

```bash
python3 scripts/faithfulrag_vs_corpus_poisoning.py --n 400 \
    --dataset faitheval_data --generation wo_cot
```

Raw: `data/registries/faithfulrag_vs_corpus_poisoning.json`.
Control sweep: `data/registries/frag_control_*.json`.
