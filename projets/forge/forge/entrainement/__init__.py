"""L'entraînement de « ton IA » : chargeur de jetons, planning, sauvegardes et boucle.

Le point d'entrée est `entrainer(lire_config("configs/mini.toml"))`, ou en ligne de commande
`python -m forge entrainer --config configs/mini.toml` (puis `--reprendre` après une pause).
"""

from forge.entrainement.boucle import CompilationImpossible, ConfigEntrainement, entrainer, lire_config
from forge.entrainement.chargeur import ChargeurJetons
from forge.entrainement.planning import taux
from forge.entrainement.sauvegarde import charger_derniere, sauvegarder

__all__ = [
    "ChargeurJetons",
    "CompilationImpossible",
    "ConfigEntrainement",
    "charger_derniere",
    "entrainer",
    "lire_config",
    "sauvegarder",
    "taux",
]
