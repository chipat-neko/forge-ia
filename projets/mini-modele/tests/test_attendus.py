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
    EXEMPLE_FLOTTANT,
    PRENOMS_COURT,
    calculer_attendus_attention,
    calculer_attendus_calcul,
    calculer_attendus_donnees,
    calculer_attendus_modele,
)
from mini_modele.calcul import depuis_hex, empreinte, empreinte_texte, racine, vers_hex
from mini_modele.donnees import donnees_par_defaut, preparer
from mini_modele.entrainement import Entraineur, ReglagesMini
from mini_modele.exemple_attention import charger_exemple, detailler_tete
from mini_modele.modele import ConfigMini, nombre_parametres

DOSSIER = pathlib.Path(__file__).resolve().parent
REGENERER = "Régénère-les avec « uv run python -m mini_modele.attendus » (dans projets/mini-modele)."


def lire(nom: str):
    return json.loads((DOSSIER / f"attendus-{nom}.json").read_text(encoding="utf-8"))


def test_attendus_a_jour():
    assert CALCULS["calcul"] is calculer_attendus_calcul
    assert CALCULS["donnees"] is calculer_attendus_donnees
    assert CALCULS["modele"] is calculer_attendus_modele
    assert CALCULS["attention"] is calculer_attendus_attention
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
    # Une clé par partie : « modele », et « entrainement » à côté.
    assert set(fichier) == {"modele", "entrainement"}
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


def test_attendus_entrainement_au_complet():
    fichier = lire("modele")
    a = fichier["entrainement"]
    assert set(a) == {
        "preset", "nb_pas", "pertes", "taux", "validation_0", "validation_20", "params_empreinte_20",
        "params_premiers_20", "echantillons_0", "echantillons_20", "taux_planning", "divergence", "presets",
        "taux_proposes", "court",
    }
    assert a["preset"] == "complet" and a["nb_pas"] == 20
    assert len(a["pertes"]) == len(a["taux"]) == 20
    assert len(a["params_premiers_20"]) == 8
    motifs = a["pertes"] + a["taux"] + a["params_premiers_20"] + [a["validation_0"], a["validation_20"]]
    motifs += [m for _, m in a["taux_planning"]] + [a["divergence"]["taux_max"], a["divergence"]["perte"]]
    motifs += a["taux_proposes"]
    assert all(re.fullmatch(r"[0-9a-f]{16}", m) for m in motifs)
    assert re.fullmatch(r"[0-9a-f]{8}", a["params_empreinte_20"])
    # Le départ de l'entraînement est le modèle de la clé « modele » : mêmes poids (graine 1234),
    # même validation (256 prénoms), mêmes prénoms inventés (graine 1234 + 2 + 0).
    assert a["validation_0"] == fichier["modele"]["perte_validation_256"]
    assert a["echantillons_0"] == fichier["modele"]["generes"]
    # Les 20 premiers pas sont dans l'échauffement : le taux monte à chaque pas, comme la courbe le montrera.
    taux = [depuis_hex(m) for m in a["taux"]]
    assert all(taux[i] > taux[i - 1] > 0.0 for i in range(1, 20))
    # Le planning couvre la montée, le sommet, le cosinus et la fin.
    assert [p for p, _ in a["taux_planning"]] == [0, 1, 50, 99, 100, 101, 550, 1000, 1550, 2000, 2999, 3000, 3001]
    assert a["divergence"]["pas"] >= 2
    assert set(a["presets"]) == {"complet", "avant-gout"}
    d = donnees_par_defaut()
    assert len(a["echantillons_0"]) == len(a["echantillons_20"]) == 8
    for p in a["echantillons_0"] + a["echantillons_20"]:
        assert isinstance(p, str) and len(p) <= 15 and set(p) <= set(d.vocabulaire[1:])


# Vingt prénoms de deux lettres (ceux de test_donnees.py et test_entrainement.py).
VINGT = ["an", "bo", "ci", "du", "el", "fa", "gu", "hi", "in", "jo", "ka", "lu", "ma", "ne", "ol", "pa", "qu", "ro", "su", "ti"]


