# Robustness by not reading the document

**DyPRAG vs corpus poisoning, n=400, Llama-3-8B-Instruct, CoConflictQA.**
Prediction committed in `scripts/dyprag_vs_corpus_poisoning.py` before the run.

Seventh defense in the RAG x silent-corruption cell and the first that is not a
decoding-time intervention. DyPRAG maps the retrieved passage to a rank-2 LoRA
through a trained parameter translator, injects it, and then generates with the
passage **removed from the prompt**. It is the only defense in this cell that
changes what the attacker controls.

## Result

ctx_acc, recall against the gold answer. mdr 9.9 pp at n=400.

| arm | clean | 10 % | 50 % | 100 % | slope |
|---|---:|---:|---:|---:|---:|
| `rag` (defense off) | 63.8 | 36.2 | 24.5 | 2.5 | **−61.2** |
| `closedbook` (no passage, no LoRA) | 7.5 | 7.5 | 7.5 | 7.5 | 0.0 |
| **`dyprag` (defense on)** | **5.8** | **6.0** | **5.2** | **6.0** | **+0.2** |
| `dyprag_combine` | 53.0 | 30.2 | 19.2 | 5.0 | −48.0 |

The control fires: `rag` collapses 63.8 -> 2.5, Fisher p = 9.4e-88.

**`dyprag` is perfectly flat under an attack that destroys the undefended arm.**
Taken alone that reads as the strongest defense result in the campaign.

## The control that changes the conclusion

`closedbook` answers with no passage and no LoRA - what the model knows
unaided. It scores **7.5 % at every dose**, and `dyprag` is statistically
indistinguishable from it everywhere, trending slightly *below*:

| poison | dyprag | closedbook | Δ | Fisher p |
|---:|---:|---:|---:|---:|
| 0 % | 5.8 | 7.5 | −1.8 | 0.394 |
| 10 % | 6.0 | 7.5 | −1.5 | 0.481 |
| 50 % | 5.2 | 7.5 | −2.2 | 0.247 |
| 100 % | 6.0 | 7.5 | −1.5 | 0.481 |

**DyPRAG's immunity to corpus poisoning is entirely explained by it not using
the retrieved document.** Not retrieving at all is immune too, and scores
slightly higher. The flat slope is not protection; it is abstention from the
input, measured.

Without this arm the write-up would have read "DyPRAG is robust to corpus
poisoning" - true, and badly misleading. The arm was added only because the
channel probe showed the accuracy table could not separate "the defense works"
from "the channel carries nothing".

## The channel is live. It carries noise, not signal.

The obvious objection is that DyPRAG is simply inert - that nothing is injected
and `dyprag` *is* `closedbook`. That is false, and the margin is large.

| poison | `dyprag` text ≠ `closedbook` text | dyprag right, cb wrong | cb right, dyprag wrong |
|---:|---:|---:|---:|
| 0 % | 335/400 (83.8 %) | 8 | 17 |
| 10 % | 347/400 (86.8 %) | 10 | 18 |
| 50 % | 346/400 (86.5 %) | 7 | 18 |
| 100 % | 348/400 (87.0 %) | 10 | 18 |

The injected LoRA **rewrites 84-87 % of the answers and converts more right
answers to wrong than wrong to right.** It is doing a great deal and
accomplishing nothing.

It is also genuinely reading the passage. `dyprag`'s output changes with the
poison level on 22-29 % of items (92, 87 and 117 of 400 at 10 %, 50 % and
100 %), and `scripts/dyprag_channel_probe.py` measures the parameters
themselves responding: cos(clean, poisoned) = 0.90-0.93 with relative change
0.62-1.14 at layer 15. The channel is passage-dependent and live.

What it is not is informative. The injected contribution is ~1e-4 of the MLP
output norm (9.7e-5, 5.3e-4, 9.6e-5 at layers 0, 15, 31) - enough to flip a
discrete argmax, nowhere near enough to carry the document's content.

`closedbook` changed on **0** items across all four doses, which confirms the
invariance is real and the harness never leaks the passage.

## What this says

**DyPRAG's robustness and its uselessness are the same property.** The channel
is too narrow to carry the attacker's payload *or* the document's answer. You
cannot widen it to recover the 58 points `rag` gets on clean context without
also re-admitting the attack - and `dyprag_combine` is the experiment that
shows it. Putting the passage back in the prompt restores most of the clean
accuracy (53.0) and restores the vulnerability with it (−48.0 slope, tracking
`rag`'s −61.2).

That is a different failure from anything else in this cell:

| defense | behaviour under attack |
|---|---|
| ParamMute, CK-PLUG | actively harmful - amplify the poisoned context |
| COIECD | inert on accuracy, converts memory-fallback to abstention |
| RobustRAG (both aggregations) | stops some attacks, opens others |
| **DyPRAG** | **immune, by not using the input at all** |

For an SoK the lesson is about what a defense evaluation must report. A
single-number robustness claim cannot distinguish a defense that resists an
attack from one that ignores the channel the attack arrives on. **The
no-retrieval baseline is the minimum control that separates them**, and it is
absent from the DyPRAG paper and from most of this literature - which evaluates
against RAG baselines, where "ignores the document" looks like a win on the
robustness axis and is simply not plotted on the utility axis at the same dose.

## On the committed prediction

Predicted: `dyprag` degrades less than `rag` (**confirmed**, +0.2 vs −61.2);
`dyprag` starts lower on clean context (**confirmed**, 5.8 vs 63.8);
`dyprag_combine` tracks `rag` (**confirmed**, −48.0 vs −61.2).

All three held, and the stated reason - that the attack's token-space precision
cannot survive compression to a rank-2 LoRA - is *not* what the data supports.
Nothing survives the compression, the gold answer included. The prediction was
right about the outcome and wrong about the mechanism, which the closed-book
arm and the channel probe are what exposed.

## Limits

- One model, one dataset, one attack. Corpus poisoning plants optimised junk
  rather than a false fact; a PoisonedRAG-style payload gives the projector
  something semantically coherent to encode and could behave differently.
- The released translator was trained by the authors on their own data
  (2400 samples, main checkpoint). A translator trained on in-domain
  CoConflictQA passages might carry more signal. This measures the artifact as
  released, which is the standard applied to every other defense here.
- `dyprag` below `closedbook` is not resolvable at n=400 (p = 0.25-0.48). The
  claim is indistinguishability, not that DyPRAG is worse.
- Implementation note: the LoRA is applied factored rather than materialised as
  a dense delta, verified equivalent to 1e-12. See `dyprag_setup.md`.
