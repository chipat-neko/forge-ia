"""Les fonctions du mot suivant : découper, compter, prédire, générer, et la ligne de commande."""

from collections import Counter
from pathlib import Path

import pytest

from mot_suivant.__main__ import principal
from mot_suivant.mots import (
    charger_texte,
    compter_suivants,
    decouper_mots,
    generer,
    predire,
    premiere_reprise,
)

PROJET = Path(__file__).resolve().parents[1]
RACINE = PROJET.parents[1]


def test_decouper_mots():
    assert decouper_mots("Le forgeron frappe, le fer !") == ["le", "forgeron", "frappe", "le", "fer", "!"]
    assert decouper_mots("L’enclume") == ["l’enclume"]
    assert decouper_mots("Salut 🙂 ! 2026") == ["salut", "!"]


def test_decouper_mots_cas_limites():
    assert decouper_mots("") == []
    assert decouper_mots("ÉTÉ été") == ["été", "été"]
    assert decouper_mots("forge-ia. Fin?") == ["forge-ia", ".", "fin", "?"]
    # « İ » devient « i » suivi d'un point suscrivant (U+0307), qui n'est pas une lettre de la liste.
    assert decouper_mots("İstanbul ΟΔΟΣ") == ["i", "stanbul"]


def test_compter_suivants():
    s = compter_suivants(["le", "fer", "et", "le", "fer", "puis", "le", "feu"])
    assert s["le"] == Counter({"fer": 2, "feu": 1})
    assert "feu" not in s


def test_compter_suivants_dans_l_ordre_de_premiere_apparition():
    s = compter_suivants(["b", "a", "b", "c", "a"])
    assert list(s) == ["b", "a", "c"]
    assert list(s["b"]) == ["a", "c"]
    assert compter_suivants([]) == {} and compter_suivants(["seul"]) == {}


# region: test-predire
def test_predire_departage_et_rien_ne_suit():
    s = compter_suivants(["a", "c", "a", "b"])
    assert predire(s, "a") == "b"
    assert predire(s, "b") is None
# fin: test-predire


def test_predire_departage_par_point_de_code():
    # « z » (U+007A) passe avant « é » (U+00E9) : l'ordre des points de code, pas celui du dictionnaire.
    s = compter_suivants(["x", "é", "x", "z"])
    assert predire(s, "x") == "z"
    assert predire(s, "absent") is None


def test_generer_et_reprise():
    s = compter_suivants("a b a b a".split())
    assert generer(s, "a", 5) == ["a", "b", "a", "b", "a"]
    assert generer(s, "z", 5) == ["z"] and generer(s, "a", 0) == []
    assert premiere_reprise(["a", "b", "a"]) == 2 and premiere_reprise(["a", "b"]) is None


def test_generer_s_arrete_quand_rien_ne_suit():
    s = compter_suivants(["un", "deux", "trois"])
    assert generer(s, "un", 12) == ["un", "deux", "trois"]
    assert generer(s, "un", -1) == [] and generer(s, "un", 1) == ["un"]
    assert premiere_reprise([]) is None


def test_texte_identique_au_corpus_de_1_3():
    original = RACINE / "projets" / "1.3-tokenizer" / "donnees" / "corpus.txt"
    if not (RACINE / "projets" / "forge").exists():
        pytest.skip("Projet téléchargé seul : le corpus du chapitre 1.3 n'est pas là pour comparer.")
    # Dans le dépôt, l'original doit exister : un chemin changé ne doit pas faire passer ce test à vide.
    assert original.exists(), f"{original} est introuvable : corrige son chemin dans ce test."
    assert (PROJET / "donnees" / "texte.txt").read_bytes() == original.read_bytes(), (
        "donnees/texte.txt n'est plus la copie exacte du corpus de 1.3 : recopie "
        "projets/1.3-tokenizer/donnees/corpus.txt à sa place."
    )


def test_charger_texte():
    texte = charger_texte()
    assert "\r" not in texte
    assert texte.startswith("Avant de lire une phrase")


def test_ligne_de_commande(capsys):
    principal(["le", "--longueur", "12"])
    sortie = capsys.readouterr().out.replace("\u202f", " ")
    assert "Après « le », ce texte met :" in sortie
    assert "métal" in sortie
    assert "Le mot suivant le plus probable : « métal »." in sortie
    assert "Une suite de 12 mots : le métal forgé" in sortie


def test_ligne_de_commande_avec_un_fichier(tmp_path, capsys):
    fichier = tmp_path / "texte.txt"
    fichier.write_text("Un chat. Un chien. Un chat.", encoding="utf-8")
    principal(["Un", "--longueur", "3", "--fichier", str(fichier)])
    sortie = capsys.readouterr().out.replace("\u202f", " ")
    assert "Le mot suivant le plus probable : « chat »." in sortie
    assert "Une suite de 3 mots : un chat ." in sortie


def test_ligne_de_commande_mot_absent_et_erreurs(tmp_path, capsys):
    principal(["dragon"])
    sortie = capsys.readouterr().out.replace("\u202f", " ")
    assert "« dragon » n’est pas dans ce texte : rien ne le suit." in sortie
    with pytest.raises(SystemExit) as fin:
        principal(["le", "--fichier", str(tmp_path / "absent.txt")])
    assert fin.value.code == 1
    assert "introuvable" in capsys.readouterr().err
    with pytest.raises(SystemExit) as fin:
        principal(["le", "--longueur", "0"])
    assert fin.value.code == 1
    assert "au moins 1" in capsys.readouterr().err
