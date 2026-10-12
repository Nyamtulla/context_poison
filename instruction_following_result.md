# It is not instruction-following either

**Same probe, same dose, same harness. Only the instruction differs.**
2026-10-11.

## The test

The sweep showed that an isolate-then-aggregate defense inherits whatever the
model does to one poisoned passage seen alone, and that only Llama-3-8B-Instruct
breaks. Two explanations were offered for *which* models break, and this
falsifies the second.

The DoS passage is an authoritative notice telling the assistant to refuse.
The probe passage is an authoritative notice in the same voice and the same
shape, telling it to begin its answer with one arbitrary word. No refusal,
nothing false, no content changed. The only thing the two share is being an
instruction inside a retrieved document.

## Result

| model | follows a benign embedded instruction | refuses under DoS |
|---|---:|---:|
| Llama-3-8B-Instruct | 87.97 % | **78.95 %** |
| **Llama-2-13B-chat** | **70.38 %** | **0.00 %** |
| **Llama-2-7B-chat** | **25.26 %** | **0.00 %** |
| Mistral-7B-Instruct | 6.77 % | 5.41 % |
| Vicuna-7B | 4.06 % | 0.45 % |

Nearly 2,000 isolated passages per model, per probe.

**Llama-2-13B-chat obeys an arbitrary formatting order from a retrieved passage
seven times in ten, and never once obeys the order to refuse.** Llama-2-7B
obeys a quarter of the time and likewise never refuses. Pearson r between the
two columns is 0.695 across five models, carried entirely by Llama-3; the
sweep's own isolated-against-defended correlation was 0.9999. This is not that.

## Two hypotheses, both dead

| hypothesis | what killed it |
|---|---|
| the attack needs a **refusal-prone** model | Llama-2-chat is the most refusal-trained model in the set and scores 0.00 % |
| the attack needs a good **instruction-follower** | Llama-2-13B follows embedded instructions 70 % of the time and still scores 0.00 % |

I proposed both and both were wrong. The first was written down before the
sweep, the second after it, and the second was meant to repair the first.

## What survives, stated narrowly

These models will take an order from a retrieved passage about **how to
format an answer**, and will not take an order about **whether to answer at
all**. Llama-2-chat's decision to refuse is its own and is not delegable to
context. Llama-3-8B-Instruct's is.

> **The DoS attack does not need a compliant model or a cautious one. It needs
> a model that treats a retrieved passage as authoritative over its own
> decision to answer.** That is a narrower property than either thing I
> guessed, and it is the one that should be measured.

It also explains the shape of the earlier result without appealing to
alignment strength at all. Llama-2-chat was trained hard on *when to refuse*,
and that training is exactly what makes the refusal decision non-delegable —
it has a strong internal policy that a passage cannot move. Llama-3-Instruct
has a weaker prior about refusing and defers to the document. More safety
training made the model **harder** to attack this way, not easier, which is the
opposite of what the first hypothesis predicted.

## What does not change

The mechanism itself is untouched. Defended behaviour still tracks the
isolated per-passage view at r = 0.9999, the undefended arm is still 0.00 % on
every model, and a one-passage probe still predicts what an
isolate-then-aggregate defense will do. What has changed is only the account of
which models are vulnerable — and it is now a question to measure rather than
an answer to assert.

## Limits

- Five models, one benign instruction, one dose.
- One marker word. A different instruction — a language switch, a length
  limit — might be obeyed at different rates, and only a formatting order was
  tested.
- The `defended` column of this probe is not comparable to the sweep's.
  KeywordAgg regenerates the answer from extracted keywords, so a required
  prefix cannot survive aggregation by construction; it reads near zero for
  every model regardless. The isolated column is the measurement, and it was
  chosen for that reason before the run.
