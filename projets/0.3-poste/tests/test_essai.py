"""L'essai de calcul : un produit de matrices en float32, comparé au même calcul en float64."""

import pytest
import torch

from poste.appareil import AppareilIndisponible
from poste.essai import EssaiCalcul, decrire_essai, en_francais, essai_de_calcul


def test_essai_processeur():
    assert essai_de_calcul("cpu").ecart_max < 1e-3


def test_essai_processeur_en_detail():
    essai = essai_de_calcul("cpu", taille=64)
    assert isinstance(essai, EssaiCalcul)
    assert essai.appareil == "cpu"
    # float32 n'a que 7 chiffres environ : l'écart n'est pas nul, mais minuscule.
    assert 0 < essai.ecart_max < 1e-5
    assert essai.millisecondes > 0


def test_essai_reproductible():
    # Les mêmes matrices à chaque fois (graine fixée) : le même écart.
    assert essai_de_calcul("cpu", taille=32).ecart_max == essai_de_calcul("cpu", taille=32).ecart_max


def test_essai_sur_la_carte_sans_carte(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(AppareilIndisponible):
        essai_de_calcul("cuda")


@pytest.mark.gpu
def test_essai_carte():
    assert essai_de_calcul("cuda").ecart_max < 1e-3


def test_en_francais():
    assert en_francais(2.134) == "2,1"
    assert en_francais(12.6) == "13"
    assert en_francais(123.4) == "123"
    assert en_francais(0.0312) == "0,031"
    assert en_francais(1.23e-6) == "0,0000012"
    assert en_francais(0.0) == "0"
    assert en_francais(1234.5) == "1\u202f234"


def test_decrire_essai():
    assert decrire_essai(EssaiCalcul("cpu", 1.23e-6, 2.134)) == (
        "processeur (cpu)\u202f: 2,1 ms par produit, écart maximal 0,0000012"
    )
    assert decrire_essai(EssaiCalcul("cuda", 9.5e-7, 0.0312)).startswith("carte graphique (cuda)\u202f: 0,031 ms")
