"""Les attendus partagés avec le site sont à jour.

Le fichier tests/attendus.json est écrit par
`uv run --extra cpu python -m premier_reseau.attendus`. Le jumeau du neurone
(site/src/lib/partie-0/neurone.ts) est comparé à sa section `neurone`, au bit
près. Le chapitre lit les pertes, les prédictions et les graines. Si le code
change, ces tests échouent tant que le fichier n'est pas régénéré.
"""

import json
import math

import pytest

from premier_reseau.a_la_main import DONNEES, GRAINE, NB_PAS, SEUIL_PERTE, TAUX, initialiser, nb_poids
from premier_reseau.attendus import CHEMIN_ATTENDUS, CLES_LIBM, NB_GRAINES, calculer_attendus, vers_json
from premier_reseau.neurone import GRILLE, POINTS, PORTES, bien_classes, meilleur_reglage

REGENERER = "Régénère-le avec « uv run --extra cpu python -m premier_reseau.attendus » (dans projets/0.5-reseau)."

# Les pertes et les prédictions passent par math.exp et math.log, qui viennent de la
# bibliothèque mathématique du système : celle de Linux (glibc) et celle de Windows (UCRT)
# ne sont pas arrondies au plus juste, et peuvent différer d'un bit sur le dernier chiffre.
# Sur 3 000 pas, ces écarts se propagent, sans grandir au-delà de quelques 10⁻¹⁵. Le fichier,
# écrit sur une machine, est relu sur l'autre par l'intégration continue : ces deux listes
# (les clés CLES_LIBM de la section entrainement) se comparent donc nombre par nombre, à
# 10⁻⁹ près en relatif (10⁻¹² en absolu). Tout le reste (le neurone, les réglages de
# l'entraînement, les poids de départ, les graines) se compare au bit près.
TOLERANCE_RELATIVE = 1e-9
TOLERANCE_ABSOLUE = 1e-12


@pytest.fixture(scope="module")
def calcule() -> dict:
    """Les attendus recalculés, relus comme le fichier (les tuples deviennent des listes)."""
    return json.loads(vers_json(calculer_attendus()))


def lire() -> dict:
    return json.loads(CHEMIN_ATTENDUS.read_text(encoding="utf-8"))


def comparer_entrainement(calcule: dict, lu: dict) -> None:
    """Les clés CLES_LIBM à la tolérance près, nombre par nombre ; le reste au bit près.

    Lève une AssertionError qui nomme le premier écart (« entrainement.pertes[12] »)."""
    assert list(calcule) == list(lu), "entrainement : clés différentes"
    for cle in lu:
        if cle not in CLES_LIBM:
            # Par le texte JSON : -0.0 et 0.0, ou 6 et 6.0, ne passent pas l'un pour l'autre.
            assert vers_json(calcule[cle]) == vers_json(lu[cle]), f"entrainement.{cle} : {calcule[cle]!r} au lieu de {lu[cle]!r}"
            continue
        assert len(calcule[cle]) == len(lu[cle]), f"entrainement.{cle} : longueurs différentes"
        for i, (a, b) in enumerate(zip(calcule[cle], lu[cle])):
            assert type(a) is float, f"entrainement.{cle}[{i}] : {a!r} n'est pas un flottant"
            assert math.isclose(a, b, rel_tol=TOLERANCE_RELATIVE, abs_tol=TOLERANCE_ABSOLUE), (
                f"entrainement.{cle}[{i}] : {a!r} au lieu de {b!r}"
            )


def test_attendus_a_jour(calcule):
    assert CHEMIN_ATTENDUS.exists(), f"tests/attendus.json est introuvable. {REGENERER}"
    lu = lire()
    assert list(calcule) == list(lu), f"tests/attendus.json n'a plus les mêmes sections. {REGENERER}"
    for nom in ("neurone", "graines"):
        assert vers_json(calcule[nom]) == vers_json(lu[nom]), (
            f"La section « {nom} » de tests/attendus.json n'est plus à jour. {REGENERER}"
        )
    try:
        comparer_entrainement(calcule["entrainement"], lu["entrainement"])
    except AssertionError as ecart:
        raise AssertionError(f"La section « entrainement » n'est plus à jour ({ecart}). {REGENERER}") from None


