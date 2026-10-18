# Running the experiments

This repo has two halves. The **corpus half** (search, screening, the
registries, the dashboards) needs no GPU and is described in `README.md`. This
file is about the **experiment half**: the platform that runs released attacks
against released defenses, and the commands that produce every number in the
paper's results sections.

Three things are worth stating before the instructions, because they are what
the artifact is for.

**Nothing here is a reimplementation.** Every attack and every defense runs
from its authors' released code at a pinned commit. `third_party/MANIFEST.json`
lists all 20 repositories with their commits, and
`scripts/setup_third_party.py --verify` checks that none of them has a modified
tracked file. Carlini's critique of DeepSec found several attacks and one
defense reimplemented incorrectly; the defense against that is not care, it is
not reimplementing, and the verify command is how you check that we did not.

**The decoder is greedy everywhere.** There is no run-to-run noise to average
over. We checked rather than assumed: one published cell rerun three times from
scratch produced byte-identical output (`data/registries/variance_replicates_coiecd.json`).
See "Determinism" below for what that does and does not cover.

**The controls run whether or not you ask for them.** Every run carries a clean
dose, an undefended arm and, in the retrieval cell, a no-retrieval arm. A
defense that scores well by not reading the document and a defense that scores
well by reading it correctly look identical on an accuracy curve without that
third arm.

## What it was run on

| | |
|---|---|
| GPU | 1 × NVIDIA RTX A6000, 48 GB |
| Driver / CUDA | 535.274.02 / 12.8 |
| Python | 3.10.12 |
| torch | 2.10.0+cu128 |
| transformers | 5.5.0 |
| Main model | `NousResearch/Meta-Llama-3-8B-Instruct` |
| Second model | `mistralai/Mistral-7B-Instruct-v0.2`, where a defense required it |

48 GB is enough for every run in the paper. The retrieval-cell runs hold one
8B model in bf16 and nothing else; contrastive-decoding defenses hold two
forward passes of it at once, which is where the memory goes. Smaller cards
work by lowering `--batch_size`, which changes nothing about the result
because decoding is greedy.

`transformers` is pinned rather than bounded. Several vendored defenses
subclass the sampling loop, and `Cache` and `logits_to_keep` were reorganised
between 4.x and 5.x. A different minor version may run and may not reproduce.

## Setup

```bash
git lfs install
git clone git@github.com:Nyamtulla/context_poison.git
cd context_poison
git lfs pull
```

Git LFS is not optional. `data/context_sok.db` is 72 MB and stored in LFS;
without it you get a 133-byte pointer and every script that opens the database
fails with `sqlite3.DatabaseError: file is not a database`. This is the single
most common setup failure in this repo.

```bash
pip install -r requirements-experiments.txt
python3 scripts/setup_third_party.py              # clone the 20 implementations
python3 scripts/setup_third_party.py --payloads   # install the built payloads
python3 scripts/check_artifact.py                 # no GPU, no network
```

`check_artifact.py` is the gate. It checks the environment, the LFS payloads,
every third-party pin, every attack payload against the hash the published
numbers came from, and every registry the paper's macros read. It exits 0 only
if all five pass, and prints the fixing command for anything that does not.

Some defenses need weights beyond the base model. Those are downloaded by the
upstream project's own instructions, not by us: `third_party/ParamMute` needs
its merged checkpoint and `third_party/DyPRAG` its trained projectors. Both
are gitignored here because they are large and are not ours to redistribute.

## First run: eight items, two doses

Before spending an hour, spend two minutes confirming the model loads, the
defense's vendored decoder runs, and the scorer agrees with itself.

```bash
python3 scripts/coiecd_vs_corpus_poisoning.py --n 8 --fracs 0 1.0 \
  --attack distractor_evidence --data NaturalQuestionsShort_kc_distractor.jsonl \
  --no_resume --out /tmp/first_run.json
```

The first invocation downloads Llama-3-8B-Instruct (about 16 GB) and is slow
for that reason alone. What to look for in the output: three arms per dose
(`rag`, `closedbook`, the defense), the clean dose showing the defense at or
near the undefended arm, and the attacked dose showing both of them fall. Eight
items is far below anything decidable — the point is that the machinery runs,
not that the numbers mean something.

## Reproduce a headline result

### The mechanism finding: what a defense takes from memory, the attacker gets

This is the paper's central result, and the distractor payload is what makes it
measurable. The payload asserts a **third** answer, equal to neither the gold
answer nor the model's own prior answer, so copying the attacker and falling
back on memory are separable outcomes rather than one residual.

