"""Les attendus du chapitre 0.5 : le neurone à seuil, l'entraînement à la main, et les graines.

Le site refait le neurone à seuil en TypeScript (site/src/lib/partie-0/
neurone.ts) : il est comparé à la section `neurone` de ce fichier, au bit
près. Le site ne refait pas l'entraînement : il lit les pertes et les
prédictions de la section `entrainement`, et le compte des graines qui
apprennent dans la section `graines`. Pour régénérer `tests/attendus.json`
(dans projets/0.5-reseau) :

    uv run --extra cpu python -m premier_reseau.attendus
"""

import json
from dataclasses import asdict
from pathlib import Path

from premier_reseau.a_la_main import (
    DONNEES,
    GRAINE,
    NB_PAS,
    SEUIL_PERTE,
    TAUX,
    a_appris,
    entrainer,
    initialiser,
    nb_poids,
    predictions,
)
from premier_reseau.neurone import GRILLE, POINTS, PORTES, bien_classes, meilleur_reglage

CHEMIN_ATTENDUS = Path(__file__).resolve().parent.parent / "tests" / "attendus.json"

# Les graines essayées, de 1 à NB_GRAINES : certaines apprennent le OU exclusif, d'autres restent coincées.
NB_GRAINES = 20

# Les nombres de la section entrainement qui passent par math.exp et math.log : leur dernier
# chiffre peut changer d'un système à l'autre (voir tests/test_attendus.py). Tout le reste du
# fichier (le neurone, les poids de départ, les graines) est le même au bit près partout.
CLES_LIBM = ("pertes", "predictions")


def calculer_neurone() -> dict:
    """Les points, la grille, et pour chaque porte : son meilleur réglage, et le compte de chaque réglage."""
    return {
        "points": [list(point) for point in POINTS],
        "grille": GRILLE,
        "portes": [
            {
                "porte": porte,
                "sorties": sorties,
                "meilleur_reglage": meilleur_reglage(porte),
                # bien_classes[i][j][k] : le compte du réglage w1 = GRILLE[i], w2 = GRILLE[j], b = GRILLE[k].
                "bien_classes": [[[bien_classes((w1, w2), b, porte) for b in GRILLE] for w2 in GRILLE] for w1 in GRILLE],
            }
            for porte, sorties in PORTES.items()
        ],
    }


def calculer_entrainement() -> dict:
    """L'entraînement à la main du chapitre : ses réglages, ses poids de départ, ses pertes et ses prédictions."""
    depart = initialiser(GRAINE)
    historique = entrainer(depart, DONNEES, TAUX, NB_PAS)
    return {
        "graine": GRAINE,
        "taux": TAUX,
        "nb_pas": NB_PAS,
        "nb_poids": nb_poids(depart),
        "seuil_perte": SEUIL_PERTE,
        "depart": asdict(depart),
        "pertes": historique.pertes,
        "predictions": predictions(historique.reseau, DONNEES),
    }


def calculer_graines() -> list[dict]:
    """Pour chaque graine de 1 à NB_GRAINES : l'entraînement réussit-il ?"""
    return [
        {"graine": graine, "reussit": a_appris(entrainer(initialiser(graine), DONNEES, TAUX, NB_PAS), DONNEES)}
        for graine in range(1, NB_GRAINES + 1)
    ]


def calculer_attendus() -> dict:
    """{"neurone": {…}, "entrainement": {…}, "graines": […]}"""
    return {"neurone": calculer_neurone(), "entrainement": calculer_entrainement(), "graines": calculer_graines()}


def vers_json(valeur) -> str:
    """Le texte JSON d'un fichier : UTF-8 lisible, sans NaN, indenté d'une espace, fini par un retour à la ligne."""
    return json.dumps(valeur, ensure_ascii=False, allow_nan=False, indent=1) + "\n"


def ecrire_attendus() -> None:
    """Écrit tests/attendus.json (UTF-8, fins de ligne LF)."""
    with open(CHEMIN_ATTENDUS, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(vers_json(calculer_attendus()))


if __name__ == "__main__":
    ecrire_attendus()
    print(f"Écrit\u202f: {CHEMIN_ATTENDUS}")
