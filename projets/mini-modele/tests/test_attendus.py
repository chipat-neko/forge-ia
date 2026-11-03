"""Les attendus partagés avec le site sont à jour.

Chaque fichier tests/attendus-<nom>.json est écrit par
`uv run python -m mini_modele.attendus` et relu par Vitest (et par la page de
parité du site). Si le code change, ces tests échouent tant que les fichiers
ne sont pas régénérés.
"""

import json
import pathlib
import re

from mini_modele.attendus import (
    CALCULS,
    calculer_attendus_calcul,
    calculer_attendus_donnees,
    calculer_attendus_modele,
)
from mini_modele.calcul import empreinte_texte
from mini_modele.donnees import donnees_par_defaut
from mini_modele.modele import ConfigMini, nombre_parametres

DOSSIER = pathlib.Path(__file__).resolve().parent
REGENERER = "Régénère-les avec « uv run python -m mini_modele.attendus » (dans projets/mini-modele)."


def lire(nom: str):
    return json.loads((DOSSIER / f"attendus-{nom}.json").read_text(encoding="utf-8"))


def test_attendus_a_jour():
    assert CALCULS["calcul"] is calculer_attendus_calcul
    assert CALCULS["donnees"] is calculer_attendus_donnees
    assert CALCULS["modele"] is calculer_attendus_modele
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


def test_attendus_donnees_au_complet():
    a = lire("donnees")
    assert set(a) == {
        "nb_prenoms", "empreinte_fichier", "vocabulaire", "nb_entrainement", "nb_validation",
        "entrainement_10", "validation_10", "empreinte_entrainement", "empreinte_validation",
    }
    assert a["nb_entrainement"] + a["nb_validation"] == a["nb_prenoms"]
    assert a["nb_validation"] == a["nb_prenoms"] // 10
    assert a["vocabulaire"][0] == "." and list(a["vocabulaire"][1:]) == sorted(set(a["vocabulaire"][1:]))
    assert len(a["entrainement_10"]) == len(a["validation_10"]) == 10
    assert all(isinstance(p, str) and p for p in a["entrainement_10"] + a["validation_10"])
    for cle in ("empreinte_fichier", "empreinte_entrainement", "empreinte_validation"):
        assert re.fullmatch(r"[0-9a-f]{8}", a[cle]), cle
    # Le fichier versionné est celui des attendus : même nombre de prénoms, même empreinte.
    octets = (DOSSIER.parent / "donnees" / "prenoms.txt").read_bytes()
    assert a["nb_prenoms"] == octets.count(b"\n")
    assert a["empreinte_fichier"] == empreinte_texte(octets.decode("utf-8"))


def test_attendus_modele_au_complet():
    fichier = lire("modele")
    # Une clé par partie : « modele » ici ; l'entraînement aura la sienne à côté.
    assert "modele" in fichier
    a = fichier["modele"]
    assert set(a) == {
        "config", "graine", "nb_parametres", "init_empreinte", "init_premiers", "lot", "perte_lot",
        "pertes_positions_empreinte", "gradient_empreinte", "gradient_premiers", "perte_validation_256", "generes",
    }
    d = donnees_par_defaut()
    v = len(d.vocabulaire)
    # La configuration est écrite comme en Python (taille_vocabulaire, largeur_mlp) : le TypeScript émet les mêmes clés.
    assert a["config"] == {"taille_vocabulaire": v, "dim": 16, "tetes": 4, "contexte": 16, "largeur_mlp": 64}
    assert a["graine"] == 1234
    assert a["nb_parametres"] == nombre_parametres(ConfigMini(taille_vocabulaire=v)) == 32 * v + 3328
    assert a["lot"] == [list(s) for s in d.entrainement[:8]]
    assert len(a["init_premiers"]) == len(a["gradient_premiers"]) == 8
    motifs = a["init_premiers"] + a["gradient_premiers"] + [a["perte_lot"], a["perte_validation_256"]]
    assert all(re.fullmatch(r"[0-9a-f]{16}", m) for m in motifs)
    assert re.fullmatch(r"[0-9a-f]{8}", a["init_empreinte"])
    assert re.fullmatch(r"[0-9a-f]{8}", a["gradient_empreinte"])
    assert re.fullmatch(r"[0-9a-f]{8}", a["pertes_positions_empreinte"])
    assert len(a["generes"]) == 8
    assert all(isinstance(p, str) and len(p) <= 15 and set(p) <= set(d.vocabulaire[1:]) for p in a["generes"])
