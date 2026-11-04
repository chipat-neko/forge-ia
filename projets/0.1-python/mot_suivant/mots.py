"""Deviner le mot suivant en comptant, écrit pour apprendre Python.

L'idée tient en trois lignes :

1. On découpe un texte en mots.
2. Pour chaque mot, on compte les mots qui le suivent dans le texte.
3. Pour deviner la suite d'un mot, on prend celui qui le suit le plus souvent.

En recommençant à partir du mot deviné, on écrit une suite de mots. Le site
refait exactement le même calcul en TypeScript (site/src/lib/partie-0/mot-suivant.ts).
"""

import re
from collections import Counter
from pathlib import Path
from typing import NamedTuple

# Les lettres d'un mot, en minuscules : l'alphabet, puis les lettres accentuées du français.
LETTRES = "abcdefghijklmnopqrstuvwxyzàâäçéèêëîïôöùûüÿœæ"

# Un mot est une suite de lettres, d'apostrophes (droite ou courbe) et de traits d'union.
# Le point, le point d'exclamation et le point d'interrogation sont des mots à part :
# ils marquent la fin d'une phrase. Tout le reste sépare les mots.
MOTIF = re.compile(rf"[{LETTRES}'’-]+|[.!?]")

CHEMIN_TEXTE = Path(__file__).resolve().parent.parent / "donnees" / "texte.txt"


def charger_texte() -> str:
    """Lit le texte du projet (donnees/texte.txt, en UTF-8)."""
    with open(CHEMIN_TEXTE, encoding="utf-8", newline="") as fichier:
        return fichier.read()


# region: decouper
def decouper_mots(texte: str) -> list[str]:
    """Découpe un texte en mots, en minuscules : « Le fer ! » donne ["le", "fer", "!"]."""
    return MOTIF.findall(texte.lower())
# fin: decouper


# region: compter
def compter_suivants(mots: list[str]) -> dict[str, Counter[str]]:
    """Pour chaque mot, compte les mots qui le suivent.

    Les clés sont dans l'ordre où les mots apparaissent pour la première fois.
    """
    suivants: dict[str, Counter[str]] = {}
    # zip associe chaque mot à son voisin de droite : (mots[0], mots[1]), (mots[1], mots[2])…
    for mot, suivant in zip(mots, mots[1:]):
        if mot not in suivants:
            suivants[mot] = Counter()
        suivants[mot][suivant] += 1
    return suivants
# fin: compter


# region: trier
def suivants_tries(compte: Counter[str]) -> list[tuple[str, int]]:
    """Les suivants d'un mot et leurs comptes, du plus fréquent au moins fréquent.

    À compte égal, dans l'ordre des points de code, comme pour predire.
    """
    return sorted(compte.items(), key=lambda paire: (-paire[1], paire[0]))
# fin: trier


# region: predire
def predire(suivants: dict[str, Counter[str]], mot: str) -> str | None:
    """Le mot qui suit le plus souvent `mot`, ou None si rien ne le suit.

    En cas d'égalité, on prend le plus petit dans l'ordre des points de code :
    « le plus petit » de (-compte, mot), c'est le plus grand compte, puis le
    premier mot dans cet ordre.
    """
    compte = suivants.get(mot)
    if not compte:
        return None
    return min(compte, key=lambda m: (-compte[m], m))
# fin: predire


# region: generer
def generer(suivants: dict[str, Counter[str]], depart: str, longueur: int) -> list[str]:
    """La suite qui commence par `depart`, de `longueur` mots au plus.

    Elle s'arrête plus tôt quand rien ne suit le dernier mot. Si `depart` n'est
    pas dans le texte, rien ne le suit : la suite vaut [depart].
    """
    if longueur <= 0:
        return []
    suite = [depart]
    while len(suite) < longueur:
        suivant = predire(suivants, suite[-1])
        if suivant is None:
            break
        suite.append(suivant)
    return suite
# fin: generer


def premiere_reprise(suite: list[str]) -> int | None:
    """L'indice du premier mot déjà vu plus tôt dans la suite, ou None.

    À partir de ce mot, la suite tourne en rond : le même mot est toujours
    suivi du même mot.
    """
    vus: set[str] = set()
    for indice, mot in enumerate(suite):
        if mot in vus:
            return indice
        vus.add(mot)
    return None


# region: suivre
class Suite(NamedTuple):
    """Une suite de mots, et l'endroit où elle se met à tourner en rond."""

    mots: list[str]  # les mots de la suite, en commençant par le mot de départ
    reprise: int | None  # l'indice du premier mot qui revient, ou None si aucun ne revient


def suivre(suivants: dict[str, Counter[str]], depart: str, longueur: int) -> Suite:
    """La suite de `longueur` mots au plus qui part de `depart`, avec sa première reprise."""
    mots = generer(suivants, depart, longueur)
    return Suite(mots, premiere_reprise(mots))
# fin: suivre
