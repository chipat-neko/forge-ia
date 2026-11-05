"""Les attendus partagés avec le site sont à jour.

Le fichier tests/attendus.json est écrit par `uv run --extra cpu python -m poste.attendus`
et relu par le chapitre 0.3 (son tableau des situations, ses paris). Si le
diagnostic change, ces tests échouent tant que le fichier n'est pas régénéré.
"""

import json
from dataclasses import fields

from poste.attendus import CHEMIN_ATTENDUS, calculer_attendus, vers_json
from poste.diagnostic import SITUATIONS
from poste.faits import Faits

REGENERER = "Régénère-le avec « uv run --extra cpu python -m poste.attendus » (dans projets/0.3-poste)."


def lire() -> dict:
    return json.loads(CHEMIN_ATTENDUS.read_text(encoding="utf-8"))


def test_attendus_a_jour():
    assert CHEMIN_ATTENDUS.exists(), f"tests/attendus.json est introuvable. {REGENERER}"
    # Le texte entier, écrit comme le fichier : rien n'y est calculé en flottant.
    assert vers_json(calculer_attendus()) == CHEMIN_ATTENDUS.read_text(encoding="utf-8"), (
        f"tests/attendus.json n'est plus à jour. {REGENERER}"
    )


def test_fichier_en_utf8_et_lf():
    octets = CHEMIN_ATTENDUS.read_bytes()
    assert b"\r" not in octets, f"tests/attendus.json contient des fins de ligne Windows. {REGENERER}"
    assert octets.endswith(b"}\n"), f"tests/attendus.json doit finir par « }} » puis un retour à la ligne. {REGENERER}"


def test_forme_des_attendus():
    a = lire()
    assert list(a) == ["situations"]
    # Une liste de paires [nom, {faits, constats}], dans l'ordre de SITUATIONS.
    assert [nom for nom, _ in a["situations"]] == list(SITUATIONS)
    champs = [c.name for c in fields(Faits)]
    for nom, situation in a["situations"]:
        assert list(situation) == ["faits", "constats"], nom
        assert list(situation["faits"]) == champs, nom
        assert situation["constats"], nom
        for constat in situation["constats"]:
            assert list(constat) == ["niveau", "cle", "message", "a_faire"], nom
            assert constat["niveau"] in {"bon", "attention", "probleme"}, nom
            assert (constat["a_faire"] is None) == (constat["niveau"] == "bon"), nom


def test_ce_que_lit_le_chapitre():
    situations = dict(lire()["situations"])

    def cles(nom):
        return [c["cle"] for c in situations[nom]["constats"]]

    # Les paris et l'ouverture du chapitre 0.3.
    assert "roue_processeur" in cles("windows_pypi_rtx5070ti")
    assert "carte_trop_recente" in cles("windows_cu126_rtx5070ti")
    assert cles("windows_cu132_rtx5070ti") == ["carte_prete"]
    # Les fils du processeur et ceux que PyTorch prend par défaut (mesure du plan 2 : 16 et 8).
    fils = situations["fils_par_defaut"]["faits"]
    assert (fils["fils_processeur"], fils["fils_torch"]) == (16, 8)
    # Les capacités sont des listes [majeure, mineure] dans le JSON.
    assert situations["windows_cu132_rtx5070ti"]["faits"]["capacite"] == [12, 0]
    assert situations["colab_t4"]["faits"]["capacite"] == [7, 5]
