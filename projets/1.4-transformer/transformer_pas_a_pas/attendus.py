"""Valeurs de référence pour les jumeaux TypeScript et pour le chapitre 1.4.

Le site refait deux calculs en TypeScript : la répartition des paramètres
(site/src/lib/partie-1/parametres.ts) et les angles de RoPE (site/src/lib/partie-1/rope.ts).
Ce fichier produit `tests/attendus.json`, dans l'ordre :

- `repartitions` : pour chaque preset de `forge.modele.config.PRESETS`, ses dimensions et le
  nombre de paramètres de chaque famille (des entiers, comparés exactement) ;
- `rope` : les angles de la figure du chapitre, `positions` lignes (0 à 32) de `dim_tete // 2`
  paires (4 paires d'une tête de 8), pour la base de `ConfigModele`. Ils sont calculés en float64,
  par `**`, pour l'affichage : forge, lui, les calcule en float32 (voir `pieces.angles_rope`). Ils
  passent par `pow`, `cos` et `sin` des bibliothèques mathématiques du système, qui peuvent
  différer d'un bit : les tests les comparent à 10⁻⁹ près.

Pour régénérer le fichier (dans projets/1.4-transformer) :

    uv run --extra cpu python -m transformer_pas_a_pas.attendus
"""

import json
from pathlib import Path

from forge.modele.config import PRESETS, ConfigModele

from transformer_pas_a_pas.compter import repartition

CHEMIN_ATTENDUS = Path(__file__).resolve().parent.parent / "tests" / "attendus.json"

BASE = ConfigModele(dim=8, couches=1, tetes=1, longueur_contexte=1).base_rope
DIM_TETE = 8
POSITIONS = 33


def angles_de_la_figure() -> list[list[float]]:
    """L'angle de chaque paire à chaque position, en float64 : `p × base^(-2i / dim_tete)`."""
    return [[p * BASE ** (-(2 * i) / DIM_TETE) for i in range(DIM_TETE // 2)] for p in range(POSITIONS)]


def calculer_attendus() -> dict:
    repartitions = [
        {
            "preset": nom,
            "taille_vocabulaire": c.taille_vocabulaire,
            "dim": c.dim,
            "couches": c.couches,
            "tetes": c.tetes,
            "longueur_contexte": c.longueur_contexte,
            **repartition(c),
            "total": sum(repartition(c).values()),
        }
        for nom, c in PRESETS.items()
    ]
    rope = {"dim_tete": DIM_TETE, "base": BASE, "positions": POSITIONS, "angles": angles_de_la_figure()}
    return {"repartitions": repartitions, "rope": rope}


def vers_json(valeur: object) -> str:
    return json.dumps(valeur, ensure_ascii=False, allow_nan=False, indent=1)


def main() -> None:
    CHEMIN_ATTENDUS.write_text(vers_json(calculer_attendus()) + "\n", encoding="utf-8", newline="\n")
    print(f"Attendus écrits dans {CHEMIN_ATTENDUS}")


if __name__ == "__main__":
    main()
