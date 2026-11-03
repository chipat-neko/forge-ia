"""Le chargeur de jetons : il pioche des morceaux de texte au hasard pour former les lots.

`forge encoder` range les jetons dans `train/` et `val/` (des fichiers `fragment-*.bin` en
`uint16`), avec `index.json` (le nombre de jetons de chaque fichier) et `.complet` à côté.
Chaque fichier vient d'une seule source : du web, de Wikipédia ou du code.

Si l'on lisait les fichiers l'un après l'autre, le modèle verrait des centaines de pas de
web, puis des centaines de pas de code : il oublierait un peu l'un pendant qu'il apprend
l'autre. On pioche donc des morceaux au hasard dans tout le corpus, pour que chaque lot
mélange web, Wikipédia et code :

- chaque ligne d'un lot est un morceau de `longueur + 1` jetons qui se suivent, pris dans UN
  fichier (jamais à cheval sur deux) ;
- son point de départ est tiré au hasard, uniformément parmi toutes les positions possibles
  de tous les fichiers : un fichier deux fois plus gros est pioché deux fois plus souvent ;
- les entrées `x` sont les `longueur` premiers jetons du morceau, les cibles `y` les mêmes
  décalés d'un jeton (la cible de chaque position est le jeton qui la suit).

Le hasard vient d'un générateur NumPy (PCG64) lancé avec la graine. Tout l'état du chargeur
est l'état de ce générateur : `etat()` le donne, `restaurer()` le remet, et les lots suivants
sont exactement les mêmes qu'avant la pause. Chaque ligne consomme un tirage, quelle que soit
la taille du lot : on peut reprendre avec un `micro_lot` réduit (après un manque de mémoire),
les jetons de chaque pas restent les mêmes.

Ce tirage se fait avec remise : sur un passage, certains morceaux sont vus deux fois et
d'autres pas du tout, ce qui ne gêne pas un grand corpus.
"""

import json
from bisect import bisect_right
from pathlib import Path

import numpy as np
import torch

from forge.donnees.jetons import lire_jetons
from forge.tokenizer.apprentissage import DonneesManquantes

VERSION_DE_L_ETAT = 2


def _lister_fragments(dossier: Path) -> tuple[list[Path], list[int]]:
    """Les fichiers de jetons de `dossier` (`train/` ou `val/`) et leur nombre de jetons.

    La liste vient de `index.json`, dans le dossier parent : un fichier sans jeton n'est pas
    écrit par l'encodage, il n'y figure donc pas. Le dossier parent doit avoir son `.complet`.
    """
    racine, partie = dossier.parent, dossier.name
    encoder = f"python -m forge encoder --donnees {racine.name} --tokenizer <chemin>"
    if not (racine / ".complet").exists():
        raise DonneesManquantes(
            f"Les jetons de {racine} ne sont pas prêts : il manque le marqueur .complet, donc "
            f"l'encodage n'est pas terminé. Termine-le d'abord avec : {encoder} (il reprend là "
            "où il s'est arrêté)."
        )
    try:
        index = json.loads((racine / "index.json").read_text(encoding="utf-8"))
        fichiers = index["fichiers"]
    except (OSError, ValueError, KeyError, TypeError) as erreur:
        raise DonneesManquantes(
            f"L'index des jetons {racine / 'index.json'} est absent ou illisible ({erreur}). "
            f"Relance l'encodage : {encoder}"
        ) from erreur
    noms = sorted(nom for nom in fichiers if nom.startswith(f"{partie}/"))
    if not noms:
        raise DonneesManquantes(
            f"Aucun jeton dans {dossier} d'après {racine / 'index.json'}. Vérifie le nom du "
            "dossier (train ou val), ou encode davantage de textes."
        )
    return [racine / nom for nom in noms], [int(fichiers[nom]) for nom in noms]


