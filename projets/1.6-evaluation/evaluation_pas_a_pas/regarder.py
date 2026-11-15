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


def regard_des_tetes(cartes: Tensor) -> list[dict[str, float]]:
    """Ce que regarde chaque tête d'une couche, en trois nombres, à partir de ses cartes `[têtes, n, n]`.

    Le jeton 0 est `<|fin_texte|>` (voir `jetons_de_la_phrase`). Les moyennes se font sur les jetons qui ont
    un jeton de la phrase juste avant eux, les jetons 2 à n − 1\u202f:

    - `jeton_d_avant`\u202f: la part de l'attention donnée au jeton juste avant (`poids[i][i − 1]`)\u202f;
    - `distance`\u202f: combien de jetons en arrière la tête regarde, sur les mots de la phrase\u202f: la somme des
      `poids[i][j] × (i − j)` pour j de 1 à i. L'attention posée sur `<|fin_texte|>` n'y compte pas\u202f:
      beaucoup de têtes y reposent quand rien ne les intéresse, et elle ferait passer leur regard pour lointain\u202f;
    - `debut`\u202f: la part de l'attention posée sur `<|fin_texte|>`.
    """
    n = cartes.shape[-1]
    if n < 3:
        raise ValueError(f"Il faut au moins deux jetons après <|fin_texte|> pour mesurer un regard\u202f: la phrase en a {n - 1}.")
    cartes = cartes.double()
    positions = torch.arange(n, dtype=torch.float64)
    ecarts = (positions[:, None] - positions[None, :]).clamp(min=0)  # i − j, nul en avant (où le poids est nul)
    i = torch.arange(2, n)
    avant = cartes[:, i, i - 1].mean(dim=-1)
    distance = (cartes[:, 2:, 1:] * ecarts[2:, 1:]).sum(dim=-1).mean(dim=-1)
    debut = cartes[:, 2:, 0].mean(dim=-1)
    return [
        {"jeton_d_avant": float(a), "distance": float(d), "debut": float(b)} for a, d, b in zip(avant, distance, debut)
    ]


def choisir_couche_et_tetes(modele: Transformer, ids: Tensor) -> tuple[int, int, int, list[list[dict[str, float]]]]:
    """La couche et les deux têtes à montrer pour la phrase `ids`, avec le regard de chaque tête de chaque couche.

    La couche est celle de la tête qui regarde le plus le jeton d'avant, dans tout le modèle (le plus grand
    `jeton_d_avant`). Dans cette couche, la seconde tête est celle qui regarde le plus loin (la plus grande
    `distance`), parmi les autres. Rend `(couche, tête_jeton_d_avant, tête_loin, regards)`, où `regards[c][t]`
    est le regard de la tête `t` de la couche `c` (voir `regard_des_tetes`).
    """
    config = modele.config
    regards = [regard_des_tetes(cartes_attention(modele, ids, couche)) for couche in range(config.couches)]
    couche, avant = max(
        ((c, t) for c in range(config.couches) for t in range(config.tetes)),
        key=lambda ct: regards[ct[0]][ct[1]]["jeton_d_avant"],
    )
    loin = max((t for t in range(config.tetes) if t != avant), key=lambda t: regards[couche][t]["distance"])
    return couche, avant, loin, regards


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
