"""Les tirages : le hasard reproductible, les probabilités et les tirages au sort."""

import ast
from pathlib import Path

import pytest

from maths_utiles import tirage
from maths_utiles.tirage import (
    ENTIER_SUR_MAX,
    EXEMPLE_COMPTES,
    GRAINE_TIRAGE,
    Hasard,
    probabilites,
    tirages,
    tirer,
)

PROJET = Path(__file__).resolve().parents[1]
RACINE = PROJET.parents[1]
# Les trois méthodes de Hasard copiées du mini-modèle, sans rien changer.
METHODES_COPIEES = ["__init__", "suivant32", "uniforme"]


def test_exemple_et_graine():
    assert EXEMPLE_COMPTES == {"fer": 6, "métal": 3, "feu": 1}
    assert list(EXEMPLE_COMPTES) == ["fer", "métal", "feu"]
    assert GRAINE_TIRAGE == 1234


def test_probabilites():
    assert probabilites(EXEMPLE_COMPTES) == [0.6, 0.3, 0.1]
    assert probabilites({"a": 1, "b": 3}) == [0.25, 0.75]


def test_probabilites_sans_compte_positif():
    message = (
        "Aucun compte positif (le total vaut 0)\u202f: "
        "il faut au moins un compte plus grand que 0 pour calculer des probabilités."
    )
    for comptes in ({}, {"fer": 0, "feu": 0}):
        with pytest.raises(ValueError) as erreur:
            probabilites(comptes)
        assert str(erreur.value) == message


def test_tirer():
    probas = [0.6, 0.3, 0.1]
    assert tirer(probas, 0.0) == 0 and tirer(probas, 0.59) == 0
    assert tirer(probas, 0.6) == 1 and tirer(probas, 0.75) == 1
    assert tirer(probas, 0.95) == 2
    # 0,6 + 0,3 vaut 0,8999999999999999 en flottant : u = 0,9 tombe déjà sur la troisième issue.
    assert 0.6 + 0.3 < 0.9 and tirer(probas, 0.9) == 2
    # Dix fois 0,1 font 0,9999999999999999 en flottant : u = 0,9999999999999999 n'est sous
    # aucun cumul, et prend la dernière issue.
    dixiemes = [0.1] * 10
    assert tirer(dixiemes, 0.9999999999999999) == 9 and tirer(dixiemes, 0.3) == 2


def test_tirages():
    assert sum(tirages(probabilites(EXEMPLE_COMPTES), 1000, 1234)) == 1000
    assert tirages([0.5, 0.5], 0, 1) == [0, 0]
    # Même graine, mêmes tirages ; autre graine, autres tirages.
    probas = probabilites(EXEMPLE_COMPTES)
    assert tirages(probas, 100, 7) == tirages(probas, 100, 7)
    assert tirages(probas, 100, 7) != tirages(probas, 100, 8)
    # Une issue certaine sort à chaque fois.
    assert tirages([0.0, 1.0, 0.0], 50, 3) == [0, 50, 0]


def test_tirages_sans_issue():
    # Même sans tirage (n = 0) : une liste vide de probabilités n'a aucun sens.
    for n in (10, 0):
        with pytest.raises(ValueError) as erreur:
            tirages([], n, 1234)
        assert str(erreur.value) == "Aucune issue à tirer\u202f: donne au moins une probabilité."


def test_hasard_reproductible():
    a, b = Hasard(1234), Hasard(1234)
    suite = [a.uniforme() for _ in range(20)]
    assert suite == [b.uniforme() for _ in range(20)]
    assert all(0.0 <= u < 1.0 for u in suite)
    # La graine est ramenée à 32 bits : 2^32 donne la même suite que 0.
    assert Hasard(0).suivant32() == Hasard(2**32).suivant32()


def test_hasard_refuse_les_graines_qui_ne_sont_pas_des_entiers():
    with pytest.raises(TypeError, match="entier"):
        Hasard(1.5)
    with pytest.raises(TypeError, match="entier"):
        Hasard(True)
    with pytest.raises(ValueError, match="entiers sûrs"):
        Hasard(ENTIER_SUR_MAX + 1)


def _sources_de_hasard(chemin: Path) -> dict[str, str]:
    """Le texte de ENTIER_SUR_MAX et des méthodes copiées de Hasard, lu dans le fichier sans l'importer."""
    texte = chemin.read_text(encoding="utf-8")
    arbre = ast.parse(texte)
    sources: dict[str, str] = {}
    for noeud in arbre.body:
        if isinstance(noeud, ast.Assign) and [getattr(c, "id", None) for c in noeud.targets] == ["ENTIER_SUR_MAX"]:
            sources["ENTIER_SUR_MAX"] = ast.get_source_segment(texte, noeud)
        if isinstance(noeud, ast.ClassDef) and noeud.name == "Hasard":
            for methode in noeud.body:
                if isinstance(methode, ast.FunctionDef) and methode.name in METHODES_COPIEES:
                    sources[methode.name] = ast.get_source_segment(texte, methode)
    return sources


def test_hasard_identique_a_celui_du_mini_modele():
    original = RACINE / "projets" / "mini-modele" / "mini_modele" / "calcul.py"
    if not (RACINE / "projets" / "forge").exists():
        pytest.skip("Projet téléchargé seul : le mini-modèle n'est pas là pour comparer.")
    # Dans le dépôt, l'original doit exister : un chemin changé ne doit pas faire passer ce test à vide.
    assert original.exists(), f"{original} est introuvable : corrige son chemin dans ce test."
    copie = _sources_de_hasard(Path(tirage.__file__))
    attendu = _sources_de_hasard(original)
    assert sorted(attendu) == sorted(["ENTIER_SUR_MAX", *METHODES_COPIEES]), (
        "calcul.py du mini-modèle n'a plus ENTIER_SUR_MAX ou une des méthodes copiées : mets ce test à jour."
    )
    for nom in ["ENTIER_SUR_MAX", *METHODES_COPIEES]:
        assert copie.get(nom) == attendu[nom], (
            f"{nom} de maths_utiles/tirage.py n'est plus la copie exacte de celui de "
            "projets/mini-modele/mini_modele/calcul.py : recopie-le tel quel."
        )
