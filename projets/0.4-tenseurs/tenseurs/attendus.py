"""Les attendus du chapitre 0.4 : les formes de PyTorch, des cas de mémoire et les exemples.

Le site ne lance pas PyTorch : son jumeau des formes (site/src/lib/partie-0/
formes.ts) est comparé à ce fichier, `tests/attendus-formes.json`. Les formes
y viennent de PyTorch lui-même, `torch.broadcast_shapes` et `torch.matmul`,
sur toutes les formes de 1 à 3 dimensions de tailles 1 à 3, prises deux à
deux : 39 formes, 1 521 paires. Pour le régénérer (dans projets/0.4-tenseurs) :

    uv run --extra cpu python -m tenseurs.attendus
"""

import itertools
import json
from pathlib import Path

import torch

from tenseurs.exemples import exemple_calculer, exemple_creer, exemple_lire
from tenseurs.memoire import octets

CHEMIN_ATTENDUS = Path(__file__).resolve().parent.parent / "tests" / "attendus-formes.json"

# Les 39 formes de 1 à 3 dimensions, de tailles 1 à 3 : 3 + 9 + 27.
FORMES = tuple(forme for n in (1, 2, 3) for forme in itertools.product((1, 2, 3), repeat=n))

# Les cas de mémoire : les matrices des chronos en float32, puis d'autres types et d'autres formes.
CAS_MEMOIRE = (
    *(((taille, taille), torch.float32) for taille in (64, 256, 1024, 2048, 4096)),
    ((4096, 4096), torch.float64),
    ((4096, 4096), torch.float16),
    ((4096, 4096), torch.bfloat16),
    ((32, 1024, 4096), torch.float32),
    ((), torch.float32),
    ((3,), torch.float32),
    ((2, 3), torch.int64),
    ((2, 3, 4), torch.int8),
    ((2, 3, 4), torch.bool),
)


def nom_du_type(dtype: torch.dtype) -> str:
    """« float32 » pour torch.float32."""
    return str(dtype).removeprefix("torch.")


def diffusion_de_pytorch(a: tuple[int, ...], b: tuple[int, ...]) -> list[int] | None:
    """La forme de a + b selon PyTorch, ou None s'il refuse."""
    try:
        return list(torch.broadcast_shapes(a, b))
    except RuntimeError:
        return None


def produit_de_pytorch(a: tuple[int, ...], b: tuple[int, ...]) -> list[int] | None:
    """La forme de a @ b selon PyTorch (sur des tenseurs vides, sans rien calculer d'utile), ou None s'il refuse."""
    try:
        return list(torch.matmul(torch.empty(a), torch.empty(b)).shape)
    except RuntimeError:
        return None


def calculer_paires() -> list[dict]:
    """Les 1 521 paires, avec les formes que leur donne le PyTorch installé."""
    return [
        {"a": list(a), "b": list(b), "diffusion": diffusion_de_pytorch(a, b), "produit": produit_de_pytorch(a, b)}
        for a, b in itertools.product(FORMES, repeat=2)
    ]


def tenseur_en_json(t: torch.Tensor) -> dict:
    return {"forme": list(t.shape), "dtype": nom_du_type(t.dtype), "valeurs": t.tolist()}


def calculer_attendus() -> dict:
    """{"formes": […], "paires": […], "memoire": […], "exemples": {"creer", "lire", "calculer"}}"""
    return {
        "formes": [{"forme": list(f), "texte": str(f)} for f in FORMES],
        "paires": calculer_paires(),
        "memoire": [
            {
                "forme": list(forme),
                "dtype": nom_du_type(dtype),
                "octets_par_nombre": torch.empty((), dtype=dtype).element_size(),
                "octets": octets(forme, dtype),
            }
            for forme, dtype in CAS_MEMOIRE
        ],
        "exemples": {
            "creer": {nom: tenseur_en_json(t) for nom, t in exemple_creer().items()},
            "lire": {cle: list(v) if isinstance(v, tuple) else v for cle, v in exemple_lire().items()},
            "calculer": exemple_calculer(),
        },
    }


def vers_json(valeur) -> str:
    """Le texte JSON d'un fichier : UTF-8 lisible, sans NaN, indenté d'une espace, fini par un retour à la ligne."""
    return json.dumps(valeur, ensure_ascii=False, allow_nan=False, indent=1) + "\n"


def ecrire_attendus() -> None:
    """Écrit tests/attendus-formes.json (UTF-8, fins de ligne LF)."""
    with open(CHEMIN_ATTENDUS, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(vers_json(calculer_attendus()))


if __name__ == "__main__":
    ecrire_attendus()
    print(f"Écrit\u202f: {CHEMIN_ATTENDUS}")
