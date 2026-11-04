"""Le mot suivant : compter quel mot suit quel autre dans un texte, puis deviner la suite."""

from mot_suivant.mots import (
    charger_texte,
    compter_suivants,
    decouper_mots,
    generer,
    predire,
    premiere_reprise,
)

__all__ = ["charger_texte", "compter_suivants", "decouper_mots", "generer", "predire", "premiere_reprise"]
