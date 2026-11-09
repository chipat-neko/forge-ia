"""Les attendus partagés avec le site sont à jour.

Le fichier tests/attendus.json est écrit par `uv run python -m modele_de_langage.attendus`
et relu par Vitest, par la page de parité du site et par le chapitre 1.1. Si le
code ou le texte d'apprentissage change, ces tests échouent tant que le fichier
n'est pas régénéré.
"""

import json
import math

import pytest

from modele_de_langage.attendus import (
    CAS_LIMITES,
    CHEMIN_ATTENDUS,
    SECTIONS_EXACTES,
    SECTIONS_LIBM,
    SORTIES_LIBM,
    calculer_attendus,
    vers_json,
)
from modele_de_langage.ngrammes import ORDRE_MAX, TEMPERATURES, charger_texte, couper

REGENERER = "Régénère-le avec « uv run python -m modele_de_langage.attendus » (dans projets/1.1-modele-de-langage)."

# Les deux perplexités de chaque ordre passent par math.exp et math.log, qui dépendent
# de la bibliothèque mathématique du système : celle de Linux (glibc) et celle de
# Windows (UCRT) ne sont pas arrondies au plus juste, et peuvent différer d'un bit
# sur le dernier chiffre. Le fichier, écrit sur une machine, est relu sur l'autre
# par l'intégration continue : ces nombres (les clés de SORTIES_LIBM) se comparent
# donc un par un, à 10^-9 près en relatif (10^-12 en absolu, pour les zéros).
# Tout le reste (comptes, probabilités lissées, suites écrites) n'utilise que des
# entiers, + − × ÷ et la racine carrée, arrondis au plus juste partout : il se
# compare au bit près.
TOLERANCE_RELATIVE = 1e-9
TOLERANCE_ABSOLUE = 1e-12


def lire() -> dict:
    return json.loads(CHEMIN_ATTENDUS.read_text(encoding="utf-8"))


def comparer_a_peu_pres(calcule, lu, chemin: str, tolerant: bool = False) -> None:
    """Même forme, mêmes textes, mêmes entiers ; les sorties d'exp et de log (sous une
    clé de SORTIES_LIBM) à la tolérance près.

    Lève une AssertionError qui nomme le chemin du premier écart (« ordres[2].perplexite_validation »).
    """
    if isinstance(lu, dict):
        assert isinstance(calcule, dict) and list(calcule) == list(lu), f"{chemin} : clés différentes"
        for cle in lu:
            comparer_a_peu_pres(calcule[cle], lu[cle], f"{chemin}.{cle}", tolerant or cle in SORTIES_LIBM)
    elif isinstance(lu, list):
        assert isinstance(calcule, list) and len(calcule) == len(lu), f"{chemin} : longueurs différentes"
        for i, (a, b) in enumerate(zip(calcule, lu)):
            comparer_a_peu_pres(a, b, f"{chemin}[{i}]", tolerant)
    elif isinstance(lu, float) and tolerant:
        assert isinstance(calcule, float), f"{chemin} : {calcule!r} n'est pas un flottant"
        assert math.isclose(calcule, lu, rel_tol=TOLERANCE_RELATIVE, abs_tol=TOLERANCE_ABSOLUE), (
            f"{chemin} : {calcule!r} au lieu de {lu!r}"
        )
    else:
        # Par le texte JSON : -0.0 et 0.0, ou 6 et 6.0, ne passent pas l'un pour l'autre.
        assert type(calcule) is type(lu) and vers_json(calcule) == vers_json(lu), (
            f"{chemin} : {calcule!r} au lieu de {lu!r}"
        )


def test_attendus_a_jour():
    assert CHEMIN_ATTENDUS.exists(), f"tests/attendus.json est introuvable. {REGENERER}"
    calcule = calculer_attendus()
    lu = lire()
    assert list(calcule) == list(lu), f"tests/attendus.json n'a plus les mêmes sections. {REGENERER}"
    for nom in SECTIONS_EXACTES:
        # Le texte JSON, écrit comme le fichier : « == » prendrait -0.0 pour 0.0, et 6 pour 6.0.
        assert vers_json(calcule[nom]) == vers_json(lu[nom]), (
            f"La section « {nom} » de tests/attendus.json n'est plus à jour. {REGENERER}"
        )
    for nom in SECTIONS_LIBM:
        try:
            # Aller-retour par JSON : les tuples deviennent des listes, comme à la relecture.
            comparer_a_peu_pres(json.loads(vers_json(calcule[nom])), lu[nom], nom)
        except AssertionError as ecart:
            raise AssertionError(f"La section « {nom} » n'est plus à jour ({ecart}). {REGENERER}") from None


def test_sections_exactes_et_libm():
    assert SECTIONS_EXACTES == ("alphabet", "suites", "tirages", "cas_limites")
    assert SECTIONS_LIBM == ("ordres",)
    # Chaque section du fichier est dans l'une des deux listes, et une seule.
    assert sorted(lire()) == sorted(SECTIONS_EXACTES + SECTIONS_LIBM)


