"""Les avantages d'un groupe à la main, comparés à forge ; la chance qu'un groupe n'apprenne rien.

`avantages_a_la_main` doit égaler `forge.raisonnement.grpo.avantages` à 10⁻¹² près : forge calcule sur des tenseurs,
ici des nombres Python, et les deux sont comparés en float64.
"""

import itertools
import math

import pytest
import torch
from forge.raisonnement.grpo import avantages

from raisonnement_pas_a_pas.avantages import avantages_a_la_main, sans_signal


# region: test-avantages
def test_les_avantages_a_la_main_sont_ceux_de_forge():
    # Dix groupes de huit réponses : des 0 et des 1 tirés à la main, puis des récompenses fractionnaires.
    groupes = [
        [1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
        [0.0] * 8,
        [1.0] * 8,
        [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0],
        [0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0],
        [0.5, 0.25, 0.75, 0.125, 0.0, 1.0, 0.3, 0.7],
        [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
        [-1.0, 2.0, 0.0, 3.5, -0.5, 1.0, 1.0, 0.0],
        [1e-9, 1.0, 2e-9, 3.0, 0.0, 1e9, 1.0, 0.5],
    ]
    a_la_main = avantages_a_la_main(groupes)
    de_forge = avantages(torch.tensor(groupes, dtype=torch.float64)).tolist()
    for groupe, ligne in zip(a_la_main, de_forge, strict=True):
        for x, y in zip(groupe, ligne, strict=True):
            assert abs(x - y) <= 1e-12 * max(1.0, abs(y))
# fin: test-avantages


def test_l_avantage_est_la_recompense_moins_la_moyenne_du_groupe():
    assert avantages_a_la_main([[1.0, 0.0, 0.0, 1.0]]) == [[0.5, -0.5, -0.5, 0.5]]
    # Une seule bonne réponse sur quatre : elle gagne 0,75, chacune des autres perd 0,25.
    assert avantages_a_la_main([[1.0, 0.0, 0.0, 0.0]]) == [[0.75, -0.25, -0.25, -0.25]]


def test_un_groupe_sans_signal_a_des_avantages_nuls():
    for groupe in ([0.0, 0.0, 0.0, 0.0], [1.0, 1.0, 1.0, 1.0], [0.25, 0.25, 0.25]):
        assert avantages_a_la_main([groupe]) == [[0.0] * len(groupe)]


def test_les_avantages_d_un_groupe_somment_a_zero_et_chaque_groupe_est_independant():
    groupes = [[1.0, 0.0, 0.0, 1.0, 1.0], [0.0, 1.0], [1.0, 1.0, 0.0]]
    for groupe, ligne in zip(groupes, avantages_a_la_main(groupes), strict=True):
        assert abs(sum(ligne)) < 1e-12
        assert avantages_a_la_main([groupe]) == [ligne]  # les autres groupes ne changent rien


def test_un_groupe_vide_est_refuse_et_aucun_groupe_est_permis():
    with pytest.raises(ValueError, match="Un groupe sans aucune réponse"):
        avantages_a_la_main([[1.0], []])
    assert avantages_a_la_main([]) == []


def test_sans_signal_est_la_chance_de_tout_juste_ou_tout_faux():
    assert sans_signal(0.5, 1) == 1.0  # une seule réponse : toujours sans signal (aucune autre à comparer)
    assert sans_signal(0.5, 2) == 0.5
    assert sans_signal(0.0, 8) == 1.0 and sans_signal(1.0, 8) == 1.0
    assert sans_signal(0.2, 8) == pytest.approx(0.2**8 + 0.8**8, rel=1e-12)
    assert sans_signal(0.05, 16) == pytest.approx(0.05**16 + 0.95**16, rel=1e-12)


def test_sans_signal_egale_le_denombrement_des_groupes_possibles():
    # Tous les groupes de n réponses justes ou fausses, chacun avec sa chance : la somme de ceux sans signal.
    for p, n in itertools.product((0.1, 0.3, 0.5, 0.9), (2, 3, 4, 6)):
        somme = 0.0
        for groupe in itertools.product((0.0, 1.0), repeat=n):
            chance = math.prod(p if r == 1.0 else 1 - p for r in groupe)
            if all(a == 0 for a in avantages_a_la_main([list(groupe)])[0]):
                somme += chance
        assert sans_signal(p, n) == pytest.approx(somme, rel=1e-12)


def test_un_groupe_plus_grand_a_moins_de_chances_d_etre_sans_signal_tant_que_p_n_est_pas_extreme():
    for p in (0.05, 0.25, 0.5, 0.75, 0.95):
        chances = [sans_signal(p, n) for n in (2, 4, 8, 16, 32)]
        assert chances == sorted(chances, reverse=True)


def test_sans_signal_refuse_une_chance_ou_une_taille_impossibles():
    for p in (-0.1, 1.5, float("nan")):
        with pytest.raises(ValueError, match="entre 0 et 1"):
            sans_signal(p, 4)
    for n in (0, -2, 2.5, True):
        with pytest.raises(ValueError, match="au moins une réponse"):
            sans_signal(0.5, n)
