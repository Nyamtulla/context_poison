# Paper workflow

Kept here rather than in `latex/README.md` because that file is mirrored into
the Overleaf project, where setup instructions are noise for co-authors. This
file stays in `context_sok` only.

## The two repos

| repo | holds | who edits |
|---|---|---|
| `context_sok` | everything, including `latex/` | you, via Claude |
| `context_poison_paper` | a mirror of `latex/` only | Overleaf co-authors |

They are **not** linked automatically. The mirror is refreshed by hand.

## The rule: pull, regenerate, edit, push

```bash
scripts/sync_paper.sh status     # compare latex/ with the mirror
scripts/sync_paper.sh pull       # bring the mirror's edits into latex/
python3 scripts/gen_paper_numbers.py
python3 scripts/gen_paper_figures.py
scripts/build_paper.sh           # compile before pushing; see below
scripts/sync_paper.sh push "message"
```

Regenerate **after** pulling, never before. `gen_paper_numbers.py` rewrites
`latex/numbers.tex`, and pulling on top of a freshly generated file conflicts
in a generated artifact.

`pull` copies each differing file from the mirror into `latex/` and tells you
which. It does not commit. Read `git diff latex/` before you do, because a
co-author's edit may collide with a rewrite on this side, and only a person
can decide which wins.

## Why this is not `git subtree` any more

It used to be. The history rewrite that purged the source PDFs removed the
marker commit `git subtree pull` looks for, so it fails with *"'latex' was
never added"*, and every push after a co-author edit needed `--force`.
Force-moving a branch other people pull from is a bad default and it was
avoidable: the mirror is a **content copy** of `latex/`, not a projection of
this repo's history. A plain clone, copy, commit and push keeps both
histories intact and never rewrites the other side's.

## If Overleaf opens a branch

Overleaf creates `overleaf-YYYY-MM-DD-HHMM` when it cannot fast-forward, and
sometimes a pull request with it. Check what is actually on it before
assuming it matters:

```bash
git clone git@github.com:Nyamtulla/context_poison_paper.git /tmp/mi
cd /tmp/mi && git log --oneline origin/main..origin/<branch>
```

One such branch commented out every Semantic Scholar URL in `refs.bib` with
`#`, which is not a BibTeX comment character, and the same problem had already
been fixed properly in `scripts/build_bibtex.py`. It was superseded, not lost.
Bundle a branch before deleting it:

```bash
git bundle create ~/overleaf-<sha>.bundle origin/<branch>
git push origin --delete <branch>
```
