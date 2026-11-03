"""L'attention : scores, softmax et mélange des valeurs.

Ces trois fonctions servent au mini-modèle (test_modele.py) et à l'animation
de l'attention. Le jumeau TypeScript (site/src/lib/mini-modele/attention.ts) a
les mêmes tests, avec les mêmes valeurs ; sa parité au bit près est vérifiée
par les attendus du modèle (tests/attendus-modele.json), qui passent par ces
fonctions à chaque tête et à chaque position.
"""

import math

import pytest

from mini_modele.attention import melanger_valeurs, poids_attention, scores_attention, softmax
from mini_modele.calcul import Hasard, exp, somme, vers_hex


def test_softmax_et_masque():
    assert poids_attention([0.0, 0.0], [[1.0, 2.0], [3.0, 4.0]], 0.5) == [0.5, 0.5]
    p = poids_attention([1.0, -2.0], [[0.3, 0.1], [2.0, -1.0], [-0.5, 0.5]], 0.5)
    assert abs(somme(p) - 1.0) <= 1e-15


def test_scores_attention():
    # Des valeurs exactes : chaque produit et chaque somme tombent juste.
    assert scores_attention([1.0, 2.0], [[3.0, 4.0], [5.0, 6.0]], 0.5) == [5.5, 8.5]
    assert scores_attention([1.0, -2.0], [[0.5, 0.25]], 2.0) == [0.0]
    # Une requête sans clé visible n'a aucun score.
    assert scores_attention([1.0, 2.0], [], 0.5) == []
    with pytest.raises(ValueError, match="même longueur"):
        scores_attention([1.0, 2.0], [[1.0, 2.0, 3.0]], 0.5)


def test_scores_dans_l_ordre_des_cles():
    cles = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
    assert scores_attention([2.0, 3.0], cles, 1.0) == [2.0, 3.0, 5.0]
    assert scores_attention([2.0, 3.0], cles[::-1], 1.0) == [5.0, 3.0, 2.0]


def test_softmax():
    assert softmax([0.0]) == [1.0]
    assert softmax([2.0, 2.0, 2.0, 2.0]) == [0.25, 0.25, 0.25, 0.25]
    # Le plus grand score est retiré d'abord : rien ne déborde, même à 1000.
    assert softmax([1000.0, 1000.0]) == [0.5, 0.5]
    assert softmax([-1000.0, 0.0]) == [0.0, 1.0]
    # La définition, opération par opération : m, puis exp(s − m), puis la somme, puis la division.
    scores = [0.3, -1.2, 2.5, 0.0]
    e = [exp(s - 2.5) for s in scores]
    total = somme(e)
    assert [vers_hex(p) for p in softmax(scores)] == [vers_hex(v / total) for v in e]
    with pytest.raises(ValueError, match="vide"):
        softmax([])


def test_softmax_proche_de_la_libm():  # précision, pas parité : la libm n'est qu'un témoin
    h = Hasard(11)
    for _ in range(200):
        scores = [(h.uniforme() - 0.5) * 20 for _ in range(7)]
        m = scores[0]
        for s in scores:
            if s > m:
                m = s
        temoin = [math.exp(s - m) for s in scores]
        total = math.fsum(temoin)
        for p, t in zip(softmax(scores), temoin):
            assert abs(p - t / total) <= 1e-15


def test_poids_attention_est_softmax_des_scores():
    requete = [0.7, -0.4, 1.1]
    cles = [[0.2, 0.5, -0.3], [1.5, -0.2, 0.4], [-0.6, 0.9, 0.0]]
    attendu = softmax(scores_attention(requete, cles, 0.5))
    assert [vers_hex(p) for p in poids_attention(requete, cles, 0.5)] == [vers_hex(p) for p in attendu]
    # Une seule clé visible (la première position) : tout le poids va sur elle.
    assert poids_attention(requete, cles[:1], 0.5) == [1.0]


def test_melanger_valeurs():
    assert melanger_valeurs([0.25, 0.75], [[1.0, 2.0], [3.0, 4.0]]) == [2.5, 3.5]
    assert melanger_valeurs([1.0], [[-1.5, 0.0, 2.0]]) == [-1.5, 0.0, 2.0]
    assert melanger_valeurs([0.0, 1.0], [[9.0], [-3.0]]) == [-3.0]
    with pytest.raises(ValueError, match="autant de poids que de valeurs"):
        melanger_valeurs([0.5, 0.5], [[1.0, 2.0]])
    with pytest.raises(ValueError, match="au moins une valeur"):
        melanger_valeurs([], [])
    with pytest.raises(ValueError, match="même longueur"):
        melanger_valeurs([0.5, 0.5], [[1.0, 2.0], [3.0]])


def test_melanger_valeurs_somme_par_j_croissant():
    # s = 0,0, puis s += poids[j] × valeurs[j][d], par j croissant : l'ordre change le dernier bit.
    poids = [1.0, 1.0, 1.0]
    valeurs = [[1e16], [1.0], [1.0]]
    assert melanger_valeurs(poids, valeurs) == [1e16]
    assert melanger_valeurs(poids, valeurs[::-1]) == [1e16 + 2.0]
