"""La mémoire d'un tenseur : le nombre de nombres, fois la taille d'un nombre."""

import pytest
import torch

from tenseurs.memoire import octets


def test_une_matrice_4096_par_4096():
    # 4 096 × 4 096 nombres de 4 octets : 64 Mo. En bfloat16, deux octets par nombre : la moitié.
    assert octets((4096, 4096), torch.float32) == 67_108_864 and octets((4096, 4096), torch.bfloat16) == 33_554_432
    assert octets((4096, 4096), torch.float32) == 64 * 1024 * 1024


@pytest.mark.parametrize(
    ("forme", "dtype", "attendu"),
    [
        ((), torch.float32, 4),
        ((3,), torch.float32, 12),
        ((2, 3), torch.float64, 48),
        ((2, 3), torch.int64, 48),
        ((2, 3, 4), torch.int8, 24),
        ((2, 3, 4), torch.float16, 48),
        ((5, 0), torch.float32, 0),
    ],
)
def test_petits_tenseurs(forme, dtype, attendu):
    assert octets(forme, dtype) == attendu


@pytest.mark.parametrize("dtype", [torch.float64, torch.float32, torch.float16, torch.bfloat16, torch.int64, torch.int8, torch.bool])
def test_comme_un_vrai_tenseur(dtype):
    # Le même nombre d'octets qu'un tenseur créé pour de bon.
    forme = (3, 5, 7)
    t = torch.empty(forme, dtype=dtype)
    assert octets(forme, dtype) == t.nelement() * t.element_size()


def test_octets_est_un_entier():
    assert type(octets((2, 2), torch.float32)) is int
