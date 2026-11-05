"""Valeurs de référence pour le jumeau TypeScript et pour le chapitre 0.2.

Le site refait en TypeScript les vecteurs, les matrices, la descente et les
tirages (site/src/lib/partie-0/maths.ts). Ce fichier produit
`tests/attendus.json` : des entrées fixées, et ce que le Python en tire. Le
jumeau TypeScript doit retrouver exactement les mêmes valeurs.

Le fichier contient aussi ce que le site ne recalcule pas, et qu'il lit tel
quel : la pente approchée, l'exemple de la règle de la chaîne, softmax et
l'erreur −ln p.

Pour régénérer le fichier (dans projets/0.2-maths) :

    uv run python -m maths_utiles.attendus
"""

import json
from pathlib import Path

from maths_utiles.derivees import (
    TAUX_DESCENTE,
    descendre,
    erreur,
    exemple_chaine,
    pas_pour_atteindre,
    pente,
    pente_approchee,
)
from maths_utiles.probabilites import erreur_de_prediction, softmax
from maths_utiles.tirage import EXEMPLE_COMPTES, GRAINE_TIRAGE, Hasard, probabilites, tirages, tirer
from maths_utiles.vecteurs import cosinus, matrice_fois_vecteur, norme, produit_scalaire, somme

# Les sections qui n'utilisent que + − × ÷ et la racine carrée : le même résultat
# au bit près sur toutes les machines, et dans le navigateur.
SECTIONS_EXACTES = ("vecteurs", "matrices", "descente", "tirage", "pente", "chaine")
# Les sections qui passent par math.exp et math.log : leur dernier chiffre peut
# changer d'un système à l'autre (voir tests/test_attendus.py).
SECTIONS_LIBM = ("softmax", "erreur")

# Des vecteurs entiers de −4 à 4 : le vecteur nul, ceux de départ de la figure,
# (3, 1) et (1, 2), la paire perpendiculaire du pari, (2, 1) et (−1, 2), un
# opposé, des axes et des coins. Toutes les paires ordonnées sont calculées.
VECTEURS_DE_REFERENCE: list[list[int]] = [
    [0, 0],
    [3, 1],
    [1, 2],
    [2, 1],
    [-1, 2],
    [-3, -1],
    [1, 0],
    [0, -4],
    [4, 4],
    [-4, 4],
    [4, -3],
    [-4, -4],
    [-2, 3],
]

# (matrice, vecteur) : l'exemple du chapitre en premier, puis des matrices
# carrées, une de 3 lignes et 4 colonnes, des demi-entiers, une matrice vide, et
# des tailles qui ne vont pas.
MATRICES_DE_REFERENCE: list[tuple[list[list[float]], list[float]]] = [
    ([[1, 2, 3], [0, 1, 0]], [1, 1, 1]),
    ([[1, 0], [0, 1]], [3, -2]),
    ([[2, 0], [0, 3]], [1, 1]),
    ([[0, -1], [1, 0]], [3, 1]),
    ([[1, 2, 3, 4], [-1, 0, 1, 0], [2, 2, 2, 2]], [1, -1, 2, 0]),
    ([[0.5, -1.5], [2, 0.25]], [4, -2]),
    ([[5]], [-3]),
    ([], [1, 2]),
    ([[1, 2, 3, 4]], [1, 2, 3]),
    ([[1, 2, 3]], [1, 2, 3, 4]),
    ([[1], [2]], [1, 2]),
]

# Les départs de la descente : à gauche du fond, au milieu de la figure, et à droite.
DEPARTS_DESCENTE = [-2.0, 0.0, 0.5, 7.0]
NB_PAS_DESCENTE = 30
# L'erreur la plus basse vaut 1 : sous 1,01, on est tout près du fond.
SEUIL_DESCENTE = 1.01

# Les premiers nombres du hasard, pour relier ce Hasard à celui du site.
NB_UNIFORMES = 20
GRAINE_UNIFORMES = 1234

# (probabilités, u) : des u au bord de chaque issue, et des cumuls que les arrondis
# laissent un peu sous 1 (0,6 + 0,3 + 0,1, dix fois 0,1).
CAS_TIRER: list[tuple[list[float], float]] = [
    *(
        ([0.6, 0.3, 0.1], u)
        for u in (0.0, 0.3, 0.5999999999999999, 0.6, 0.75, 0.8999999999999999, 0.9, 0.95, 0.9999999999999999)
    ),
    *(([0.5, 0.5], u) for u in (0.0, 0.4999999999999999, 0.5, 0.9999999999999999)),
    *(([1.0], u) for u in (0.0, 0.9999999999999999)),
    *(([0.0, 1.0], u) for u in (0.0, 0.5)),
    *(([0.1] * 10, u) for u in (0.0, 0.1, 0.3, 0.9999999999999999)),
    *(([1 / 3, 1 / 3, 1 / 3], u) for u in (0.3333333333333333, 0.6666666666666666, 0.9999999999999999)),
]

