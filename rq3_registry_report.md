# RQ3 -- Context Pollution Mechanism Registry (auto-generated)

Regenerated 2026-09-22 by `scripts/build_registry.py rq3`.

**Registry size: 223 distinct entries.**

By track:
- Security: 168
- ML/AI: 55

Exact-name duplicate groups found (merged automatically): 0
Fuzzy near-duplicate name pairs (>= 75 similarity, flagged for manual review, NOT auto-merged): 4

| Similarity | Name 1 (row) | Name 2 (row) |
|---:|---|---|
| 87 | PromptFuzz-SC (row 727) | PromptFuzz (row 780) |
| 83 | context drift (row 29) | context rot (row 308) |
| 77 | Indirect Prompt Injection (IPI) (row 2) | Image-based Prompt Injection (IPI) (row 1085) |
| 75 | PoisonedRAG (row 5) | PoisonedAlign (row 1060) |

**Action needed:** for each pair above, check whether it's (a) two distinct techniques with a coincidentally similar name -- the common case, no action needed -- or (b) the same underlying paper indexed twice under a slightly different title, which is a corpus-level duplicate to fix via `scripts/dedupe_corpus.py --apply <row>`, not a registry-merge issue.