```bash
python3 scripts/coiecd_vs_corpus_poisoning.py --n 400 \
  --attack distractor_evidence --data NaturalQuestionsShort_kc_distractor.jsonl
```

About 50 minutes. Repeat with `ckplug_vs_corpus_poisoning.py`,
`parammute_vs_corpus_poisoning.py` and `acd_vs_corpus_poisoning.py` for the
other three defenses. The conservation claim is read off the resulting
registries: across the defenses, memory loss and copy gain cancel to within 7
points.

### The adaptive attack on ACD

Two stages. The payload is built once, then run like any other attack.

```bash
# best-of-five over sentence forms, white-box, about 40 min
python3 scripts/build_adaptive_acd_payload.py --n 686

# the GCG version: a 20-token suffix optimised against the same objective
python3 scripts/build_gradient_acd_payload.py --n 686 --steps 8 --batch 20

python3 scripts/acd_vs_corpus_poisoning.py --n 686 --n_shots 5 \
  --attack adaptive_evidence --data NaturalQuestionsShort_kc_adaptive.jsonl \
  --out data/registries/acd_vs_adaptive_evidence.json
```

`--n_shots` must match the value the payload was built with. The few-shot
demonstrations are held out of the evaluation slice, so a different count
shifts which items are evaluated and the arms stop being comparable. The
builder prints the exact run command for this reason.

Both payloads are already in `data/payloads/` with their hashes, so the ACD
run can be reproduced without redoing the search.

### Determinism

```bash
python3 scripts/coiecd_vs_corpus_poisoning.py --n 400 \
  --attack distractor_evidence --data NaturalQuestionsShort_kc_distractor.jsonl \
  --no_resume --out /tmp/replicate.json
```

Run it three times. Removing the timestamp, the files are identical: 72
numeric cells across 8 result rows, zero differences. What this does **not**
cover is sensitivity to item order, batch composition, or which items a
defense holds out as few-shot examples. A method fragile to those would pass
this check and still be fragile.

## The agent cell

The retrieval cell above is one of two. The other runs injection attacks
against agent-side defenses inside AgentDojo, which supplies a real
tool-calling victim where a hijack is scored by the suite's own checker
observing the injected goal being carried out, rather than by a regex over the
reply. It has its own setup, its own virtual environment and its own README:

- `agentdojo_harness/README.md` — why AgentDojo is the victim harness, the 16
  corpus mechanisms rebuilt as AgentDojo attacks, and the undefended/defended
  pairing that makes an inert payload report as inconclusive rather than as a
  defense success.
- `corpus_poisoning_harness/README.md` — the released corpus-poisoning attack,
  reconstructed and checked against the numbers its own paper reports before
  it was used against anything.

The agent cell's results are the `technique_transfer_*`, `mechanism_triage_*`
and `*_attack_screen_*` registries in `RUNS.md`.

## Every other run

`RUNS.md` is generated by `scripts/gen_run_index.py`. It lists all 87 result
registries with the script that produced each and the command rebuilt from the
metadata the registry stores about itself. Four registries have no single
claimed producer and are listed as such rather than attributed by guess.

`python3 scripts/pair_tally.py` recomputes the campaign totals from the
registries: distinct (defense, attack) pairs, episodes, and which pairs the
literature had already run.

## What is deliberately not here

| | why |
|---|---|
| Third-party attack/defense source | own git histories and licenses; `setup_third_party.py` fetches them at pinned commits |
| Model weights | from Hugging Face, by their own terms |
| The upstream CoConflictQA item set | ships with ParamMute; our payload files add one field to it and are indexed in `data/payloads/INDEX.json` |
| Source PDFs of the surveyed papers | they carry their own redistribution terms; every record keeps its DOI or arXiv id, and `scripts/fetch_missing_pdfs.py` re-fetches |
| API keys | `.env` is gitignored; `.env.example` lists the variables |

## Resuming and interrupted runs

The retrieval-cell runners write after every dose rather than at the end, and
re-running the same command resumes from the doses already present. This
exists because poisoned contexts are longer than clean ones, so memory grows
with the dose, and two early attempts finished the clean and 10% doses, OOMed
on 50%, and discarded the finished work with them. If a run dies, lower
`--batch_size` and re-run the identical command; it will pick up the missing
doses. `--no_resume` forces a recompute, which is what the determinism check
above uses.
