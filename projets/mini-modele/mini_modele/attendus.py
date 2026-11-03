"""Valeurs de référence pour le jumeau TypeScript.

Le site refait les calculs de ce paquet en TypeScript. Ce module écrit
`tests/attendus-<nom>.json` : des entrées, et ce que le Python en tire. Chaque
flottant y est écrit en 16 chiffres hexadécimaux (`vers_hex`), pour comparer
les deux langages au bit près. Vitest, pytest et la page de parité du site
lisent les mêmes fichiers.

Pour les régénérer (dans projets/mini-modele) :

    uv run python -m mini_modele.attendus

Chaque tâche qui ajoute un module ajoute ici son `calculer_attendus_<nom>()`,
et l'inscrit dans CALCULS.
"""

import json
from collections.abc import Callable
from pathlib import Path

from mini_modele.calcul import (
    C_COS,
    C_EXP,
    C_LOG,
    INV_LN2,
    LN2_BAS,
    LN2_HAUT,
    PI,
    SQRT_DEMI,
    Hasard,
    cos,
    empreinte,
    empreinte_texte,
    exp,
    log,
    vers_hex,
)

DOSSIER_TESTS = Path(__file__).resolve().parent.parent / "tests"

# Entrées fixes : les cas limites (sous-normaux, débordements, −0, très petits et très grands).
# Pour exp, -745.0, -744.4, -740.0, -720.0 et -709.0 donnent des k de -1075 à -1023
# (la branche des résultats sous-normaux), 709.7 et 709.78 un k de 1024.
ENTREES_EXP = [
    -745.2, -745.0, -744.4, -740.0, -720.0, -709.0, -708.5, -50.0, -10.0, -1.0, -0.5, -1e-10,
    -0.0, 0.0, 1e-300, 1e-10, 0.25, 0.5, 1.0, 2.0, 10.0, 50.0, 700.0, 709.7, 709.78, 709.79, 710.0,
]
# Pour log, 2.225073858507201e-308 est le plus grand sous-normal.
ENTREES_LOG = [
    5e-324, 1e-310, 2.225073858507201e-308, 1e-300, 1e-10, 0.1, 0.5, SQRT_DEMI, 0.75, 1.0,
    1.0000001, 1.5, 2.0, 10.0, 1e10, 1e300, 1.7976931348623157e308,
]
ENTREES_COS = [0.0, 1e-8, 0.5, 1.0, PI * 0.25, PI * 0.5, 2.0, 3.0, PI]
# Les valeurs de l'empreinte : des signes, des sous-normaux, des infinis.
VALEURS_EMPREINTE = [0.0, -0.0, 1.0, -2.5, 0.1, PI, 5e-324, 1e300, float("inf"), float("-inf")]
TEXTE_EMPREINTE = "Élodie, Zoé et Maël"
GRAINE = 1234
# Avec l'écart-type 1, la dernière multiplication de gaussienne ne change rien :
# la suite « gaussienne_0_08 » (l'écart-type de l'initialisation du mini-modèle)
# vérifie aussi cette multiplication.
ECART_TYPE_ESSAI = 0.08


def tirer(graine: int, n: int, tirage: Callable[[Hasard], float]) -> list:
    """n tirages d'un Hasard(graine) neuf."""
    h = Hasard(graine)
    return [tirage(h) for _ in range(n)]


def paires(fonction: Callable[[float], float], entrees: list[float]) -> list[list[str]]:
    """[x, f(x)] pour chaque entrée, en motifs hexadécimaux."""
    return [[vers_hex(x), vers_hex(fonction(x))] for x in entrees]


def calculer_attendus_calcul() -> dict:
    """Les attendus du noyau de calcul (tests/attendus-calcul.json)."""
    entrees_exp = ENTREES_EXP + tirer(42, 200, lambda h: (h.uniforme() - 0.5) * 60)
    entrees_log = ENTREES_LOG + tirer(43, 200, lambda h: h.uniforme() * 100 + 0.001)
    entrees_cos = ENTREES_COS + tirer(44, 100, lambda h: h.uniforme() * PI)
    melange = list(range(20))
    Hasard(GRAINE).melanger(melange)
    return {
        "constantes": {
            "LN2_HAUT": vers_hex(LN2_HAUT),
            "LN2_BAS": vers_hex(LN2_BAS),
            "INV_LN2": vers_hex(INV_LN2),
            "SQRT_DEMI": vers_hex(SQRT_DEMI),
            "PI": vers_hex(PI),
        },
        # Les tables des séries : le TypeScript doit construire exactement les mêmes.
        "coefficients": {
            "C_EXP": [vers_hex(c) for c in C_EXP],
            "C_LOG": [vers_hex(c) for c in C_LOG],
            "C_COS": [vers_hex(c) for c in C_COS],
        },
        "exp": paires(exp, entrees_exp),
        "log": paires(log, entrees_log),
        "cos": paires(cos, entrees_cos),
        "hasard": {
            "graine": GRAINE,
            "suivant32": tirer(GRAINE, 20, lambda h: h.suivant32()),
            "uniforme": [vers_hex(u) for u in tirer(GRAINE, 20, lambda h: h.uniforme())],
            "gaussienne": [vers_hex(g) for g in tirer(GRAINE, 20, lambda h: h.gaussienne(1.0))],
            "gaussienne_0_08": [vers_hex(g) for g in tirer(GRAINE, 20, lambda h: h.gaussienne(ECART_TYPE_ESSAI))],
            "entier_10": tirer(GRAINE, 20, lambda h: h.entier(10)),
            "melange_20": melange,
        },
        "empreinte": {
            "valeurs": [vers_hex(v) for v in VALEURS_EMPREINTE],
            "empreinte": empreinte(VALEURS_EMPREINTE),
        },
        "empreinte_texte": {
            "texte": TEXTE_EMPREINTE,
            "empreinte": empreinte_texte(TEXTE_EMPREINTE),
        },
    }


# Chaque fichier tests/attendus-<nom>.json et la fonction qui le calcule.
CALCULS: dict[str, Callable[[], dict]] = {
    "calcul": calculer_attendus_calcul,
}


def ecrire_attendus() -> None:
    """Écrit chaque tests/attendus-<nom>.json (UTF-8, fins de ligne LF)."""
    for nom, calculer in CALCULS.items():
        chemin = DOSSIER_TESTS / f"attendus-{nom}.json"
        with open(chemin, "w", encoding="utf-8", newline="\n") as fichier:
            fichier.write(json.dumps(calculer(), ensure_ascii=False, indent=1) + "\n")
        print(f"Écrit : {chemin}")


if __name__ == "__main__":
    ecrire_attendus()