def test_attendus_entrainement_court():
    a = lire("modele")["entrainement"]["court"]
    assert set(a) == {
        "prenoms", "reglages", "nb_pas", "pertes", "taux", "validation", "params_empreinte", "params_premiers",
        "echantillons",
    }
    assert a["prenoms"] == VINGT == list(PRENOMS_COURT)
    r = a["reglages"]
    # Des lots de 4 sur 18 prénoms : l'ordre est remélangé aux pas 5 et 9 (16 + 4 > 18).
    assert r["lot"] == 4 and len(preparer(VINGT).entrainement) == 18
    assert a["nb_pas"] == 10 and r["pas_total"] == 10 and r["echauffement"] == 2
    assert depuis_hex(r["ecretage"]) == 100.0
    assert len(a["pertes"]) == len(a["taux"]) == 10 and len(a["params_premiers"]) == 8
    motifs = a["pertes"] + a["taux"] + a["params_premiers"] + [a["validation"]]
    assert all(re.fullmatch(r"[0-9a-f]{16}", m) for m in motifs)
    assert re.fullmatch(r"[0-9a-f]{8}", a["params_empreinte"])
    # La montée (pas 1), le cosinus (pas 2 à 9) et la fin (pas 10, au taux minimal) : le planning entier.
    taux = [depuis_hex(m) for m in a["taux"]]
    assert taux[0] < taux[1] and taux[1] > taux[8] > taux[9] == 0.1 * 0.01
    assert len(a["echantillons"]) == 8


def test_l_entrainement_court_n_ecrete_jamais():
    # Avec un écrêtage à 100, la branche « pas d'écrêtage » sert à chaque pas : un écrêtage
    # bien plus grand donne les mêmes bits. À 1, il aurait servi (sinon le cas ne prouverait rien).
    a = lire("modele")["entrainement"]["court"]
    empreintes = {}
    for ecretage in (100.0, 1e300, 1.0):
        e = Entraineur(ReglagesMini(pas_total=10, echauffement=2, lot=4, ecretage=ecretage), preparer(VINGT))
        for _ in range(10):
            e.faire_un_pas()
        empreintes[ecretage] = empreinte(e.params)
    assert empreintes[100.0] == empreintes[1e300] == a["params_empreinte"]
    assert empreintes[1.0] != a["params_empreinte"]


def test_attendus_attention_au_complet():
    a = lire("attention")
    ex = charger_exemple()
    assert set(a) == {"phrase", "jetons", "tetes", "flottant"}
    assert a["phrase"] == ex["phrase"] and a["jetons"] == ex["jetons"]
    assert [t["nom"] for t in a["tetes"]] == [t["nom"] for t in ex["tetes"]] == ["qui agit", "de qui on parle"]
    n = len(ex["jetons"])
    for t in a["tetes"]:
        assert set(t) == {"nom", "requetes", "cles", "valeurs", "scores", "scores_echelles", "poids", "sorties"}
        for cle in ("requetes", "cles", "valeurs", "sorties"):
            assert len(t[cle]) == n and all(len(ligne) == 4 for ligne in t[cle]), cle
            assert all(re.fullmatch(r"[0-9a-f]{16}", m) for ligne in t[cle] for m in ligne), cle
        for cle in ("scores", "scores_echelles", "poids"):
            assert len(t[cle]) == n and all(len(ligne) == n for ligne in t[cle]), cle
            for i in range(n):
                for j in range(n):
                    m = t[cle][i][j]
                    if j > i and cle != "poids":
                        assert m is None, (cle, i, j)  # une case masquée : null
                    elif j > i:
                        assert m == "0000000000000000", (i, j)  # un poids masqué vaut +0,0
                    else:
                        assert re.fullmatch(r"[0-9a-f]{16}", m), (cle, i, j)


