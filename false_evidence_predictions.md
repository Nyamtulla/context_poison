# Predictions: ParamMute, CK-PLUG and COIECD against false evidence

Committed before the runs. Same 400 CoConflictQA items, same chunk-replacement
dosing, same scorers as each defense's corpus-poisoning run — only the payload
changes, so each defense is its own control.

**The payload.** Corpus poisoning plants an optimised token sequence that reads
as incoherent junk. False evidence plants a short, fluent, citation-bearing
sentence asserting the wrong answer — and specifically the model's *own prior*
wrong answer, so **context and memory agree**.

That agreement is the whole point. Every defense in this family is built on
detecting or arbitrating a *conflict* between what the model knows and what it
reads. An attack that removes the conflict attacks the premise rather than the
implementation.

## Per-defense predictions

**COIECD — should do nothing at all, more completely than before.**
Against corpus poisoning COIECD was already inert on accuracy (deltas −0.8 to
−1.8 pp, none resolvable) while firing on its own mechanism: it suppressed the
parametric answer by up to 7.0 pp. It detects conflict via an
information-entropy constraint. False evidence that *agrees* with the prior
produces no conflict to detect, so the constraint should fire less, not more.
Concretely: `pm_acc` suppression should shrink toward zero, and accuracy should
stay flat. If COIECD's parametric-suppression effect survives here, the
entropy-constraint explanation of its behaviour is wrong.

**ParamMute — should be harmful, and for a new reason.**
ParamMute suppresses knowledge-critical FFNs to force reliance on the context.
Under corpus poisoning that was dangerous because the context was the attack.
Under false evidence it is worse in a specific way: ParamMute suppresses the
model's memory of the right answer *and* the context re-supplies the same wrong
answer the memory would have produced anyway. Both paths now lead to the
planted answer. Predict `ctx_acc` at or below its corpus-poisoning result and
`pm_acc` rising sharply in both arms.

**CK-PLUG — same direction as ParamMute, smaller.**
CK-PLUG slides between memory and context by a confidence gain. Fluent evidence
raises the context's confidence, so the slider should move toward the context,
which carries the planted answer. Predict harm, but less than ParamMute's
because CK-PLUG's α is a soft blend rather than an FFN suppression.

## What would falsify the family story

If any of the three does **better** against false evidence than against corpus
poisoning, then "these defenses fail because they trust the context" is not the
mechanism, and the corpus-poisoning results were measuring something else —
most likely just that optimised junk degrades generation on its own.

## Known in advance

False evidence is the stronger attack per unit dose. On ACD's run the
undefended arm scored 28.2 % at 10 % poison under false evidence against 43.2 %
under corpus poisoning. So every defended number here should be read against
its own undefended arm in the same run, never across attacks.
