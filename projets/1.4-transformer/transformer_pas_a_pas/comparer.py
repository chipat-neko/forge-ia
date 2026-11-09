"""Comparer chaque pièce au module correspondant de forge.

Le modèle de forge est construit en float64 sur le processeur, puis ses poids sont tirés de
nouveau avec un écart-type de 0,2 (ceux de départ, 0,02, rendraient chaque pièce presque nulle :
l'égalité ne prouverait presque rien). Les deux versions reçoivent les mêmes poids et le même lot.
"""

import torch
from forge.modele import ConfigModele, Transformer
from forge.modele.transformer import appliquer_rope, rope_cos_sin

from transformer_pas_a_pas import pieces

PIECES = ("rmsnorm", "rope", "attention", "swiglu", "bloc", "modele")
ECART_POIDS = 0.2
LOT = 2


def preparer_forge(config: ConfigModele, graine: int = 0) -> Transformer:
    """Le `Transformer` de forge, en float64, avec des poids tirés au hasard (graine fixée)."""
    modele = Transformer(config).double().eval()
    tirage = torch.Generator().manual_seed(graine)
    for poids in modele.parameters():  # les poids liés ne sont parcourus qu'une fois
        bruit = torch.randn(poids.shape, generator=tirage, dtype=torch.float64) * ECART_POIDS
        with torch.no_grad():
            poids.copy_(1 + bruit if poids.ndim == 1 else bruit)  # les RMSNorm tournent autour de 1
    return modele


def poids_de_forge(modele: Transformer) -> dict:
    """Les poids d'un `Transformer` de forge, rangés comme `pieces.modele` les attend."""
    c = modele.config
    blocs = [
        {
            "norme_attention": b.norme_attention.poids.detach(),
            "w_qkv": b.attention.proj_qkv.weight.detach(),
            "w_sortie": b.attention.proj_sortie.weight.detach(),
            "norme_mlp": b.norme_mlp.poids.detach(),
            "w_porte": b.mlp.proj_porte.weight.detach(),
            "w_haute": b.mlp.proj_haute.weight.detach(),
            "w_basse": b.mlp.proj_basse.weight.detach(),
            "tetes": c.tetes,
            "base_rope": c.base_rope,
        }
        for b in modele.blocs
    ]
    return {
        "plongement": modele.plongement.weight.detach(),
        "blocs": blocs,
        "norme_finale": modele.norme_finale.poids.detach(),
    }


def plus_grand_ecart(a: torch.Tensor, b: torch.Tensor) -> float:
    return float((a - b).abs().max())


def ecarts(config: ConfigModele, graine: int = 0) -> dict[str, float]:
    """Le plus grand écart (en valeur absolue) entre chaque pièce et le module de forge."""
    modele = preparer_forge(config, graine)
    p = poids_de_forge(modele)
    n, dim, tetes = config.longueur_contexte, config.dim, config.tetes
    dim_tete = dim // tetes
    tirage = torch.Generator().manual_seed(graine + 1)
    x = torch.randn(LOT, n, dim, generator=tirage, dtype=torch.float64) * 3
    q = torch.randn(LOT, tetes, n, dim_tete, generator=tirage, dtype=torch.float64)
    ids = torch.randint(0, config.taille_vocabulaire, (LOT, n), generator=tirage)
    cos, sin = rope_cos_sin(n, dim_tete, config.base_rope, "cpu")
    forge_bloc, mon_bloc = modele.blocs[0], p["blocs"][0]
    with torch.no_grad():
        return {
            "rmsnorm": plus_grand_ecart(
                forge_bloc.norme_attention(x), pieces.rmsnorm(x, mon_bloc["norme_attention"])
            ),
            "rope": plus_grand_ecart(
                appliquer_rope(q, cos, sin), pieces.tourner(q, pieces.angles_rope(n, dim_tete, config.base_rope))
            ),
            "attention": plus_grand_ecart(
                forge_bloc.attention(x, cos, sin),
                pieces.attention(x, mon_bloc["w_qkv"], mon_bloc["w_sortie"], tetes, config.base_rope),
            ),
            "swiglu": plus_grand_ecart(
                forge_bloc.mlp(x),
                pieces.swiglu(x, mon_bloc["w_porte"], mon_bloc["w_haute"], mon_bloc["w_basse"]),
            ),
            "bloc": plus_grand_ecart(forge_bloc(x, cos, sin), pieces.bloc(x, mon_bloc)),
            "modele": plus_grand_ecart(modele(ids)[0], pieces.modele(ids, p)),
        }