def test_la_tolerance_ne_cache_pas_une_vraie_difference():
    lu = lire()["entrainement"]
    copie = lambda: json.loads(json.dumps(lu))  # noqa: E731
    # Un bit de différence sur le dernier chiffre d'une perte passe : c'est ce que la tolérance laisse aux systèmes.
    a_un_bit = copie()
    a_un_bit["pertes"][1500] = math.nextafter(a_un_bit["pertes"][1500], 1.0)
    a_un_bit["predictions"][2] = math.nextafter(a_un_bit["predictions"][2], 0.0)
    comparer_entrainement(a_un_bit, lu)
    # Une vraie différence, même au millionième, ne passe pas.
    au_millionieme = copie()
    au_millionieme["pertes"][1500] *= 1 + 1e-6
    with pytest.raises(AssertionError, match=r"entrainement\.pertes\[1500\]"):
        comparer_entrainement(au_millionieme, lu)
    # Les poids de départ se comparent au bit près : un bit de plus ne passe pas.
    depart = copie()
    depart["depart"]["b2"] = math.nextafter(depart["depart"]["b2"], 2.0)
    with pytest.raises(AssertionError, match=r"entrainement\.depart"):
        comparer_entrainement(depart, lu)
    # Ni une perte en moins, ni un entier à la place d'un flottant.
    en_moins = copie()
    en_moins["pertes"].pop()
    with pytest.raises(AssertionError, match="longueurs"):
        comparer_entrainement(en_moins, lu)
    entier = copie()
    entier["predictions"][0] = 0
    with pytest.raises(AssertionError, match="flottant"):
        comparer_entrainement(entier, lu)


def test_fichier_en_utf8_et_lf():
    octets = CHEMIN_ATTENDUS.read_bytes()
    assert b"\r" not in octets, f"tests/attendus.json contient des fins de ligne Windows. {REGENERER}"
    assert octets.endswith(b"}\n"), f"tests/attendus.json doit finir par « }} » puis un retour à la ligne. {REGENERER}"


def test_forme_des_attendus():
    a = lire()
    assert list(a) == ["neurone", "entrainement", "graines"]

    n = a["neurone"]
    assert list(n) == ["points", "grille", "portes"]
    assert n["points"] == [list(p) for p in POINTS] and n["grille"] == GRILLE
    assert [p["porte"] for p in n["portes"]] == list(PORTES)
    for p in n["portes"]:
        assert list(p) == ["porte", "sorties", "meilleur_reglage", "bien_classes"]
        assert p["sorties"] == PORTES[p["porte"]]
        # bien_classes[i][j][k] : w1 = GRILLE[i], w2 = GRILLE[j], b = GRILLE[k].
        assert len(p["bien_classes"]) == 9 and all(len(ligne) == 9 for ligne in p["bien_classes"])
        assert all(len(case) == 9 for ligne in p["bien_classes"] for case in ligne)

    e = a["entrainement"]
    assert list(e) == ["graine", "taux", "nb_pas", "nb_poids", "seuil_perte", "depart", "pertes", "predictions"]
    assert (e["graine"], e["taux"], e["nb_pas"], e["seuil_perte"]) == (GRAINE, TAUX, NB_PAS, SEUIL_PERTE)
    assert list(e["depart"]) == ["w1", "b1", "w2", "b2"]
    assert len(e["pertes"]) == NB_PAS + 1 and len(e["predictions"]) == len(DONNEES)
    assert set(CLES_LIBM) == {"pertes", "predictions"}

    assert [g["graine"] for g in a["graines"]] == list(range(1, NB_GRAINES + 1))
    assert all(list(g) == ["graine", "reussit"] and type(g["reussit"]) is bool for g in a["graines"])


def test_ce_que_lit_le_chapitre():
    a = lire()
    portes = {p["porte"]: p for p in a["neurone"]["portes"]}
    assert [portes[nom]["meilleur_reglage"][0] for nom in ("et", "ou", "ou_exclusif")] == [4, 4, 3]
    for nom, p in portes.items():
        compte, poids, biais = meilleur_reglage(nom)
        assert p["meilleur_reglage"] == [compte, list(poids), biais]
    # Le réglage de départ de l'atelier, w = (1, 1) et b = 0, puis b = −1,5, sur la porte ET.
    i, k0, k15 = GRILLE.index(1.0), GRILLE.index(0.0), GRILLE.index(-1.5)
    assert portes["et"]["bien_classes"][i][i][k0] == bien_classes((1.0, 1.0), 0.0, "et") == 2
    assert portes["et"]["bien_classes"][i][i][k15] == 4
    assert max(c for ligne in portes["ou_exclusif"]["bien_classes"] for case in ligne for c in case) == 3

    e = a["entrainement"]
    # Le nombre de poids se compte sur le réseau (M7) : le chapitre le lit ici.
    assert e["nb_poids"] == nb_poids(initialiser(GRAINE)) == 9
    assert e["pertes"][-1] < e["seuil_perte"] < e["pertes"][0]
    assert [round(p) for p in e["predictions"]] == [y for _, y in DONNEES]

    # Des graines qui apprennent, d'autres qui restent coincées : sinon, NB_GRAINES passe de 20 à 100.
    reussites = sum(g["reussit"] for g in a["graines"])
    assert 0 < reussites < len(a["graines"])
    assert NB_GRAINES == 20
