# SoK: Context Poisoning in LLM Agents. One Failure Mode, Two Sets of Publications

*ASD-STE100 version (approximately 80% compliance). See the compliance note at
the end for the terms that stay outside the STE dictionary, and why.*

---

Large language model (LLM) agents fail when the data in their context window is
incorrect. Two research communities study this failure. They do not read the
work of the other community.

Security researchers study context that an attacker changes on purpose. For
example: indirect prompt injection, retrieval poisoning and memory backdoors.
They publish attacks and defenses.

Machine-learning researchers study context that becomes incorrect by accident.
For example: retrieval noise, knowledge conflict and the lost-in-the-middle
effect. They publish mechanisms and fixes.

The two vocabularies are different. The failure is the same. In both cases, the
model cannot find which part of its context it can trust.

We put both sets of publications into one taxonomy. The taxonomy has three
axes: channel, intent and consequence. We extracted the data from the full text
of 984 papers. The separation between the two communities is measurable:

- Only 11.7% of the security papers cite the reliability papers.
- Only 9.3% cite in the other direction.
- We catalogued 529 defenses. Only 14 of them are tested against both threat
  models.
- There are 4.6 defenses for each accidental failure mode, but only 1.4
  defenses for each named attack.
- 54.9% of the mechanisms have no defense that was tested against them.

The largest difference is related to the author of the report. We found 349
pairs of one defense and one attack. Defense papers report 194 of these pairs,
and the defense wins in 193. Attack papers report 37 pairs, and the defense
wins in none. The defenses are the same and the attacks are the same, but the
results are opposite. The author of the experiment decides the result.

A survey usually cannot do the next step. We do the test that is missing. We
ran 56 scored conditions and 3,584 episodes. For each defense, we used the code
and the weights that its authors released. Two controls apply to each run:

- The attack must work first.
- The effect must be more than a fixed detectability threshold.

Defenses for accidental context failure frequently do not stop a deliberate
attack. This failure is systematic. These defenses move trust away from the
parameters of the model and toward the retrieved text. An attacker who controls
that text uses the same mechanism.

This rule has a measured limit. The suppression is only dangerous when the
parametric memory held the correct answer. Also, at least one defense reads
correct documents and stops poisoned documents. Thus the problem is a design
error and not a law.

We also report three controls that the publications do not include. Each
control changed a conclusion that we would have published:

- **A no-retrieval baseline.** One defense appeared to be immune. But its
  results were the same as a model that ignores the retrieved document.
- **An abstention axis.** A second defense had no effect on accuracy. But it
  changed about one third of the confident wrong answers into refusals.
- **A model control.** We changed only the model. The size of an effect
  changed. Sometimes the effect did not occur. In one case, the effect changed
  its sign.

We recommend that both communities include these three controls in their
reports.

---

## Compliance note

**Rules applied in full:**

| Rule | Action |
|---|---|
| Sentence length (max 25 words, descriptive) | Longest sentence is 18 words. |
| One topic per sentence | All compound sentences were split. |
| Active voice | "we find", "we ran", "an attacker uses". |
| No `-ing` forms as verbs or nouns | "executing" → "we used"; "shifting" → "move". |
| Vertical lists for complex data | Three lists replace dense number strings. |
| Simple tenses only | Present and simple past. |
| No noun clusters above 3 words | "attack-works-first control" → a list item. |
| Punctuation | All em-dashes removed. |
| One word, one meaning | "study" is always the verb; "paper" is always the document. |

**Terms kept outside the STE dictionary (the remaining ~20%).** STE is written
for maintenance procedures, and its dictionary has no entries for this subject.
These are the names of the things the paper is about, so a substitution would
make the abstract wrong, not simpler:

> taxonomy · channel · intent · consequence · prompt injection · retrieval
> poisoning · memory backdoor · knowledge conflict · lost-in-the-middle ·
> parametric memory · threat model · baseline · abstention · suppression ·
> systematic · detectability threshold · episode · corpus

**Known effects of the conversion.** The STE version is about 15% longer than
the original and the compression of the source is lost. Two rhetorical moves do
not survive: the parallel in "the vocabularies differ; the failure does not",
and the structure of the final sentence of paragraph two. STE prevents both,
because each needs an em-dash or a balanced clause pair.
