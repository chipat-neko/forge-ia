"""Le réseau 2-2-1 à la main : propagation, erreur, rétropropagation, descente, entraînement."""

import math
import random

import pytest

from premier_reseau.a_la_main import (
    DONNEES,
    GRAINE,
    NB_PAS,
    SEUIL_PERTE,
    TAUX,
    Gradients,
    Reseau,
    a_appris,
    entrainer,
    erreur,
    gradient_moyen,
    initialiser,
    nb_poids,
    pas,
    perte_moyenne,
    predictions,
    propager,
    retropropager,
    sigmoide,
)


def a_plat(poids: Reseau | Gradients) -> list[float]:
    return [*poids.w1[0], *poids.w1[1], *poids.b1, *poids.w2, poids.b2]


def depuis_plat(nombres: list[float]) -> Reseau:
    return Reseau([nombres[0:2], nombres[2:4]], nombres[4:6], nombres[6:8], nombres[8])


def test_donnees_du_ou_exclusif():
    assert DONNEES == [((0, 0), 0), ((0, 1), 1), ((1, 0), 1), ((1, 1), 0)]
    assert TAUX == 1.0 and NB_PAS == 3000 and SEUIL_PERTE == 0.05


def test_initialiser():
    r = initialiser(GRAINE)
    assert nb_poids(r) == 9 and len(a_plat(r)) == 9
    assert all(-1 <= w <= 1 for w in a_plat(r))
    # Tirés dans l'ordre w1, b1, w2, b2, avec random.Random(graine).uniform(-1, 1).
    hasard = random.Random(GRAINE)
    assert a_plat(r) == [hasard.uniform(-1, 1) for _ in range(9)]
    assert initialiser(GRAINE) == r and initialiser(GRAINE + 1) != r


def test_sigmoide():
    assert sigmoide(0) == 0.5
    assert sigmoide(40) == 1.0 and 0 < sigmoide(-40) < 1e-17
    for z in [-3.0, -0.5, 0.25, 2.0]:
        assert math.isclose(sigmoide(-z), 1 - sigmoide(z), rel_tol=1e-12)


def test_propager_avec_des_poids_nuls():
    # Tout à 0 : chaque somme vaut 0, chaque sigmoïde 0,5.
    nul = Reseau([[0.0, 0.0], [0.0, 0.0]], [0.0, 0.0], [0.0, 0.0], 0.0)
    passage = propager(nul, (1, 1))
    assert passage.z1 == [0.0, 0.0] and passage.h == [0.5, 0.5] and passage.z2 == 0.0 and passage.p == 0.5


def test_propager_fait_le_calcul_du_chapitre():
    r = Reseau([[1.0, 2.0], [-1.0, 0.5]], [0.5, -0.5], [2.0, -3.0], 0.25)
    passage = propager(r, (1, 0))
    assert passage.z1 == [1.5, -1.5]
    assert passage.h == [sigmoide(1.5), sigmoide(-1.5)]
    assert passage.z2 == 2.0 * sigmoide(1.5) - 3.0 * sigmoide(-1.5) + 0.25
    assert passage.p == sigmoide(passage.z2)


def test_erreur():
    assert erreur(0.5, 1) == erreur(0.5, 0) == math.log(2)
    for p in [0.1, 0.5, 0.97]:
        for y in [0, 1]:
            # L'entropie croisée binaire, −[y ln p + (1 − y) ln(1 − p)].
            assert math.isclose(erreur(p, y), -(y * math.log(p) + (1 - y) * math.log(1 - p)), rel_tol=1e-15)
    # Plus la probabilité de la bonne réponse est petite, plus l'erreur est grande.
    assert erreur(0.9, 1) < erreur(0.5, 1) < erreur(0.1, 1)


def test_la_sortie_donne_p_moins_y():
    r = initialiser(GRAINE)
    for x, y in DONNEES:
        passage = propager(r, x)
        g = retropropager(r, passage, x, y)
        assert g.b2 == passage.p - y
        assert g.w2 == [(passage.p - y) * passage.h[j] for j in range(2)]


def derivees_approchees(r: Reseau, h: float = 1e-5) -> list[float]:
    """Les 9 dérivées de la perte moyenne par la pente approchée de 0.2 : (E(w + h) − E(w − h)) / 2h."""
    nombres = a_plat(r)
    derivees = []
    for k in range(9):
        plus, moins = list(nombres), list(nombres)
        plus[k] += h
        moins[k] -= h
        derivees.append((perte_moyenne(depuis_plat(plus), DONNEES) - perte_moyenne(depuis_plat(moins), DONNEES)) / (2 * h))
    return derivees