class ChargeurJetons:
    """Forme des lots de morceaux piochés au hasard dans `dossier` (`.../train` ou `.../val`).

    - `longueur` : nombre de positions de chaque ligne du lot (la longueur de contexte) ;
    - `taille_lot` : nombre de lignes (de morceaux) de chaque lot ;
    - `graine` : la graine du générateur qui tire les points de départ ;
    - `lot()` renvoie `(x, y)`, deux tenseurs d'entiers `[taille_lot, longueur]` ;
    - `etat()` et `restaurer(etat)` sauvegardent puis retrouvent le hasard exact.
    """

    def __init__(self, dossier: Path, longueur: int, taille_lot: int, graine: int) -> None:
        if longueur < 1 or taille_lot < 1:
            raise ValueError(
                f"longueur ({longueur}) et taille_lot ({taille_lot}) doivent valoir au moins 1."
            )
        self.dossier = Path(dossier)
        self.longueur = longueur
        self.taille_lot = taille_lot
        self.graine = graine
        self._fichiers, self._tailles = _lister_fragments(self.dossier)
        self.jetons = sum(self._tailles)
        # Un morceau prend `longueur + 1` jetons d'un même fichier : un fichier de n jetons
        # offre n - longueur points de départ. On les numérote à la suite, fichier après
        # fichier ; `_departs_cumules[i]` est le premier numéro du fichier i.
        self._departs_cumules = [0]
        for taille in self._tailles:
            self._departs_cumules.append(self._departs_cumules[-1] + max(0, taille - longueur))
        if self._departs_cumules[-1] == 0:
            raise ValueError(
                f"Aucun fichier de {self.dossier} n'a plus de {longueur} jetons : pas de quoi "
                f"faire un seul morceau de {longueur + 1} jetons. Encode davantage de textes."
            )
        self._hasard = np.random.Generator(np.random.PCG64(graine))
        self._ouverts: dict[int, np.memmap] = {}

    def _ouvrir(self, rang: int) -> np.memmap:
        """Ouvre le fichier `rang` une seule fois, sans le charger en mémoire."""
        if rang not in self._ouverts:
            jetons = lire_jetons(self._fichiers[rang])
            if len(jetons) != self._tailles[rang]:
                raise ValueError(
                    f"{self._fichiers[rang]} contient {len(jetons)} jetons, mais index.json en "
                    f"annonce {self._tailles[rang]} : les jetons ont changé depuis l'encodage. "
                    "Relance l'encodage de ce dossier."
                )
            self._ouverts[rang] = jetons
        return self._ouverts[rang]

    def _morceau(self, numero: int) -> np.ndarray:
        """Les `longueur + 1` jetons qui partent du point de départ numéro `numero`."""
        rang = bisect_right(self._departs_cumules, numero) - 1  # le fichier qui le contient
        debut = numero - self._departs_cumules[rang]
        return self._ouvrir(rang)[debut : debut + self.longueur + 1]

    def lot(self) -> tuple[torch.Tensor, torch.Tensor]:
        """Le lot suivant : `(x, y)`, entiers `int64` de forme `[taille_lot, longueur]`."""
        numeros = self._hasard.integers(0, self._departs_cumules[-1], size=self.taille_lot)
        morceaux = torch.from_numpy(np.stack([self._morceau(int(n)) for n in numeros]).astype(np.int64))
        return morceaux[:, :-1].contiguous(), morceaux[:, 1:].contiguous()

    def etat(self) -> dict:
        """Ce qu'il faut garder pour reprendre au même endroit : l'état du générateur, et de quoi vérifier."""
        return {
            "version": VERSION_DE_L_ETAT,
            "graine": self.graine,
            "hasard": self._hasard.bit_generator.state,
            "fragments": len(self._fichiers),
            "jetons": self.jetons,
        }

    def restaurer(self, etat: dict) -> None:
        """Remet le générateur dans l'état décrit par `etat` (venu de `etat()`)."""
        if etat.get("version") != VERSION_DE_L_ETAT:
            raise ValueError(
                f"État du chargeur de version {etat.get('version')!r}, cette version de la forge lit "
                f"la version {VERSION_DE_L_ETAT}."
            )
        if etat["graine"] != self.graine:
            raise ValueError(
                f"La sauvegarde a été faite avec la graine {etat['graine']}, la configuration "
                f"donne {self.graine} : remets graine = {etat['graine']} pour reprendre le même "
                "entraînement."
            )
        if (etat["fragments"], etat["jetons"]) != (len(self._fichiers), self.jetons):
            raise ValueError(
                f"Les jetons de {self.dossier} ne sont plus ceux de la sauvegarde : "
                f"{etat['fragments']} fragments et {etat['jetons']} jetons alors, "
                f"{len(self._fichiers)} fragments et {self.jetons} jetons maintenant. "
                "Reprends avec les mêmes données (le même `donnees` dans la configuration)."
            )
        self._hasard.bit_generator.state = etat["hasard"]
