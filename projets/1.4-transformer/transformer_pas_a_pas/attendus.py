"""Valeurs de référence pour les jumeaux TypeScript et pour le chapitre 1.4.

Le site refait deux calculs en TypeScript : la répartition des paramètres
(site/src/lib/partie-1/parametres.ts) et les angles de RoPE (site/src/lib/partie-1/rope.ts).
Il lit aussi, sans le refaire, ce que deviennent deux textes sans le `x +` des blocs (le pari
« residus » du chapitre). Ce fichier produit `tests/attendus.json`, dans l'ordre :

- `repartitions` : pour chaque preset de `forge.modele.config.PRESETS`, ses dimensions et le
  nombre de paramètres de chaque famille (des entiers, comparés exactement) ;
- `rope` : les angles de la figure du chapitre, `positions` lignes (0 à 32) de `dim_tete // 2`
  paires (4 paires d'une tête de 8), pour la base de `ConfigModele`. Ils sont calculés en float64,
  par `**`, pour l'affichage : forge, lui, les calcule en float32 (voir `pieces.angles_rope`). Ils
  passent par `pow`, `cos` et `sin` des bibliothèques mathématiques du système, qui peuvent
  différer d'un bit : les tests les comparent à 10⁻⁹ près ;
- `residus` : deux textes de `JETONS_RESIDUS` jetons qui ne diffèrent que par leur dernier jeton
  traversent les blocs de « ton IA » en taille mini, avec les poids que forge tire au départ
  (graine fixée), une fois avec `pieces.bloc`, une fois sans ses `x +` (`bloc_sans_residus`).
  Après chaque bloc, la ressemblance (le cosinus du chapitre 0.2) entre les deux sorties de la
  dernière position. RMSNorm et RoPE y calculent en float32, comme forge : les tests les
  comparent à 10⁻⁶ près.

Pour régénérer le fichier (dans projets/1.4-transformer) :

    uv run --extra cpu python -m transformer_pas_a_pas.attendus
"""

import json
from pathlib import Path

import torch
from forge.modele import Transformer
from forge.modele.config import PRESETS, ConfigModele
from torch import Tensor

from transformer_pas_a_pas import pieces
from transformer_pas_a_pas.comparer import poids_de_forge
from transformer_pas_a_pas.compter import repartition
from transformer_pas_a_pas.pieces import attention, rmsnorm, swiglu

CHEMIN_ATTENDUS = Path(__file__).resolve().parent.parent / "tests" / "attendus.json"

BASE = ConfigModele(dim=8, couches=1, tetes=1, longueur_contexte=1).base_rope
DIM_TETE = 8
POSITIONS = 33

# Le pari « residus » : ton IA en taille mini, ses poids de départ tirés avec la graine 0, et
# deux textes de 16 jetons.
PRESET_RESIDUS = "mini"
GRAINE_RESIDUS = 0
JETONS_RESIDUS = 16


def angles_de_la_figure() -> list[list[float]]:
    """L'angle de chaque paire à chaque position, en float64 : `p × base^(-2i / dim_tete)`."""
    return [[p * BASE ** (-(2 * i) / DIM_TETE) for i in range(DIM_TETE // 2)] for p in range(POSITIONS)]


def bloc_sans_residus(x: Tensor, p: dict) -> Tensor:
    """`pieces.bloc` sans ses deux `x +` : chaque sous-couche remplace le vecteur au lieu de le corriger."""
    x = attention(rmsnorm(x, p["norme_attention"]), p["w_qkv"], p["w_sortie"], p["tetes"], p["base_rope"])
    return swiglu(rmsnorm(x, p["norme_mlp"]), p["w_porte"], p["w_haute"], p["w_basse"])


def ressemblance(a: Tensor, b: Tensor) -> float:
    """Le cosinus de l'angle entre deux vecteurs (chapitre 0.2) : leur produit scalaire divisé par leurs normes."""
    return float(a @ b / (a.norm() * b.norm()))


def textes_du_pari_residus() -> tuple[Tensor, Tensor]:
    """Deux textes de `JETONS_RESIDUS` jetons tirés au hasard, pareils sauf leur dernier jeton."""
    tirage = torch.Generator().manual_seed(GRAINE_RESIDUS)
    ids = torch.randint(0, PRESETS[PRESET_RESIDUS].taille_vocabulaire, (JETONS_RESIDUS + 1,), generator=tirage)
    return ids[:-1], torch.cat((ids[:-2], ids[-1:]))


def residus() -> dict:
    """Ce que deviennent deux textes qui ne diffèrent que par leur dernier jeton, avec et sans le `x +`.

    Le modèle est le `Transformer` de forge en taille mini, avec les poids que forge tire au départ
    (`Transformer._initialiser`, graine `GRAINE_RESIDUS`), passé en float64. Les poids d'attention
    sont ceux de la dernière position dans le premier bloc, toutes têtes comprises.
    """
    config = PRESETS[PRESET_RESIDUS]
    with torch.random.fork_rng():  # la graine ne touche pas le hasard du reste du programme
        torch.manual_seed(GRAINE_RESIDUS)
        modele = Transformer(config).double().eval()
    p = poids_de_forge(modele)
    texte_a, texte_b = textes_du_pari_residus()
    with torch.no_grad():
        entree_a = pieces.plongement(texte_a, p["plongement"])
        entree_b = pieces.plongement(texte_b, p["plongement"])
        premier = p["blocs"][0]
        poids = pieces.poids_attention(
            rmsnorm(entree_a, premier["norme_attention"]), premier["w_qkv"], premier["tetes"], premier["base_rope"]
        )[:, -1, :]
        avec_a, avec_b, sans_a, sans_b = entree_a, entree_b, entree_a, entree_b
        par_bloc = []
        for numero, b in enumerate(p["blocs"], start=1):
            avec_a, avec_b = pieces.bloc(avec_a, b), pieces.bloc(avec_b, b)
            sans_a, sans_b = bloc_sans_residus(sans_a, b), bloc_sans_residus(sans_b, b)
            par_bloc.append(
                {
                    "bloc": numero,
                    "avec": ressemblance(avec_a[-1], avec_b[-1]),
                    "sans": ressemblance(sans_a[-1], sans_b[-1]),
                }
            )
    return {
        "preset": PRESET_RESIDUS,
        "couches": config.couches,
        "dim": config.dim,
        "jetons": JETONS_RESIDUS,
        "graine": GRAINE_RESIDUS,
        "entrees": ressemblance(entree_a[-1], entree_b[-1]),
        "poids_attention_min": float(poids.min()),
        "poids_attention_max": float(poids.max()),
        "par_bloc": par_bloc,
    }


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
    return {"repartitions": repartitions, "rope": rope, "residus": residus()}


def vers_json(valeur: object) -> str:
    return json.dumps(valeur, ensure_ascii=False, allow_nan=False, indent=1)


def main() -> None:
    CHEMIN_ATTENDUS.write_text(vers_json(calculer_attendus()) + "\n", encoding="utf-8", newline="\n")
    print(f"Attendus écrits dans {CHEMIN_ATTENDUS}")


if __name__ == "__main__":
    main()
