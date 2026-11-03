"""Le chargeur de jetons : il découpe les fragments encodés en lots pour l'entraînement.

`forge encoder` range les jetons dans `train/` et `val/` (des fichiers `fragment-*.bin` en
`uint16`), avec `index.json` (le nombre de jetons de chaque fichier) et `.complet` à côté.
Le chargeur lit l'un de ces deux dossiers comme un seul long ruban de jetons :

- les fragments sont mis bout à bout, dans un ordre tiré au hasard à partir de la graine.
  Cet ordre change à chaque époque (une époque est un passage complet sur les données) ;
- on avance dans le ruban sans jamais revenir en arrière. Un lot prend les
  `taille_lot × longueur + 1` jetons suivants : les entrées `x` sont les `taille_lot × longueur`
  premiers, les cibles `y` les mêmes décalés d'un jeton (la cible de chaque position est le
  jeton qui la suit) ;
- quand il ne reste plus de quoi faire un lot entier, l'époque suivante commence, avec un
  nouvel ordre des fragments (les quelques jetons restants sont sautés).

Tout l'état tient en trois nombres : la graine, l'époque et la position dans le ruban de
cette époque. Avec eux, `restaurer` retrouve exactement les mêmes lots après une pause. La
position compte des jetons, pas des lots : on peut reprendre avec une autre `taille_lot`
(un `micro_lot` réduit après un manque de mémoire), et les jetons suivants restent les mêmes.
"""

import json
from bisect import bisect_right
from pathlib import Path

import numpy as np
import torch

from forge.donnees.jetons import lire_jetons
from forge.tokenizer.apprentissage import DonneesManquantes

VERSION_DE_L_ETAT = 1


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
    """Découpe les jetons de `dossier` (`.../train` ou `.../val`) en lots, dans un ordre tiré de `graine`.

    - `longueur` : nombre de positions de chaque ligne du lot (la longueur de contexte) ;
    - `taille_lot` : nombre de lignes de chaque lot ;
    - `lot()` renvoie `(x, y)`, deux tenseurs d'entiers `[taille_lot, longueur]` ;
    - `etat()` et `restaurer(etat)` sauvegardent puis retrouvent la position exacte.
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
        self.jetons_par_epoque = sum(self._tailles)
        if self.jetons_par_epoque < self._jetons_par_lot + 1:
            raise ValueError(
                f"{self.dossier} ne contient que {self.jetons_par_epoque} jetons : pas assez pour "
                f"un seul lot de {taille_lot} × {longueur} jetons. Réduis micro_lot, ou encode "
                "davantage de textes."
            )
        self._ouverts: dict[int, np.memmap] = {}
        self.epoque = 0
        self.position = 0
        self._preparer_epoque()

    @property
    def _jetons_par_lot(self) -> int:
        return self.taille_lot * self.longueur

    def _preparer_epoque(self) -> None:
        """Tire l'ordre des fragments de l'époque en cours : il ne dépend que de (graine, époque)."""
        hasard = np.random.default_rng([self.graine, self.epoque])
        self._ordre = [int(rang) for rang in hasard.permutation(len(self._fichiers))]
        self._debuts = [0]  # position, dans le ruban de l'époque, du début de chaque fragment
        for rang in self._ordre:
            self._debuts.append(self._debuts[-1] + self._tailles[rang])

    def _ouvrir(self, rang: int) -> np.memmap:
        """Ouvre le fragment `rang` une seule fois, sans le charger en mémoire."""
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

    def _lire(self, debut: int, nombre: int) -> np.ndarray:
        """Lit `nombre` jetons du ruban de l'époque à partir de `debut`, à cheval sur des fragments au besoin."""
        morceaux = []
        place = bisect_right(self._debuts, debut) - 1  # le fragment qui contient `debut`
        while nombre > 0:
            rang = self._ordre[place]
            decalage = debut - self._debuts[place]
            pris = self._ouvrir(rang)[decalage : decalage + nombre]
            morceaux.append(pris)
            nombre -= len(pris)
            debut += len(pris)
            place += 1
        return np.concatenate(morceaux)

    def lot(self) -> tuple[torch.Tensor, torch.Tensor]:
        """Le lot suivant : `(x, y)`, entiers `int64` de forme `[taille_lot, longueur]`."""
        besoin = self._jetons_par_lot + 1
        if self.position + besoin > self.jetons_par_epoque:
            self.epoque += 1
            self.position = 0
            self._preparer_epoque()
        ruban = torch.from_numpy(self._lire(self.position, besoin).astype(np.int64))
        self.position += self._jetons_par_lot
        x = ruban[:-1].view(self.taille_lot, self.longueur)
        y = ruban[1:].view(self.taille_lot, self.longueur)
        return x, y

    def etat(self) -> dict:
        """Ce qu'il faut garder pour reprendre au même endroit (des nombres simples)."""
        return {
            "version": VERSION_DE_L_ETAT,
            "graine": self.graine,
            "epoque": self.epoque,
            "position": self.position,
            "fragments": len(self._fichiers),
            "jetons_par_epoque": self.jetons_par_epoque,
        }

    def restaurer(self, etat: dict) -> None:
        """Replace le chargeur à la position décrite par `etat` (venu de `etat()`)."""
        if etat.get("version") != VERSION_DE_L_ETAT:
            raise ValueError(
                f"État du chargeur de version {etat.get('version')!r}, celle-ci lit la version "
                f"{VERSION_DE_L_ETAT}."
            )
        if etat["graine"] != self.graine:
            raise ValueError(
                f"La sauvegarde a été faite avec la graine {etat['graine']}, la configuration "
                f"donne {self.graine} : remets graine = {etat['graine']} pour reprendre le même "
                "entraînement."
            )
        if (etat["fragments"], etat["jetons_par_epoque"]) != (len(self._fichiers), self.jetons_par_epoque):
            raise ValueError(
                f"Les jetons de {self.dossier} ne sont plus ceux de la sauvegarde : "
                f"{etat['fragments']} fragments et {etat['jetons_par_epoque']} jetons alors, "
                f"{len(self._fichiers)} fragments et {self.jetons_par_epoque} jetons maintenant. "
                "Reprends avec les mêmes données (le même `donnees` dans la configuration)."
            )
        self.epoque = int(etat["epoque"])
        self.position = int(etat["position"])
        self._preparer_epoque()
