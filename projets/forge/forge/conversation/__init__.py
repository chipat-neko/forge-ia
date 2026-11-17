"""Le format de conversation de « ton IA » : gabarit, masque de perte, invite et lecture."""

from forge.conversation.format import (
    JETON_DE_DEBUT,
    ExempleMasque,
    Reponse,
    Tour,
    conversation_depuis_json,
    conversation_vers_json,
    encoder_conversation,
    invite_de_reponse,
    lire_reponse,
    verifier_conversation,
)

__all__ = [
    "JETON_DE_DEBUT",
    "ExempleMasque",
    "Reponse",
    "Tour",
    "conversation_depuis_json",
    "conversation_vers_json",
    "encoder_conversation",
    "invite_de_reponse",
    "lire_reponse",
    "verifier_conversation",
]
