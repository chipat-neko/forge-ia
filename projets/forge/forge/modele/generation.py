"""Génération de texte : on tire les jetons un par un, à partir de ce que le modèle prédit.

À chaque pas, le modèle lit le texte déjà écrit et donne un score à chacun des jetons
possibles pour la suite. On en tire UN, on l'ajoute au texte, et on recommence. Trois
réglages décident de ce tirage :

- la `temperature` divise les scores avant de les transformer en probabilités : basse
  (0,2), le jeton le mieux noté gagne presque toujours, le texte est sage et répétitif ;
  haute (1,5), les probabilités s'aplatissent, le texte devient varié puis incohérent ;
  0 veut dire « glouton » : on prend toujours le jeton le mieux noté, sans hasard ;
- `top_k` ne garde que les k jetons les mieux notés et ignore tous les autres, ce qui évite de
  tomber sur un jeton très improbable (0 : pas de limite) ;
- la `graine` fixe le hasard : même modèle, même début, mêmes réglages, même graine, même texte.
"""

import torch

from forge.modele.transformer import Transformer


@torch.no_grad()
def generer(
    modele: Transformer,
    ids: list[int],
    n_nouveaux: int,
    temperature: float = 0.8,
    top_k: int = 50,
    graine: int = 0,
    arret: int | None = None,
) -> list[int]:
    """Prolonge `ids` de `n_nouveaux` jetons au plus, et renvoie SEULEMENT les nouveaux.

    - `ids` : le début du texte, en identifiants de jetons (jamais vide, jamais modifié) ;
    - `n_nouveaux` : nombre maximal de jetons à produire ;
    - `temperature` : 0 pour le choix glouton, sinon plus elle est haute, plus le texte varie ;
    - `top_k` : on ne tire que parmi les `top_k` jetons les mieux notés (0 : tous) ;
    - `graine` : graine du hasard, propre à cet appel (le hasard global de PyTorch n'est ni
      lu ni modifié) ;
    - `arret` : un jeton qui termine la génération ; il est inclus dans le résultat, et rien
      ne le suit. Si on le tire, on s'arrête là, même avant `n_nouveaux`.

    Le modèle ne lit que ses `longueur_contexte` derniers jetons : quand le texte devient plus
    long, le début est oublié. Pendant l'appel le modèle passe en mode évaluation, puis chaque
    sous-module retrouve le mode qu'il avait, même en cas d'erreur. Aucun gradient n'est gardé.

    Pas de cache des calculs précédents : chaque pas relit tout le contexte. C'est simple et
    exact ; ça suffit pour essayer le modèle, et ça devient lent sur de très longs textes.
    """
    config = modele.config
    if n_nouveaux < 0:
        raise ValueError(f"`n_nouveaux` vaut {n_nouveaux} : il doit être 0 ou plus.")
    if not temperature >= 0:
        raise ValueError(
            f"`temperature` vaut {temperature} : elle doit être 0 (choix glouton) ou plus."
        )
    if top_k < 0:
        raise ValueError(f"`top_k` vaut {top_k} : il doit être 0 (pas de limite) ou plus.")
    if len(ids) == 0:
        raise ValueError(
            "Le texte de départ est vide : donne au moins un jeton, par exemple "
            "`<|debut_texte|>`."
        )
    hors = [t for t in ids if not 0 <= t < config.taille_vocabulaire]
    if hors:
        raise ValueError(
            f"Le jeton {hors[0]} n'est pas dans le vocabulaire (0 à "
            f"{config.taille_vocabulaire - 1}). Vérifie que le texte a été découpé avec le "
            "bon tokenizer."
        )

    peripherique = next(modele.parameters()).device
    hasard = torch.Generator(device=peripherique)
    hasard.manual_seed(graine)

    modes = {module: module.training for module in modele.modules()}
    modele.eval()
    try:
        texte = list(ids)
        nouveaux: list[int] = []
        for _ in range(n_nouveaux):
            contexte = torch.tensor([texte[-config.longueur_contexte :]], device=peripherique)
            logits, _ = modele(contexte)
            scores = logits[0, -1].float()  # les scores de la suite du dernier jeton
            if temperature == 0:
                suivant = int(scores.argmax())
            else:
                scores = scores / temperature
                if 0 < top_k < scores.shape[0]:
                    seuil = torch.topk(scores, top_k).values[-1]
                    scores = scores.masked_fill(scores < seuil, float("-inf"))
                probabilites = torch.softmax(scores, dim=-1)
                suivant = int(torch.multinomial(probabilites, 1, generator=hasard))
            texte.append(suivant)
            nouveaux.append(suivant)
            if arret is not None and suivant == arret:
                break
        return nouveaux
    finally:
        for module, mode in modes.items():
            module.training = mode
