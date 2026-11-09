"""Compter les paramètres par famille : la somme est celle de forge."""

import pytest
from forge.modele.config import PRESETS, ConfigModele, largeur_cachee, nombre_parametres

from transformer_pas_a_pas.compter import repartition


@pytest.mark.parametrize("nom", list(PRESETS))
def test_repartition(nom):
    r = repartition(PRESETS[nom])
    assert sum(r.values()) == nombre_parametres(PRESETS[nom])


def test_les_familles_et_leur_ordre():
    assert list(repartition(PRESETS["mini"])) == ["plongement", "attention", "mlp", "normes"]


def test_valeurs_d_un_petit_modele():
    c = ConfigModele(dim=32, couches=2, tetes=4, longueur_contexte=16, taille_vocabulaire=50)
    h = largeur_cachee(32)
    assert repartition(c) == {
        "plongement": 50 * 32,
        "attention": 2 * 4 * 32 * 32,
        "mlp": 2 * 3 * 32 * h,
        "normes": 2 * 2 * 32 + 32,
    }


def test_le_nombre_de_tetes_ne_change_pas_les_parametres():
    a = ConfigModele(dim=64, couches=3, tetes=2, longueur_contexte=16)
    b = ConfigModele(dim=64, couches=3, tetes=8, longueur_contexte=16)
    assert repartition(a) == repartition(b)
