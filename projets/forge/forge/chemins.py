"""Chemins des données de « ton IA » : dossier racine, sous-dossiers et place libre.

Les données lourdes (téléchargements, jetons, poids, sauvegardes) restent hors
du dépôt, sous le dossier `FORGE_DONNEES`.
"""

import math
import os
import shutil
from pathlib import Path

from forge.fichiers import nombre

# Un « Go » est ici 1024³ octets : c'est la valeur que l'Explorateur de Windows
# affiche, et celle de `outils/env-forge.ps1`.
OCTETS_PAR_GO = 1024**3


class PlaceInsuffisante(Exception):
    """Il n'y a pas assez de place libre sur le disque pour continuer."""


def racine_donnees() -> Path:
    """Dossier des données : `FORGE_DONNEES`, sinon `~/forge-ia-donnees`."""
    valeur = os.environ.get("FORGE_DONNEES")
    if valeur:
        return Path(valeur)
    return Path.home() / "forge-ia-donnees"


def sous_forge_donnees(nom_ou_chemin: str | Path, sorte: str) -> Path:
    """Un chemin absolu est gardé tel quel ; un nom va sous `FORGE_DONNEES/<sorte>/`."""
    chemin = Path(nom_ou_chemin)
    return chemin if chemin.is_absolute() else racine_donnees() / sorte / chemin


def plus_proche_existant(chemin: Path) -> Path:
    """Remonte jusqu'au premier dossier qui existe (le dossier visé peut ne pas être créé)."""
    chemin = chemin.absolute()
    while not chemin.exists() and chemin != chemin.parent:
        chemin = chemin.parent
    return chemin.resolve()


def en_go(octets: int, arrondi) -> str:
    """Écrit une taille en Go (1024³ octets) avec une décimale (virgule française)."""
    return nombre(arrondi(octets / OCTETS_PAR_GO * 10) / 10, 1)


def verifier_place(octets_requis: int, chemin: Path | None = None) -> None:
    """Vérifie qu'il reste `octets_requis` octets libres sur le disque de `chemin`.

    Sans `chemin`, on regarde le disque du dossier des données. Lève
    `PlaceInsuffisante`, avec un message qui dit combien il manque, si la place
    ne suffit pas. Les chiffres sont arrondis de façon prudente : le manque et
    la place nécessaire vers le haut, la place libre vers le bas.
    """
    cible = plus_proche_existant(chemin if chemin is not None else racine_donnees())
    libres = shutil.disk_usage(cible).free
    if libres >= octets_requis:
        return
    lecteur = cible.drive or cible.anchor
    raise PlaceInsuffisante(
        f"Il manque {en_go(octets_requis - libres, math.ceil)} Go sur {lecteur} : "
        f"{en_go(libres, math.floor)} Go libres, "
        f"{en_go(octets_requis, math.ceil)} Go nécessaires. "
        "Libère de la place, puis relance la même commande : "
        "elle reprendra là où elle s'est arrêtée."
    )
