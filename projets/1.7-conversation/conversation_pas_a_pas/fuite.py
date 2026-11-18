"""La fuite entre conversations d'une même rangée, avec et sans le masque par document.

Pour ne pas gaspiller de places, l'affinage range plusieurs conversations courtes dans une même rangée
(`forge.affinage.empaquetage.empaqueter`). Sans précaution, l'attention de la deuxième conversation
verrait la première : ses logits ne seraient plus ceux d'une conversation lue seule. Le modèle de forge
prend donc `documents`, le numéro de la conversation de chaque position, et chaque conversation ne voit
plus que la sienne (`forge.modele.transformer.masque_des_documents`).

`ecarts_de_fuite` le mesure sur un modèle minuscule tiré au hasard : l'écart maximal entre les logits de
B dans la rangée « A puis B » et ceux de B lue seule, avec le masque (presque rien : l'arrondi des
nombres) et sans (net : B a regardé A).
"""

import torch
from forge.conversation.format import Tour, encoder_conversation
from forge.modele import ConfigModele, Transformer
from forge.tokenizer import TokenizerOctets

from conversation_pas_a_pas.gabarit import TOKENIZER

# Un modèle minuscule, avec les poids de départ de forge (tirés au hasard, jamais entraînés).
CONFIG = ConfigModele(dim=32, couches=2, tetes=4, longueur_contexte=64)

CONVERSATION_A = [
    Tour("utilisateur", "Bonjour !"),
    Tour("assistant", "Bonjour, que veux-tu forger ?"),
]
CONVERSATION_B = [
    Tour("utilisateur", "Quelle est la capitale de la France ?"),
    Tour("assistant", "Paris."),
]


# region: fuite
@torch.no_grad()
def ecarts_de_fuite(graine: int = 0) -> dict:
    """L'écart maximal des logits de B, dans la rangée « A puis B », face à B lue seule.

    Rend `avec_masque` (avec `documents`) et `sans_masque` (sans), plus la taille de la rangée.
    Le modèle est tiré de `graine`.
    """
    tok = TokenizerOctets.charger(TOKENIZER)
    a = encoder_conversation(tok, CONVERSATION_A).ids
    b = encoder_conversation(tok, CONVERSATION_B).ids
    with torch.random.fork_rng():
        torch.manual_seed(graine)
        modele = Transformer(CONFIG).eval()

    rangee = torch.tensor([a + b])
    documents = torch.tensor([[0] * len(a) + [1] * len(b)])  # le numéro de la conversation de chaque position
    seule, _ = modele(torch.tensor([b]))
    avec, _ = modele(rangee, documents=documents)
    sans, _ = modele(rangee)
    # Les logits de B dans la rangée : les positions qui suivent A.
    return {
        "graine": graine,
        "jetons_a": len(a),
        "jetons_b": len(b),
        "avec_masque": float((avec[:, len(a):] - seule).abs().max()),
        "sans_masque": float((sans[:, len(a):] - seule).abs().max()),
    }
# fin: fuite
