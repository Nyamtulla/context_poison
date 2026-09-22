# RQ4 -- Defense Technique Registry (auto-generated)

Regenerated 2026-09-21 by `scripts/build_registry.py rq4`.

**Registry size: 534 distinct entries.**

By track:
- ML/AI: 266
- Security: 263
- Both: 5

Exact-name duplicate groups found (merged automatically): 1
Fuzzy near-duplicate name pairs (>= 75 similarity, flagged for manual review, NOT auto-merged): 7

| Similarity | Name 1 (row) | Name 2 (row) |
|---:|---|---|
| 88 | IPIGuard (row 52) | PIIGuard (row 156) |
| 83 | IDE-Sanitizer (row 104) | PISanitizer (row 191) |
| 80 | ProjGuard (row 165) | PromptGuard (row 1132) |
| 78 | ClawGuard (row 62) | PlanGuard (row 72) |
| 78 | KV-Fusion (row 413) | DP-Fusion (row 1095) |
| 76 | AttriGuard (row 63) | AprielGuard (row 804) |
| 75 | FinLongDocAgent (row 387) | LongAgent (row 418) |

**Action needed:** for each pair above, check whether it's (a) two distinct techniques with a coincidentally similar name -- the common case, no action needed -- or (b) the same underlying paper indexed twice under a slightly different title, which is a corpus-level duplicate to fix via `scripts/dedupe_corpus.py --apply <row>`, not a registry-merge issue.
