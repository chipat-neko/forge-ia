"""L'attention : les scores, le softmax et le mélange des valeurs.

Ces fonctions servent deux fois : dans le mini-modèle (modele.py), pour chaque
tête et chaque position, et dans l'animation de l'attention, qui montre leurs
résultats pas à pas.

Une seule convention : une requête pose la question, et le score d'une clé
vaut requête · clé, multiplié par l'échelle (1 / √ de la taille d'une tête).
Le masque causal ne se calcule pas : l'appelant ne passe que les clés
visibles, celles des positions jusqu'à la requête comprise.

Le jumeau TypeScript est site/src/lib/mini-modele/attention.ts : il suit ce
fichier ligne à ligne. Ce fichier est vérifié par tests/test_sources.py.
"""

from collections.abc import Sequence

from mini_modele.calcul import exp, maximum, produit_scalaire, somme


# region: scores
def scores_attention(requete: Sequence[float], cles: Sequence[Sequence[float]], echelle: float) -> list[float]:
    """Le score de chaque clé visible, dans l'ordre des clés : requête · clé, fois l'échelle."""
    return [produit_scalaire(requete, cle) * echelle for cle in cles]
# fin: scores


# region: softmax
def softmax(scores: Sequence[float]) -> list[float]:
    """Des scores aux poids : chaque poids est positif, et leur somme vaut 1.

    On retire d'abord le plus grand score m : les poids ne changent pas, et
    exp(s − m) ne dépasse jamais 1, donc rien ne déborde.
    """
    m = maximum(scores)
    e = [exp(s - m) for s in scores]
    total = somme(e)
    return [v / total for v in e]
# fin: softmax


def poids_attention(requete: Sequence[float], cles: Sequence[Sequence[float]], echelle: float) -> list[float]:
    """Les poids d'attention de la requête sur les clés visibles : le softmax de leurs scores."""
    return softmax(scores_attention(requete, cles, echelle))


def verifier_valeurs(poids: Sequence[float], valeurs: Sequence[Sequence[float]]) -> None:
    """Autant de poids que de valeurs, au moins une valeur, et des valeurs de même longueur."""
    if len(poids) != len(valeurs):
        raise ValueError(
            f"melanger_valeurs : il faut autant de poids que de valeurs (reçu {len(poids)} et {len(valeurs)})."
        )
    if len(valeurs) == 0:
        raise ValueError("melanger_valeurs : il faut au moins une valeur (la position de la requête est toujours visible).")
    for valeur in valeurs:
        if len(valeur) != len(valeurs[0]):
            raise ValueError(
                "melanger_valeurs : les valeurs n'ont pas toutes la même longueur "
                f"({len(valeurs[0])} et {len(valeur)}). Donne des valeurs de même longueur."
            )


# region: melange
def melanger_valeurs(poids: Sequence[float], valeurs: Sequence[Sequence[float]]) -> list[float]:
    """La sortie de la tête : les valeurs, mélangées selon les poids.

    Pour chaque composante d : poids[0] × valeurs[0][d] + poids[1] × valeurs[1][d] + …
    """
    verifier_valeurs(poids, valeurs)
    sortie = []
    for d in range(len(valeurs[0])):
        s = 0.0
        for j in range(len(poids)):
            s += poids[j] * valeurs[j][d]
        sortie.append(s)
    return sortie
# fin: melange
