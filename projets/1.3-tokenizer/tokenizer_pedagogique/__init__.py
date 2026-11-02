"""Tokenizer BPE pédagogique : apprendre des fusions sur un corpus, puis découper un texte."""

from tokenizer_pedagogique.bpe import (
    Fusion,
    Jeton,
    TokenizerPedagogique,
    apprendre,
    charger_corpus,
)

__all__ = ["Fusion", "Jeton", "TokenizerPedagogique", "apprendre", "charger_corpus"]
