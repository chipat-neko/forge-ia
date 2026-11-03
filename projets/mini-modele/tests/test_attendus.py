"""Les attendus partagés avec le site sont à jour.

Chaque fichier tests/attendus-<nom>.json est écrit par
`uv run python -m mini_modele.attendus` et relu par Vitest (et par la page de
parité du site). Si le code change, ces tests échouent tant que les fichiers
ne sont pas régénérés.
"""

import json
import pathlib
import re

from mini_modele.attendus import CALCULS, calculer_attendus_calcul

DOSSIER = pathlib.Path(__file__).resolve().parent
REGENERER = "Régénère-les avec « uv run python -m mini_modele.attendus » (dans projets/mini-modele)."


def lire(nom: str):
    return json.loads((DOSSIER / f"attendus-{nom}.json").read_text(encoding="utf-8"))


def test_attendus_a_jour():
    assert CALCULS["calcul"] is calculer_attendus_calcul
    for nom, calculer in CALCULS.items():
        fichier = DOSSIER / f"attendus-{nom}.json"
        assert fichier.exists(), f"tests/attendus-{nom}.json est introuvable. {REGENERER}"
        # Aller-retour par JSON : les tuples deviennent des listes, comme à la relecture.
        assert json.loads(json.dumps(calculer())) == lire(nom), f"tests/attendus-{nom}.json n'est plus à jour. {REGENERER}"


def test_un_fichier_par_calcul():
    trouves = sorted(p.name for p in DOSSIER.glob("attendus-*.json"))
    assert trouves == sorted(f"attendus-{nom}.json" for nom in CALCULS), (
        "Chaque tests/attendus-<nom>.json doit avoir son calculer_attendus_<nom> dans CALCULS "
        "(mini_modele/attendus.py) : supprime le fichier orphelin ou ajoute son calcul."
    )


def test_attendus_calcul_au_complet():
    a = lire("calcul")
    assert a["constantes"] == {
        "LN2_HAUT": "3fe62e42fee00000",
        "LN2_BAS": "3dea39ef35793c76",
        "INV_LN2": "3ff71547652b82fe",
        "SQRT_DEMI": "3fe6a09e667f3bcd",
        "PI": "400921fb54442d18",
    }
    coefficients = a["coefficients"]
    assert (len(coefficients["C_EXP"]), len(coefficients["C_LOG"]), len(coefficients["C_COS"])) == (14, 12, 13)
    assert coefficients["C_EXP"][0] == coefficients["C_LOG"][0] == coefficients["C_COS"][0] == "3ff0000000000000"
    assert (len(a["exp"]), len(a["log"]), len(a["cos"])) == (27 + 200, 17 + 200, 9 + 100)
    hasard = a["hasard"]
    assert hasard["graine"] == 1234
    for cle in ("suivant32", "uniforme", "gaussienne", "gaussienne_0_08", "entier_10"):
        assert len(hasard[cle]) == 20, cle
    assert sorted(hasard["melange_20"]) == list(range(20))
    assert len(a["empreinte"]["valeurs"]) == 10
    assert a["empreinte_texte"]["texte"] == "Élodie, Zoé et Maël"
    motifs = [m for nom in ("exp", "log", "cos") for paire in a[nom] for m in paire]
    motifs += [m for table in coefficients.values() for m in table]
    motifs += hasard["uniforme"] + hasard["gaussienne"] + hasard["gaussienne_0_08"] + a["empreinte"]["valeurs"]
    assert all(re.fullmatch(r"[0-9a-f]{16}", m) for m in motifs)
    assert re.fullmatch(r"[0-9a-f]{8}", a["empreinte"]["empreinte"])
    assert re.fullmatch(r"[0-9a-f]{8}", a["empreinte_texte"]["empreinte"])


def test_fichiers_en_utf8_et_lf():
    for nom in CALCULS:
        octets = (DOSSIER / f"attendus-{nom}.json").read_bytes()
        assert b"\r" not in octets, f"tests/attendus-{nom}.json contient des fins de ligne Windows. {REGENERER}"
        assert octets.endswith(b"}\n")
