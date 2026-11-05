"""Le même réseau dans PyTorch : mêmes gradients que la main, et même entraînement."""

import math

import pytest
import torch

from premier_reseau.a_la_main import DONNEES, GRAINE, NB_PAS, TAUX, entrainer, gradient_moyen, initialiser
from premier_reseau.appareil import AppareilIndisponible
from premier_reseau.avec_pytorch import (
    construire,
    en_liste,
    en_tenseurs,
    entrainer_pytorch,
    gradients_pytorch,
    plus_grand_ecart,
    reseau_de,
)


@pytest.fixture(autouse=True)
def sans_variable(monkeypatch):
    # Les tests ne dépendent pas d'un FORGE_APPAREIL réglé sur la machine.
    monkeypatch.delenv("FORGE_APPAREIL", raising=False)


@pytest.fixture(scope="module")
def sur_le_processeur():
    """L'entraînement du chapitre, fait par PyTorch sur le processeur (une seule fois pour ce fichier)."""
    return entrainer_pytorch(construire(initialiser(GRAINE)), DONNEES, TAUX, NB_PAS, "cpu")


@pytest.fixture(scope="module")
def a_la_main():
    return entrainer(initialiser(GRAINE), DONNEES, TAUX, NB_PAS)


def test_construire_recopie_les_poids():
    r = initialiser(GRAINE)
    modele = construire(r)
    assert [type(couche).__name__ for couche in modele] == ["Linear", "Sigmoid", "Linear", "Sigmoid"]
    assert all(p.dtype == torch.float64 for p in modele.parameters())
    assert sum(p.numel() for p in modele.parameters()) == 9
    # Les poids reviennent tels quels, au bit près.
    assert reseau_de(modele) == r


def test_en_tenseurs():
    x, y = en_tenseurs(DONNEES)
    assert x.shape == (4, 2) and y.shape == (4, 1)
    assert x.dtype == y.dtype == torch.float64
    assert x.tolist() == [[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]] and y.flatten().tolist() == [0.0, 1.0, 1.0, 0.0]


def test_plus_grand_ecart():
    r = initialiser(GRAINE)
    assert plus_grand_ecart(r, r) == 0.0
    autre = initialiser(GRAINE)
    autre.w2[1] += 0.25
    assert plus_grand_ecart(r, autre) == pytest.approx(0.25)
    assert len(en_liste(r)) == 9


@pytest.mark.parametrize("graine", [GRAINE, 1, 2, 1234])
def test_gradients_a_la_main_egalent_pytorch(graine):
    r = initialiser(graine)
    assert plus_grand_ecart(gradient_moyen(r, DONNEES), gradients_pytorch(construire(r), DONNEES)) < 1e-12


def test_gradients_egaux_apres_l_entrainement(a_la_main):
    r = a_la_main.reseau
    assert plus_grand_ecart(gradient_moyen(r, DONNEES), gradients_pytorch(construire(r), DONNEES)) < 1e-12


def test_gradients_pytorch_ne_cumule_pas():
    # Deux appels de suite donnent les mêmes gradients : les anciens sont effacés avant chaque calcul.
    modele = construire(initialiser(GRAINE))
    assert gradients_pytorch(modele, DONNEES) == gradients_pytorch(modele, DONNEES)


def test_pytorch_suit_la_main(sur_le_processeur, a_la_main):
    # Sur le processeur, poids finaux à moins de 1e-6.
    assert plus_grand_ecart(a_la_main.reseau, sur_le_processeur.reseau) < 1e-6
    assert len(sur_le_processeur.pertes) == NB_PAS + 1
    for perte_torch, perte_main in zip(sur_le_processeur.pertes, a_la_main.pertes, strict=True):
        assert math.isclose(perte_torch, perte_main, rel_tol=1e-9)
    assert sur_le_processeur.millisecondes > 0


def test_entrainer_pytorch_sur_la_carte_absente(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(AppareilIndisponible, match="FORGE_APPAREIL=cpu"):
        entrainer_pytorch(construire(initialiser(GRAINE)), DONNEES, TAUX, 10, "cuda")


@pytest.mark.gpu
def test_pytorch_sur_la_carte(sur_le_processeur):
    # entrainer_pytorch(…, "cuda") : poids finaux à moins de 1e-6 de ceux du processeur.
    sur_la_carte = entrainer_pytorch(construire(initialiser(GRAINE)), DONNEES, TAUX, NB_PAS, "cuda")
    assert plus_grand_ecart(sur_la_carte.reseau, sur_le_processeur.reseau) < 1e-6
    assert len(sur_la_carte.pertes) == NB_PAS + 1 and sur_la_carte.millisecondes > 0
