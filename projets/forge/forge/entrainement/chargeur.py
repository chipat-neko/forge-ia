"""Le chargeur de jetons : il découpe le corpus en morceaux, les mélange et forme les lots.

`forge encoder` range les jetons dans `train/` et `val/` (des fichiers `fragment-*.bin` en
`uint16`), avec `index.json` (le nombre de jetons de chaque fichier) et `.complet` à côté.
Chaque fichier vient d'une seule source : du web, de Wikipédia ou du code.

Si l'on lisait les fichiers l'un après l'autre, le modèle verrait des centaines de pas de
web, puis des centaines de pas de code : il oublierait un peu l'un pendant qu'il apprend
l'autre. On découpe donc tout le corpus en morceaux de même taille, on les mélange à chaque
passage, et on les lit dans cet ordre : chaque lot mélange les sources, et aucun morceau
n'est oublié.

- Un morceau fait `longueur + 1` jetons qui se suivent dans UN fichier : chaque fichier est
  coupé en morceaux bout à bout, sans chevauchement, et la fin trop courte pour un morceau
  entier est laissée de côté. Les morceaux de tous les fichiers sont numérotés à la suite.
- Une époque est un passage sur tous les morceaux. Au début de chaque époque, on tire au
  hasard un ordre de lecture (une permutation des numéros) à partir de la graine et du
  numéro de l'époque.
- Un lot prend les `taille_lot` morceaux suivants dans cet ordre (quand l'époque s'achève au
  milieu d'un lot, le lot se complète avec le début de l'époque suivante). Les entrées `x`
  sont les `longueur` premiers jetons de chaque morceau, les cibles `y` les mêmes décalés
  d'un jeton (la cible de chaque position est le jeton qui la suit).

Tout l'état tient en deux nombres : l'époque et la position dans son ordre de lecture.
`etat()` les donne, `restaurer()` les remet, et les lots suivants sont exactement ceux
d'avant la pause. La position compte des morceaux, pas des lots : on peut reprendre avec un
`micro_lot` réduit (après un manque de mémoire), les jetons de chaque pas restent les mêmes.
"""

import json
from bisect import bisect_right
from pathlib import Path

import numpy as np
import torch

from forge.donnees.jetons import lire_jetons
from forge.tokenizer.apprentissage import DonneesManquantes

VERSION_DE_L_ETAT = 3


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
    """Forme des lots de morceaux de `dossier` (`.../train` ou `.../val`), mélangés à chaque époque.

    - `longueur` : nombre de positions de chaque ligne du lot (la longueur de contexte) ;
    - `taille_lot` : nombre de lignes (de morceaux) de chaque lot ;
    - `graine` : la graine du hasard qui mélange les morceaux ;
    - `lot()` renvoie `(x, y)`, deux tenseurs d'entiers `[taille_lot, longueur]` ;
    - `etat()` et `restaurer(etat)` sauvegardent puis retrouvent la position exacte.

    `morceaux` est le nombre de morceaux d'une époque, `jetons` le nombre de jetons du dossier.
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
        # Un fichier de n jetons donne n // (longueur + 1) morceaux. `_premiers[i]` est le
        # numéro du premier morceau du fichier i ; le dernier élément est le total.
        self._premiers = [0]
        for taille in self._tailles:
            self._premiers.append(self._premiers[-1] + taille // (longueur + 1))
        self.morceaux = self._premiers[-1]
        if self.morceaux == 0:
            raise ValueError(
                f"Aucun fichier de {self.dossier} n'a {longueur + 1} jetons : pas de quoi faire un "
                "seul morceau. Encode davantage de textes."
            )
        self._ouverts: dict[int, np.memmap] = {}
        self.epoque = 0
        self.position = 0
        self._melanger()

    def _melanger(self) -> None:
        """Tire l'ordre de lecture de l'époque en cours : il ne dépend que de (graine, époque)."""
        hasard = np.random.default_rng([self.graine, self.epoque])  # un générateur PCG64
        self._ordre = hasard.permutation(self.morceaux)

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
        """Les `longueur + 1` jetons du morceau numéro `numero`."""
        rang = bisect_right(self._premiers, numero) - 1  # le fichier qui le contient
        debut = (numero - self._premiers[rang]) * (self.longueur + 1)
        return self._ouvrir(rang)[debut : debut + self.longueur + 1]

    def lot(self) -> tuple[torch.Tensor, torch.Tensor]:
        """Le lot suivant : `(x, y)`, entiers `int64` de forme `[taille_lot, longueur]`."""
        numeros = []
        while len(numeros) < self.taille_lot:
            if self.position == self.morceaux:  # l'époque est finie : nouvel ordre de lecture
                self.epoque += 1
                self.position = 0
                self._melanger()
            pris = min(self.taille_lot - len(numeros), self.morceaux - self.position)
            numeros.extend(int(n) for n in self._ordre[self.position : self.position + pris])
            self.position += pris
        morceaux = torch.from_numpy(np.stack([self._morceau(n) for n in numeros]).astype(np.int64))
        return morceaux[:, :-1].contiguous(), morceaux[:, 1:].contiguous()

    def etat(self) -> dict:
        """Ce qu'il faut garder pour reprendre au même endroit (des nombres simples)."""
        return {
            "version": VERSION_DE_L_ETAT,
            "graine": self.graine,
            "epoque": self.epoque,
            "position": self.position,
            # Pour vérifier, à la reprise, que les données n'ont pas changé :
            "fragments": len(self._fichiers),
            "jetons": self.jetons,
            "morceaux": self.morceaux,
        }

    def restaurer(self, etat: dict) -> None:
        """Replace le chargeur à la position décrite par `etat` (venu de `etat()`)."""
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
        sauve = (etat["fragments"], etat["jetons"], etat["morceaux"])
        if sauve != (len(self._fichiers), self.jetons, self.morceaux):
            raise ValueError(
                f"Les jetons de {self.dossier} ne sont plus ceux de la sauvegarde : "
                f"{etat['fragments']} fragments, {etat['jetons']} jetons et {etat['morceaux']} "
                f"morceaux alors, {len(self._fichiers)} fragments, {self.jetons} jetons et "
                f"{self.morceaux} morceaux maintenant. Reprends avec les mêmes données (le même "
                "`donnees` dans la configuration)."
            )
        self.epoque = int(etat["epoque"])
        self.position = int(etat["position"])
        self._melanger()
