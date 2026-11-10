"""Valeurs de référence pour le jumeau TypeScript et pour le chapitre 1.6.

Le site refait deux calculs en TypeScript (site/src/lib/partie-1/evaluation.ts) : la marge d'une
exactitude (`marge95`) et le verdict d'un QCM (`verdictQcm`). Ce fichier produit
`tests/attendus.json`, une grille ordonnée (un tableau JSON, jamais un objet) de
`exactitudes × n × nombres de choix`, avec pour chaque cas :

- `marge_95` : la marge de la mesure, `1,96 × √(p (1 − p) / n)` ;
- `hasard` : `1 / choix` ;
- `marge_hasard` : la marge d'un tirage au sort sur `n` questions de `choix` choix ;
- `verdict` : celui de l'exactitude, prise pour l'exactitude normalisée.

Ce sont des flottants : le Python et le TypeScript font les mêmes opérations dans le même ordre
(multiplications, divisions, une racine carrée, exacte dans les deux langages), et les comparent
sans tolérance.

Pour régénérer le fichier (dans projets/1.6-evaluation) :

    uv run --extra cpu python -m evaluation_pas_a_pas.attendus
"""

import json
from pathlib import Path

from evaluation_pas_a_pas.pas_a_pas import marge_95, marge_hasard, verdict

CHEMIN_ATTENDUS = Path(__file__).resolve().parent.parent / "tests" / "attendus.json"

# Les exactitudes de la grille : les extrêmes (où la marge de la mesure s'annule), le hasard, et celle
# de HellaSwag pour « mini » (27,2 %).
EXACTITUDES = [0.0, 0.1, 0.2, 0.25, 0.2721139430284857, 0.3, 0.5, 1.0]
# 5 questions, 100, les 1 169 d'ARC et les 9 338 de HellaSwag.
NOMBRES_DE_QUESTIONS = [5, 100, 1169, 9338]
NOMBRES_DE_CHOIX = [3, 4, 5]


def calculer_attendus() -> list[dict]:
    cas = []
    for choix in NOMBRES_DE_CHOIX:
        for n in NOMBRES_DE_QUESTIONS:
            hasard = 1 / choix
            marge = marge_hasard(n, choix)
            for exactitude in EXACTITUDES:
                cas.append(
                    {
                        "exactitude": exactitude,
                        "n": n,
                        "choix": choix,
                        "marge_95": marge_95(exactitude, n),
                        "hasard": hasard,
                        "marge_hasard": marge,
                        "verdict": verdict(exactitude, hasard, marge),
                    }
                )
    return cas


def vers_json(valeur: object) -> str:
    return json.dumps(valeur, ensure_ascii=False, allow_nan=False, indent=1)


def main() -> None:
    CHEMIN_ATTENDUS.write_text(vers_json(calculer_attendus()) + "\n", encoding="utf-8", newline="\n")
    print(f"Attendus écrits dans {CHEMIN_ATTENDUS}")


if __name__ == "__main__":
    main()
