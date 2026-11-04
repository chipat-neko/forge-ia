"""Les attendus partagés avec le site sont à jour.

Le fichier tests/attendus.json est écrit par `uv run python -m mot_suivant.attendus`
et relu par Vitest et par la page de parité du site. Si le code change, ces
tests échouent tant que le fichier n'est pas régénéré.
"""

import json

from mot_suivant.attendus import CHEMIN_ATTENDUS, LONGUEURS, TEXTES_DE_REFERENCE, calculer_attendus
from mot_suivant.mots import charger_texte

REGENERER = "Régénère-le avec « uv run python -m mot_suivant.attendus » (dans projets/0.1-python)."


def lire() -> dict:
    return json.loads(CHEMIN_ATTENDUS.read_text(encoding="utf-8"))


def test_attendus_a_jour():
    assert CHEMIN_ATTENDUS.exists(), f"tests/attendus.json est introuvable. {REGENERER}"
    # Aller-retour par JSON : les tuples deviennent des listes, comme à la relecture.
    assert json.loads(json.dumps(calculer_attendus())) == lire(), f"tests/attendus.json n'est plus à jour. {REGENERER}"


def test_fichier_en_utf8_et_lf():
    octets = CHEMIN_ATTENDUS.read_bytes()
    assert b"\r" not in octets, f"tests/attendus.json contient des fins de ligne Windows. {REGENERER}"
    assert octets.endswith(b"}\n")


def test_textes_et_longueurs_de_reference():
    assert TEXTES_DE_REFERENCE[0] == charger_texte()
    assert TEXTES_DE_REFERENCE[1:] == [
        "",
        "le",
        "Le LE le.",
        "l’enclume et l'enclume",
        "Salut 🙂 ! 2026",
        "ÉTÉ été",
        "a b a b a",
        "İstanbul ΟΔΟΣ forge-ia",
        "a " * 5000,
    ]
    assert LONGUEURS == [1, 2, 12, 30]


def test_forme_des_attendus():
    a = lire()
    assert set(a) == {"textes"}
    assert [t["texte"] for t in a["textes"]] == TEXTES_DE_REFERENCE
    for t in a["textes"]:
        assert set(t) == {"texte", "mots", "suivants", "predictions", "suites"}
        distincts = list(dict.fromkeys(t["mots"]))
        # « inconnu » sert de mot absent : il ne doit être dans aucun texte de référence.
        assert "inconnu" not in distincts
        assert [mot for mot, _ in t["predictions"]] == distincts
        assert [(s["depart"], s["longueur"]) for s in t["suites"]] == [
            (depart, longueur) for depart in [*distincts, "inconnu"] for longueur in LONGUEURS
        ]
        for _, suivants in t["suivants"]:
            # Par compte décroissant, puis par point de code.
            assert suivants == sorted(suivants, key=lambda paire: (-paire[1], paire[0]))
        for s in t["suites"]:
            assert set(s) == {"depart", "longueur", "suite", "reprise"}
            assert 1 <= len(s["suite"]) <= s["longueur"]


def test_quelques_valeurs_connues():
    textes = {t["texte"]: t for t in lire()["textes"]}
    vide = textes[""]
    assert (vide["mots"], vide["suivants"], vide["predictions"]) == ([], [], [])
    assert [s["suite"] for s in vide["suites"]] == [["inconnu"]] * len(LONGUEURS)
    assert textes["le"]["predictions"] == [["le", None]]
    assert textes["Le LE le."]["suivants"] == [["le", [["le", 2], [".", 1]]]]
    assert textes["l’enclume et l'enclume"]["mots"] == ["l’enclume", "et", "l'enclume"]
    assert textes["Salut 🙂 ! 2026"]["mots"] == ["salut", "!"]
    assert textes["İstanbul ΟΔΟΣ forge-ia"]["mots"] == ["i", "stanbul", "forge-ia"]
    alternance = textes["a b a b a"]["suites"]
    assert {"depart": "a", "longueur": 12, "suite": ["a", "b"] * 6, "reprise": 2} in alternance
    assert {"depart": "inconnu", "longueur": 30, "suite": ["inconnu"], "reprise": None} in alternance
    longue = textes["a " * 5000]
    assert len(longue["mots"]) == 5000 and longue["suivants"] == [["a", [["a", 4999]]]]
