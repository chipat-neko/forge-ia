"""Les nombres à la française : en_francais (copie de 0.3), les puissances de dix et les réglages."""

import ast
import pathlib

import pytest

from premier_reseau.nombres import en_francais, en_puissance_de_dix, simple_en_francais

PROJET = pathlib.Path(__file__).resolve().parents[1]
RACINE = PROJET.parents[1]
ESSAI_03 = RACINE / "projets" / "0.3-poste" / "poste" / "essai.py"


def test_en_francais():
    assert en_francais(2.134) == "2,1"
    assert en_francais(0.00523) == "0,0052"
    assert en_francais(3000) == "3\u202f000"
    assert en_francais(0.0036957, 3) == "0,00370"
    assert en_francais(0) == "0"


def source_de(chemin: pathlib.Path, nom: str) -> str:
    """Le texte exact de la fonction `nom` du fichier."""
    texte = chemin.read_text(encoding="utf-8")
    noeud = next(n for n in ast.parse(texte).body if isinstance(n, ast.FunctionDef) and n.name == nom)
    return ast.get_source_segment(texte, noeud)


def test_en_francais_copie_exacte_de_0_3():
    # en_francais vient de projets/0.3-poste/poste/essai.py : la copie reste identique.
    if not (RACINE / "projets" / "forge").exists():
        pytest.skip("Projet téléchargé seul : projets/0.3-poste n'est pas là pour comparer la copie.")
    # Dans le dépôt, l'original doit exister : un chemin changé ne doit pas faire passer ce test à vide.
    assert ESSAI_03.exists(), f"{ESSAI_03} est introuvable : corrige son chemin dans ce test."
    assert source_de(PROJET / "premier_reseau" / "nombres.py", "en_francais") == source_de(ESSAI_03, "en_francais"), (
        "en_francais (premier_reseau/nombres.py) n'est plus la copie exacte de celle de projets/0.3-poste/poste/essai.py. "
        "Recopie-la : une correction se fait dans 0.3, puis se recopie dans 0.4 et 0.5."
    )


def test_en_puissance_de_dix():
    assert en_puissance_de_dix(3.1e-17) == "3,1 × 10⁻¹⁷"
    assert en_puissance_de_dix(2.2e-15) == "2,2 × 10⁻¹⁵"
    assert en_puissance_de_dix(9.96e-13) == "1,0 × 10⁻¹²"  # arrondi à 2 chiffres, l'exposant suit
    assert en_puissance_de_dix(4.0e-7) == "4,0 × 10⁻⁷"
    assert en_puissance_de_dix(0.0) == "0"


def test_simple_en_francais():
    assert [simple_en_francais(x) for x in (-2.0, -1.5, -0.5, 0.0, 0.5, 2.0)] == [
        "−2",
        "−1,5",
        "−0,5",
        "0",
        "0,5",
        "2",
    ]
