"""Les vecteurs : des listes de nombres, et ce qu'on en tire.

Un vecteur est une liste de nombres : (3, 1) en a deux, et un mot de ton IA en
a plusieurs centaines. Le produit scalaire de deux vecteurs dit s'ils vont dans
le même sens ; une matrice fois un vecteur, c'est un produit scalaire par ligne
de la matrice.

Le site refait exactement les mêmes calculs en TypeScript
(site/src/lib/partie-0/maths.ts) : seulement des + − × ÷ et des racines
carrées, dans le même ordre, qui donnent le même résultat au bit près.
"""

import math
from collections.abc import Sequence


def verifier_tailles(a: Sequence[float], b: Sequence[float]) -> None:
    """Arrête le calcul, avec un message qui dit quoi faire, si a et b n'ont pas
    la même taille. Le même message que le site (maths.ts), mot pour mot."""
    if len(a) != len(b):
        raise ValueError(
            f"Les deux vecteurs n’ont pas la même taille ({len(a)} et {len(b)} nombres)"
            "\u202f: il en faut autant."
        )


# region: scalaire
def produit_scalaire(
    a: Sequence[float],
    b: Sequence[float],
) -> float:
    """La somme des produits, case par case : a · b.

    (3, 1) · (1, 2) = 3 × 1 + 1 × 2 = 5.
    """
    # Deux tailles différentes : un message clair, en
    # français, plutôt que l'erreur anglaise de zip.
    verifier_tailles(a, b)
    s = 0.0
    # strict=True : zip vérifie lui aussi que les deux
    # vecteurs vont ensemble, au lieu d'oublier la fin
    # du plus long.
    for x, y in zip(a, b, strict=True):
        s += x * y
    return s


def norme(a: Sequence[float]) -> float:
    """La longueur du vecteur : la racine carrée de a · a."""
    return math.sqrt(produit_scalaire(a, a))


def cosinus(
    a: Sequence[float],
    b: Sequence[float],
) -> float | None:
    """Le cosinus de l'angle entre a et b, de −1 à 1.

    1 : même direction ; 0 : perpendiculaires ; −1 :
    directions opposées. None si l'un des deux est nul :
    un vecteur nul n'a pas de direction.
    """
    na = norme(a)
    nb = norme(b)
    if na == 0.0 or nb == 0.0:
        return None
    return produit_scalaire(a, b) / (na * nb)
# fin: scalaire


def somme(a: Sequence[float], b: Sequence[float]) -> list[float]:
    """La somme case par case : (3, 1) + (1, 2) = (4, 3)."""
    verifier_tailles(a, b)
    return [x + y for x, y in zip(a, b, strict=True)]


def quantite(n: int, mot: str) -> str:
    """« 1 colonne », « 4 colonnes » : le mot prend un s à partir de 2."""
    return f"{n} {mot}" if n <= 1 else f"{n} {mot}s"


# region: matrice
def matrice_fois_vecteur(
    m: list[list[float]],
    v: list[float],
) -> list[float]:
    """Chaque ligne de la matrice fois le vecteur : un
    produit scalaire par case du résultat.

    [[1, 2, 3], [0, 1, 0]] × [1, 1, 1] = [6, 1].
    """
    resultat = []
    for ligne in m:
        if len(ligne) != len(v):
            raise ValueError(
                f"La matrice a {quantite(len(ligne), 'colonne')}"
                f" et le vecteur {quantite(len(v), 'nombre')}"
                "\u202f: il en faut autant."
            )
        resultat.append(produit_scalaire(ligne, v))
    return resultat
# fin: matrice
