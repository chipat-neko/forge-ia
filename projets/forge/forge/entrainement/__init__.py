"""L'entraînement de « ton IA » : chargeur de jetons, planning, sauvegardes, boucle et méthodes.

Le point d'entrée est `entrainer(lire_config("configs/mini.toml"))`, ou en ligne de commande
`python -m forge entrainer --config configs/mini.toml` (puis `--reprendre` après une pause).
Le réglage `methode` choisit la méthode dans le registre `METHODES` : « pre_entrainement »
(par défaut) ou « sft », l'affinage supervisé depuis une version publiée (`depart`).
"""

from forge.entrainement.boucle import CompilationImpossible, ConfigEntrainement, entrainer, lire_config
from forge.entrainement.chargeur import ChargeurJetons
from forge.entrainement.methodes import METHODES, Methode, enregistrer_methode
from forge.entrainement.planning import taux
from forge.entrainement.sauvegarde import charger_derniere, sauvegarder

__all__ = [
    "METHODES",
    "ChargeurJetons",
    "CompilationImpossible",
    "ConfigEntrainement",
    "Methode",
    "charger_derniere",
    "enregistrer_methode",
    "entrainer",
    "lire_config",
    "sauvegarder",
    "taux",
]
