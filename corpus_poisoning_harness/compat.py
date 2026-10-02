"""Compatibility shims for running the EMNLP 2023 corpus-poisoning code today.

The attack itself (`src/attack_poison.py`) needs none of this - it runs
unmodified on torch 2.11 / transformers 5.18. Only the *evaluation* path does,
because it goes through `beir` 1.0.1 and Contriever's `beir_utils.py`, both of
which predate two removals.

Each shim restores a removed API with its documented equivalent. None of them
changes what is computed. Import this module before importing anything from
the corpus-poisoning tree.
"""
from __future__ import annotations


def patch_batch_encode_plus() -> bool:
    """Restore `tokenizer.batch_encode_plus`, removed in transformers v5.

    Contriever's `beir_utils.py` calls it in `encode_queries` and
    `encode_corpus` with plain kwargs (max_length, padding, truncation,
    add_special_tokens, return_tensors). Calling the tokenizer directly is the
    documented replacement and is what the method delegated to for years, so
    this restores behaviour exactly rather than approximating it.
    """
    from transformers.tokenization_utils_base import PreTrainedTokenizerBase
    if hasattr(PreTrainedTokenizerBase, "batch_encode_plus"):
        return False

    def batch_encode_plus(self, batch_text_or_text_pairs, **kwargs):
        return self(batch_text_or_text_pairs, **kwargs)

    PreTrainedTokenizerBase.batch_encode_plus = batch_encode_plus
    return True


def apply() -> list[str]:
    """Apply every shim, and report which ones were actually needed."""
    applied = []
    if patch_batch_encode_plus():
        applied.append("transformers: restored tokenizer.batch_encode_plus")
    return applied
