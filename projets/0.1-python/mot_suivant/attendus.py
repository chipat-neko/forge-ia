"""Valeurs de référence pour le jumeau TypeScript.

Le site refait le même calcul en TypeScript. Ce fichier produit
`tests/attendus.json` : pour chaque texte de référence, ses mots, les suivants
de chaque mot, les prédictions, et des suites de plusieurs longueurs à partir
de chaque mot. Le jumeau TypeScript doit retrouver exactement les mêmes valeurs.

Pour régénérer le fichier (dans projets/0.1-python) :

    uv run python -m mot_suivant.attendus
"""

import json
from collections import Counter
from pathlib import Path

from mot_suivant.mots import charger_texte, compter_suivants, decouper_mots, generer, predire, premiere_reprise

TEXTES_DE_REFERENCE: list[str] = [
    charger_texte(),
    "",
    "le",
    "Le LE le.",
    "l’enclume et l'enclume",
    "Salut 🙂 ! 2026",
    "ÉTÉ été",
    "a b a b a",
    # « İ » (I turc) devient « i » suivi d'un point suscrivant ; les lettres grecques ne sont pas des lettres du texte.
    "İstanbul ΟΔΟΣ forge-ia",
    # 10 000 caractères : le cas le plus long de l'atelier.
    "a " * 5000,
]

# Les longueurs des suites essayées à partir de chaque mot.
LONGUEURS = [1, 2, 12, 30]

# Un mot de départ absent de tous les textes de référence : sa suite s'arrête aussitôt.
MOT_ABSENT = "inconnu"

CHEMIN_ATTENDUS = Path(__file__).resolve().parent.parent / "tests" / "attendus.json"


def suivants_tries(compte: Counter[str]) -> list[list]:
    """Les suivants d'un mot et leurs comptes, par compte décroissant, puis par point de code."""
    return [[mot, n] for mot, n in sorted(compte.items(), key=lambda paire: (-paire[1], paire[0]))]


def calculer_texte(texte: str) -> dict:
    """Les valeurs de référence d'un texte (listes et nombres, prêts pour le JSON)."""
    mots = decouper_mots(texte)
    suivants = compter_suivants(mots)
    # Chaque mot une seule fois, dans l'ordre de sa première apparition.
    distincts = list(dict.fromkeys(mots))
    suites = []
    for depart in [*distincts, MOT_ABSENT]:
        for longueur in LONGUEURS:
            suite = generer(suivants, depart, longueur)
            suites.append({"depart": depart, "longueur": longueur, "suite": suite, "reprise": premiere_reprise(suite)})
    return {
        "texte": texte,
        "mots": mots,
        "suivants": [[mot, suivants_tries(compte)] for mot, compte in suivants.items()],
        "predictions": [[mot, predire(suivants, mot)] for mot in distincts],
        "suites": suites,
    }


def calculer_attendus() -> dict:
    """Calcule les valeurs de référence de tous les textes."""
    return {"textes": [calculer_texte(texte) for texte in TEXTES_DE_REFERENCE]}


def ecrire_attendus() -> None:
    """Écrit tests/attendus.json (UTF-8, fins de ligne LF)."""
    texte = json.dumps(calculer_attendus(), ensure_ascii=False, allow_nan=False, indent=1)
    with open(CHEMIN_ATTENDUS, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(texte + "\n")


if __name__ == "__main__":
    ecrire_attendus()
    print(f"Écrit : {CHEMIN_ATTENDUS}")
