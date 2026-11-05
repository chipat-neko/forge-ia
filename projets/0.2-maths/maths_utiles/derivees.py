"""La pente : de quel côté l'erreur descend, et comment la suivre.

Une IA apprend en réglant ses poids pour faire baisser son erreur. Ici, un seul
poids x, et une erreur toute simple, (x − 3)² + 1, la plus petite en x = 3. Sa
pente dit de quel côté l'erreur descend : on fait un pas dans ce sens, de la
taille du taux, puis on recommence. C'est la descente de gradient.

Le site refait l'erreur, la pente et la descente en TypeScript
(site/src/lib/partie-0/maths.ts), au bit près. La pente approchée et l'exemple
de la règle de la chaîne ne servent qu'en Python : le site lit leurs valeurs
dans tests/attendus.json.
"""

from collections.abc import Callable

# Les taux de la figure de la descente, du plus prudent au plus grand.
TAUX_DESCENTE = [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0, 1.05, 1.2]


# region: erreur
def erreur(x: float) -> float:
    """L'erreur selon le poids x : (x − 3)² + 1.

    La plus petite erreur, 1, est atteinte en x = 3.
    """
    return (x - 3.0) * (x - 3.0) + 1.0
# fin: erreur


# region: pente
def pente(x: float) -> float:
    """La pente exacte de l'erreur en x : 2 × (x − 3).

    Négative à gauche de 3 (l'erreur descend vers la
    droite), positive à droite, nulle au fond.
    """
    return 2.0 * (x - 3.0)


def pente_approchee(
    f: Callable[[float], float],
    x: float,
    h: float = 1e-6,
) -> float:
    """La pente de f en x, sans formule : on regarde f un
    tout petit peu à droite et à gauche de x.

    (f(x + h) − f(x − h)) ÷ 2h : la montée, divisée par
    la distance parcourue.
    """
    return (f(x + h) - f(x - h)) / (2 * h)
# fin: pente


# region: descendre
def descendre(
    x0: float,
    taux: float,
    nb_pas: int,
) -> list[float]:
    """Les positions de la descente : x0, puis une par pas.

    À chaque pas, x recule de taux × pente(x) : vers la
    droite si la pente est négative, vers la gauche si
    elle est positive.
    """
    positions = [x0]
    x = x0
    for _ in range(nb_pas):
        x = x - taux * pente(x)
        positions.append(x)
    return positions
# fin: descendre


def pas_pour_atteindre(
    x0: float,
    taux: float,
    seuil: float,
    max_pas: int = 100,
) -> int | None:
    """Le premier pas n où l'erreur passe sous le seuil (0 si x0 y est déjà).

    None si la descente n'y arrive pas en max_pas pas : elle oscille, ou elle
    s'éloigne du fond.
    """
    x = x0
    for n in range(max_pas + 1):
        if erreur(x) < seuil:
            return n
        x = x - taux * pente(x)
    return None


# region: chaine
def interieur(x: float) -> float:
    """f(x) = 2x + 1 : sa pente vaut 2."""
    return 2.0 * x + 1.0


def exterieur(u: float) -> float:
    """g(u) = u² : sa pente vaut 2u."""
    return u * u


def composee(x: float) -> float:
    """h(x) = g(f(x)) = (2x + 1)² : f d'abord, puis g."""
    return exterieur(interieur(x))


def pente_composee(x: float) -> float:
    """La règle de la chaîne : la pente de g en f(x),
    fois la pente de f. Ici 2 × (2x + 1), fois 2,
    soit 4 × (2x + 1).
    """
    u = interieur(x)
    return (2.0 * u) * 2.0


def exemple_chaine() -> dict:
    """En x = 1 : h(x), sa pente par la règle de la
    chaîne, et la pente approchée, qui doit lui
    ressembler."""
    x = 1.0
    return {
        "x": x,
        "h": composee(x),
        "exacte": pente_composee(x),
        "approchee": pente_approchee(composee, x),
    }
# fin: chaine
