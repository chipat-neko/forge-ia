"""Les pièces du transformer, refaites en fonctions pures, égales à celles de forge.

Chaque pièce est comparée à son module de forge sur un même lot, en float64, sur le
processeur. forge calcule RMSNorm et RoPE en float32 même dans un modèle en float64 :
`pieces.py` refait ces passages aux mêmes endroits, et l'égalité tient à 10⁻¹² près.
"""

import ast
import pathlib
import re

import pytest
import torch
from forge.modele import ConfigModele

from transformer_pas_a_pas import pieces
from transformer_pas_a_pas.comparer import ecarts, poids_de_forge, preparer_forge

CONFIG = ConfigModele(dim=32, couches=2, tetes=4, longueur_contexte=16, taille_vocabulaire=50)


# region: test-egalite
@pytest.mark.parametrize("piece", ["rmsnorm", "rope", "attention", "swiglu", "bloc", "modele"])
def test_piece_egale_a_forge(piece):
    assert ecarts(CONFIG)[piece] <= 1e-12
# fin: test-egalite


def test_les_ecarts_ne_sont_pas_triviaux():
    # Des poids trop petits rendraient chaque pièce presque nulle : l'égalité ne prouverait rien.
    p = poids_de_forge(preparer_forge(CONFIG, graine=0))
    logits = pieces.modele(torch.arange(10), p)
    assert logits.dtype == torch.float64
    assert logits.std() > 0.1
    assert set(ecarts(CONFIG)) == {"rmsnorm", "rope", "attention", "swiglu", "bloc", "modele"}


def test_les_poids_lies():
    p = poids_de_forge(preparer_forge(CONFIG, graine=0))
    # La même matrice sert d'entrée et de sortie : pieces.modele n'a pas de matrice de sortie à part.
    assert "sortie" not in p
    assert p["plongement"].shape == (50, 32)


def test_masque_causal():
    # Changer le dernier jeton ne change aucune sortie des positions d'avant.
    p = poids_de_forge(preparer_forge(CONFIG, graine=1))
    ids = torch.tensor([3, 14, 15, 9, 2, 6, 5, 3])
    autres = ids.clone()
    autres[-1] = 40
    a, b = pieces.modele(ids, p), pieces.modele(autres, p)
    assert torch.equal(a[:-1], b[:-1])
    assert not torch.equal(a[-1], b[-1])


def test_masque_au_dessus_de_la_diagonale():
    m = pieces.masque(4)
    assert m.dtype == torch.bool
    assert m.tolist() == [
        [False, True, True, True],
        [False, False, True, True],
        [False, False, False, True],
        [False, False, False, False],
    ]


def test_poids_attention_somment_a_un_et_redonnent_la_sortie():
    p = poids_de_forge(preparer_forge(CONFIG, graine=2))["blocs"][0]
    x = torch.randn(7, 32, dtype=torch.float64, generator=torch.Generator().manual_seed(5))
    poids = pieces.poids_attention(x, p["w_qkv"], 4, 10000.0)
    assert poids.shape == (4, 7, 7)
    assert torch.allclose(poids.sum(dim=-1), torch.ones(4, 7, dtype=torch.float64), atol=1e-14, rtol=0)
    # Au-dessus de la diagonale : exactement 0.
    assert torch.all(poids.triu(diagonal=1) == 0)
    # Les poids, appliqués aux valeurs, redonnent la sortie de l'attention.
    v = (x @ p["w_qkv"].T).chunk(3, dim=-1)[2]
    v = v.reshape(7, 4, 8).transpose(0, 1)
    melange = (poids @ v).transpose(0, 1).reshape(7, 32)
    sortie = pieces.attention(x, p["w_qkv"], p["w_sortie"], 4, 10000.0)
    assert torch.allclose(melange @ p["w_sortie"].T, sortie, atol=1e-14, rtol=0)