def test_la_tolerance_ne_cache_pas_une_vraie_difference():
    lu = lire()["ordres"]
    # Un bit de différence sur la perplexité passe : c'est ce que la tolérance laisse aux systèmes.
    a_un_bit = json.loads(json.dumps(lu))
    a_un_bit[2]["perplexite_validation"] = math.nextafter(a_un_bit[2]["perplexite_validation"], 1e9)
    comparer_a_peu_pres(a_un_bit, lu, "ordres")
    # Une vraie différence, même au millionième, ne passe pas.
    au_millionieme = json.loads(json.dumps(lu))
    au_millionieme[2]["perplexite_validation"] *= 1 + 1e-6
    with pytest.raises(AssertionError, match=r"ordres\[2\]\.perplexite_validation"):
        comparer_a_peu_pres(au_millionieme, lu, "ordres")
    # Les autres nombres se comparent au bit près : un bit de plus sur une probabilité ne passe pas.
    probabilite = json.loads(json.dumps(lu))
    rang = probabilite[1]["distributions"][0]["rangs"][0]
    rang[1] = math.nextafter(rang[1], 1.0)
    with pytest.raises(AssertionError, match=r"ordres\[1\]\.distributions\[0\]\.rangs\[0\]\[1\]"):
        comparer_a_peu_pres(probabilite, lu, "ordres")
    # Ni un nombre en moins, ni un entier à la place d'un flottant.
    en_moins = json.loads(json.dumps(lu))
    en_moins[3]["distributions"].pop()
    with pytest.raises(AssertionError, match="longueurs"):
        comparer_a_peu_pres(en_moins, lu, "ordres")
    with pytest.raises(AssertionError, match="flottant"):
        comparer_a_peu_pres([{"perplexite_validation": 1}], [{"perplexite_validation": 1.0}], "ordres")
    # Les jamais_vus sont des entiers : ils se comparent exactement.
    jamais_vus = json.loads(json.dumps(lu))
    jamais_vus[4]["jamais_vus"][0] += 1
    with pytest.raises(AssertionError, match=r"ordres\[4\]\.jamais_vus\[0\]"):
        comparer_a_peu_pres(jamais_vus, lu, "ordres")


def test_le_texte_json_distingue_ce_que_egal_confond():
    # « == » confond -0.0 et 0.0, 6 et 6.0 : le texte JSON du fichier, non.
    assert -0.0 == 0.0 and vers_json(-0.0) != vers_json(0.0)
    assert 6 == 6.0 and vers_json(6) != vers_json(6.0)


def test_contenu_du_fichier():
    lu = lire()
    texte = charger_texte()
    entrainement, validation = couper(texte)
    assert lu["alphabet"] == sorted(set(texte))
    assert [o["n"] for o in lu["ordres"]] == list(range(ORDRE_MAX + 1))
    assert len(lu["suites"]) == ORDRE_MAX * len(TEMPERATURES) * 2
    assert all(s["suite"].startswith(s["depart"]) and len(s["suite"]) == s["n"] + 120 for s in lu["suites"])
    assert all(s["depart"] == validation[: s["n"]] for s in lu["suites"])
    assert [c["nom"] for c in lu["cas_limites"]] == [nom for nom, *_ in CAS_LIMITES]
    # Les tirages : chaque ordre, chaque température, chaque contexte de référence.
    assert len(lu["tirages"]) == (ORDRE_MAX + 1) * len(TEMPERATURES) * 6
    for t in lu["tirages"]:
        assert 0 <= t["ordre"] <= t["n"] and 1 <= len(t["rangs"]) <= 10 and len(t["rangs"]) <= t["nombre"]
    # Le contexte absent recule toujours à l'ordre 0 ; à température 0, un seul caractère a une chance.
    assert all(t["ordre"] == 0 for t in lu["tirages"] if set(t["contexte"]) == {"¤"})
    assert all(t["nombre"] == 1 and t["rangs"][0][1] == 1.0 for t in lu["tirages"] if t["temperature"] == 0)
    # Les cas limites ont aussi leur tirage, ou l'erreur qu'il lève.
    assert all((c["tirage"] is None) != (c["erreur_tirage"] is None) for c in lu["cas_limites"])
    # Chaque contexte de référence a ses dix premiers rangs.
    assert all(len(d["rangs"]) == 10 for o in lu["ordres"] for d in o["distributions"])
    assert len(entrainement) + len(validation) == len(texte)


def test_les_perplexites_de_chaque_ordre_sont_finies_et_les_entiers_sont_des_entiers():
    for o in lire()["ordres"]:
        for cle in SORTIES_LIBM:
            assert isinstance(o[cle], float) and math.isfinite(o[cle]) and o[cle] > 1
        absents, total = o["jamais_vus"]
        assert isinstance(absents, int) and isinstance(total, int) and 0 <= absents <= total
