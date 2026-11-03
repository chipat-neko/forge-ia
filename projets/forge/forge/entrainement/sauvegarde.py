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
import math
import os
import re
import shutil
import sys
import time
from collections.abc import Callable
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


def _cause_disque_plein(erreur: BaseException) -> bool:
    """Un disque plein se cache-t-il dans `erreur` ou dans les erreurs qui l'ont provoquée ?

    `torch.save` ne laisse pas passer l'erreur du disque : il lève une `RuntimeError`
    (« unexpected pos… »), et l'`OSError` d'origine n'est plus que son contexte.
    """
    vues: set[int] = set()
    while erreur is not None and id(erreur) not in vues:
        vues.add(id(erreur))
        if isinstance(erreur, OSError) and est_disque_plein(erreur):
            return True
        erreur = erreur.__cause__ or erreur.__context__
    return False


def _octets_libres(dossier: Path) -> int:
    try:
        return shutil.disk_usage(dossier).free
    except OSError:
        return 2**63  # inconnu : on ne conclut pas à un disque plein


def _go(octets: int, arrondi) -> str:
    """Une taille en Go (1024³ octets), une décimale, virgule française."""
    return f"{arrondi(octets / 1024**3 * 10) / 10:.1f}".replace(".", ",")


def _message_disque_plein(chemin: Path, estimation: int) -> str:
    """Le message d'un disque rempli pendant l'écriture : combien il manque, et quoi faire."""
    libres = _octets_libres(chemin.parent)  # après l'effacement du `.tmp`
    besoin = 2 * estimation
    if libres < besoin:
        manque = (
            f"Il manque {_go(besoin - libres, math.ceil)} Go : {_go(libres, math.floor)} Go libres, "
            f"{_go(besoin, math.ceil)} Go nécessaires (la nouvelle sauvegarde et l'ancienne, le "
            "temps de l'écriture)."
        )
    else:
        manque = (
            f"Un autre programme a sans doute rempli le disque en même temps : il faut "
            f"{_go(besoin, math.ceil)} Go libres pour écrire cette sauvegarde."
        )
    return (
        f"Le disque s'est rempli pendant l'écriture de {chemin}. {manque} Les sauvegardes "
        "précédentes sont intactes. Libère de la place, puis relance avec --reprendre : "
        "l'entraînement repartira de la dernière sauvegarde complète."
    )


# Attentes entre deux essais de `os.replace` quand Windows refuse (fichier ouvert par un
# antivirus, l'Explorateur ou une évaluation en cours) : 3 secondes en tout.
_ATTENTES_DU_REMPLACEMENT = (0.1, 0.2, 0.4, 0.8, 1.6)


def remplacer(temporaire: Path, chemin: Path) -> None:
    """`os.replace`, réessayé quelques fois si Windows refuse l'accès un instant."""
    for attente in _ATTENTES_DU_REMPLACEMENT:
        try:
            os.replace(temporaire, chemin)
            return
        except PermissionError:
            time.sleep(attente)
    try:
        os.replace(temporaire, chemin)
    except PermissionError as erreur:
        raise PermissionError(
            f"Windows refuse de remplacer {chemin} : un autre programme le garde ouvert "
            "(antivirus, Explorateur, évaluation en cours…). Ferme-le, puis relance avec "
            "--reprendre : l'entraînement repartira de la dernière sauvegarde complète."
        ) from erreur


def _avertir(message: str) -> None:
    print(f"Attention : {message}", file=sys.stderr)


def sauvegarder(dossier: Path, etat: dict, nom: str, noter: Callable[[str], None] | None = None) -> Path:
    """Écrit `etat` dans `dossier/nom`, d'un coup ; renvoie le chemin écrit.

    Ordre des opérations : effacer les `.tmp` d'une panne précédente, vérifier la place
    (deux fois la taille estimée), écrire `nom.tmp`, `os.fsync`, `os.replace` vers `nom`
    (réessayé quelques secondes si Windows refuse l'accès), puis, pour une `etape-*.pt`,
    effacer les plus anciennes au-delà des deux dernières.

    Si la place manque, `PlaceInsuffisante` est levée avant d'écrire quoi que ce soit. Si le
    disque se remplit pendant l'écriture, le `.tmp` est effacé et `PlaceInsuffisante` est
    levée aussi, avec ce qu'il manque. Dans les deux cas, les sauvegardes déjà là restent
    intactes.

    Ne pas réussir à effacer une ancienne sauvegarde n'arrête rien : `noter` reçoit un
    message (sans `noter`, il va sur la sortie d'erreur).
    """
    dossier = Path(dossier)
    noter = noter or _avertir
    if dossier.is_dir():
        for reste in dossier.glob("*.pt.tmp"):
            try:
                reste.unlink(missing_ok=True)  # une écriture coupée : elle ne vaut rien et prend de la place
            except OSError:
                pass  # on réessaiera à la sauvegarde suivante
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
        remplacer(temporaire, chemin)
    except BaseException as erreur:
        # Disque plein ? On regarde AVANT d'effacer le `.tmp`, qui occupe encore la place.
        plein = isinstance(erreur, Exception) and (
            _cause_disque_plein(erreur) or _octets_libres(dossier) < estimation
        )
        try:
            temporaire.unlink(missing_ok=True)  # Ctrl+C, disque plein ou autre : jamais de demi-fichier
        except OSError:
            pass  # jamais lu (ce n'est pas une `etape-*.pt`), et effacé à la sauvegarde suivante
        if plein:
            raise PlaceInsuffisante(_message_disque_plein(chemin, estimation)) from erreur
        raise
    if MOTIF_ETAPE.fullmatch(nom):
        for _, ancienne in _etapes(dossier)[ETAPES_GARDEES:]:
            try:
                ancienne.unlink(missing_ok=True)
            except OSError as erreur:
                noter(f"impossible d'effacer l'ancienne sauvegarde {ancienne.name} ({erreur}) ; elle reste là.")
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
