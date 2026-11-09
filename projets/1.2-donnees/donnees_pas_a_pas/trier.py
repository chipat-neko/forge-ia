"""Trier des documents : trop court, doublon, licence ou langage refusés, ou gardé.

Ce fichier n'écrit aucun nettoyage de son cru : il appelle celui de forge, le moteur de
« ton IA » (`forge.donnees`), dans l'ordre où le téléchargement l'appelle. Pour chaque
ligne d'une source, `trier` rend un `Verdict` qui dit si le document est gardé, et sinon
pourquoi. Les mêmes textes sont gardés, dans le même ordre, que par
`forge.donnees.telechargement.telecharger` (tests/test_trier.py le vérifie).
"""

import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from forge.donnees.melange import est_validation
from forge.donnees.nettoyage import empreinte_du_texte_nettoye, nettoyer
from forge.donnees.sources import Source

Raison = Literal["gardé", "trop court", "doublon", "licence", "langage"]

# Dans l'ordre où on les affiche : d'abord ce qui est gardé, puis les raisons d'écart.
RAISONS: tuple[Raison, ...] = ("gardé", "trop court", "doublon", "licence", "langage")

# Le téléchargement de forge retient les 64 premiers bits de l'empreinte (16 chiffres
# hexadécimaux) pour reconnaître un doublon : on fait de même, pour garder les mêmes textes.
CHIFFRES_DE_LA_CLE = 16


@dataclass
class Verdict:
    """Ce que le tri décide d'un document.

    `texte` (nettoyé), `empreinte` et `validation` ne sont remplis que pour un document gardé ;
    un doublon garde l'empreinte qu'il partage avec le document déjà vu.
    """

    garde: bool
    raison: Raison
    texte: str | None = None
    empreinte: str | None = None
    validation: bool | None = None


# region: nettoyer
def texte_propre(source: Source, ligne: dict) -> str | None:
    """Le texte nettoyé de la ligne, ou `None` : pas de texte, ou moins de 200 caractères."""
    brut = ligne.get(source.colonne)
    if not isinstance(brut, str):
        return None
    return nettoyer(brut)
# fin: nettoyer


# region: licence
def raison_du_refus(ligne: dict) -> Raison:
    """Pourquoi la source refuse la ligne : un autre langage que Python, sinon la licence."""
    if ligne.get("language") != "Python":
        return "langage"
    return "licence"
# fin: licence


# region: doublons
def est_un_doublon(vues: set[str], empreinte: str) -> bool:
    """Dit si cette empreinte a déjà été vue, et la retient sinon."""
    cle = empreinte[:CHIFFRES_DE_LA_CLE]
    if cle in vues:
        return True
    vues.add(cle)
    return False
# fin: doublons


# region: validation
def va_en_validation(empreinte: str) -> bool:
    """Un document sur 200 (0,5 %) est mis de côté pour la validation, d'après son empreinte."""
    return est_validation(empreinte)
# fin: validation


# region: trier
def trier(lignes: Iterable[dict], source: Source) -> Iterator[Verdict]:
    """Un verdict par ligne, dans l'ordre : licence et langage, longueur, doublon, puis gardé."""
    vues: set[str] = set()
    for ligne in lignes:
        if not source.garder(ligne):
            yield Verdict(garde=False, raison=raison_du_refus(ligne))
            continue
        texte = texte_propre(source, ligne)
        if texte is None:
            yield Verdict(garde=False, raison="trop court")
            continue
        empreinte = empreinte_du_texte_nettoye(texte)
        if est_un_doublon(vues, empreinte):
            yield Verdict(garde=False, raison="doublon", empreinte=empreinte)
            continue
        yield Verdict(garde=True, raison="gardé", texte=texte, empreinte=empreinte, validation=va_en_validation(empreinte))
# fin: trier


# region: compter
def compter_raisons(verdicts: Iterable[Verdict]) -> dict[str, int]:
    """Combien de verdicts pour chaque raison, dans l'ordre de `RAISONS` (zéro compris)."""
    comptes = {raison: 0 for raison in RAISONS}
    for verdict in verdicts:
        comptes[verdict.raison] += 1
    return comptes
# fin: compter


def lire_jsonl(chemin: Path) -> Iterator[dict]:
    """Les lignes d'un fichier `.jsonl` : un document (un dictionnaire) par ligne non vide."""
    with open(chemin, encoding="utf-8") as fichier:
        for ligne in fichier:
            if ligne.strip():
                yield json.loads(ligne)
