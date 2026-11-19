"""Les jeux d'affinage sur disque, et leurs chargeurs (SFT et DPO).

Un jeu est un dossier, `sous_forge_donnees(nom, "affinage")` :

- `train/` et `val/` : `ids.bin` (`uint16`), `appris.bin` (`uint8`, 0 ou 1) et `documents.bin`
  (`int16`, -1 pour le bourrage), rangée après rangée, de `longueur + 1` valeurs chacune ;
  `reference.bin` (`float64`, une valeur par rangée) s'y ajoute quand le DPO a calculé la
  référence ;
- `index.json` : la version, la sorte (`sft` ou `dpo`), la longueur, les comptes, les sources
  (avec licence et lien) et le bloc `tokenizer`, le même que l'index des jetons de
  pré-entraînement (l'export compare son empreinte à celle de la sauvegarde) ;
- `.complet` : posé en dernier.

Pour la sorte `dpo`, les rangées vont par paires : la rangée `2k` est la réponse choisie, la
rangée `2k + 1` la réponse rejetée.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from forge.affinage.empaquetage import Rangee
from forge.chemins import verifier_place
from forge.donnees.jetons import empreinte_du_tokenizer
from forge.donnees.telechargement import MARGE_PLACE
from forge.erreurs import DonneesManquantes
from forge.fichiers import ecrire_atomique, ecrire_texte
from forge.tokenizer import TokenizerOctets

VERSION_DU_JEU = 1
VERSION_DE_L_ETAT = 1
SORTES = ("sft", "dpo")
PARTIES = ("train", "val")
IGNORE = -100  # la cible que la perte ne compte pas

_DTYPE_IDS = np.dtype("<u2")
_DTYPE_APPRIS = np.dtype("u1")
_DTYPE_DOCUMENTS = np.dtype("<i2")
_DTYPE_REFERENCE = np.dtype("<f8")


# --- Écrire -------------------------------------------------------------------------


def _ecrire(chemin: Path, tableau: np.ndarray) -> None:
    verifier_place(tableau.nbytes + MARGE_PLACE, chemin.parent)
    ecrire_atomique(chemin, lambda fichier: fichier.write(tableau.tobytes()))


def _verifier_rangees(rangees: Sequence[Rangee], partie: str, largeur: int) -> None:
    for numero, rangee in enumerate(rangees):
        if not len(rangee.ids) == len(rangee.appris) == len(rangee.documents) == largeur:
            raise ValueError(
                f"La rangée {numero} de {partie} n'a pas {largeur} positions : toutes les rangées "
                "d'un jeu ont la même longueur. Refais l'empaquetage avec `empaqueter`."
            )


def ecrire_jeu(
    dossier: Path,
    train: Sequence[Rangee],
    val: Sequence[Rangee],
    sorte: str,
    infos: dict,
    tok: TokenizerOctets,
) -> None:
    """Écrit le jeu dans `dossier` ; `.complet` vient en dernier.

    `infos` donne `ecartes` (le nombre d'exemples écartés à l'empaquetage), `sources` (nom →
    exemples, licence, lien) et, si aucune rangée n'est écrite, `longueur`. Le reste (rangées,
    exemples, jetons, jetons appris) se compte ici sur les rangées.
    """
    if sorte not in SORTES:
        raise ValueError(f"Sorte de jeu inconnue : {sorte!r}. Les sortes sont {', '.join(SORTES)}.")
    parties = {"train": list(train), "val": list(val)}
    modele = parties["train"] or parties["val"]
    if modele:
        largeur = len(modele[0].ids)
    elif "longueur" in infos:
        largeur = int(infos["longueur"]) + 1
    else:
        raise ValueError("Aucune rangée à écrire : le jeu serait vide. Prépare d'abord des exemples.")
    for partie, rangees in parties.items():
        _verifier_rangees(rangees, partie, largeur)
        if sorte == "dpo" and len(rangees) % 2:
            raise ValueError(
                f"Un jeu dpo va par paires (choisie, rejetée) : {partie} a {len(rangees)} rangées, "
                "un nombre impair. Écris chaque paire en deux rangées à la suite."
            )

    toutes = parties["train"] + parties["val"]
    if any(
        min(r.ids) < 0
        or max(r.ids) > np.iinfo(_DTYPE_IDS).max
        or max(r.documents) > np.iinfo(_DTYPE_DOCUMENTS).max
        for r in toutes
    ):
        raise ValueError(
            "Un identifiant de jeton ne tient pas dans 16 bits (ou une rangée a plus de 32 767 "
            "documents). Vérifie le tokenizer et la longueur des rangées."
        )

    dossier = Path(dossier)
    (dossier / ".complet").unlink(missing_ok=True)  # un jeu à moitié refait n'est pas complet
    for partie in PARTIES:  # une référence calculée sur l'ancien jeu ne vaut plus rien
        for ancien in ("reference.bin", "reference.json"):
            (dossier / partie / ancien).unlink(missing_ok=True)
    for partie, rangees in parties.items():
        (dossier / partie).mkdir(parents=True, exist_ok=True)
        _ecrire(dossier / partie / "ids.bin", np.array([r.ids for r in rangees], dtype=_DTYPE_IDS).reshape(-1))
        _ecrire(
            dossier / partie / "appris.bin",
            np.array([r.appris for r in rangees], dtype=_DTYPE_APPRIS).reshape(-1),
        )
        _ecrire(
            dossier / partie / "documents.bin",
            np.array([r.documents for r in rangees], dtype=_DTYPE_DOCUMENTS).reshape(-1),
        )
    index = {
        **infos,
        "version": VERSION_DU_JEU,
        "sorte": sorte,
        "longueur": largeur - 1,
        "rangees": {partie: len(rangees) for partie, rangees in parties.items()},
        "exemples": sum(max(r.documents) + 1 for r in toutes),
        "jetons": sum(1 for r in toutes for d in r.documents if d >= 0),
        "jetons_appris": sum(sum(r.appris) for r in toutes),
        "ecartes": int(infos.get("ecartes", 0)),
        "sources": infos.get("sources", {}),
        "tokenizer": {  # le même bloc que l'index des jetons de pré-entraînement
            "nom": tok.nom,
            "taille_vocabulaire": tok.taille_vocabulaire,
            "empreinte": empreinte_du_tokenizer(tok),
        },
    }
    texte = json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    verifier_place(len(texte.encode("utf-8")) + MARGE_PLACE, dossier)
    ecrire_texte(dossier / "index.json", texte)
    ecrire_texte(dossier / ".complet", "")


def lire_index(dossier: Path) -> dict:
    """L'index d'un jeu complet. Sans `.complet` : `DonneesManquantes` ; version inconnue : `ValueError`."""
    dossier = Path(dossier)
    if not (dossier / ".complet").is_file() or not (dossier / "index.json").is_file():
        raise DonneesManquantes(
            f"Le jeu d'affinage {dossier} est absent ou pas fini (pas de `.complet`). "
            "Refais `forge preparer` : il reprendra là où il s'est arrêté."
        )
    index = json.loads((dossier / "index.json").read_text(encoding="utf-8"))
    if index.get("version") != VERSION_DU_JEU:
        raise ValueError(
            f"Le jeu {dossier} est de version {index.get('version')!r}, cette version de la forge "
            f"lit la version {VERSION_DU_JEU}. Refais `forge preparer`."
        )
    return index


# --- Lire ---------------------------------------------------------------------------


@dataclass
class LotAffinage:
    """Un lot : `ids`, `cibles` (-100 là où rien n'est appris) et `documents`, `[lot, longueur]`.

    `reference` (`[lot]`, `float64`) n'existe que si le jeu a un `reference.bin` (DPO).
    """

    ids: torch.Tensor
    cibles: torch.Tensor
    documents: torch.Tensor
    reference: torch.Tensor | None = None


class ChargeurAffinage:
    """Forme des lots de rangées de `partie` (`train` ou `val`), mélangés à chaque époque.

    L'ordre ne dépend que de `(graine, époque)`, comme `ChargeurJetons`. Pour la sorte `dpo`,
    `taille_lot` est pair et le mélange porte sur des paires (choisie, rejetée), qui restent à
    la suite l'une de l'autre. `rangees` est le nombre de rangées de la partie.
    """

    def __init__(self, dossier: Path, partie: str, taille_lot: int, graine: int) -> None:
        if partie not in PARTIES:
            raise ValueError(f"Partie inconnue : {partie!r}. Les parties sont {', '.join(PARTIES)}.")
        self.dossier = Path(dossier)
        self.partie = partie
        self.index = lire_index(self.dossier)
        self.sorte = self.index["sorte"]
        self.longueur = int(self.index["longueur"])
        self.rangees = int(self.index["rangees"][partie])
        self.taille_lot = taille_lot
        self.graine = graine
        self._groupe = 2 if self.sorte == "dpo" else 1
        if taille_lot < self._groupe or taille_lot % self._groupe:
            raise ValueError(
                f"La taille de lot ({taille_lot}) doit être un nombre pair d'au moins 2 pour un jeu "
                "dpo : chaque paire (choisie, rejetée) tient dans le même lot."
            )
        if self.rangees == 0:
            raise ValueError(
                f"La partie {partie} du jeu {self.dossier} n'a aucune rangée. "
                "Prépare davantage d'exemples avec `forge preparer`."
            )
        self.unites = self.rangees // self._groupe
        largeur = self.longueur + 1
        dossier_partie = self.dossier / partie
        self._ids = self._ouvrir(dossier_partie / "ids.bin", _DTYPE_IDS, largeur)
        self._appris = self._ouvrir(dossier_partie / "appris.bin", _DTYPE_APPRIS, largeur)
        self._documents = self._ouvrir(dossier_partie / "documents.bin", _DTYPE_DOCUMENTS, largeur)
        fichier_reference = dossier_partie / "reference.bin"
        self._reference = (
            self._ouvrir(fichier_reference, _DTYPE_REFERENCE, 1) if fichier_reference.is_file() else None
        )
        self.epoque = 0
        self.position = 0
        self._melanger()

    def _ouvrir(self, fichier: Path, dtype: np.dtype, largeur: int) -> np.ndarray:
        attendu = self.rangees * largeur * dtype.itemsize
        taille = fichier.stat().st_size if fichier.is_file() else -1
        if taille != attendu:
            raise ValueError(
                f"{fichier} a {taille} octets, l'index en annonce {attendu} ({self.rangees} rangées) : "
                "le fichier a changé ou a été coupé. Refais `forge preparer` pour ce jeu."
            )
        return np.memmap(fichier, dtype=dtype, mode="r").reshape(self.rangees, largeur)

    def _melanger(self) -> None:
        hasard = np.random.default_rng([self.graine, self.epoque])
        self._ordre = hasard.permutation(self.unites)

    def lot(self) -> LotAffinage:
        """Le lot suivant, en `int64` ; `reference` en `float64` s'il y a un `reference.bin`."""
        voulues = self.taille_lot // self._groupe
        unites: list[int] = []
        while len(unites) < voulues:
            if self.position == self.unites:  # l'époque est finie : nouvel ordre de lecture
                self.epoque += 1
                self.position = 0
                self._melanger()
            pris = min(voulues - len(unites), self.unites - self.position)
            unites.extend(int(u) for u in self._ordre[self.position : self.position + pris])
            self.position += pris
        return self._lot([u * self._groupe + k for u in unites for k in range(self._groupe)])

    def lot_des_rangees(self, debut: int, fin: int) -> LotAffinage:
        """Les rangées `debut` à `fin` (exclue), dans l'ordre du fichier, sans bouger la position du
        chargeur : de quoi parcourir toute une partie, comme le calcul de la référence de la DPO."""
        if not 0 <= debut < fin <= self.rangees:
            raise ValueError(f"Rangées {debut} à {fin} demandées, la partie {self.partie} en a {self.rangees}.")
        return self._lot(list(range(debut, fin)))

    def _lot(self, numeros: list[int]) -> LotAffinage:
        ids = np.stack([self._ids[n] for n in numeros]).astype(np.int64)
        appris = np.stack([self._appris[n] for n in numeros]).astype(bool)
        documents = np.stack([self._documents[n] for n in numeros]).astype(np.int64)
        # Pas de cible à la frontière de deux documents : le premier jeton du suivant n'est
        # pas la suite de celui qui précède.
        suite = appris[:, 1:] & (documents[:, 1:] == documents[:, :-1])
        cibles = np.where(suite, ids[:, 1:], IGNORE)
        reference = None
        if self._reference is not None:
            valeurs = [self._reference[n, 0] for n in numeros]
            reference = torch.from_numpy(np.array(valeurs, dtype=np.float64))
        return LotAffinage(
            ids=torch.from_numpy(ids[:, :-1].copy()),
            cibles=torch.from_numpy(cibles.astype(np.int64)),
            documents=torch.from_numpy(documents[:, :-1].copy()),
            reference=reference,
        )

    def etat(self) -> dict:
        """Ce qu'il faut garder pour reprendre au même endroit (des nombres simples)."""
        return {
            "version": VERSION_DE_L_ETAT,
            "graine": self.graine,
            "epoque": self.epoque,
            "position": self.position,
            "rangees": self.rangees,
        }

    def restaurer(self, etat: dict) -> None:
        """Replace le chargeur à la position décrite par `etat` (venu de `etat()`)."""
        if etat.get("version") != VERSION_DE_L_ETAT:
            raise ValueError(
                f"État du chargeur d'affinage de version {etat.get('version')!r}, cette version de la "
                f"forge lit la version {VERSION_DE_L_ETAT}."
            )
        if etat["graine"] != self.graine:
            raise ValueError(
                f"La sauvegarde a été faite avec la graine {etat['graine']}, la configuration donne "
                f"{self.graine} : remets graine = {etat['graine']} pour reprendre le même entraînement."
            )
        if etat["rangees"] != self.rangees:
            raise ValueError(
                f"Le jeu {self.dossier} n'a plus les rangées de la sauvegarde ({etat['rangees']} alors, "
                f"{self.rangees} maintenant). Reprends avec le même jeu."
            )
        self.epoque = int(etat["epoque"])
        self.position = int(etat["position"])
        self._melanger()
