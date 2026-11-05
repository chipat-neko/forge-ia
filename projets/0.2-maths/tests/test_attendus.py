"""Les attendus partagés avec le site sont à jour.

Le fichier tests/attendus.json est écrit par `uv run python -m maths_utiles.attendus`
et relu par Vitest, par la page de parité du site et par le chapitre 0.2. Si le
code change, ces tests échouent tant que le fichier n'est pas régénéré.
"""

import json
import math

import pytest

from maths_utiles.attendus import (
    CAS_MESSAGES,
    CAS_TIRER,
    CHEMIN_ATTENDUS,
    DEPARTS_DESCENTE,
    GRAINE_UNIFORMES,
    MATRICES_DE_REFERENCE,
    NB_GRAINES,
    NB_PAS_DESCENTE,
    NB_UNIFORMES,
    NOMBRES_DE_TIRAGES,
    PROBAS_ERREUR,
    SCORES_SOFTMAX,
    SECTIONS_EXACTES,
    SECTIONS_LIBM,
    SEUIL_DESCENTE,
    TEMPERATURES,
    VECTEURS_DE_REFERENCE,
    calculer_attendus,
    vers_json,
)
from maths_utiles.derivees import TAUX_DESCENTE
from maths_utiles.tirage import EXEMPLE_COMPTES, GRAINE_TIRAGE

REGENERER = "Régénère-le avec « uv run python -m maths_utiles.attendus » (dans projets/0.2-maths)."

# Les sections qui passent par math.exp et math.log (softmax, erreur) dépendent de
# la bibliothèque mathématique du système : celle de Linux (glibc) et celle de
# Windows (UCRT) ne sont pas arrondies au plus juste, et peuvent différer d'un bit
# sur le dernier chiffre. Le fichier, écrit sur une machine, est relu sur l'autre
# par l'intégration continue : les nombres que ces sections tirent d'exp et de log
# (les clés de SORTIES_LIBM) se comparent donc un par un, à 10^-9 près en relatif
# (10^-12 en absolu, pour les zéros). Leurs entrées (scores, température, p) se
# comparent au bit près. Toutes les autres sections n'utilisent que + − × ÷ et la
# racine carrée, arrondies au plus juste partout : elles se comparent au bit près.
TOLERANCE_RELATIVE = 1e-9
TOLERANCE_ABSOLUE = 1e-12
SORTIES_LIBM = {"probabilites", "erreur"}


def lire() -> dict:
    return json.loads(CHEMIN_ATTENDUS.read_text(encoding="utf-8"))


