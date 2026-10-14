# SoK paper source

LaTeX source for *SoK: Context Poisoning in LLM Agents*.

## Building

There is no LaTeX toolchain on the machine this was written on. The source is
written for Overleaf, which has both required classes installed.

- Upload this folder to Overleaf and set `main.tex` as the main document.
- Compiler: pdfLaTeX. Run latex, bibtex, latex, latex.

Locally, if you install a toolchain:

```bash
latexmk -pdf main.tex
```

## Switching venue

The source is written for `acmart` in `sigconf` mode, which is the CCS format.
Only `main.tex` is venue specific. The `sections/` files contain no class
specific markup.

For CCS submission, remove `nonacm` from the class options and add the real
copyright block.

For USENIX, replace the preamble and the title block in `main.tex` with the
`usenix2019_v3` template and keep every `\input{sections/...}` line unchanged.

## Files

| file | holds |
|---|---|
| `main.tex` | class, title, section order, bibliography |
| `sections/00-abstract.tex` | abstract |
| `sections/01-introduction.tex` | problem, contributions |
| `sections/02-background.tex` | scope, the two vocabularies, the channel picture |
| `sections/03-corpus.tex` | discovery, screening, coding, verification |
| `sections/04-taxonomy.tex` | the three axes, the cube, both censuses |
| `sections/05-literatures.tex` | citation and evaluation separation |
| `sections/06-coverage.tex` | the coverage matrix, who reports what |
| `sections/07-experiments.tex` | pair selection, reconstruction standard, rules |
| `sections/08-results.tex` | all experimental results |
| `sections/09-discussion.tex` | proposed reporting conventions |
| `sections/10-threats.tex` | threats to validity |
| `sections/11-related.tex` | related systematizations |
| `sections/12-conclusion.tex` | conclusion and future work |
| `refs.bib` | only the works cited, 21 entries |

## References

`refs.bib` holds only works actually cited in the text.

`../manuscript/references.bib` is the screening record, not the corpus
bibliography. It has one entry per screened paper: 1,158 entries, being the
984 papers included in the corpus plus the 174 that screening rejected. It is
not part of the submission. Keeping the rejected papers in it is deliberate,
because a screening decision has to stay auditable against the paper it was
made about.

## Working with Overleaf

The source of truth is this directory, inside the main `context_sok` repo, so
the paper stays next to the scripts that generate its numbers. Co-authors work
in Overleaf against a second, paper-only repo that mirrors this directory.

### One-time setup (run from the repo root, not from here)

Create an empty GitHub repo first, then:

```bash
git subtree push --prefix=latex git@github.com:Nyamtulla/context_poison_paper.git main
```

In Overleaf: New Project, Import from GitHub, pick `context_poison_paper`.
Overleaf's Git and GitHub integration is a paid feature. On the free tier,
download the folder as a zip and use Upload Project instead, then export the
zip back when co-authors have edited.

### Sending your changes to Overleaf

```bash
git subtree push --prefix=latex git@github.com:Nyamtulla/context_poison_paper.git main
```

### Pulling co-author edits back

```bash
git subtree pull --prefix=latex git@github.com:Nyamtulla/context_poison_paper.git main --squash
```

Pull before you regenerate numbers, so a co-author's prose edit and a number
refresh do not collide.

## Numbers

**Never type a count into a section file.** Every corpus-derived figure is a
macro defined in `numbers.tex`, which is generated:

```bash
python3 ../scripts/gen_paper_numbers.py
```

Run it after any corpus rebuild, registry rebuild, or new experiment, then
commit `numbers.tex`. The prose says `\NCorpus{}`, never `984`, so one command
updates every figure in the paper at once.

This exists because four numbers in the first draft were wrong: the
bibliography size, the no-mechanism paper count, the coded-field count, and the
single-mechanism testing rate, which mixed two different pair sets. Each had
been correct when it was typed, and then the corpus moved. A fifth was found
the same day: RQ5's coverage figures predated reverse-scan pass 3, because
`pair_tally.py` had folded it in and `src/registry_source.py` had not.

Experiment effect sizes (`+9.2 pp`, `82.3 %` and so on) are deliberately NOT
macros. They come from completed runs on fixed items and do not move when the
corpus is rescreened. Keeping them literal marks which numbers are live and
which are settled.

### Regenerating the rest

```bash
python3 ../scripts/pair_tally.py                  # pair counts, who reports what
python3 ../scripts/false_evidence_comparison.py   # the two payload classes
```


## Open items

- Section 8, CK-PLUG against false evidence: the run was still in progress
  when this draft was written. The cell is filled from
  `data/registries/ckplug_vs_false_evidence.json` once it lands.
- Section 11 cites no related systematizations by key. The competitor surveys
  are in the corpus; add their bibkeys before submission.
- The verification pass is described in the past tense in Section 3.4 and
  Section 10 as agreed, because it will be complete before submission. Confirm
  the stratified sample sizes and the inter-rater figure before it ships.
