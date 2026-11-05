"""Un réseau 2-2-1 à sigmoïdes, entraîné à la main sur le OU exclusif, en Python pur.

Le réseau a 2 entrées, une couche cachée de 2 neurones, et 1 neurone de
sortie. Chaque neurone fait une somme pondérée, puis l'écrase entre 0 et 1
avec la sigmoïde : la sortie p est la probabilité que la réponse soit 1.
Ses 9 poids partent du hasard (graine GRAINE), puis la descente de gradient
de 0.2 les corrige, pas après pas, pour faire baisser l'erreur de 0.2, −ln
de la probabilité donnée à la bonne réponse.

Les dérivées sont calculées à la main, de la sortie vers l'entrée : c'est la
rétropropagation. Rien d'autre que math.exp et math.log : pas de PyTorch ici.
Le module avec_pytorch refait le même calcul avec PyTorch, pour comparer.
"""

import math
import random
from dataclasses import dataclass

from premier_reseau.neurone import POINTS, PORTES

# Les 4 points du OU exclusif, chacun avec sa réponse : ((0, 0), 0), ((0, 1), 1)…
DONNEES = list(zip(POINTS, PORTES["ou_exclusif"]))
# La graine du hasard qui tire les poids de départ. Avec 1234, puis 1235, le réseau reste coincé
# (perte finale 0,35, deux réponses à 0,5) : 1236 est la première graine au-dessus qui apprend.
GRAINE = 1236
TAUX = 1.0  # le taux d'apprentissage : la longueur de chaque pas
NB_PAS = 3000  # le nombre de pas de descente
# L'entraînement a réussi si la perte finale passe sous ce seuil, et si les 4 réponses arrondies sont justes.
SEUIL_PERTE = 0.05


@dataclass
class Reseau:
    """Les 9 poids du réseau 2-2-1."""

    w1: list[list[float]]  # w1[j][i] : le poids de l'entrée i vers le neurone caché j (2 × 2)
    b1: list[float]  # le biais de chaque neurone caché (2)
    w2: list[float]  # w2[j] : le poids du neurone caché j vers la sortie (2)
    b2: float  # le biais de la sortie (1)


@dataclass
class Gradients:
    """La dérivée de l'erreur par rapport à chaque poids : la même forme que Reseau."""

    w1: list[list[float]]
    b1: list[float]
    w2: list[float]
    b2: float


def initialiser(graine: int) -> Reseau:
    """Des poids de départ tirés au hasard entre −1 et 1, dans l'ordre w1, b1, w2, b2."""
    hasard = random.Random(graine)
    w1 = [[hasard.uniform(-1, 1) for _ in range(2)] for _ in range(2)]
    b1 = [hasard.uniform(-1, 1) for _ in range(2)]
    w2 = [hasard.uniform(-1, 1) for _ in range(2)]
    b2 = hasard.uniform(-1, 1)
    return Reseau(w1, b1, w2, b2)


def nb_poids(r: Reseau) -> int:
    """Le nombre de poids du réseau : 4 + 2 + 2 + 1 = 9."""
    return sum(len(ligne) for ligne in r.w1) + len(r.b1) + len(r.w2) + 1


# region: sigmoide
def sigmoide(z: float) -> float:
    """Écrase z entre 0 et 1 : 0,5 pour z = 0, presque 1 pour z grand, presque 0 pour z très négatif."""
    return 1 / (1 + math.exp(-z))
# fin: sigmoide


# region: propager
@dataclass
class Passage:
    """Tout ce que calcule un point en traversant le réseau : la rétropropagation en a besoin."""

    z1: list[float]  # la somme pondérée de chaque neurone caché
    h: list[float]  # leur sortie, après la sigmoïde
    z2: float  # la somme pondérée du neurone de sortie
    p: float  # sa sortie : la probabilité que la réponse soit 1


def propager(r: Reseau, x: tuple[int, int]) -> Passage:
    """Fait traverser le réseau au point x, de l'entrée vers la sortie."""
    z1 = [r.w1[j][0] * x[0] + r.w1[j][1] * x[1] + r.b1[j] for j in range(2)]
    h = [sigmoide(z1[j]) for j in range(2)]
    z2 = r.w2[0] * h[0] + r.w2[1] * h[1] + r.b2
    p = sigmoide(z2)
    return Passage(z1, h, z2, p)
# fin: propager


