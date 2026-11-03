"""Point d'entrée en ligne de commande : `python -m forge <commande>`.

Les commandes `donnees`, `tokenizer`, `encoder`, `mesurer`, `entrainer`,
`evaluer` et `suivi` s'y branchent une par une, au fil des tâches du plan
(chacune ajoute son sous-parseur dans `construire_parseur`). Déjà là :
`tokenizer`.
"""

import argparse
import re
import sys
from pathlib import Path

# Multiplicateurs des tailles écrites « 300M » : comme l'Explorateur de Windows
# (et `forge.chemins`), un Mo vaut ici 1024² octets.
_MULTIPLICATEURS = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}


class _AideFrancaise(argparse.HelpFormatter):
    """Met en français le seul libellé que `argparse` ajoute lui-même à l'aide."""

    def add_usage(self, usage, actions, groups, prefix=None):
        if prefix is None:
            prefix = "Utilisation : "
        super().add_usage(usage, actions, groups, prefix)


def taille_en_octets(texte: str) -> int:
    """Lit une taille comme « 300M » : K, M et G valent 1024, 1024² et 1024³ octets.

    Un « o » final est accepté (« 300Mo ») ; un nombre seul compte en octets.
    """
    lu = re.fullmatch(r"\s*(\d+)\s*([KMG]?)O?\s*", texte.upper())
    if lu is None:
        raise argparse.ArgumentTypeError(
            f"taille illisible : {texte!r}. Écris un nombre d'octets, suivi au besoin de "
            "K, M ou G (par exemple 300M)."
        )
    return int(lu.group(1)) * _MULTIPLICATEURS[lu.group(2)]


def _nouvelle_commande(sous_parseurs, nom: str, aide: str) -> argparse.ArgumentParser:
    """Ajoute une sous-commande, avec son aide en français."""
    commande = sous_parseurs.add_parser(
        nom, help=aide, description=aide, formatter_class=_AideFrancaise, add_help=False
    )
    commande._optionals.title = "Options"
    commande.add_argument("-h", "--help", action="help", help="Affiche cette aide, puis quitte.")
    return commande


def _commande_tokenizer(choix: argparse.Namespace) -> int:
    """`forge tokenizer` : apprend le tokenizer sur les textes téléchargés."""
    # Import ici : les autres commandes n'ont pas besoin du tokenizer.
    from forge.tokenizer.apprentissage import DonneesManquantes, apprendre_depuis_dossier

    def journal(message: str) -> None:
        print(message, flush=True)

    try:
        tokenizer = apprendre_depuis_dossier(
            Path(choix.donnees), choix.taille, choix.nom, choix.sortie, choix.octets_max, journal
        )
    except (DonneesManquantes, ValueError) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1
    print(
        f"Tokenizer « {tokenizer.nom} » enregistré dans {choix.sortie} : "
        f"{len(tokenizer.fusions)} fusions, {tokenizer.taille_vocabulaire} jetons en tout."
    )
    return 0


def _ajouter_tokenizer(sous_parseurs) -> None:
    commande = _nouvelle_commande(
        sous_parseurs,
        "tokenizer",
        "Apprend le tokenizer de ton IA (BPE sur les octets) sur les textes téléchargés.",
    )
    commande.add_argument(
        "--donnees",
        required=True,
        metavar="NOM",
        help="dossier des textes, sous FORGE_DONNEES/textes (celui de « forge donnees --dossier »)",
    )
    commande.add_argument(
        "--taille", type=int, default=32768, metavar="N", help="nombre total de jetons (32768 par défaut)"
    )
    commande.add_argument("--nom", default="ton-ia-v1", help="nom du tokenizer (ton-ia-v1 par défaut)")
    commande.add_argument(
        "--sortie", required=True, type=Path, metavar="CHEMIN", help="fichier JSON à écrire"
    )
    commande.add_argument(
        "--octets-max",
        type=taille_en_octets,
        default=None,
        metavar="TAILLE",
        help="volume de texte à lire, par exemple 300M (tout par défaut), réparti selon le mélange",
    )
    commande.set_defaults(fonction=_commande_tokenizer)


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
    # Pour ajouter une commande : `_nouvelle_commande(sous_parseurs, "donnees", …)`.
    # Chaque commande règle sa fonction avec `set_defaults(fonction=…)` : elle
    # reçoit les arguments lus et renvoie le code de sortie.
    sous_parseurs = parseur.add_subparsers(dest="commande", metavar="<commande>")
    _ajouter_tokenizer(sous_parseurs)
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
