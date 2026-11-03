"""Les sauvegardes de l'entraînement : écrites d'un coup, jamais prises à moitié.

Une sauvegarde est un dictionnaire (le modèle, l'optimiseur, le pas, la position dans les
données, l'état du hasard, la configuration) écrit par `torch.save`. Une coupure de courant
ou un plantage peut survenir pendant l'écriture : on écrit donc d'abord dans `nom.tmp`, on
force les octets sur le disque (`os.fsync`), et seulement ensuite le fichier prend son vrai
nom, d'un seul coup (`os.replace`). Un `.tmp` resté là après une panne n'est jamais lu.

Dans le dossier des sauvegardes, on garde :

- les deux dernières `etape-0000123.pt` (le numéro est le pas, sur 7 chiffres) : si la
  dernière était abîmée, la précédente sert ;
- `meilleur.pt`, le modèle qui a la plus petite perte de validation.

Avant d'écrire, on vérifie qu'il reste deux fois la taille estimée de la sauvegarde : la
nouvelle et l'ancienne coexistent le temps de l'écriture.
"""

import errno
import os
import re
import sys
from pathlib import Path

import torch

from forge.chemins import PlaceInsuffisante, verifier_place

# `etape-0000123.pt` : le pas, sur 7 chiffres. Rien d'autre (ni `.tmp`, ni copie) n'est pris.
MOTIF_ETAPE = re.compile(r"etape-(\d{7})\.pt")
ETAPES_GARDEES = 2

# Marge pour ce que `torch.save` écrit en plus des tenseurs (noms, nombres, structure).
_MARGE_OCTETS = 1024**2

# Codes d'erreur d'un disque plein : ENOSPC partout, et sous Windows ERROR_DISK_FULL (112)
# ou ERROR_HANDLE_DISK_FULL (39).
_ERREURS_WINDOWS_DISQUE_PLEIN = {39, 112}


def nom_etape(pas: int) -> str:
    """Nom de la sauvegarde du pas `pas` : `etape-0000123.pt`."""
    return f"etape-{pas:07d}.pt"


def _estimer_octets(etat) -> int:
    """Taille approchée de `etat` une fois écrit : la mémoire de ses tenseurs, plus une marge.

    Un tenseur partagé (le plongement et la sortie du modèle sont la même matrice) n'est
    compté qu'une fois, comme `torch.save` ne l'écrit qu'une fois.
    """
    vus: set[int] = set()
    total = 0

    def parcourir(valeur) -> None:
        nonlocal total
        if isinstance(valeur, torch.Tensor):
            stockage = valeur.untyped_storage()
            if stockage.data_ptr() not in vus:
                vus.add(stockage.data_ptr())
                total += stockage.nbytes()
        elif isinstance(valeur, dict):
            for element in valeur.values():
                parcourir(element)
        elif isinstance(valeur, list | tuple):
            for element in valeur:
                parcourir(element)

    parcourir(etat)
    return total + _MARGE_OCTETS


def est_disque_plein(erreur: OSError) -> bool:
    """L'erreur dit-elle que le disque est plein ?"""
    return erreur.errno == errno.ENOSPC or getattr(erreur, "winerror", None) in _ERREURS_WINDOWS_DISQUE_PLEIN


def _etapes(dossier: Path) -> list[tuple[int, Path]]:
    """Les sauvegardes `etape-*.pt` complètes de `dossier`, du pas le plus haut au plus bas."""
    if not dossier.is_dir():
        return []
    trouvees = []
    for fichier in dossier.iterdir():
        lu = MOTIF_ETAPE.fullmatch(fichier.name)
        if lu is not None and fichier.is_file():
            trouvees.append((int(lu.group(1)), fichier))
    return sorted(trouvees, reverse=True)


def sauvegarder(dossier: Path, etat: dict, nom: str) -> Path:
    """Écrit `etat` dans `dossier/nom`, d'un coup ; renvoie le chemin écrit.

    Ordre des opérations : effacer les `.tmp` d'une panne précédente, vérifier la place
    (deux fois la taille estimée), écrire `nom.tmp`, `os.fsync`, `os.replace` vers `nom`,
    puis, pour une `etape-*.pt`, effacer les plus anciennes au-delà des deux dernières.

    Si la place manque, `PlaceInsuffisante` est levée avant d'écrire quoi que ce soit. Si le
    disque se remplit pendant l'écriture, le `.tmp` est effacé et `PlaceInsuffisante` est
    levée aussi. Dans les deux cas, les sauvegardes déjà là restent intactes.
    """
    dossier = Path(dossier)
    if dossier.is_dir():
        for reste in dossier.glob("*.pt.tmp"):
            reste.unlink(missing_ok=True)  # une écriture coupée : elle ne vaut rien et prend de la place
    estimation = _estimer_octets(etat)
    verifier_place(estimation * 2, dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / nom
    temporaire = chemin.with_name(nom + ".tmp")
    try:
        with open(temporaire, "wb") as fichier:
            torch.save(etat, fichier)
            fichier.flush()
            os.fsync(fichier.fileno())
        os.replace(temporaire, chemin)
    except OSError as erreur:
        temporaire.unlink(missing_ok=True)
        if est_disque_plein(erreur):
            go = f"{estimation / 1024**3:.1f}".replace(".", ",")
            raise PlaceInsuffisante(
                f"Le disque s'est rempli pendant l'écriture de {chemin} (environ {go} Go à "
                "écrire). Les sauvegardes précédentes sont intactes. Libère de la place, puis "
                "relance avec --reprendre : l'entraînement repartira de la dernière sauvegarde "
                "complète."
            ) from erreur
        raise
    except BaseException:
        temporaire.unlink(missing_ok=True)  # Ctrl+C ou autre : jamais de demi-fichier
        raise
    if MOTIF_ETAPE.fullmatch(nom):
        for _, ancienne in _etapes(dossier)[ETAPES_GARDEES:]:
            ancienne.unlink(missing_ok=True)
    return chemin


def charger(chemin: Path) -> dict:
    """Lit une sauvegarde, tenseurs sur le processeur (le modèle les recopie où il faut)."""
    return torch.load(chemin, map_location="cpu", weights_only=True)


def charger_derniere(dossier: Path) -> dict | None:
    """La sauvegarde `etape-*.pt` complète du pas le plus haut, ou `None` s'il n'y en a pas.

    Les `.tmp` (écritures coupées) sont ignorés. Si la plus récente ne se lit pas (fichier
    abîmé), on le signale et on prend la précédente.
    """
    for _, fichier in _etapes(Path(dossier)):
        try:
            return charger(fichier)
        except Exception as erreur:  # fichier tronqué ou abîmé : on passe au précédent
            print(
                f"Attention : la sauvegarde {fichier} est illisible ({type(erreur).__name__}), "
                "je prends la précédente.",
                file=sys.stderr,
            )
    return None
