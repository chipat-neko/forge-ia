"""Le hasard partagé de la forge : SplitMix32, calculé en entiers seulement.

C'est le hasard du mini-modèle (`projets/mini-modele/mini_modele/calcul.py`) : les trois premières
méthodes, `__init__`, `suivant32` et `uniforme`, en sont une copie exacte (un test compare les textes).
Les trois suivantes, `entier`, `choisir` et `melanger`, n'emploient que des entiers : le site les refait
à l'identique en TypeScript (plan 8), et une même graine donne la même suite des deux côtés.

Il sert aux graines reproductibles : tirage des contraintes, mélanges, jeux d'évaluation générés.
"""

from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")

# Le plus grand entier sûr de JavaScript, 2^53 − 1 (Number.MAX_SAFE_INTEGER).
ENTIER_SUR_MAX = 9007199254740991


class Hasard:
    """Le hasard reproductible du mini-modèle : SplitMix32.

    Une même graine donne la même suite en Python et en TypeScript, sur toutes
    les machines. La graine est un entier, ramené à 32 bits (de 0 à 2^32 − 1).
    Les graines refusées sont les mêmes qu'en TypeScript : ce qui n'est pas un
    nombre entier (True compris), et les entiers au-delà des entiers sûrs de
    JavaScript (2^53 − 1). Un flottant entier comme 7.0 est accepté, puisqu'en
    JavaScript 7.0 et 7 sont le même nombre.
    """

    def __init__(self, graine: int) -> None:
        entier = isinstance(graine, int) or (isinstance(graine, float) and graine.is_integer())
        if isinstance(graine, bool) or not entier:
            raise TypeError(
                f"La graine du hasard doit être un entier (reçu {graine!r}). Donne un entier de 0 à 2^32 − 1."
            )
        if not -ENTIER_SUR_MAX <= graine <= ENTIER_SUR_MAX:
            raise ValueError(
                f"La graine du hasard dépasse les entiers sûrs de JavaScript (reçu {graine!r}). "
                "Donne un entier de 0 à 2^32 − 1."
            )
        self.etat = int(graine) & 0xFFFFFFFF

    def suivant32(self) -> int:
        """Le prochain entier sur 32 bits, de 0 à 2^32 − 1."""
        self.etat = (self.etat + 0x9E3779B9) & 0xFFFFFFFF
        z = self.etat
        z = ((z ^ (z >> 16)) * 0x21F0AAAD) & 0xFFFFFFFF
        z = ((z ^ (z >> 15)) * 0x735A2D97) & 0xFFFFFFFF
        return z ^ (z >> 15)

    def uniforme(self) -> float:
        """Un flottant de [0, 1[ : suivant32 divisé par 2^32 (une division exacte)."""
        return self.suivant32() / 4294967296.0

    def entier(self, a: int, b: int) -> int:
        """Un entier de a à b, bornes comprises : a + suivant32() % (b − a + 1), en entiers seulement."""
        if b < a:
            raise ValueError(
                f"Hasard.entier : l'intervalle est vide (de {a} à {b}). Donne a inférieur ou égal à b."
            )
        return a + self.suivant32() % (b - a + 1)

    def choisir(self, suite: Sequence[T]) -> T:
        """Un élément de la suite, au hasard : suite[entier(0, len(suite) − 1)]."""
        if len(suite) == 0:
            raise ValueError("Hasard.choisir : la suite est vide. Donne au moins un élément à choisir.")
        return suite[self.entier(0, len(suite) - 1)]

    def melanger(self, liste: Sequence[T]) -> list[T]:
        """Une copie mélangée de la liste (la liste reçue ne bouge pas) : Fisher-Yates, de la fin vers le début."""
        copie = list(liste)
        for i in range(len(copie) - 1, 0, -1):
            j = self.entier(0, i)
            copie[i], copie[j] = copie[j], copie[i]
        return copie
