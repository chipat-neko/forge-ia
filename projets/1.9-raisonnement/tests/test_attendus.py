"""Les attendus partagés avec le site sont à jour.

Le fichier tests/attendus.json est écrit par `uv run --extra cpu python -m raisonnement_pas_a_pas.attendus`. Les jumeaux
TypeScript (site/src/lib/partie-1/problemes.ts et avantages.ts) sont comparés à ce fichier, sans tolérance : les
problèmes sont du texte et des entiers, les avantages et les chances des flottants que les deux langages calculent avec
les mêmes opérations dans le même ordre.
"""

import json

from forge.conversation.format import Reponse
from forge.raisonnement.problemes import FORMES, GRAINES_EVALUATION, GRAINES_VALIDATION_RL, PRENOMS_EVALUATION, PRENOMS_VALIDATION_RL, generer_probleme
from forge.raisonnement.verification import est_juste, extraire_nombre

from raisonnement_pas_a_pas.attendus import CHANCES, CHEMIN_ATTENDUS, GRAINES, GROUPES, TAILLES, TEXTES, calculer_attendus, vers_json
from raisonnement_pas_a_pas.avantages import avantages_a_la_main, sans_signal


def attendus() -> dict:
    return json.loads(CHEMIN_ATTENDUS.read_text(encoding="utf-8"))


def test_attendus_a_jour():
    # Relu valeur par valeur, pas octet par octet : seuls des entiers, du texte, des verdicts et des flottants issus
    # d'additions, de soustractions, de multiplications et de divisions (exactes sous Windows comme sous Linux) y sont écrits,
    # mais aucune fonction de la bibliothèque mathématique du C (exp, log, pow) : si une s'y glissait, elle se comparerait à 1e-12 près.
    assert json.loads(CHEMIN_ATTENDUS.read_text(encoding="utf-8")) == json.loads(vers_json(calculer_attendus())), (
        "tests/attendus.json n'est plus à jour. Régénère-le\u202f: uv run --extra cpu python -m raisonnement_pas_a_pas.attendus"
    )


def test_le_fichier_est_ecrit_comme_les_autres_attendus():
    octets = CHEMIN_ATTENDUS.read_bytes()
    assert b"\r\n" not in octets and octets.endswith(b"}\n")
    assert json.dumps(json.loads(octets), ensure_ascii=False, allow_nan=False, indent=1) + "\n" == octets.decode("utf-8")


def test_les_cinq_sections():
    assert list(attendus()) == ["problemes", "problemes_reserves", "nombres", "avantages", "sans_signal"]


def test_les_problemes_de_chaque_famille_difficulte_et_graine_0_a_4():
    problemes = attendus()["problemes"]
    couples = [(f, d) for f, difficultes in FORMES.items() for d in difficultes]
    assert len(couples) == 14 and len(problemes) == 14 * 5 == 70
    assert [(p["famille"], p["difficulte"], p["graine"]) for p in problemes] == [(f, d, g) for f, d in couples for g in GRAINES]
    for p in problemes:
        assert list(p) == ["famille", "difficulte", "graine", "enonce", "etapes", "reponse"]
        de_forge = generer_probleme(p["famille"], p["difficulte"], p["graine"])
        assert (p["enonce"], p["etapes"], p["reponse"]) == (de_forge.enonce, list(de_forge.etapes), de_forge.reponse)
        assert p["etapes"][-1].endswith(f" = {p['reponse']}")


def test_les_problemes_reserves_ont_les_prenoms_de_leur_usage():
    reserves = attendus()["problemes_reserves"]
    assert len(reserves) == 14 * 2
    for p in reserves:
        usage = PRENOMS_EVALUATION if p["graine"] == GRAINES_EVALUATION else PRENOMS_VALIDATION_RL
        assert p["graine"] in (GRAINES_EVALUATION, GRAINES_VALIDATION_RL)
        assert any(prenom in p["enonce"] for prenom in usage), p["enonce"]


