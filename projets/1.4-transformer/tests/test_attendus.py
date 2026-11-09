"""Les attendus partagés avec le site sont à jour.

Le fichier tests/attendus.json est écrit par
`uv run --extra cpu python -m transformer_pas_a_pas.attendus`. Le jumeau de la répartition
(site/src/lib/partie-1/parametres.ts) est comparé à sa section `repartitions`, au bit près
(des entiers). Le jumeau des angles (rope.ts) est comparé à la section `rope`.

Les angles passent par `**` (pow) : la bibliothèque mathématique de Windows (UCRT) et celle de
Linux (glibc) peuvent différer d'un bit. Ils se comparent donc à 10⁻⁹ près en relatif, comme le
projet 0.5. Les répartitions, des entiers, se comparent exactement.
"""

import json
import math

import pytest
from forge.modele.config import PRESETS, ConfigModele

from transformer_pas_a_pas.attendus import (
    BASE,
    CHEMIN_ATTENDUS,
    DIM_TETE,
    POSITIONS,
    angles_de_la_figure,
    calculer_attendus,
    vers_json,
)

REGENERER = "Régénère-le avec « uv run --extra cpu python -m transformer_pas_a_pas.attendus » (dans projets/1.4-transformer)."
TOLERANCE_RELATIVE = 1e-9
TOLERANCE_ABSOLUE = 1e-12


def lire() -> dict:
    return json.loads(CHEMIN_ATTENDUS.read_text(encoding="utf-8"))


def comparer_angles(calcule: list, lu: list) -> None:
    """Les angles à la tolérance près, nombre par nombre. Nomme le premier écart (« angles[17][2] »)."""
    assert len(calcule) == len(lu), "angles : longueurs différentes"
    for p, (ligne_a, ligne_b) in enumerate(zip(calcule, lu)):
        assert len(ligne_a) == len(ligne_b), f"angles[{p}] : longueurs différentes"
        for i, (a, b) in enumerate(zip(ligne_a, ligne_b)):
            assert type(a) is float, f"angles[{p}][{i}] : {a!r} n'est pas un flottant"
            assert math.isclose(a, b, rel_tol=TOLERANCE_RELATIVE, abs_tol=TOLERANCE_ABSOLUE), f"angles[{p}][{i}] : {a!r} au lieu de {b!r}"


def test_attendus_a_jour():
    assert CHEMIN_ATTENDUS.exists(), f"tests/attendus.json est introuvable. {REGENERER}"
    calcule = json.loads(vers_json(calculer_attendus()))
    lu = lire()
    assert list(calcule) == list(lu), f"tests/attendus.json n'a plus les mêmes sections. {REGENERER}"
    # Des entiers : exactement.
    assert vers_json(calcule["repartitions"]) == vers_json(lu["repartitions"]), f"La section « repartitions » n'est plus à jour. {REGENERER}"
    for cle in ("dim_tete", "base", "positions"):
        assert calcule["rope"][cle] == lu["rope"][cle], f"rope.{cle} n'est plus à jour. {REGENERER}"
    # Des flottants issus de pow, cos, sin : à 10⁻⁹ près.
    try:
        comparer_angles(calcule["rope"]["angles"], lu["rope"]["angles"])
    except AssertionError as ecart:
        raise AssertionError(f"La section « rope » n'est plus à jour ({ecart}). {REGENERER}") from None


def test_la_tolerance_ne_cache_pas_une_vraie_difference():
    lu = lire()["rope"]["angles"]
    copie = json.loads(json.dumps(lu))
    copie[17][2] = math.nextafter(copie[17][2], 100.0)
    comparer_angles(copie, lu)
    copie[17][2] *= 1 + 1e-6
    with pytest.raises(AssertionError, match=r"angles\[17\]\[2\]"):
        comparer_angles(copie, lu)


def test_fichier_en_utf8_et_lf():
    octets = CHEMIN_ATTENDUS.read_bytes()
    assert b"\r" not in octets, f"tests/attendus.json contient des fins de ligne Windows. {REGENERER}"
    assert octets.endswith(b"}\n"), f"tests/attendus.json doit finir par « }} » puis un retour à la ligne. {REGENERER}"


def test_forme_des_attendus():
    a = lire()
    assert list(a) == ["repartitions", "rope"]
    assert [r["preset"] for r in a["repartitions"]] == list(PRESETS)
    for r in a["repartitions"]:
        assert list(r) == ["preset", "taille_vocabulaire", "dim", "couches", "tetes", "longueur_contexte", "plongement", "attention", "mlp", "normes", "total"]
        assert r["total"] == r["plongement"] + r["attention"] + r["mlp"] + r["normes"]
    assert list(a["rope"]) == ["dim_tete", "base", "positions", "angles"]
    assert (a["rope"]["dim_tete"], a["rope"]["base"], a["rope"]["positions"]) == (8, 10000.0, 33)
    assert len(a["rope"]["angles"]) == 33 and all(len(ligne) == 4 for ligne in a["rope"]["angles"])


def test_la_base_est_celle_de_config_modele():
    assert BASE == ConfigModele(dim=8, couches=1, tetes=1, longueur_contexte=1).base_rope
    assert (DIM_TETE, POSITIONS) == (8, 33)


def test_la_figure_reste_en_float64():
    # Les angles de la figure ne passent pas par float32 (comme dans forge) : 10000 ** (-0,25) y serait arrondi.
    angles = angles_de_la_figure()
    assert angles[0] == [0.0, 0.0, 0.0, 0.0]
    assert angles[1][0] == 1.0
    assert angles[32][0] == 32.0
    assert angles[1][1] == BASE ** (-2 / 8)
    assert angles[1][1] != float(__import__("numpy").float32(BASE ** (-2 / 8)))