def comparer_a_peu_pres(calcule, lu, chemin: str, tolerant: bool = False) -> None:
    """Même forme, mêmes textes, mêmes entiers et mêmes entrées ; les sorties d'exp et
    de log (sous une clé de SORTIES_LIBM) à la tolérance près.

    Lève une AssertionError qui nomme le chemin du premier écart (« softmax[2].probabilites[0] »).
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
    assert SECTIONS_EXACTES == ("vecteurs", "matrices", "descente", "tirage", "messages", "pente", "chaine")
    assert SECTIONS_LIBM == ("softmax", "erreur")
    # Chaque section du fichier est dans l'une des deux listes, et une seule.
    assert sorted(lire()) == sorted(SECTIONS_EXACTES + SECTIONS_LIBM)


def test_la_tolerance_ne_cache_pas_une_vraie_difference():
    lu = lire()["softmax"]
    # Un bit de différence sur le dernier chiffre passe : c'est ce que la tolérance laisse aux systèmes.
    a_un_bit = json.loads(json.dumps(lu))
    a_un_bit[0]["probabilites"][0] = math.nextafter(a_un_bit[0]["probabilites"][0], 1.0)
    comparer_a_peu_pres(a_un_bit, lu, "softmax")
    # Une vraie différence, même au millionième, ne passe pas.
    au_millionieme = json.loads(json.dumps(lu))
    au_millionieme[0]["probabilites"][0] *= 1 + 1e-6
    with pytest.raises(AssertionError, match=r"softmax\[0\]\.probabilites\[0\]"):
        comparer_a_peu_pres(au_millionieme, lu, "softmax")
    # Les entrées se comparent au bit près : un bit de plus sur la température ne passe pas.
    entree = json.loads(json.dumps(lu))
    entree[1]["temperature"] = math.nextafter(entree[1]["temperature"], 2.0)
    with pytest.raises(AssertionError, match=r"softmax\[1\]\.temperature"):
        comparer_a_peu_pres(entree, lu, "softmax")
    # Ni un nombre en moins, ni un entier à la place d'un flottant.
    en_moins = json.loads(json.dumps(lu))
    en_moins[2]["probabilites"].pop()
    with pytest.raises(AssertionError, match="longueurs"):
        comparer_a_peu_pres(en_moins, lu, "softmax")
    with pytest.raises(AssertionError, match="flottant"):
        comparer_a_peu_pres([{"p": 1.0, "erreur": 0}], [{"p": 1.0, "erreur": 0.0}], "erreur")
    # Dans la section erreur, seul −ln p a la tolérance : p, l'entrée, se compare au bit près.
    erreurs = lire()["erreur"]
    p_change = json.loads(json.dumps(erreurs))
    p_change[3]["p"] = math.nextafter(p_change[3]["p"], 1.0)
    with pytest.raises(AssertionError, match=r"erreur\[3\]\.p"):
        comparer_a_peu_pres(p_change, erreurs, "erreur")
    ln_a_un_bit = json.loads(json.dumps(erreurs))
    ln_a_un_bit[3]["erreur"] = math.nextafter(ln_a_un_bit[3]["erreur"], 0.0)
    comparer_a_peu_pres(ln_a_un_bit, erreurs, "erreur")


def test_le_texte_json_distingue_ce_que_egal_confond():
    # « == » confond -0.0 et 0.0, 6 et 6.0 : le texte JSON du fichier, non.
    assert -0.0 == 0.0 and vers_json(-0.0) != vers_json(0.0)
    assert 6 == 6.0 and vers_json([6]) != vers_json([6.0])
    with pytest.raises(AssertionError):
        comparer_a_peu_pres({"p": -0.0, "erreur": 1.0}, {"p": 0.0, "erreur": 1.0}, "erreur")


def test_fichier_en_utf8_et_lf():
    octets = CHEMIN_ATTENDUS.read_bytes()
    assert b"\r" not in octets, f"tests/attendus.json contient des fins de ligne Windows. {REGENERER}"
    assert octets.endswith(b"}\n"), f"tests/attendus.json doit finir par « }} » puis un retour à la ligne. {REGENERER}"


def test_entrees_de_reference():
    assert DEPARTS_DESCENTE == [-2.0, 0.0, 0.5, 7.0]
    assert NB_PAS_DESCENTE == 30 and SEUIL_DESCENTE == 1.01
    assert NB_UNIFORMES == 20 and GRAINE_UNIFORMES == 1234
    assert NOMBRES_DE_TIRAGES == [10, 100, 1000, 10000, 100000] and NB_GRAINES == 3
    assert SCORES_SOFTMAX == [2.0, 1.0, 0.1] and TEMPERATURES == [0.5, 1.0, 2.0]
    assert PROBAS_ERREUR == [1.0, 0.5, 0.1, 1 / 40]
    # Des vecteurs entiers de −4 à 4, dont le vecteur nul, et ceux de la figure et du pari.
    assert all(isinstance(x, int) and -4 <= x <= 4 for v in VECTEURS_DE_REFERENCE for x in v)
    assert [0, 0] in VECTEURS_DE_REFERENCE
    for v in ([3, 1], [1, 2], [2, 1], [-1, 2]):
        assert v in VECTEURS_DE_REFERENCE
    # L'exemple du chapitre, en premier.
    assert MATRICES_DE_REFERENCE[0] == ([[1, 2, 3], [0, 1, 0]], [1, 1, 1])
    assert all(0.0 <= u < 1.0 and isinstance(probas, list) for probas, u in CAS_TIRER)


def test_forme_des_attendus():
    a = lire()
    assert list(a) == ["vecteurs", "matrices", "descente", "tirage", "messages", "pente", "chaine", "softmax", "erreur"]

    # Toutes les paires ordonnées de vecteurs de référence.
    assert [(v["a"], v["b"]) for v in a["vecteurs"]] == [
        (x, y) for x in VECTEURS_DE_REFERENCE for y in VECTEURS_DE_REFERENCE
    ]
    for v in a["vecteurs"]:
        assert list(v) == ["a", "b", "produit_scalaire", "norme_a", "norme_b", "cosinus", "somme"]
        assert (v["cosinus"] is None) == (v["a"] == [0, 0] or v["b"] == [0, 0])

    assert [(m["m"], m["v"]) for m in a["matrices"]] == list(MATRICES_DE_REFERENCE)
    for m in a["matrices"]:
        assert list(m) == ["m", "v", "resultat", "erreur"]
        assert (m["resultat"] is None) != (m["erreur"] is None)

    d = a["descente"]
    assert list(d) == ["taux", "nb_pas", "seuil", "cas"]
    assert d["taux"] == TAUX_DESCENTE and d["nb_pas"] == 30 and d["seuil"] == 1.01
    assert [(c["x0"], c["taux"]) for c in d["cas"]] == [(x0, t) for x0 in DEPARTS_DESCENTE for t in TAUX_DESCENTE]
    for c in d["cas"]:
        assert list(c) == ["x0", "taux", "positions", "erreurs", "pentes", "pas_pour_atteindre"]
        assert len(c["positions"]) == len(c["erreurs"]) == len(c["pentes"]) == 31
        assert c["positions"][0] == c["x0"]

    t = a["tirage"]
    assert list(t) == ["graine_tirage", "exemple_comptes", "probabilites", "uniformes", "tirer", "tirages"]
    assert t["graine_tirage"] == GRAINE_TIRAGE
    assert t["exemple_comptes"] == [[mot, n] for mot, n in EXEMPLE_COMPTES.items()]
    assert t["uniformes"]["graine"] == 1234 and len(t["uniformes"]["valeurs"]) == 20
    assert [(c["probas"], c["u"]) for c in t["tirer"]] == [(probas, u) for probas, u in CAS_TIRER]
    # Les graines qu'on atteint par « Autre graine » dans la figure : GRAINE_TIRAGE, + 1, + 2.
    assert [(c["n"], c["graine"]) for c in t["tirages"]] == [
        (n, GRAINE_TIRAGE + i) for n in NOMBRES_DE_TIRAGES for i in range(NB_GRAINES)
    ]
    for c in t["tirages"]:
        assert sum(c["comptes"]) == c["n"] and len(c["comptes"]) == len(EXEMPLE_COMPTES)

    assert [(m["fonction"], m["arguments"]) for m in a["messages"]] == [(f, args) for f, args in CAS_MESSAGES]
    for m in a["messages"]:
        assert list(m) == ["fonction", "arguments", "message"] and m["message"]
    assert list(a["pente"]) == ["x", "exacte", "approchee"]
    assert list(a["chaine"]) == ["x", "h", "exacte", "approchee"]
    assert [(s["scores"], s["temperature"]) for s in a["softmax"]] == [(SCORES_SOFTMAX, t) for t in TEMPERATURES]
    assert [e["p"] for e in a["erreur"]] == PROBAS_ERREUR


def test_quelques_valeurs_connues():
    a = lire()
    exemple = a["matrices"][0]
    assert exemple["resultat"] == [6.0, 1.0] and exemple["erreur"] is None
    assert any(m["erreur"] == "La matrice a 4 colonnes et le vecteur 3 nombres\u202f: il en faut autant." for m in a["matrices"])
    figure = next(v for v in a["vecteurs"] if v["a"] == [3, 1] and v["b"] == [1, 2])
    assert figure["produit_scalaire"] == 5.0 and figure["somme"] == [4, 3]
    pari = next(v for v in a["vecteurs"] if v["a"] == [2, 1] and v["b"] == [-1, 2])
    assert pari["produit_scalaire"] == 0.0 and pari["cosinus"] == 0.0
    cas = {(c["x0"], c["taux"]): c for c in a["descente"]["cas"]}
    assert cas[(0.0, 0.1)]["pas_pour_atteindre"] == 16
    assert cas[(0.0, 0.5)]["pas_pour_atteindre"] == 1 and cas[(0.0, 0.5)]["positions"][1] == 3.0
    assert cas[(0.0, 1.0)]["pas_pour_atteindre"] is None
    # Au taux 1,2, la descente s'éloigne du fond : plus de 1 000 au trentième pas.
    assert abs(cas[(0.0, 1.2)]["positions"][-1] - 3.0) > 1000
    assert a["pente"]["exacte"] == -6.0 and abs(a["pente"]["approchee"] + 6.0) < 1e-6
    assert a["chaine"]["exacte"] == 12.0 and abs(a["chaine"]["approchee"] - 12.0) < 1e-5
    messages = {(m["fonction"], json.dumps(m["arguments"])): m["message"] for m in a["messages"]}
    assert messages[("produit_scalaire", "[[1, 2, 3], [1, 2]]")] == (
        "Les deux vecteurs n’ont pas la même taille (3 et 2 nombres)\u202f: il en faut autant."
    )
    assert messages[("probabilites", "[[]]")].startswith("Aucun compte positif (le total vaut 0)")
    assert messages[("tirages", "[[], 0, 1234]")] == "Aucune issue à tirer\u202f: donne au moins une probabilité."
    for s in a["softmax"]:
        assert math.isclose(math.fsum(s["probabilites"]), 1.0)
    assert a["erreur"][-1]["p"] == 1 / 40 and abs(a["erreur"][-1]["erreur"] - math.log(40)) < 1e-12
