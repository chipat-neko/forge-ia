"""Écrire des fichiers d'un coup, et écrire les nombres à la française.

- `ecrire_atomique`, `ecrire_atomique_vers` et `ecrire_texte` : un fichier s'écrit sous un nom
  en `.tmp`, est forcé sur le disque (`os.fsync`), puis prend son vrai nom d'un seul coup. Si
  quoi que ce soit échoue (Ctrl+C, disque plein…), le `.tmp` est effacé et le fichier visé reste
  tel qu'il était : un demi-fichier n'existe jamais.
- `remplacer` : `os.replace`, réessayé quelques secondes quand Windows refuse l'accès.
- `nombre`, `entier`, `duree` : les formats de la typographie française.
"""

import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO

# Attentes entre deux essais de `os.replace` quand Windows refuse (fichier ouvert par un
# antivirus, l'Explorateur ou une évaluation en cours) : 3 secondes en tout.
_ATTENTES_DU_REMPLACEMENT = (0.1, 0.2, 0.4, 0.8, 1.6)

CONSEIL_PAR_DEFAUT = "Ferme-le, puis relance la même commande."

# L'espace fine insécable de la typographie française : milliers, avant « : ; ? ! % ».
ESPACE_FINE = "\u202f"


def remplacer(source: Path, cible: Path, *, conseil: str = CONSEIL_PAR_DEFAUT) -> None:
    """`os.replace`, réessayé quelques fois si Windows refuse l'accès un instant.

    `conseil` termine le message de l'erreur finale : ce qu'il faut faire ensuite.
    """
    for attente in _ATTENTES_DU_REMPLACEMENT:
        try:
            os.replace(source, cible)
            return
        except PermissionError:
            time.sleep(attente)
    try:
        os.replace(source, cible)
    except PermissionError as erreur:
        raise PermissionError(
            f"Windows refuse de remplacer {cible} : un autre programme le garde ouvert "
            f"(antivirus, Explorateur, évaluation en cours…). {conseil}"
        ) from erreur


def _temporaire(chemin: Path) -> Path:
    return chemin.with_name(chemin.name + ".tmp")


def _effacer(temporaire: Path) -> None:
    try:
        temporaire.unlink(missing_ok=True)  # Ctrl+C, disque plein ou autre : jamais de demi-fichier
    except OSError:
        pass  # jamais lu, et effacé à l'écriture suivante : l'erreur d'origine reste la seule dite


def ecrire_atomique_vers(chemin: Path, ecrire: Callable[[Path], None], *, conseil: str = CONSEIL_PAR_DEFAUT) -> None:
    """`ecrire(temporaire)`, forcé sur le disque, puis renommé en `chemin` d'un seul coup.

    Pour les écritures qui veulent un chemin et non un fichier ouvert (`safetensors`…).
    """
    temporaire = _temporaire(chemin)
    try:
        ecrire(temporaire)
        with open(temporaire, "rb+") as fichier:
            os.fsync(fichier.fileno())
        remplacer(temporaire, chemin, conseil=conseil)
    except BaseException:
        _effacer(temporaire)
        raise


def ecrire_atomique(chemin: Path, ecrire: Callable[[BinaryIO], None], *, conseil: str = CONSEIL_PAR_DEFAUT) -> None:
    """Écrit `chemin` d'un coup : `ecrire(fichier)` sur un `.tmp`, `fsync`, puis `remplacer`.

    Si quoi que ce soit échoue, le `.tmp` est effacé et `chemin` reste tel qu'il était.
    """
    temporaire = _temporaire(chemin)
    try:
        with open(temporaire, "wb") as fichier:
            ecrire(fichier)
            fichier.flush()
            os.fsync(fichier.fileno())
        remplacer(temporaire, chemin, conseil=conseil)
    except BaseException:
        _effacer(temporaire)
        raise


def ecrire_texte(
    chemin: Path, texte: str, *, conseil: str = CONSEIL_PAR_DEFAUT, fins_de_ligne: str | None = "\n"
) -> None:
    """Écrit `texte` d'un coup, en UTF-8 et avec des fins de ligne LF (sur tous les systèmes).

    `fins_de_ligne=None` laisse celles du système (CRLF sous Windows), comme `Path.write_text`.
    """
    if fins_de_ligne is None:
        texte = texte.replace("\n", os.linesep)
    octets = texte.encode("utf-8")
    ecrire_atomique(chemin, lambda fichier: fichier.write(octets), conseil=conseil)


# --- Les formats à la française ----------------------------------------------------------


def nombre(valeur: float, decimales: int = 1, *, milliers: str | None = None) -> str:
    """Un nombre à la française : virgule décimale.

    `milliers`, s'il est donné, sépare les milliers (une espace, ou l'espace fine insécable
    `\u202f`) ; sans lui, aucun séparateur.
    """
    if milliers is None:
        return f"{valeur:.{decimales}f}".replace(".", ",")
    return f"{valeur:,.{decimales}f}".replace(",", milliers).replace(".", ",")


def entier(valeur: float, *, milliers: str = " ") -> str:
    """Un entier avec une espace entre les milliers : 52 000."""
    return f"{round(valeur):,}".replace(",", milliers)


def duree(secondes: float) -> str:
    """Une durée lisible : 2 j 3 h, 1 h 05 min, 4 min 10 s, 12 s."""
    secondes = max(0, round(secondes))
    jours, reste = divmod(secondes, 86400)
    heures, reste = divmod(reste, 3600)
    minutes, secondes = divmod(reste, 60)
    if jours:
        return f"{jours} j {heures} h"
    if heures:
        return f"{heures} h {minutes:02d} min"
    if minutes:
        return f"{minutes} min {secondes:02d} s"
    return f"{secondes} s"
