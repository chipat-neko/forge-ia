"""Découpe un texte en ligne de commande.

Exemple (dans projets/1.3-tokenizer) :

    uv run python -m tokenizer_pedagogique "Les forgerons" --fusions 30
"""

import argparse
import sys

from tokenizer_pedagogique.bpe import TokenizerPedagogique, charger_corpus


def rendre_visible(texte: str) -> str:
    """Rend les caractères invisibles lisibles : espace en ␣, retour à la ligne en ↵."""
    return texte.replace(" ", "␣").replace("\n", "↵")


def principal() -> None:
    lecteur = argparse.ArgumentParser(
        prog="python -m tokenizer_pedagogique",
        description="Découpe un texte en jetons avec le tokenizer BPE pédagogique.",
    )
    lecteur.add_argument("texte", help="le texte à découper (entre guillemets)")
    lecteur.add_argument(
        "--fusions",
        type=int,
        default=30,
        help="nombre de fusions à rejouer (0 : lettre par lettre ; 30 par défaut)",
    )
    arguments = lecteur.parse_args()

    # La console Windows n'est pas toujours en UTF-8 : sans cela, « ␣ » ferait planter l'affichage.
    sys.stdout.reconfigure(encoding="utf-8")

    tokenizer = TokenizerPedagogique(charger_corpus())
    jetons = tokenizer.decouper(arguments.texte, arguments.fusions)

    print("|".join(rendre_visible(jeton.texte) for jeton in jetons))
    print("|".join("?" if jeton.id is None else str(jeton.id) for jeton in jetons))
    print(f"{len(jetons)} jetons avec {min(max(arguments.fusions, 0), len(tokenizer.fusions))} fusions")


if __name__ == "__main__":
    principal()
