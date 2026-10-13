# Abstract — SoK: Context Integrity for LLM Agents

Large language model agents fail when their context is corrupted, and two
research communities study that failure without reading each other. The
security community studies context corrupted on purpose — prompt injection,
retrieval poisoning, memory backdoors — and publishes attacks and defenses. The
ML/AI community studies context that degrades on its own — retrieval noise,
knowledge conflict, context rot — and publishes mechanisms and fixes. Both
describe one underlying property: the model cannot tell which part of its
context deserves trust.

We systematize both literatures under a single taxonomy of channel × intent ×
consequence over 1,158 screened papers, and find the separation is measurable
rather than rhetorical: 60.5 % of the taxonomy's 162 cells are empty, 11.7 % of
security papers cite the other literature and 9.1 % the reverse, and 55.3 % of
named failure mechanisms have no defense evaluated against them at all.

We then do what a survey normally cannot: we execute the missing test. Across
70 defense × attack combinations, run on the authors' own released code and
weights and gated on an attack-works-first control and a fixed detectability
threshold, we find that defenses built for accidental context failure
frequently do not survive deliberate attack, and that the failure is
systematic — the mechanism that repairs accidental corruption, shifting trust
from the model's parameters toward retrieved text, is the mechanism an attacker
who owns that text exploits. The rule has a measured scope condition:
suppressing parametric memory is harmful only where that memory held the right
answer.

Two results caution against the generalization that the SoK genre invites. Two
implementations of a single published principle, shipped side by side in one
codebase, disagree by 29.7 points on whether the defense helps or hurts, with
the gap monotone in how small the honest minority of passages is. And across
five base models, holding defense and attack fixed, changing only the model
changes an effect's magnitude, its existence, and in one case its sign.

Finally, we report three controls that the literature omits and that each
overturned a conclusion we would otherwise have published: a no-retrieval
baseline, which showed one defense's apparent immunity to be indistinguishable
from not reading the retrieved document at all; an abstention axis, which
showed another defense to be inert on accuracy while converting roughly a third
of confident wrong answers into explicit refusals; and a model control. We
argue these belong in the reporting conventions of both communities.

---

**Status note.** The corpus coding is an LLM-assisted extraction pass that has
not yet been independently verified by a human. Every count in this abstract is
provisional pending that verification; see `CONTRIBUTOR_BRIEF.md`.
