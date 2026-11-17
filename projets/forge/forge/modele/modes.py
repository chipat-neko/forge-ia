"""Changer le mode d'un modèle le temps d'un calcul, puis le lui rendre."""

from collections.abc import Iterator
from contextlib import contextmanager

from torch import nn


@contextmanager
def en_evaluation(modele: nn.Module) -> Iterator[None]:
    """Met le modèle en mode évaluation (sans dropout, etc.), puis rend à chaque sous-module le mode qu'il avait."""
    modes = {module: module.training for module in modele.modules()}
    modele.eval()
    try:
        yield
    finally:
        for module, mode in modes.items():
            module.training = mode
