"""Regarder dans le modèle : les cartes d'attention d'une couche, et les jetons qu'il juge les plus probables.

`cartes_attention` refait, à la main, l'attention d'une couche de forge pour en rendre les poids\u202f: pour
chaque tête, un tableau «\u202fqui regarde qui\u202f». `suivants` donne les `k` jetons que le modèle trouve les
plus probables après une phrase.

Les cartes que le site montre sont calculées ici, par forge, sur le processeur, pour une phrase, une
couche et une tête, et écrites dans un fichier que le site lit à la construction (voir le README).
"""

import math

import torch
from forge.evaluation.qcm import JETON_DE_DEBUT
from forge.modele.transformer import Transformer, appliquer_rope, rope_cos_sin
from torch import Tensor


class _Assez(Exception):
    """Levée par le crochet pour arrêter le modèle quand l'entrée de la couche est prise."""


# region: cartes
@torch.no_grad()
def cartes_attention(modele: Transformer, ids: Tensor, couche: int) -> Tensor:
    """Les poids d'attention de la couche `couche` (à partir de 0)\u202f: un tenseur `[têtes, n, n]`.

    `ids` est la phrase en jetons (`n` entiers, ou `[1, n]`). Le poids `[t, i, j]` dit quelle part de
    l'attention la position `i` donne à la position `j`, pour la tête `t`\u202f: il vaut 0 pour `j > i`
    (le modèle ne regarde jamais en avant), et chaque ligne totalise 1.

    On prend l'entrée de la couche (le texte déjà normé par `norme_attention`) avec un crochet, puis on
    refait à la main ce que fait `Attention.forward`\u202f: `proj_qkv` donne q, k et v\u202f; RoPE tourne q et k\u202f;
    le produit q · k, divisé par √dim_tete, est masqué (pas de regard en avant), puis mis en softmax.
    """
    if ids.dim() == 1:
        ids = ids[None]
    if ids.shape[0] != 1:
        raise ValueError(f"Les cartes se calculent pour une seule phrase à la fois\u202f: ids a {ids.shape[0]} lignes, il en faut 1.")
    config = modele.config
    if not 0 <= couche < config.couches:
        raise ValueError(f"La couche {couche} n'existe pas\u202f: ce modèle a {config.couches} couches, numérotées de 0 à {config.couches - 1}.")
    bloc = modele.blocs[couche]
    prise: dict[str, Tensor] = {}

    def prendre(_module, _entree, sortie):
        prise["x"] = sortie.detach()
        raise _Assez  # les couches d'après ne servent à rien ici

    crochet = bloc.norme_attention.register_forward_hook(prendre)
    try:
        modele(ids.to(next(modele.parameters()).device))
    except _Assez:
        pass
    finally:
        crochet.remove()
    x = prise["x"]  # [1, n, dim]
    n = x.shape[1]
    tetes, dim_tete = config.tetes, config.dim // config.tetes
    q, k, _ = bloc.attention.proj_qkv(x).chunk(3, dim=-1)
    q, k = (t.reshape(1, n, tetes, dim_tete).transpose(1, 2) for t in (q, k))  # [1, têtes, n, dim_tete]
    cos, sin = rope_cos_sin(n, dim_tete, config.base_rope, x.device)
    q, k = appliquer_rope(q, cos, sin), appliquer_rope(k, cos, sin)
    scores = (q @ k.transpose(-2, -1)) / math.sqrt(dim_tete)  # [1, têtes, n, n]
    interdit = torch.ones(n, n, dtype=torch.bool, device=x.device).triu(diagonal=1)  # j > i
    scores = scores.masked_fill(interdit, float("-inf"))
    return torch.softmax(scores, dim=-1)[0]
# fin: cartes


def jetons_de_la_phrase(tokenizer, phrase: str, longueur_contexte: int) -> list[int]:
    """`<|fin_texte|>` (le début de document du modèle), puis la phrase en jetons ; les derniers jetons si elle est trop longue."""
    ids = [tokenizer.id_special(JETON_DE_DEBUT), *tokenizer.encoder(phrase)]
    return ids[-longueur_contexte:]


def texte_du_jeton(tokenizer, identifiant: int) -> str:
    """Le texte d'un jeton (un morceau de caractère donne le caractère de remplacement U+FFFD)."""
    return tokenizer.octets_du_jeton(identifiant).decode("utf-8", errors="replace")


# region: suivants
@torch.no_grad()
def suivants(modele: Transformer, tokenizer, phrase: str, k: int = 10) -> list[tuple[str, float]]:
    """Les `k` jetons que le modèle juge les plus probables après `phrase`, avec leur probabilité (du plus au moins probable).

    Le modèle donne un score à chacun des jetons possibles pour la suite de la dernière position\u202f; la
    softmax les change en probabilités qui totalisent 1.
    """
    if k < 1:
        raise ValueError(f"k vaut {k}\u202f: il faut demander au moins un jeton.")
    ids = jetons_de_la_phrase(tokenizer, phrase, modele.config.longueur_contexte)
    appareil = next(modele.parameters()).device
    logits, _ = modele(torch.tensor([ids], device=appareil))
    probas = torch.softmax(logits[0, -1].float(), dim=-1)
    meilleures = probas.topk(min(k, probas.numel()))
    return [(texte_du_jeton(tokenizer, int(i)), float(p)) for p, i in zip(meilleures.values, meilleures.indices)]
# fin: suivants
