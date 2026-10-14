# Abstract — SoK: Context Integrity for LLM Agents

*Target venue: ACM CCS. ~320 words.*

---

Large language model agents fail when their context window is corrupted, and
two research communities have studied that failure without reading each other.
Security researchers study context corrupted on purpose — indirect prompt
injection, retrieval poisoning, memory backdoors — and publish *attacks* and
*defenses*. The machine-learning community studies context that degrades on its
own — retrieval noise, knowledge conflict, lost-in-the-middle — and publishes
*mechanisms* and *fixes*. The vocabularies differ; the failure does not. In both
cases the model cannot tell which part of its context deserves trust.

We systematize both literatures under a single taxonomy of channel × intent ×
consequence over 984 papers coded from full text, and find the separation is
measurable rather than rhetorical. Only 11.7% of security papers cite the
reliability literature, and 9.3% the reverse. Of 529 catalogued defenses, just
14 are validated against both threat models. The halves are also unevenly
served: 4.6 defenses exist per non-adversarial failure mode against 1.4 per
named attack, and 54.9% of mechanisms have no defense ever evaluated against
them. The sharpest asymmetry is in who holds the pen. Across 349 (defense,
attack) pairs recovered from both literatures, defenses prevail in 193 of 194
pairs reported by defense papers and in 0 of 37 reported by attack papers — the
same defenses, the same attacks, opposite verdicts, decided by which paper ran
the experiment.

We then do what a survey normally cannot: we run the missing test. In 56 scored
conditions over 3,584 episodes, executing each defense's own released code and
weights under an attack-works-first control and a fixed detectability threshold,
we find that defenses built for accidental context failure frequently do not
survive deliberate attack, and that the failure is systematic rather than
incidental. The mechanism that repairs accidental corruption — shifting trust
from the model's parameters toward retrieved text — is the mechanism an attacker
who owns that text exploits. The rule carries a measured scope condition: such
suppression is harmful only where parametric memory held the right answer, and
at least one defense both reads honest documents and resists poisoned ones, so
the trade-off is a design error rather than a law.

Finally, we report three controls the literature omits, each of which overturned
a conclusion we would otherwise have published: a no-retrieval baseline, which
revealed one defense's apparent immunity to be indistinguishable from ignoring
the retrieved document entirely; an abstention axis, which showed another to be
inert on accuracy while converting roughly a third of confident errors into
explicit refusals; and a model control, under which an effect's magnitude, its
existence, and in one case its sign all changed. We argue these belong in the
reporting conventions of both communities.

---

## Provenance of every number above

| Claim | Source | Status |
|---|---|---|
| 984 papers, full-text coded | corpus rebuild 2026-10-12 | firm |
| 11.7% / 9.3% cross-citation | `cross_citation_analysis.md`, full-population | firm, LLM-coded tracks |
| 529 defenses, 14 both-validated | `rq4_defense_registry.json` | firm |
| 4.6 vs 1.4 defenses per target; 54.9% uncovered | `scripts/pair_tally.py` | firm |
| 193/194 vs 0/37 | `scripts/pair_tally.py`, "who reports what" | firm |
| 56 conditions, 3,584 episodes | `scripts/pair_tally.py` | firm, grows as runs land |
| "at least one defense resists" | `acd_result.md` | **scope-limited — see note** |
| three controls | `scr_result.md`, `model_dependence.md`, closed-book arm | firm |

**Note on the ACD sentence.** ACD is the counterexample that keeps the paper
from being a hit piece: +53.5 pp over closed-book on clean documents *and*
+9.2 pp over undefended at saturation. But `acd_false_evidence_result.md` shows
it falls 4.0 pp *below* closed-book against fluent false evidence (p=0.0499).
The abstract's phrasing ("reads honest documents and resists poisoned ones") is
true of the corpus-poisoning payload only. If the three false-evidence runs now
in flight (ParamMute, CK-PLUG, COIECD) reproduce ACD's pattern, this sentence
must be narrowed to name the payload class, and the stronger claim becomes:
*no defense tested resists both payload classes.*
