"""Le mot suivant : compter quel mot suit quel autre dans un texte, puis deviner la suite."""

from mot_suivant.mots import (
    Suite,
    charger_texte,
    compter_suivants,
    decouper_mots,
    generer,
    predire,
    premiere_reprise,
    suivants_tries,
    suivre,
)

__all__ = [
    "Suite",
    "charger_texte",
    "compter_suivants",
    "decouper_mots",
    "generer",
    "predire",
    "premiere_reprise",
    "suivants_tries",
    "suivre",
]