def test_les_enonces_sont_tous_differents():
    # Les 70 énoncés sont tous différents : de quoi vérifier que le jumeau ne rend pas toujours le même problème.
    enonces = [p["enonce"] for p in attendus()["problemes"]]
    assert len(set(enonces)) == len(enonces)
    texte = " ".join(enonces)
    assert "d'" in texte and "qu'" in texte  # l'élision devant une voyelle, de « de » et de « que »


def test_les_nombres_lus_sont_ceux_de_forge():
    nombres = attendus()["nombres"]
    assert [n["texte"] for n in nombres] == list(TEXTES)
    for n in nombres:
        lu = extraire_nombre(n["texte"])
        assert n["lu"] == (None if lu is None else (str(lu.numerator) if lu.denominator == 1 else f"{lu.numerator}/{lu.denominator}"))
        for v in n["verdicts"]:
            reponse = Reponse(texte=n["texte"], pensee=None, ids=[], terminee=v["terminee"])
            assert v["juste"] is est_juste(reponse, v["attendu"]), (n["texte"], v)
            assert v["juste"] is False or v["terminee"] is True  # une réponse coupée n'est jamais juste


def test_les_pieges_de_la_lecture_d_un_nombre():
    lu = {n["texte"]: n["lu"] for n in attendus()["nombres"]}
    assert lu["12 3456"] == "3456" and lu["12 345"] == "12345" and lu["1 2 3"] == "3"
    assert lu["12,5"] == "25/2" and lu["12,50"] == "25/2" and lu["3.5"] == "7/2" and lu["1.234"] == "617/500"
    assert lu["3, puis 4"] == "4" and lu["3,"] == "3" and lu["4."] == "4"
    assert lu["-3"] == "-3" and lu["x = -4"] == "-4" and lu["5-3"] == "3" and lu["5 - 3"] == "3" and lu["a-3"] == "3"
    assert lu["-0"] == "0" and lu["-0,0"] == "0" and lu["007"] == "7"
    assert lu[""] is None and lu["trois"] is None
    assert lu["a" + "9" * 40] == "9" * 40  # bien au-delà des entiers sûrs de JavaScript : des BigInt
    # Les chiffres hors de [0-9] ne sont pas des chiffres.
    assert lu[chr(0x0663)] is None and lu["12" + chr(0x0663)] == "12" and lu[chr(0xFF13) + "4"] == "4"
    # Un signe collé à une lettre, un chiffre, un exposant ou un chiffre romain n'en est pas un ; un tiret après « _ » en est un.
    assert lu["3" + chr(0x00B2) + "-3"] == "3" and lu[chr(0x2167) + "-3"] == "3" and lu["_-3"] == "-3"
    assert lu["𝒜-3"] == "3"  # une lettre hors du premier plan d'Unicode


def test_les_avantages_sont_ceux_de_la_main():
    section = attendus()["avantages"]
    assert len(section) == len(GROUPES) == 10
    assert [s["recompenses"] for s in section] == [list(g) for g in GROUPES]
    assert [s["avantages"] for s in section] == avantages_a_la_main([list(g) for g in GROUPES])
    assert any(all(a == 0 for a in s["avantages"]) for s in section)  # il y a des groupes sans signal


def test_la_grille_de_sans_signal():
    grille = attendus()["sans_signal"]
    assert len(grille) == len(CHANCES) * len(TAILLES) == 54
    assert [(g["p"], g["n"]) for g in grille] == [(p, n) for p in CHANCES for n in TAILLES]
    for g in grille:
        assert g["chance"] == sans_signal(g["p"], g["n"]) and 0 <= g["chance"] <= 1


def test_hors_des_avantages_et_de_la_grille_aucun_flottant():
    def flottants(valeur) -> list:
        if isinstance(valeur, float):
            return [valeur]
        if isinstance(valeur, dict):
            return [f for v in valeur.values() for f in flottants(v)]
        if isinstance(valeur, list):
            return [f for v in valeur for f in flottants(v)]
        return []

    donnees = attendus()
    assert flottants(donnees["problemes"]) == [] and flottants(donnees["problemes_reserves"]) == [] and flottants(donnees["nombres"]) == []
