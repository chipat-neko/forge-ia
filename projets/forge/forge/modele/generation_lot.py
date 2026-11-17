"""Génération par lots, avec cache : écrire vite beaucoup de réponses.

`generer` écrit un seul texte à la fois et relit tout ce texte à chaque jeton. Pour fabriquer
des milliers de réponses (les paires de préférences de 1.8, l'apprentissage par renforcement de
1.9), `generer_lot` fait deux économies :

- plusieurs invites avancent ensemble, un seul passage du modèle par jeton pour tout le lot :
  sur la carte graphique, 32 textes coûtent à peine plus qu'un seul ;
- le cache des clés et des valeurs (`CacheKV`) : chaque pas ne lit que le nouveau jeton.

Les invites d'un lot n'ont pas la même longueur : on les complète à GAUCHE par `<|bourrage|>`,
que le masque cache à tout le monde. Complétées à gauche, toutes les invites finissent à la même
colonne : à chaque pas, chaque texte écrit son jeton dans la même colonne du cache, et un seul
passage du modèle sert à tous. Les positions de RoPE comptent à partir du premier vrai jeton de
chaque invite : chaque texte se lit comme s'il était seul.
"""

from collections.abc import Sequence

import torch
from torch import Tensor

from forge.fichiers import ESPACE_FINE, entier
from forge.modele.cache import CacheKV
from forge.modele.config import ConfigModele
from forge.modele.modes import en_evaluation
from forge.modele.transformer import Transformer
from forge.tokenizer.speciaux import NOMBRE_SPECIAUX, SPECIAUX


def _id_bourrage(config: ConfigModele) -> int:
    """L'identifiant de `<|bourrage|>` : les jetons spéciaux occupent la fin du vocabulaire."""
    return config.taille_vocabulaire - NOMBRE_SPECIAUX + SPECIAUX.index("<|bourrage|>")


def _verifier(
    config: ConfigModele,
    invites: Sequence[Sequence[int]],
    n_nouveaux: int,
    temperature: float,
    top_k: int,
    lot: int,
) -> None:
    """Lève `ValueError`, en nommant l'invite fautive (dès 1), si la demande est impossible."""
    if n_nouveaux < 0:
        raise ValueError(f"`n_nouveaux` vaut {n_nouveaux} : il doit être 0 ou plus.")
    if not temperature >= 0:
        raise ValueError(
            f"`temperature` vaut {temperature} : elle doit être 0 (choix glouton) ou plus."
        )
    if top_k < 0:
        raise ValueError(f"`top_k` vaut {top_k} : il doit être 0 (pas de limite) ou plus.")
    if lot < 1:
        raise ValueError(f"`lot` vaut {lot} : il faut au moins une invite par lot.")
    contexte = entier(config.longueur_contexte, milliers=ESPACE_FINE)
    for rang, invite in enumerate(invites, start=1):
        if len(invite) == 0:
            raise ValueError(
                f"L'invite {rang} est vide : donne au moins un jeton, par exemple `<|fin_texte|>`."
            )
        if len(invite) + n_nouveaux > config.longueur_contexte:
            raise ValueError(
                f"L'invite {rang} a {entier(len(invite), milliers=ESPACE_FINE)} jetons : avec "
                f"{entier(n_nouveaux, milliers=ESPACE_FINE)} nouveaux, le texte dépasserait les "
                f"{contexte} jetons que ce modèle lit d'un coup (`longueur_contexte`), et la "
                "génération par lots n'oublie jamais le début. Raccourcis l'invite ou demande "
                "moins de jetons."
            )
        hors = [t for t in invite if not 0 <= t < config.taille_vocabulaire]
        if hors:
            raise ValueError(
                f"L'invite {rang} contient le jeton {hors[0]}, qui n'est pas dans le vocabulaire "
                f"(0 à {entier(config.taille_vocabulaire - 1, milliers=ESPACE_FINE)}). Vérifie que "
                "le texte a été découpé avec le bon tokenizer."
            )


def _tirer(scores: Tensor, temperature: float, top_k: int, hasard: torch.Generator) -> Tensor:
    """Un jeton par rangée de `scores` (`[lot, V]`), tiré comme `generer` le tire."""
    scores = scores.float()
    if temperature == 0:
        return scores.argmax(dim=-1)
    scores = scores / temperature
    if 0 < top_k < scores.shape[-1]:
        seuil = torch.topk(scores, top_k, dim=-1).values[:, -1:]
        scores = scores.masked_fill(scores < seuil, float("-inf"))
    probabilites = torch.softmax(scores, dim=-1)
    return torch.multinomial(probabilites, 1, generator=hasard)[:, 0]


