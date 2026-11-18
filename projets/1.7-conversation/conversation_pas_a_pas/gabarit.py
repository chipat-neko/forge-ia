"""Le gabarit de conversation et le masque de perte, refaits à la main pour le chapitre 1.7.

Une conversation devient une suite de jetons (`forge.conversation.format.encoder_conversation`) :

    <|fin_texte|> <|systeme|> … <|fin_tour|> <|utilisateur|> … <|fin_tour|> <|assistant|> … <|fin_tour|>

et, pour chaque jeton, un booléen : « celui-ci est une cible apprise ». Seul ce que dit l'assistant
est appris, du jeton qui suit `<|assistant|>` jusqu'à son `<|fin_tour|>` compris. Les deux régions :

- `gabarit` : `montrer(tok, tours)` écrit la conversation jeton par jeton, avec son rôle et son masque ;
- `masque` : `perte_masquee_a_la_main(logits, cibles)` refait la perte d'affinage de forge : la moyenne
  des pertes des seules cibles apprises.

Le masque ne passe pas par les ids : un jeton « ordinaire » dont le texte imite `<|fin_tour|>` n'est pas le
jeton spécial (le tokenizer n'émet jamais de jeton spécial en lisant du texte). `montrer` s'appuie donc sur
les identifiants, jamais sur le texte.
"""

from collections.abc import Sequence
from pathlib import Path

import forge
import torch
from forge.conversation.format import Tour, encoder_conversation
from forge.tokenizer import TokenizerOctets
from torch import Tensor

# Le tokenizer figé de « ton IA », celui de forge.
TOKENIZER = Path(forge.__file__).resolve().parent / "ressources" / "tokenizer-ton-ia-v1.json"
IGNORE = -100  # la cible que la perte ne compte pas (la même que dans forge.affinage.jeu)
SAUT_DE_LIGNE = "␊"  # « ␊ » : un saut de ligne rendu visible

ROLES_PAR_JETON = {"<|systeme|>": "systeme", "<|utilisateur|>": "utilisateur", "<|assistant|>": "assistant"}


# region: gabarit
def montrer(tok: TokenizerOctets, tours: Sequence[Tour]) -> list[dict]:
    """La conversation, jeton par jeton : `id`, `texte` (visible), `role` et `appris`.

    `texte` est le texte du jeton, avec « ␊ » pour un saut de ligne ; pour un jeton spécial, c'est son
    nom. `role` dit qui parle : « debut » pour le premier jeton, `<|fin_texte|>`, puis le rôle du tour
    (le jeton de rôle et le `<|fin_tour|>` compris). `appris` vient de `encoder_conversation`.
    """
    exemple = encoder_conversation(tok, tours)
    role = "debut"
    jetons = []
    for identifiant, appris in zip(exemple.ids, exemple.appris):
        special = identifiant >= tok.premier_special
        texte = tok.octets_du_jeton(identifiant).decode("utf-8", errors="replace")
        if special and texte in ROLES_PAR_JETON:
            role = ROLES_PAR_JETON[texte]  # un nouveau tour commence
        jetons.append({"id": identifiant, "texte": texte.replace("\n", SAUT_DE_LIGNE), "role": role, "appris": appris})
    return jetons
# fin: gabarit


# region: masque
def perte_masquee_a_la_main(logits: Tensor, cibles: Tensor) -> float:
    """La perte d'un lot d'affinage : la moyenne de `-ln(probabilité)` sur les cibles apprises seulement.

    `logits` a la forme `[lot, positions, V]` et `cibles` `[lot, positions]` : le vrai jeton suivant, ou
    -100 là où rien n'est appris (la question, le bourrage, la frontière entre deux conversations). On
    additionne les pertes des cibles différentes de -100, et on divise par leur nombre : une réponse
    d'un mot pèse autant, par jeton, qu'une longue explication. Tout se calcule en float64.
    """
    logits = logits.double()
    apprises = cibles != IGNORE
    nombre = int(apprises.sum())
    if nombre == 0:
        raise ValueError("Aucune cible apprise dans ce lot : la perte masquée n'a rien à moyenner (0 ÷ 0).")
    plus_grand = logits.max(dim=-1, keepdim=True).values
    decales = logits - plus_grand
    log_somme = decales.exp().sum(dim=-1).log()  # ln de la somme des exponentielles
    choisis = decales.gather(-1, cibles.clamp(min=0)[..., None]).squeeze(-1)  # le score du vrai jeton
    pertes = log_somme - choisis  # -ln(proba) à chaque position
    return float(torch.where(apprises, pertes, torch.zeros_like(pertes)).sum() / nombre)
# fin: masque
