"""Les attendus partagés avec le site sont à jour.

Le fichier tests/attendus.json est écrit par
`uv run --extra cpu python -m transformer_pas_a_pas.attendus`. Le jumeau de la répartition
(site/src/lib/partie-1/parametres.ts) est comparé à sa section `repartitions`, au bit près
(des entiers). Le jumeau des angles (rope.ts) est comparé à la section `rope`.

Les angles passent par `**` (pow) : la bibliothèque mathématique de Windows (UCRT) et celle de
Linux (glibc) peuvent différer d'un bit. Ils se comparent donc à 10⁻⁹ près en relatif, comme le
projet 0.5. Les répartitions, des entiers, se comparent exactement.

La section `residus` (le pari « sans le `x +`, que devient l'entrée ? » du chapitre) passe par
les pièces du transformer, dont RMSNorm et RoPE calculent en float32, comme forge : d'un
processeur à l'autre, une somme en float32 peut changer d'un bit. Ses ressemblances se
comparent donc à 10⁻⁶ près ; le chapitre n'en montre que deux ou trois chiffres après la
virgule.
"""

import inspect
import json
import math

import pytest
import torch
from forge.modele.config import PRESETS, ConfigModele

from transformer_pas_a_pas import pieces
from transformer_pas_a_pas.attendus import (
    BASE,
    CHEMIN_ATTENDUS,
    DIM_TETE,
    GRAINE_RESIDUS,
    JETONS_RESIDUS,
    POSITIONS,
    PRESET_RESIDUS,
    angles_de_la_figure,
    bloc_sans_residus,
    calculer_attendus,
    textes_du_pari_residus,
    vers_json,
)

REGENERER = "Régénère-le avec « uv run --extra cpu python -m transformer_pas_a_pas.attendus » (dans projets/1.4-transformer)."
TOLERANCE_RELATIVE = 1e-9
TOLERANCE_ABSOLUE = 1e-12
# Les ressemblances de la section residus passent par float32 (RMSNorm, RoPE) : à 10⁻⁶ près.
TOLERANCE_RESIDUS = 1e-6
CLES_RESIDUS = ["preset", "couches", "dim", "jetons", "graine", "entrees", "poids_attention_min", "poids_attention_max", "par_bloc"]


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


def comparer_residus(calcule: dict, lu: dict) -> None:
    """La section residus : le nom et les entiers exactement, les ressemblances à 10⁻⁶ près.

    Nomme le premier écart (« residus.par_bloc[3].sans »)."""
    assert list(calcule) == list(lu), "residus : les clés ont changé"
    for cle in ("preset", "couches", "dim", "jetons", "graine"):
        assert calcule[cle] == lu[cle], f"residus.{cle} : {calcule[cle]!r} au lieu de {lu[cle]!r}"
    paires = [(f"residus.{cle}", calcule[cle], lu[cle]) for cle in ("entrees", "poids_attention_min", "poids_attention_max")]
    assert len(calcule["par_bloc"]) == len(lu["par_bloc"]), "residus.par_bloc : longueurs différentes"
    for i, (a, b) in enumerate(zip(calcule["par_bloc"], lu["par_bloc"])):
        assert list(a) == ["bloc", "avec", "sans"] and a["bloc"] == b["bloc"], f"residus.par_bloc[{i}] : forme différente"
        paires += [(f"residus.par_bloc[{i}].avec", a["avec"], b["avec"]), (f"residus.par_bloc[{i}].sans", a["sans"], b["sans"])]
    for nom, a, b in paires:
        assert type(a) is float, f"{nom} : {a!r} n'est pas un flottant"
        assert abs(a - b) <= TOLERANCE_RESIDUS, f"{nom} : {a!r} au lieu de {b!r}"


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
    # Des ressemblances qui passent par float32 : à 10⁻⁶ près.
    try:
        comparer_residus(calcule["residus"], lu["residus"])
    except AssertionError as ecart:
        raise AssertionError(f"La section « residus » n'est plus à jour ({ecart}). {REGENERER}") from None


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
    assert list(a) == ["repartitions", "rope", "residus"]
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


# --- La section residus : le pari « sans le `x +`, que devient l'entrée ? » ------------------


def test_forme_des_residus():
    r = lire()["residus"]
    assert list(r) == CLES_RESIDUS
    config = PRESETS[PRESET_RESIDUS]
    assert (r["preset"], r["couches"], r["dim"], r["jetons"], r["graine"]) == (
        PRESET_RESIDUS,
        config.couches,
        config.dim,
        JETONS_RESIDUS,
        GRAINE_RESIDUS,
    )
    assert [b["bloc"] for b in r["par_bloc"]] == list(range(1, config.couches + 1))


def test_la_tolerance_des_residus_attrape_une_vraie_difference():
    lu = lire()["residus"]
    copie = json.loads(json.dumps(lu))
    copie["par_bloc"][3]["sans"] += 1e-9
    comparer_residus(copie, lu)
    copie["par_bloc"][3]["sans"] += 1e-4
    with pytest.raises(AssertionError, match=r"par_bloc\[3\]\.sans"):
        comparer_residus(copie, lu)


def test_les_deux_textes_ne_different_que_par_le_dernier_jeton():
    a, b = textes_du_pari_residus()
    assert a.shape == b.shape == (JETONS_RESIDUS,)
    assert torch.equal(a[:-1], b[:-1])
    assert a[-1] != b[-1]


def test_sans_residus_c_est_le_bloc_moins_ses_x_plus():
    # Le même code que pieces.bloc, à ses deux « x + » près : rien d'autre ne change.
    def corps(fonction) -> list[str]:
        lignes = inspect.getsource(fonction).splitlines()
        return [ligne.strip() for ligne in lignes[2:]]  # sans la ligne def ni la docstring d'une ligne

    assert sum(ligne.count("x + ") for ligne in corps(pieces.bloc)) == 2
    assert [ligne.replace("x + ", "", 1) for ligne in corps(pieces.bloc)] == corps(bloc_sans_residus)


def test_sans_residus_avec_des_sous_couches_muettes():
    # Des poids de sortie nuls : les sous-couches n'écrivent rien. Avec le x +, le vecteur passe
    # tel quel ; sans, il ne reste rien.
    from transformer_pas_a_pas.comparer import poids_de_forge, preparer_forge

    c = ConfigModele(dim=32, couches=1, tetes=4, longueur_contexte=8, taille_vocabulaire=50)
    p = dict(poids_de_forge(preparer_forge(c, 0))["blocs"][0])
    p["w_sortie"] = torch.zeros_like(p["w_sortie"])
    p["w_basse"] = torch.zeros_like(p["w_basse"])
    x = torch.randn(8, 32, dtype=torch.float64, generator=torch.Generator().manual_seed(2))
    assert torch.equal(pieces.bloc(x, p), x)
    assert torch.equal(bloc_sans_residus(x, p), torch.zeros_like(x))


def test_les_residus_disent_ce_que_dit_le_chapitre():
    r = lire()["residus"]
    dernier = r["par_bloc"][-1]
    # Deux jetons différents : leurs vecteurs d'entrée ne se ressemblent pas.
    assert abs(r["entrees"]) < 0.5
    # Sans le x +, les deux textes finissent par sortir pareils ; avec, ils restent distincts.
    assert dernier["sans"] >= 0.999
    assert dernier["avec"] < 0.999
    # Au départ, l'attention répartit presque également : autour de 1/16 par jeton.
    assert 0.5 / JETONS_RESIDUS < r["poids_attention_min"] <= 1 / JETONS_RESIDUS <= r["poids_attention_max"] < 2 / JETONS_RESIDUS
