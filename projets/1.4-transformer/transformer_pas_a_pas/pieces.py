"""Le transformer de « ton IA », pièce par pièce, en fonctions pures.

Chaque pièce est une fonction : elle reçoit des tenseurs (les poids compris) et rend un tenseur,
sans `nn.Module` et sans `F.scaled_dot_product_attention`. Les tenseurs sont en float64, sauf aux
deux endroits où forge calcule en float32 même dans un modèle en float64 :

- RMSNorm : `x.float()` pour la moyenne des carrés (voir `rmsnorm`) ;
- RoPE : les angles, leurs cosinus et sinus, et la rotation (voir `angles_rope` et `tourner`).

Ces deux passages sont refaits ici aux mêmes endroits, dans le même ordre d'opérations : sans
cela, l'écart avec forge serait d'environ 10⁻⁷ au lieu de 10⁻¹². Les poids sont rangés comme
dans forge : une matrice `w` de forme `[sortie, entrée]`, appliquée par `x @ w.T`.

Les fonctions acceptent une suite de jetons `[n, ...]` ou un lot `[lot, n, ...]`.
"""

import math

import torch
from torch import Tensor

EPSILON_RMSNORM = 1e-5  # la valeur de forge (EPSILON_RMSNORM de forge/modele/transformer.py)


# region: plongement
def plongement(ids: Tensor, table: Tensor) -> Tensor:
    """Chaque jeton (un entier) devient une ligne de la table : un vecteur de `dim` nombres."""
    return table[ids]
# fin: plongement


# region: rmsnorm
def rmsnorm(x: Tensor, poids: Tensor, epsilon: float = EPSILON_RMSNORM) -> Tensor:
    """Divise chaque vecteur par la racine de la moyenne de ses carrés, puis multiplie par `poids`."""
    x32 = x.float()  # forge passe ici en float32, même si x est en float64
    normalise = x32 * torch.rsqrt(x32.pow(2).mean(dim=-1, keepdim=True) + epsilon)
    return (normalise * poids).to(x.dtype)
# fin: rmsnorm


# region: rope
def angles_rope(positions: int, dim_tete: int, base: float) -> Tensor:
    """L'angle de chaque paire de chaque position, en float32 comme forge : `[positions, dim_tete // 2]`.

    La paire `i` tourne, à la position `p`, de l'angle `p × base^(-2i / dim_tete)`.
    """
    exposants = torch.arange(0, dim_tete, 2, dtype=torch.float32) / dim_tete
    frequences = base ** (-exposants)
    return torch.outer(torch.arange(positions, dtype=torch.float32), frequences)


def tourner(x: Tensor, angles: Tensor) -> Tensor:
    """Tourne chaque paire de valeurs `(x[2i], x[2i+1])` de l'angle de sa position (en float32)."""
    cos, sin = angles.cos(), angles.sin()
    paires = x.float().reshape(*x.shape[:-1], -1, 2)
    x1, x2 = paires[..., 0], paires[..., 1]
    tourne = torch.stack((x1 * cos - x2 * sin, x1 * sin + x2 * cos), dim=-1)
    return tourne.flatten(-2).to(x.dtype)
# fin: rope


# region: attention
def softmax(x: Tensor) -> Tensor:
    """Des scores deviennent des poids positifs qui totalisent 1 : on soustrait le plus grand score
    (pour que `exp` ne déborde pas), on prend `exp`, on divise par la somme."""
    decale = x - x.max(dim=-1, keepdim=True).values
    exponentielles = torch.exp(decale)
    return exponentielles / exponentielles.sum(dim=-1, keepdim=True)


def poids_et_valeurs(x: Tensor, w_qkv: Tensor, tetes: int, base: float) -> tuple[Tensor, Tensor]:
    """Les poids d'attention `[..., tetes, n, n]` et les valeurs `[..., tetes, n, dim_tete]`."""
    n, dim = x.shape[-2], x.shape[-1]
    q, k, v = (x @ w_qkv.T).chunk(3, dim=-1)  # requêtes, clés, valeurs
    q, k, v = (t.unflatten(-1, (tetes, dim // tetes)).transpose(-3, -2) for t in (q, k, v))
    angles = angles_rope(n, dim // tetes, base)
    q, k = tourner(q, angles), tourner(k, angles)
    scores = q @ k.transpose(-2, -1) / math.sqrt(dim // tetes)
    return softmax(scores.masked_fill(masque(n), float("-inf"))), v


def poids_attention(x: Tensor, w_qkv: Tensor, tetes: int, base: float) -> Tensor:
    """Pour chaque tête, qui regarde qui : un tableau `n × n` dont chaque ligne totalise 1."""
    return poids_et_valeurs(x, w_qkv, tetes, base)[0]


def attention(x: Tensor, w_qkv: Tensor, w_sortie: Tensor, tetes: int, base: float) -> Tensor:
    """Attention multi-têtes causale : chaque jeton reçoit la moyenne pondérée des valeurs qui le précèdent."""
    poids, valeurs = poids_et_valeurs(x, w_qkv, tetes, base)
    melange = (poids @ valeurs).transpose(-3, -2).flatten(-2)  # les têtes se recollent
    return melange @ w_sortie.T
# fin: attention


# region: masque
def masque(n: int) -> Tensor:
    """`True` au-dessus de la diagonale : ce qu'un jeton n'a pas le droit de voir (les jetons d'après)."""
    return torch.ones(n, n, dtype=torch.bool).triu(diagonal=1)
# fin: masque


# region: swiglu
def swiglu(x: Tensor, w_porte: Tensor, w_haute: Tensor, w_basse: Tensor) -> Tensor:
    """La porte (passée par SiLU) décide, composante par composante, quoi garder de la voie haute."""
    porte = x @ w_porte.T
    silu = porte / (1 + torch.exp(-porte))
    return (silu * (x @ w_haute.T)) @ w_basse.T
# fin: swiglu


# region: bloc
def bloc(x: Tensor, p: dict) -> Tensor:
    """Un bloc : l'attention puis le MLP, chacun précédé d'une RMSNorm et AJOUTÉ au vecteur."""
    x = x + attention(rmsnorm(x, p["norme_attention"]), p["w_qkv"], p["w_sortie"], p["tetes"], p["base_rope"])
    return x + swiglu(rmsnorm(x, p["norme_mlp"]), p["w_porte"], p["w_haute"], p["w_basse"])
# fin: bloc


# region: modele
def modele(ids: Tensor, p: dict) -> Tensor:
    """Les logits : un score par jeton possible, à chaque position. La table du plongement sert aussi
    de matrice de sortie (poids liés)."""
    x = plongement(ids, p["plongement"])
    for b in p["blocs"]:
        x = bloc(x, b)
    return rmsnorm(x, p["norme_finale"]) @ p["plongement"].T
# fin: modele
