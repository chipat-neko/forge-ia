"""Nettoyage des textes et empreintes pour écarter les doublons.

Un texte nettoyé est en forme NFC, avec des fins de ligne `\\n`, sans caractère de
contrôle (sauf `\\n` et `\\t`) ni espace en fin de texte, et d'au moins 200 caractères.
"""

import hashlib
import re
import unicodedata

# Sous cette longueur (en caractères, une fois nettoyé), un texte n'apprend rien : écarté.
LONGUEUR_MINIMALE = 200

# Caractères de contrôle retirés : tout sauf \n (0x0A) et \t (0x09), donc aussi \r seul, les
# contrôles C0 (0x00 à 0x1F), 0x7F et les contrôles C1 (0x80 à 0x9F). S'y ajoutent les
# moitiés de paires de substitution (U+D800 à U+DFFF), qui ne s'écrivent pas en UTF-8.
_CONTROLES = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f\ud800-\udfff]")


def _normaliser(texte: str) -> str:
    """Les transformations du nettoyage, sans le seuil de longueur.

    Les contrôles partent avant la forme NFC : un contrôle entre une lettre et son accent
    combinant les séparerait, et le texte nettoyé ne serait plus en forme NFC. Dans cet
    ordre, nettoyer un texte déjà nettoyé ne change rien, donc son empreinte non plus.
    """
    texte = texte.replace("\r\n", "\n")
    texte = _CONTROLES.sub("", texte)
    texte = unicodedata.normalize("NFC", texte)
    return texte.rstrip()


def nettoyer(texte: str) -> str | None:
    """Nettoie un texte ; renvoie `None` s'il fait moins de 200 caractères une fois nettoyé."""
    texte = _normaliser(texte)
    if len(texte) < LONGUEUR_MINIMALE:
        return None
    return texte


def empreinte_du_texte_nettoye(texte_nettoye: str) -> str:
    """SHA-1 en hexadécimal d'un texte déjà nettoyé (pas de nettoyage de plus)."""
    return hashlib.sha1(texte_nettoye.encode("utf-8"), usedforsecurity=False).hexdigest()


def empreinte(texte: str) -> str:
    """SHA-1 en hexadécimal du texte nettoyé : deux textes qui se nettoient pareil ont la même."""
    return empreinte_du_texte_nettoye(_normaliser(texte))
