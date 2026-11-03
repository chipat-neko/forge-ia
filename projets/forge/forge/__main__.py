"""Point d'entrée en ligne de commande : `python -m forge <commande>`.

Squelette pour l'instant : les commandes `donnees`, `tokenizer`, `encoder`,
`mesurer`, `entrainer`, `evaluer` et `suivi` s'y branchent une par une, au fil
des tâches du plan (chacune ajoute son sous-parseur dans `construire_parseur`).
"""

import argparse
import sys


class _AideFrancaise(argparse.HelpFormatter):
    """Met en français le seul libellé que `argparse` ajoute lui-même à l'aide."""

    def add_usage(self, usage, actions, groups, prefix=None):
        if prefix is None:
            prefix = "Utilisation : "
        super().add_usage(usage, actions, groups, prefix)


def construire_parseur() -> argparse.ArgumentParser:
    """Construit le parseur principal et ses sous-commandes."""
    parseur = argparse.ArgumentParser(
        prog="forge",
        description=(
            "La forge de « ton IA » : prépare les données, entraîne et évalue "
            "un petit modèle de langage qui lit et écrit le français et le code."
        ),
        formatter_class=_AideFrancaise,
        add_help=False,
    )
    # Titres des sections d'aide : `argparse` les écrit en anglais par défaut.
    parseur._positionals.title = "Commandes"
    parseur._optionals.title = "Options"
    parseur.add_argument(
        "-h",
        "--help",
        action="help",
        help="Affiche cette aide, puis quitte.",
    )
    # Pour ajouter une commande : garder la valeur renvoyée ici (`sous_parseurs`),
    # puis `sous_parseurs.add_parser("donnees", …)`. Chaque commande règle sa
    # fonction avec `set_defaults(fonction=…)` : elle reçoit les arguments lus
    # et renvoie le code de sortie.
    parseur.add_subparsers(dest="commande", metavar="<commande>")
    return parseur


def main(arguments: list[str] | None = None) -> int:
    """Lance la commande demandée ; renvoie le code de sortie du programme."""
    parseur = construire_parseur()
    choix = parseur.parse_args(arguments)
    fonction = getattr(choix, "fonction", None)
    if fonction is None:
        parseur.print_help()
        return 0
    return fonction(choix)


if __name__ == "__main__":
    sys.exit(main())
