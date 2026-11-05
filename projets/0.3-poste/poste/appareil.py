"""Choisir l'appareil de calcul : la carte graphique NVIDIA (cuda) ou le processeur (cpu).

La valeur vient de l'argument, sinon de la variable d'environnement
FORGE_APPAREIL, sinon « auto » : la carte si PyTorch la voit, sinon le
processeur. MPS, la puce graphique des Mac, n'est pas proposé : rien n'est
testé sur Mac, qui calcule donc sur le processeur.

Ce fichier est copié tel quel dans les projets 0.4 et 0.5 : il n'importe que
torch et la bibliothèque standard.
"""

import os

import torch

# region: appareil
class AppareilIndisponible(Exception):
    """L'appareil demandé existe, mais PyTorch ne peut pas s'en servir sur ce poste."""


def choisir_appareil(demande: str | None = None) -> torch.device:
    """L'appareil où calculer : `demande`, sinon FORGE_APPAREIL, sinon « auto »."""
    variable = not demande
    valeur = (os.environ.get("FORGE_APPAREIL") or "auto") if variable else demande
    valeur = valeur.strip().lower()
    if valeur == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if valeur == "cpu":
        return torch.device("cpu")
    if valeur == "cuda":
        if not torch.cuda.is_available():
            # Le conseil dépend de l'endroit d'où vient la demande : l'argument passe avant la variable.
            if variable:
                demandee = "(FORGE_APPAREIL=cuda)"
                processeur = "mets FORGE_APPAREIL=cpu (ou auto)"
            else:
                demandee = "(cuda)"
                processeur = "demande cpu (ou auto) à la place, ou, sans rien demander, mets FORGE_APPAREIL=cpu"
            raise AppareilIndisponible(
                f"Tu as demandé la carte graphique {demandee}, mais PyTorch ne la voit pas. "
                f"Pour calculer sur le processeur, {processeur}. Pour savoir pourquoi, lance "
                "`uv run --extra cpu python -m poste` dans le dossier projets/0.3-poste."
            )
        return torch.device("cuda")
    origine = " (lu dans la variable FORGE_APPAREIL)" if variable else ""
    raise ValueError(
        f"Appareil inconnu{origine}\u202f: «\u202f{valeur}\u202f». "
        "Choisis auto (la carte si PyTorch la voit, sinon le processeur), cpu ou cuda."
    )


# fin: appareil