def test_attendus_attention_flottant():
    a = lire("attention")["flottant"]
    ex = EXEMPLE_FLOTTANT
    assert set(a) == {
        "x", "wq", "wk", "wv", "requetes", "cles", "valeurs", "scores", "scores_echelles", "poids", "sorties",
    }
    # Les entrées sont écrites en motifs : le TypeScript doit lire exactement les mêmes nombres.
    for cle in ("x", "wq", "wk", "wv"):
        assert a[cle] == [[vers_hex(float(v)) for v in ligne] for ligne in ex[cle]], cle
    n, traits, taille, largeur = len(ex["x"]), len(ex["x"][0]), len(ex["wq"][0]), len(ex["wv"][0])
    assert (n, traits, taille, largeur) == (5, 4, 3, 4)
    # Une tête de 3 : l'échelle 1 / √3 n'est pas une puissance de 2, sa multiplication arrondit.
    assert len(ex["wk"][0]) == taille
    # Des nombres à virgule : au moins un n'est pas entier dans chaque entrée.
    for cle in ("x", "wq", "wk", "wv"):
        assert any(v != int(v) for ligne in ex[cle] for v in ligne), cle
    for cle, colonnes in (("requetes", taille), ("cles", taille), ("valeurs", largeur), ("sorties", largeur)):
        assert len(a[cle]) == n and all(len(ligne) == colonnes for ligne in a[cle]), cle
        assert all(re.fullmatch(r"[0-9a-f]{16}", m) for ligne in a[cle] for m in ligne), cle
    for cle in ("scores", "scores_echelles", "poids"):
        assert len(a[cle]) == n and all(len(ligne) == n for ligne in a[cle]), cle
        for i in range(n):
            for j in range(n):
                m = a[cle][i][j]
                if j > i:
                    assert m == (None if cle != "poids" else "0000000000000000"), (cle, i, j)
                else:
                    assert re.fullmatch(r"[0-9a-f]{16}", m), (cle, i, j)


def _a_rebours(a: list[float], b: list[float]) -> float:
    """a · b, mais par indices décroissants."""
    s = 0.0
    for i in range(len(a) - 1, -1, -1):
        s += a[i] * b[i]
    return s


def test_l_exemple_flottant_voit_l_ordre_des_sommes():
    # Dans la phrase de l'animation, tout est entier : une somme faite dans un autre ordre donne les
    # mêmes bits, et l'exemple ne dit rien de l'ordre. L'exemple à virgule, lui, voit chacun de ces
    # écarts : la projection, le score, l'échelle et le mélange (sinon, il ne prouverait rien).
    a = lire("attention")["flottant"]
    ex = EXEMPLE_FLOTTANT
    d = detailler_tete(ex["x"], ex["wq"], ex["wk"], ex["wv"])
    n = len(ex["x"])
    projections = 0
    for nom, w in (("requetes", ex["wq"]), ("cles", ex["wk"]), ("valeurs", ex["wv"])):
        for i, x in enumerate(ex["x"]):
            for j in range(len(w[0])):
                colonne = [float(w[k][j]) for k in range(len(w))]
                projections += vers_hex(_a_rebours([float(v) for v in x], colonne)) != a[nom][i][j]
    scores = 0
    echelles = 0
    melanges = 0
    e = 1.0 / racine(float(len(ex["wq"][0])))
    for i in range(n):
        for j in range(i + 1):
            scores += vers_hex(_a_rebours(d.requetes[i], d.cles[j])) != a["scores"][i][j]
            dans_la_somme = 0.0
            for k in range(len(d.requetes[i])):
                dans_la_somme += d.requetes[i][k] * d.cles[j][k] * e
            echelles += vers_hex(dans_la_somme) != a["scores_echelles"][i][j]
        for k in range(len(d.valeurs[0])):
            melanges += vers_hex(_a_rebours(d.poids[i][: i + 1], [v[k] for v in d.valeurs[: i + 1]])) != a["sorties"][i][k]
    assert projections > 0 and scores > 0 and echelles > 0 and melanges > 0, (projections, scores, echelles, melanges)
    # Le même renversement ne change rien à l'exemple entier : d'où l'exemple à virgule.
    phrase = charger_exemple()
    for t, tete in zip(lire("attention")["tetes"], phrase["tetes"]):
        for i, x in enumerate(phrase["x"]):
            for j in range(len(tete["wq"][0])):
                colonne = [float(tete["wq"][k][j]) for k in range(len(tete["wq"]))]
                assert vers_hex(_a_rebours([float(v) for v in x], colonne)) == t["requetes"][i][j]
