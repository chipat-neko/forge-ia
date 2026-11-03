"""Test de PyTorch sur la carte graphique (RTX 5070 Ti, architecture sm_120)."""

import pytest

try:
    import torch
except ImportError as erreur:
    raise ImportError(
        "PyTorch n'est pas installé. Lance les tests avec `uv run --extra gpu pytest -q` "
        "(carte NVIDIA) ou `uv run --extra cpu pytest -q` (sans carte graphique)."
    ) from erreur


@pytest.mark.gpu
def test_cuda_sm120():
    assert torch.cuda.is_available()
    assert torch.cuda.get_device_capability(0) == (12, 0)
    x = torch.randn(256, 256, device="cuda", dtype=torch.bfloat16)
    assert torch.isfinite(x @ x).all()