@pytest.mark.parametrize("graine", [GRAINE, 1, 2, 1234])
def test_gradients_par_differences_finies(graine):
    r = initialiser(graine)
    calcules = a_plat(gradient_moyen(r, DONNEES))
    approches = derivees_approchees(r)
    assert max(abs(a - b) for a, b in zip(calcules, approches)) < 1e-6


def test_gradients_par_differences_finies_apres_l_entrainement():
    # Après l'entraînement, les poids sont grands et les sigmoïdes presque plates : le calcul tient toujours.
    r = entrainer(initialiser(GRAINE), DONNEES, TAUX, 500).reseau
    calcules = a_plat(gradient_moyen(r, DONNEES))
    assert max(abs(a - b) for a, b in zip(calcules, derivees_approchees(r))) < 1e-6


def test_gradient_moyen_est_la_moyenne():
    r = initialiser(GRAINE)
    un_par_un = [a_plat(retropropager(r, propager(r, x), x, y)) for x, y in DONNEES]
    moyenne = a_plat(gradient_moyen(r, DONNEES))
    for k in range(9):
        assert math.isclose(moyenne[k], math.fsum(g[k] for g in un_par_un) / 4, rel_tol=1e-12, abs_tol=1e-15)


def test_pas():
    r = initialiser(GRAINE)
    g = gradient_moyen(r, DONNEES)
    assert pas(r, g, 0.0) == r
    assert a_plat(pas(r, g, 0.5)) == [w - 0.5 * d for w, d in zip(a_plat(r), a_plat(g))]
    # Un petit pas fait baisser la perte : c'est la descente de 0.2.
    assert perte_moyenne(pas(r, g, 0.1), DONNEES) < perte_moyenne(r, DONNEES)


def test_le_reseau_apprend():
    h = entrainer(initialiser(GRAINE), DONNEES, TAUX, NB_PAS)
    assert h.pertes[-1] < 0.05 and [round(p) for p in predictions(h.reseau, DONNEES)] == [0, 1, 1, 0]
    assert a_appris(h, DONNEES)


def test_les_pertes():
    depart = initialiser(GRAINE)
    h = entrainer(depart, DONNEES, TAUX, NB_PAS)
    # Une perte avant le premier pas, puis une après chacun.
    assert len(h.pertes) == NB_PAS + 1
    assert h.pertes[0] == perte_moyenne(depart, DONNEES)
    assert h.pertes[-1] == perte_moyenne(h.reseau, DONNEES)
    assert all(p > 0 for p in h.pertes)
    # entrainer ne touche pas au réseau de départ.
    assert depart == initialiser(GRAINE)
    # Deux entraînements de 1 500 pas font un entraînement de 3 000 pas.
    moitie = entrainer(depart, DONNEES, TAUX, NB_PAS // 2)
    suite = entrainer(moitie.reseau, DONNEES, TAUX, NB_PAS - NB_PAS // 2)
    assert moitie.pertes + suite.pertes[1:] == h.pertes and suite.reseau == h.reseau


def test_la_graine_1236_est_la_premiere_au_dessus_de_1234_qui_apprend():
    # La graine prévue était 1234 : avec elle, puis avec 1235, le réseau reste coincé, une
    # perte vers 0,35 et deux réponses à 0,5. GRAINE est la première graine au-dessus qui apprend.
    for graine in (1234, 1235):
        coince = entrainer(initialiser(graine), DONNEES, TAUX, NB_PAS)
        assert not a_appris(coince, DONNEES)
        assert coince.pertes[-1] > 0.3
    assert GRAINE == 1236


def test_a_appris():
    h = entrainer(initialiser(GRAINE), DONNEES, TAUX, NB_PAS)
    # Les bonnes réponses ne suffisent pas : il faut aussi la perte sous le seuil.
    assert not a_appris(type(h)([*h.pertes[:-1], SEUIL_PERTE], h.reseau), DONNEES)
    # Une perte sous le seuil ne suffit pas non plus : il faut les bonnes réponses.
    autres = [(x, 1 - y) for x, y in DONNEES]
    assert not a_appris(h, autres)
