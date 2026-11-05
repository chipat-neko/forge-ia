"""Les règles de forme : la diffusion (a + b) et le produit matriciel (a @ b).

`forme_diffusee` et `forme_produit` sont écrites en Python pur, sans PyTorch :
ces tests les comparent à PyTorch lui-même, sur toutes les formes de 1 à 3
dimensions de tailles 1 à 3, prises deux à deux.
"""

import itertools

import pytest
import torch

from tenseurs.formes import forme_diffusee, forme_produit

# Les 39 formes de 1 à 3 dimensions, de tailles 1 à 3 : 3 + 9 + 27.
FORMES = [forme for n in (1, 2, 3) for forme in itertools.product((1, 2, 3), repeat=n)]


def diffusion_de_pytorch(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, ...] | None:
    try:
        return tuple(torch.broadcast_shapes(a, b))
    except RuntimeError:
        return None


def produit_de_pytorch(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, ...] | None:
    try:
        return tuple(torch.matmul(torch.empty(a), torch.empty(b)).shape)
    except RuntimeError:
        return None


def test_diffusion_exemples():
    assert forme_diffusee((3, 1), (4,)) == (3, 4) and forme_diffusee((2, 3), (3, 2)) is None
    # Les formes s'alignent par la droite ; une dimension qui manque compte pour 1.
    assert forme_diffusee((2, 1, 3), (4, 1)) == (2, 4, 3)
    assert forme_diffusee((2, 3), (3,)) == (2, 3)
    assert forme_diffusee((2, 3), (2,)) is None
    assert forme_diffusee((5,), (5,)) == (5,)
    assert forme_diffusee((), (2, 3)) == (2, 3)
    assert forme_diffusee((), ()) == ()


def test_produit_exemples():
    assert forme_produit((2, 3), (3, 4)) == (2, 4) and forme_produit((3,), (3,)) == ()
    assert forme_produit((5, 2, 3), (3, 4)) == (5, 2, 4) and forme_produit((2, 3), (2, 3)) is None
    # Un vecteur à droite : la matrice fois le vecteur.
    assert forme_produit((2, 3), (3,)) == (2,)
    # Un vecteur à gauche : le vecteur fois la matrice.
    assert forme_produit((3,), (3, 4)) == (4,)
    # Les dimensions de lot se diffusent, comme pour a + b.
    assert forme_produit((2, 1, 3, 4), (5, 4, 2)) == (2, 5, 3, 2)
    assert forme_produit((2, 3, 4), (3, 4, 5)) is None
    # La dimension intérieure ne se diffuse pas : 1 ne remplace pas 3.
    assert forme_produit((2, 1), (3, 4)) is None
    # Un nombre seul n'a pas de produit matriciel.
    assert forme_produit((), (3,)) is None and forme_produit((3,), ()) is None


def test_les_formes_et_les_paires():
    assert len(FORMES) == 39 and len(set(FORMES)) == 39
    assert len(FORMES) * len(FORMES) == 1_521


def test_les_regles_sont_celles_de_pytorch():
    for a, b in itertools.product(FORMES, repeat=2):
        assert forme_diffusee(a, b) == diffusion_de_pytorch(a, b), (a, b)
        assert forme_produit(a, b) == produit_de_pytorch(a, b), (a, b)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ((), ()),
        ((), (3,)),
        ((2, 3), ()),
        ((1, 2, 1, 3), (4, 1, 3)),
        ((2, 1, 3, 4), (5, 4, 2)),
        ((4,), (2, 3, 4, 5)),
        ((2, 3, 4, 5), (5,)),
        ((0, 3), (3, 2)),
        ((0,), (1,)),
        ((0,), (3,)),
        ((6, 1, 5), (7, 1, 1, 5, 2)),
    ],
)
def test_hors_du_tableau_aussi(a, b):
    # Des nombres seuls, des tailles 0 et 4 dimensions ou plus : toujours la règle de PyTorch.
    assert forme_diffusee(a, b) == diffusion_de_pytorch(a, b)
    assert forme_produit(a, b) == produit_de_pytorch(a, b)


def test_les_formes_rendues_sont_des_tuples():
    # Comme PyTorch : (4,) et pas [4], ce qui s'écrit « (4,) » à l'écran.
    assert isinstance(forme_diffusee([3, 1], [4]), tuple)
    assert str(forme_diffusee((4,), (4,))) == "(4,)"
    assert str(forme_produit((3,), (3,))) == "()"