# Les nombres de tirages de la figure, et trois graines : GRAINE_TIRAGE, puis les
# deux qu'on atteint par « Autre graine ».
NOMBRES_DE_TIRAGES = [10, 100, 1000, 10000, 100000]
NB_GRAINES = 3

SCORES_SOFTMAX = [2.0, 1.0, 0.1]
TEMPERATURES = [0.5, 1.0, 2.0]
# 1/40 : un modèle qui devine au hasard parmi 40 caractères, comme le mini-modèle.
PROBAS_ERREUR = [1.0, 0.5, 0.1, 1 / 40]

CHEMIN_ATTENDUS = Path(__file__).resolve().parent.parent / "tests" / "attendus.json"


def calculer_vecteurs() -> list[dict]:
    return [
        {
            "a": a,
            "b": b,
            "produit_scalaire": produit_scalaire(a, b),
            "norme_a": norme(a),
            "norme_b": norme(b),
            "cosinus": cosinus(a, b),
            "somme": somme(a, b),
        }
        for a in VECTEURS_DE_REFERENCE
        for b in VECTEURS_DE_REFERENCE
    ]


def calculer_matrices() -> list[dict]:
    cas = []
    for m, v in MATRICES_DE_REFERENCE:
        try:
            cas.append({"m": m, "v": v, "resultat": matrice_fois_vecteur(m, v), "erreur": None})
        except ValueError as e:
            cas.append({"m": m, "v": v, "resultat": None, "erreur": str(e)})
    return cas


def calculer_descente() -> dict:
    cas = []
    for x0 in DEPARTS_DESCENTE:
        for taux in TAUX_DESCENTE:
            positions = descendre(x0, taux, NB_PAS_DESCENTE)
            cas.append(
                {
                    "x0": x0,
                    "taux": taux,
                    "positions": positions,
                    "erreurs": [erreur(x) for x in positions],
                    "pentes": [pente(x) for x in positions],
                    "pas_pour_atteindre": pas_pour_atteindre(x0, taux, SEUIL_DESCENTE),
                }
            )
    return {"taux": TAUX_DESCENTE, "nb_pas": NB_PAS_DESCENTE, "seuil": SEUIL_DESCENTE, "cas": cas}


def calculer_tirage() -> dict:
    hasard = Hasard(GRAINE_UNIFORMES)
    probas = probabilites(EXEMPLE_COMPTES)
    return {
        "graine_tirage": GRAINE_TIRAGE,
        "exemple_comptes": [[mot, n] for mot, n in EXEMPLE_COMPTES.items()],
        "probabilites": probas,
        "uniformes": {"graine": GRAINE_UNIFORMES, "valeurs": [hasard.uniforme() for _ in range(NB_UNIFORMES)]},
        "tirer": [{"probas": p, "u": u, "indice": tirer(p, u)} for p, u in CAS_TIRER],
        "tirages": [
            {"n": n, "graine": GRAINE_TIRAGE + i, "comptes": tirages(probas, n, GRAINE_TIRAGE + i)}
            for n in NOMBRES_DE_TIRAGES
            for i in range(NB_GRAINES)
        ],
    }


def calculer_pente() -> dict:
    """La pente de l'erreur en x = 0 : exacte, et approchée."""
    return {"x": 0.0, "exacte": pente(0.0), "approchee": pente_approchee(erreur, 0.0)}


def calculer_softmax() -> list[dict]:
    return [{"scores": SCORES_SOFTMAX, "temperature": t, "probabilites": softmax(SCORES_SOFTMAX, t)} for t in TEMPERATURES]


def calculer_erreur() -> list[dict]:
    return [{"p": p, "erreur": erreur_de_prediction(p)} for p in PROBAS_ERREUR]


def calculer_attendus() -> dict:
    """Calcule toutes les sections, dans l'ordre du fichier."""
    return {
        "vecteurs": calculer_vecteurs(),
        "matrices": calculer_matrices(),
        "descente": calculer_descente(),
        "tirage": calculer_tirage(),
        "pente": calculer_pente(),
        "chaine": exemple_chaine(),
        "softmax": calculer_softmax(),
        "erreur": calculer_erreur(),
    }


def ecrire_attendus() -> None:
    """Écrit tests/attendus.json (UTF-8, fins de ligne LF)."""
    texte = json.dumps(calculer_attendus(), ensure_ascii=False, allow_nan=False, indent=1)
    with open(CHEMIN_ATTENDUS, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(texte + "\n")


if __name__ == "__main__":
    ecrire_attendus()
    print(f"Écrit : {CHEMIN_ATTENDUS}")
