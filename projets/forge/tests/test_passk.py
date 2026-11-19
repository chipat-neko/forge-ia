"""Tests de l'estimateur sans biais de pass@k (`forge.code.passk`)."""

from fractions import Fraction
from math import comb

import pytest

from forge.code.passk import pass_a_k


def _pass_a_k_exact(n: int, c: int, k: int) -> float:
    """La définition de l'article Codex, en fractions exactes : 1 − C(n − c, k) / C(n, k)."""
    return float(1 - Fraction(comb(n - c, k), comb(n, k)))


def test_pass_a_k_egale_la_formule_aux_coefficients_binomiaux():
    assert pass_a_k(20, 2, 10) == pytest.approx(1 - comb(18, 10) / comb(20, 10), abs=1e-12)


def test_aucun_juste_donne_0_et_trop_peu_de_faux_donne_1():
    assert pass_a_k(5, 0, 1) == 0
    assert pass_a_k(5, 5, 3) == 1
    assert pass_a_k(10, 8, 3) == 1  # 2 faux seulement : tout tirage de 3 contient un juste


def test_pass_a_1_est_la_part_des_justes():
    assert pass_a_k(200, 37, 1) == pytest.approx(37 / 200, abs=1e-12)


def test_pass_a_k_sur_une_grille_de_petites_valeurs():
    for n in range(1, 26):
        for c in range(n + 1):
            for k in range(1, n + 1):
                assert pass_a_k(n, c, k) == pytest.approx(_pass_a_k_exact(n, c, k), abs=1e-12), (n, c, k)


def test_pass_a_k_reste_juste_avec_de_grands_coefficients():
    """n = 200, k = 100 (les valeurs de l'article) : C(200, 100) dépasse 10^58, le produit reste exact."""
    for c in (1, 3, 50, 99, 100):
        assert pass_a_k(200, c, 100) == pytest.approx(_pass_a_k_exact(200, c, 100), abs=1e-12), c


@pytest.mark.parametrize(
    ("n", "c", "k", "nom"),
    [(5, 2, 6, "k"), (5, -1, 1, "c"), (5, 6, 1, "c"), (5, 2, 0, "k")],
)
def test_des_valeurs_impossibles_sont_refusees(n, c, k, nom):
    with pytest.raises(ValueError, match=f"^{nom} = "):
        pass_a_k(n, c, k)
