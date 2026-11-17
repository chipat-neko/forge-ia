"""Le hasard partagé : SplitMix32, le même que celui du mini-modèle et du site (plan 8)."""

import ast
import inspect
import textwrap
from pathlib import Path

import pytest

from forge.hasard import Hasard

CALCUL_MINI_MODELE = Path(__file__).resolve().parents[2] / "mini-modele" / "mini_modele" / "calcul.py"


def _methodes_du_mini_modele() -> dict[str, str]:
    source = CALCUL_MINI_MODELE.read_text(encoding="utf-8")
    arbre = ast.parse(source)
    classe = next(n for n in arbre.body if isinstance(n, ast.ClassDef) and n.name == "Hasard")
    return {
        n.name: textwrap.dedent(ast.get_source_segment(source, n, padded=True))
        for n in classe.body
        if isinstance(n, ast.FunctionDef) and n.name in {"__init__", "suivant32", "uniforme"}
    }


@pytest.mark.skipif(not CALCUL_MINI_MODELE.exists(), reason="le mini-modèle n'est pas dans ce dépôt")
@pytest.mark.parametrize("nom", ["__init__", "suivant32", "uniforme"])
def test_les_trois_methodes_sont_une_copie_exacte_de_celles_du_mini_modele(nom):
    attendu = _methodes_du_mini_modele()[nom]
    obtenu = textwrap.dedent(inspect.getsource(getattr(Hasard, nom)))
    assert obtenu.strip() == attendu.strip()


def test_les_cinq_premiers_nombres_de_la_graine_0():
    hasard = Hasard(0)
    assert [hasard.suivant32() for _ in range(5)] == [
        1684164658,
        3653269916,
        2939563536,
        2141751570,
        3295091513,
    ]


def test_melanger_la_graine_1():
    assert Hasard(1).melanger(list(range(10))) == [3, 1, 4, 9, 2, 0, 8, 5, 7, 6]


def test_melanger_ne_touche_pas_la_liste_recue():
    liste = [1, 2, 3, 4]
    resultat = Hasard(5).melanger(liste)
    assert liste == [1, 2, 3, 4]
    assert sorted(resultat) == [1, 2, 3, 4]


def test_melanger_listes_courtes():
    assert Hasard(3).melanger([]) == []
    assert Hasard(3).melanger(["a"]) == ["a"]


def test_entier_borne_incluse_et_en_entiers_seulement():
    hasard = Hasard(7)
    # a + suivant32() % (b - a + 1) : 7 + 1684164658... pour la graine 7, trois valeurs possibles
    valeurs = [hasard.entier(7, 9) for _ in range(5)]
    assert valeurs == [8, 8, 7, 9, 8]
    tirages = {Hasard(g).entier(-2, 2) for g in range(200)}
    assert tirages == {-2, -1, 0, 1, 2}


def test_entier_a_egal_b():
    assert Hasard(1).entier(4, 4) == 4


def test_entier_refuse_un_intervalle_vide():
    with pytest.raises(ValueError, match="entier"):
        Hasard(1).entier(5, 4)


def test_choisir_prend_un_element_de_la_suite():
    suite = ["a", "b", "c", "d"]
    hasard = Hasard(11)
    for _ in range(50):
        assert hasard.choisir(suite) in suite
    assert {Hasard(g).choisir(suite) for g in range(100)} == set(suite)


def test_choisir_refuse_une_suite_vide():
    with pytest.raises(ValueError, match="choisir"):
        Hasard(1).choisir([])


def test_deux_hasards_de_meme_graine_donnent_la_meme_suite():
    a, b = Hasard(42), Hasard(42)
    assert [a.entier(0, 99) for _ in range(20)] == [b.entier(0, 99) for _ in range(20)]