@pytest.mark.parametrize("forme", [(5,), (3, 7), (2, 3, 4)])
def test_softmax_a_la_main_egale_torch(forme):
    x = torch.randn(*forme, dtype=torch.float64, generator=torch.Generator().manual_seed(7)) * 30
    assert torch.allclose(pieces.softmax(x), torch.softmax(x, dim=-1), atol=1e-12, rtol=0)
    assert torch.allclose(pieces.softmax(x).sum(-1), torch.ones(forme[:-1], dtype=torch.float64), atol=1e-14, rtol=0)


def test_softmax_supporte_moins_l_infini_et_les_grands_nombres():
    s = pieces.softmax(torch.tensor([0.0, float("-inf"), 1.0], dtype=torch.float64))
    assert s[1] == 0 and torch.isclose(s.sum(), torch.tensor(1.0, dtype=torch.float64))
    # Sans soustraire le maximum, exp(1000) déborde : la version à la main doit s'en sortir.
    assert torch.isfinite(pieces.softmax(torch.tensor([1000.0, 999.0], dtype=torch.float64))).all()


def test_angles_rope_sont_en_float32_comme_forge():
    from forge.modele.transformer import rope_cos_sin

    cos, sin = rope_cos_sin(16, 8, 10000.0, "cpu")
    angles = pieces.angles_rope(16, 8, 10000.0)
    assert angles.dtype == torch.float32 and angles.shape == (16, 4)
    assert torch.equal(angles.cos(), cos) and torch.equal(angles.sin(), sin)


def test_rope_conserve_la_norme_et_ne_tourne_pas_la_position_zero():
    x = torch.randn(1, 2, 6, 8, dtype=torch.float64, generator=torch.Generator().manual_seed(3))
    y = pieces.tourner(x, pieces.angles_rope(6, 8, 10000.0))
    assert y.dtype == torch.float64
    # Les rotations se calculent en float32 : la norme est conservée à 10⁻⁶ près, pas mieux.
    assert torch.allclose(x.norm(dim=-1), y.norm(dim=-1), atol=1e-6, rtol=0)
    # À la position 0 l'angle est nul : rien ne tourne (au passage par float32 près).
    assert torch.allclose(x[..., 0, :], y[..., 0, :], atol=1e-6, rtol=0)
    assert not torch.allclose(x[..., 1:, :], y[..., 1:, :], atol=1e-3, rtol=0)


def test_rmsnorm_normalise_l_echelle():
    x = torch.randn(3, 32, dtype=torch.float64, generator=torch.Generator().manual_seed(4)) * 50
    y = pieces.rmsnorm(x, torch.ones(32, dtype=torch.float64))
    assert y.dtype == torch.float64
    assert torch.allclose(y.pow(2).mean(-1), torch.ones(3, dtype=torch.float64), atol=1e-4, rtol=0)


def test_les_pieces_sont_des_fonctions_pures():
    arbre = ast.parse(pathlib.Path(pieces.__file__).read_text(encoding="utf-8"))
    noms = {n.attr for n in ast.walk(arbre) if isinstance(n, ast.Attribute)} | {n.id for n in ast.walk(arbre) if isinstance(n, ast.Name)}
    # Ni attention toute faite, ni module, ni classe.
    assert "scaled_dot_product_attention" not in noms
    assert "Module" not in noms and "nn" not in noms
    assert not [n for n in ast.walk(arbre) if isinstance(n, ast.ClassDef)]
    # La softmax est écrite à la main : aucun appel à torch.softmax ni F.softmax (seule notre fonction s'appelle ainsi).
    appels = [n.func.attr for n in ast.walk(arbre) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    assert "softmax" not in appels


def test_regions_de_pieces():
    lignes = pathlib.Path(pieces.__file__).read_text(encoding="utf-8").splitlines()
    ouvertes = [m.group(1) for ligne in lignes if (m := re.match(r"\s*# region: (\S+)", ligne))]
    fermees = [m.group(1) for ligne in lignes if (m := re.match(r"\s*# fin: (\S+)", ligne))]
    assert ouvertes == ["plongement", "rmsnorm", "rope", "attention", "masque", "swiglu", "bloc", "modele"]
    assert fermees == ouvertes
