# The same mechanism that causes harm also provides protection

**BadRAG "Alignment-as-an-Attack" vs ParamMute and CK-PLUG.**
Llama-3-8B-Instruct, `open_nq`, **n = 500**, threshold **8.9 pp**. 2026-10-04.

Third attack in the series, chosen as a discriminator: it **neither removes
information nor plants a false answer**. Its passage claims the topic is
contested and harmful, so an aligned model refuses to answer. Success is
measured as refusal rate.

## Result: ParamMute nearly eliminates the attack

| poison | undefended refusal | ParamMute refusal | Δ | undefended acc | ParamMute acc | Δ |
|---:|---:|---:|---:|---:|---:|---:|
| 0/10 | 0.0 % | 0.0 % | +0.0 | 62.2 % | 59.8 % | −2.4 |
| **1/10** | **52.4 %** | **0.2 %** | **−52.2 pp** | 27.0 % | **57.4 %** | **+30.4 pp** |
| **2/10** | 43.6 % | **0.0 %** | **−43.6 pp** | 23.2 % | **58.4 %** | **+35.2 pp** |
| **3/10** | 39.6 % | 0.2 % | **−39.4 pp** | 22.8 % | **57.2 %** | **+34.4 pp** |
| **5/10** | 18.6 % | 0.4 % | **−18.2 pp** | 30.2 % | **57.4 %** | **+27.2 pp** |
| 10/10 | 20.4 % | 8.4 % | **−12.0 pp** | 3.8 % | 1.6 % | −2.2 |

Across the whole realistic range (1–5 poisoned passages) the undefended model
averages **25.8 %** accuracy and ParamMute averages **57.6 %** — within 2.2
points of its own clean baseline of 59.8 %. The defense is **flat**: it does
not degrade as more poison is added.

With a single poisoned passage the undefended model refuses **52.4 %** of the
time and keeps only 27.0 % accuracy. ParamMute drops refusal to **0.2 %** and
restores accuracy to **57.4 %** — within 2.4 points of its own clean baseline.
**The attack is almost completely neutralised.**

This was predicted to show little effect. It shows a large protective one.

### The boundary is one passage

The full dose-response, filled in at every level from 0 to 10:

| poison | undef refusal | PM refusal | undef acc | PM acc | Δacc | verdict |
|---:|---:|---:|---:|---:|---:|---|
| 0/10 | 0.0 % | 0.0 % | 62.2 % | 59.8 % | −2.4 | — |
| 1/10 | 52.4 % | 0.2 % | 27.0 % | 57.4 % | **+30.4** | protective |
| 2/10 | 43.6 % | 0.0 % | 23.2 % | 58.4 % | **+35.2** | protective |
| 3/10 | 39.6 % | 0.2 % | 22.8 % | 57.2 % | **+34.4** | protective |
| 5/10 | 18.6 % | 0.4 % | 30.2 % | 57.4 % | **+27.2** | protective |
| 6/10 | 11.2 % | 0.2 % | 31.6 % | 55.8 % | **+24.2** | protective |
| 7/10 | 10.4 % | 0.2 % | 33.4 % | 55.6 % | **+22.2** | protective |
| 8/10 | 11.0 % | 0.2 % | 29.2 % | 53.6 % | **+24.4** | protective |
| **9/10** | 15.0 % | 0.8 % | 29.4 % | **48.8 %** | **+19.4** | **protective** |
| **10/10** | 20.4 % | 8.4 % | **3.8 %** | **1.6 %** | −2.2 | **collapse** |

**Protection holds at nine of ten passages poisoned and disappears at ten.**
ParamMute's accuracy declines gently across the whole range — 57.4, 58.4,
57.2, 57.4, 55.8, 55.6, 53.6, 48.8 — and then falls to **1.6 %**. The
undefended arm does the same thing: 27 → 33 → 29 → 29 → **3.8 %**.

The cliff is not gradual and it is not at "saturation" loosely defined. It is
at the point where **the last genuine passage disappears**. With one real
passage among nine payloads, the defense still delivers **+19.4 pp**. With
zero, both arms fail together.

That is the mechanism stated exactly: these defenses make the model use the
retrieved evidence. While any genuine evidence survives, that is the right
instruction and ParamMute executes it well enough to beat the undefended model
by 19–35 points. When none survives, "use the evidence" is an instruction to
use nothing, and the model's suppressed memory is no longer available to fall
back on.

### Both regimes appear inside this one attack

The dose-response was filled in at 2 and 3 passages to check an apparent
non-monotonicity in the undefended arm. It is real and smooth: refusal peaks at
**one** poisoned passage and falls away — 52.4 → 43.6 → 39.6 → 18.6 %. One
"editorial notice" among nine ordinary passages is the most effective
configuration; adding more does not help the attacker.

