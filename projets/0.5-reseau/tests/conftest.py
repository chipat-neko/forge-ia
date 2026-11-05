"""Réglages communs des tests : le marqueur `gpu` est sauté quand CUDA est absente."""

import pytest


def _cuda_disponible() -> bool:
    try:
        import torch
    except ImportError:
        return False
    return torch.cuda.is_available()


def pytest_collection_modifyitems(config, items):
    if _cuda_disponible():
        return
    saut = pytest.mark.skip(reason="CUDA absente : test réservé à la carte graphique sauté")
    for test in items:
        if "gpu" in test.keywords:
            test.add_marker(saut)
