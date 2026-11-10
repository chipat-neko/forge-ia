"""Les attendus partagés avec le site sont à jour.

Le fichier tests/attendus.json est écrit par `uv run --extra cpu python -m evaluation_pas_a_pas.attendus`. Le jumeau
TypeScript (site/src/lib/partie-1/evaluation.ts, `marge95` et `verdictQcm`) est comparé à cette grille, sans
tolérance\u202f: les deux langages font les mêmes opérations dans le même ordre, avec une seule racine carrée, exacte.
"""

import json

from evaluation_pas_a_pas.attendus import (
    CHEMIN_ATTENDUS,
    EXACTITUDES,
    NOMBRES_DE_CHOIX,
    NOMBRES_DE_QUESTIONS,
    calculer_attendus,
    vers_json,
)
from evaluation_pas_a_pas.pas_a_pas import marge_95, marge_hasard, verdict


def test_le_fichier_est_a_jour():
    assert CHEMIN_ATTENDUS.read_bytes().decode("utf-8") == vers_json(calculer_attendus()) + "\n", (
        "tests/attendus.json n'est plus à jour. Régénère-le\u202f: uv run --extra cpu python -m evaluation_pas_a_pas.attendus"
    )


def test_le_fichier_est_ecrit_comme_les_autres_attendus():
    octets = CHEMIN_ATTENDUS.read_bytes()
    assert b"\r" not in octets and octets.endswith(b"]\n")
    assert json.dumps(json.loads(octets), ensure_ascii=False, allow_nan=False, indent=1) + "\n" == octets.decode("utf-8")


def test_la_grille_est_un_tableau_ordonne():
    cas = json.loads(CHEMIN_ATTENDUS.read_text(encoding="utf-8"))
    assert isinstance(cas, list) and len(cas) == len(NOMBRES_DE_CHOIX) * len(NOMBRES_DE_QUESTIONS) * len(EXACTITUDES)
    assert [(c["choix"], c["n"], c["exactitude"]) for c in cas[:3]] == [(3, 5, 0.0), (3, 5, 0.1), (3, 5, 0.2)]
    assert set(cas[0]) == {"exactitude", "n", "choix", "marge_95", "hasard", "marge_hasard", "verdict"}


def test_la_grille_dit_ce_que_disent_les_fonctions():
    for c in json.loads(CHEMIN_ATTENDUS.read_text(encoding="utf-8")):
        assert c["marge_95"] == marge_95(c["exactitude"], c["n"])
        assert c["hasard"] == 1 / c["choix"] and c["marge_hasard"] == marge_hasard(c["n"], c["choix"])
        assert c["verdict"] == verdict(c["exactitude"], c["hasard"], c["marge_hasard"])


def test_la_grille_montre_les_trois_verdicts_et_les_marges_nulles():
    cas = json.loads(CHEMIN_ATTENDUS.read_text(encoding="utf-8"))
    assert {c["verdict"] for c in cas} == {"au-dessus", "pas-different", "en-dessous"}
    assert any(c["marge_95"] == 0.0 for c in cas)  # 0 % et 100 % de bonnes réponses