More usefully, the **10/10 column behaves differently from every other row** —
and the sweep from 6 to 9 shows it is the *only* row that does. There accuracy
collapses for both arms (3.8 % and 1.6 %) and ParamMute stops protecting. That
is the signature of the *harmful* regime: at full saturation there is no real
evidence left, so the attack has stopped being a refusal attack and has become
a context-destruction attack.

**So a single experiment contains both signs.** While real passages survive,
BadRAG exploits the refusal reflex and ParamMute blunts it. Once every passage
is a payload, the context is destroyed and ParamMute is back in the regime
where it removes a fallback the model needed. The boundary is not the attack's
name; it is whether usable evidence remains.

## Why — and it is the same mechanism as the harm

ParamMute suppresses the FFN layers that carry parametric knowledge. Across the
three attacks that single fact explains every result, with the sign depending
on *what the attacker is exploiting*:

| attack | what it exploits | ParamMute's effect |
|---|---|---|
| corpus poisoning | the context is destroyed; the model must fall back on memory | **harmful** — blocks the fallback |
| PoisonedRAG at saturation | every passage is a lie; the model must fall back on memory | **harmful** — ASR 68.4 → 88.8 % |
| **BadRAG DoS** | **the model's own learned refusal reflex** | **protective** — refusal 52.4 → 0.2 % |

The model's parametric behaviour contains two things the defense cannot tell
apart: **factual knowledge** and **a learned tendency to refuse**. ParamMute
mutes both.

Muting factual knowledge is a loss — it removes the retreat that salvages 32 %
accuracy when every passage is a lie. Muting the refusal reflex is a gain —
it removes exactly the behaviour BadRAG's payload is engineered to trigger.

**The defense is not sometimes right and sometimes wrong. It does one thing
consistently, and whether that helps depends entirely on which part of the
model's priors the attacker is aiming at.**

## CK-PLUG: the same direction, but unreadable

| poison | undefended refusal | CK-PLUG refusal | Δ | undefended acc | CK-PLUG acc | Δ |
|---:|---:|---:|---:|---:|---:|---:|
| 0/10 | 0.0 % | 0.2 % | +0.2 | 61.6 % | 39.0 % | **−22.6 pp** |
| 1/10 | 52.8 % | 36.4 % | **−16.4 pp** | 26.4 % | 3.8 % | **−22.6 pp** |
| 5/10 | 21.4 % | 15.2 % | −6.2 | 31.0 % | 1.6 % | **−29.4 pp** |
| 10/10 | 25.0 % | 3.8 % | **−21.2 pp** | 4.0 % | 0.4 % | −3.6 |

CK-PLUG also suppresses refusal, which fits the same account. But **its control
fails on this dataset**: it costs 22.6 pp of accuracy with no attack present,
and accuracy never recovers in any condition. A defense that destroys a fifth
of clean accuracy cannot be credited with a transfer result, so the refusal
reduction is recorded and not interpreted.

## What this does to the campaign's claim

The earlier synthesis said these defenses are harmful under attack. That was
true of the two attacks tested and is **too broad**.

The accurate statement is narrower and more useful:

> Defenses that suppress parametric knowledge remove **both** the model's
> factual fallback and its refusal reflex. They are harmful against attacks
> that make the context unusable, because the fallback is what would have
> saved the answer. They are protective against attacks that weaponise the
> model's own alignment, because the reflex is what the attacker is firing.

That is a design claim rather than a verdict, and it predicts where to look
next: any attack whose payload works by provoking the model's learned
behaviour should be blunted by this family, and any attack that destroys the
retrieved evidence should be amplified by it.

## Limits

- One model, one dataset, two defenses. CK-PLUG's arm is uninterpretable here.
- The 10/10 condition sits near the floor for both arms (3.8 % and 1.6 %
  accuracy), so the −2.2 pp there is not meaningful.
- Refusal is detected by the regex in `scripts/stage3_badrag_robustrag.py`,
  reused unchanged. It will miss unusual refusal phrasings.
- BadRAG's retrieval stage is conceded, as in the earlier stage-3 work: the
  payload is placed in the retrieved set rather than made to win retrieval.

## Reproduce

```bash
python3 scripts/poisonedrag_transfer.py --defense parammute --attack badrag_dos --n 500
python3 scripts/poisonedrag_transfer.py --defense ckplug    --attack badrag_dos --n 500
```

Raw: `data/registries/badrag_dos_parammute.json`, `data/registries/badrag_dos_ckplug.json`.