def _generer_sous_lot(
    modele: Transformer,
    invites: Sequence[Sequence[int]],
    n_nouveaux: int,
    temperature: float,
    top_k: int,
    arret: int | None,
    hasard: torch.Generator,
    appareil: torch.device,
) -> list[list[int]]:
    """Un sous-lot : invites complétées à gauche, cache pré-rempli, puis un jeton par pas."""
    config = modele.config
    lot = len(invites)
    longueur = max(len(invite) for invite in invites)
    bourrage = _id_bourrage(config)
    ids = torch.tensor(
        [[bourrage] * (longueur - len(invite)) + list(invite) for invite in invites],
        device=appareil,
    )
    manques = longueur - torch.tensor([len(invite) for invite in invites], device=appareil)
    # Le dernier jeton tiré n'est jamais relu : le cache garde l'invite et n_nouveaux - 1 jetons.
    longueur_max = longueur + n_nouveaux - 1
    colonnes = torch.arange(longueur_max, device=appareil)
    valide = colonnes[None] >= manques[:, None]  # [lot, longueur_max] : faux sur le bourrage
    positions = (colonnes[None] - manques[:, None]).clamp(min=0)  # depuis le premier vrai jeton
    dtype = torch.bfloat16 if appareil.type == "cuda" else next(modele.parameters()).dtype
    cache = CacheKV(config, lot, longueur_max, appareil, dtype)

    # Pré-remplissage : les invites entières, d'un coup. Chaque jeton voit les vrais jetons
    # qui le précèdent ; la diagonale reste vraie pour que le bourrage, qui ne voit rien
    # d'autre, ne donne pas une ligne vide (un softmax sur du vide donne des NaN).
    causal = torch.ones(longueur, longueur, dtype=torch.bool, device=appareil).tril()
    diagonale = torch.eye(longueur, dtype=torch.bool, device=appareil)
    masque = (causal & valide[:, None, :longueur]) | diagonale
    logits = modele.avancer(ids, positions[:, :longueur], masque[:, None], cache)

    # Le masque des pas, préparé une fois : 0 là où on regarde, -inf sur le bourrage, dans le
    # type du calcul, et sa largeur réservée à un multiple de 16. `scaled_dot_product_attention`
    # le prend alors tel quel ; un masque booléen serait converti et recopié à chaque couche.
    largeur = -(-longueur_max // 16) * 16
    masque_des_pas = torch.zeros(lot, 1, 1, largeur, dtype=dtype, device=appareil)
    masque_des_pas[:, 0, 0, :longueur_max].masked_fill_(~valide, float("-inf"))

    generes = torch.empty(lot, n_nouveaux, dtype=torch.long, device=appareil)
    fini = torch.zeros(lot, dtype=torch.bool, device=appareil)
    for pas in range(n_nouveaux):
        suivant = _tirer(logits[:, -1], temperature, top_k, hasard)
        generes[:, pas] = suivant
        if pas == n_nouveaux - 1:
            break
        if arret is not None:
            fini |= suivant == arret
            if bool(fini.all()):
                break
        # Un pas : chaque texte lit le jeton qu'il vient d'écrire, dans la même colonne.
        fin = cache.longueur + 1
        logits = modele.avancer(
            suivant[:, None], positions[:, fin - 1 : fin], masque_des_pas[..., :fin], cache
        )

    sorties = []
    for rangee in generes[:, : pas + 1].tolist():
        if arret is not None and arret in rangee:
            rangee = rangee[: rangee.index(arret) + 1]
        sorties.append(rangee)
    return sorties


@torch.no_grad()
def generer_lot(
    modele: Transformer,
    invites: Sequence[Sequence[int]],
    n_nouveaux: int,
    temperature: float = 1.0,
    top_k: int = 50,
    graine: int = 0,
    arret: int | None = None,
    lot: int = 32,
) -> list[list[int]]:
    """Prolonge chaque invite de `n_nouveaux` jetons au plus ; rend SEULEMENT les nouveaux.

    - `invites` : les débuts de texte, en identifiants de jetons (aucune n'est vide) ;
    - `n_nouveaux`, `temperature`, `top_k`, `arret` : comme `generer`. Chaque sortie s'arrête
      après son premier `arret`, inclus ;
    - `graine` : graine d'un `torch.Generator` propre à cet appel (le hasard global de PyTorch
      n'est ni lu ni modifié) ;
    - `lot` : nombre d'invites qui avancent ensemble. Les sous-lots sont traités dans l'ordre,
      avec le même générateur : à température non nulle, le résultat dépend donc de `lot`
      (même `graine` et même `lot` : même résultat). En glouton (`temperature=0`), il n'en
      dépend pas, aux arrondis près.

    Pas de fenêtre glissante : chaque invite plus `n_nouveaux` doit tenir dans
    `longueur_contexte`, sinon `ValueError`. En glouton, le résultat est celui de `generer`,
    invite par invite, aux arrondis près (en 32 bits sur le processeur, les tests le trouvent
    identique ; en bf16, deux jetons presque ex æquo peuvent s'inverser). Pendant l'appel, le
    modèle est en mode évaluation, calcule sous
    `autocast` (bf16 sur la carte, 32 bits sur le processeur) et ne garde aucun gradient ;
    chaque sous-module retrouve ensuite son mode, même en cas d'erreur.
    """
    # Importé ici : `forge.evaluation` importe `forge.modele`, l'inverse ferait une boucle.
    from forge.evaluation.perte import autocast

    _verifier(modele.config, invites, n_nouveaux, temperature, top_k, lot)
    if n_nouveaux == 0:
        return [[] for _ in invites]
    appareil = next(modele.parameters()).device
    hasard = torch.Generator(device=appareil)
    hasard.manual_seed(graine)
    sorties: list[list[int]] = []
    with en_evaluation(modele), autocast(appareil):
        for debut in range(0, len(invites), lot):
            sorties += _generer_sous_lot(
                modele, invites[debut : debut + lot], n_nouveaux, temperature, top_k, arret,
                hasard, appareil,
            )
    return sorties