# region: erreur
def erreur(p: float, y: int) -> float:
    """L'erreur de 0.2, −ln de la probabilité donnée à la bonne réponse : p si y vaut 1, 1 − p si y vaut 0.
    C'est l'entropie croisée binaire, −[y ln p + (1 − y) ln(1 − p)]."""
    return -math.log(p) if y == 1 else -math.log(1 - p)
# fin: erreur


# region: retropropager
def retropropager(r: Reseau, passage: Passage, x: tuple[int, int], y: int) -> Gradients:
    """Les dérivées de l'erreur du point x par rapport aux 9 poids, de la sortie vers l'entrée."""
    d_z2 = passage.p - y  # la sigmoïde et l'erreur, dérivées ensemble, donnent simplement p − y
    d_w2 = [d_z2 * passage.h[j] for j in range(2)]
    d_b2 = d_z2
    d_h = [d_z2 * r.w2[j] for j in range(2)]  # chaque neurone caché reçoit sa part, selon son poids
    d_z1 = [d_h[j] * passage.h[j] * (1 - passage.h[j]) for j in range(2)]  # la sigmoïde se dérive en h × (1 − h)
    d_w1 = [[d_z1[j] * x[i] for i in range(2)] for j in range(2)]
    d_b1 = [d_z1[j] for j in range(2)]
    return Gradients(d_w1, d_b1, d_w2, d_b2)


def gradient_moyen(r: Reseau, donnees: list[tuple[tuple[int, int], int]]) -> Gradients:
    """La moyenne des gradients de tous les points : la pente de la perte moyenne."""
    total = Gradients([[0.0, 0.0], [0.0, 0.0]], [0.0, 0.0], [0.0, 0.0], 0.0)
    for x, y in donnees:
        g = retropropager(r, propager(r, x), x, y)
        for j in range(2):
            for i in range(2):
                total.w1[j][i] += g.w1[j][i]
            total.b1[j] += g.b1[j]
            total.w2[j] += g.w2[j]
        total.b2 += g.b2
    n = len(donnees)
    return Gradients(
        [[total.w1[j][i] / n for i in range(2)] for j in range(2)],
        [total.b1[j] / n for j in range(2)],
        [total.w2[j] / n for j in range(2)],
        total.b2 / n,
    )
# fin: retropropager


# region: pas
def pas(r: Reseau, g: Gradients, taux: float) -> Reseau:
    """Un pas de descente, comme en 0.2 : chaque poids recule de taux × sa dérivée."""
    return Reseau(
        w1=[[r.w1[j][i] - taux * g.w1[j][i] for i in range(2)] for j in range(2)],
        b1=[r.b1[j] - taux * g.b1[j] for j in range(2)],
        w2=[r.w2[j] - taux * g.w2[j] for j in range(2)],
        b2=r.b2 - taux * g.b2,
    )
# fin: pas


# region: entrainer
@dataclass
class Historique:
    pertes: list[float]  # la perte moyenne avant le premier pas, puis après chaque pas
    reseau: Reseau  # le réseau après le dernier pas


def perte_moyenne(r: Reseau, donnees: list[tuple[tuple[int, int], int]]) -> float:
    """La moyenne des erreurs sur tous les points : le nombre que l'entraînement fait baisser."""
    total = 0.0
    for x, y in donnees:
        total += erreur(propager(r, x).p, y)
    return total / len(donnees)


def entrainer(r: Reseau, donnees: list[tuple[tuple[int, int], int]], taux: float, nb_pas: int) -> Historique:
    """nb_pas pas de descente sur tout le lot ; la perte est notée avant le premier pas, puis après chacun."""
    pertes = [perte_moyenne(r, donnees)]
    for _ in range(nb_pas):
        r = pas(r, gradient_moyen(r, donnees), taux)
        pertes.append(perte_moyenne(r, donnees))
    return Historique(pertes, r)


def predictions(r: Reseau, donnees: list[tuple[tuple[int, int], int]]) -> list[float]:
    """La probabilité que donne le réseau pour chaque point."""
    return [propager(r, x).p for x, _ in donnees]
# fin: entrainer


def a_appris(h: Historique, donnees: list[tuple[tuple[int, int], int]]) -> bool:
    """Vrai si l'entraînement a réussi : perte finale sous SEUIL_PERTE, et les réponses arrondies justes."""
    arrondies = [round(p) for p in predictions(h.reseau, donnees)]
    return h.pertes[-1] < SEUIL_PERTE and arrondies == [y for _, y in donnees]
