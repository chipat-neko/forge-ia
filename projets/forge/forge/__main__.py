"""Point d'entrée en ligne de commande : `python -m forge <commande>`.

Les commandes `donnees`, `tokenizer`, `encoder`, `mesurer`, `entrainer`,
`evaluer` et `suivi` s'y branchent une par une, au fil des tâches du plan
(chacune ajoute son sous-parseur dans `construire_parseur`). Déjà là :
`donnees`, `tokenizer`, `encoder` et `entrainer`.
"""

import argparse
import os
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


def _commande_donnees(choix: argparse.Namespace) -> int:
    """`forge donnees` : télécharge les trois sources, dans les parts du mélange."""
    # Imports ici : les autres commandes n'ont pas besoin des données.
    from forge.chemins import PlaceInsuffisante
    from forge.donnees import telechargement
    from forge.donnees.melange import repartir
    from forge.donnees.sources import SOURCES

    def journal(message: str) -> None:
        print(message, flush=True)

    # Cette commande a besoin du réseau. Si la session coupe Hugging Face (variable
    # `HF_HUB_OFFLINE=1`, souvent posée pour les autres projets), on la lève pour ce
    # processus seulement, avant que `datasets` ne lise la variable à son import.
    for variable in ("HF_HUB_OFFLINE", "HF_DATASETS_OFFLINE"):
        if os.environ.get(variable, "").strip().upper() in {"1", "ON", "YES", "TRUE"}:
            journal(f"{variable} est à 1 : levé pour ce téléchargement seulement, qui a besoin du réseau.")
            os.environ[variable] = "0"
    racine = telechargement.dossier_des_textes(Path(choix.dossier))
    budgets = repartir(choix.octets)
    for nom, octets in budgets.items():
        journal(f"{nom} : {telechargement.en_mo(octets)} Mo de texte visés, dans {racine / nom}.")
        try:
            telechargement.telecharger(SOURCES[nom], octets, racine / nom, journal=journal)
        except PlaceInsuffisante as erreur:
            print(f"Erreur : {erreur}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print(
                f"Interrompu pendant « {nom} ». "
                "Relance la même commande : seul le fragment en cours sera relu.",
                file=sys.stderr,
            )
            return 130
        except Exception as erreur:  # réseau coupé, Hugging Face indisponible, disque…
            print(
                f"Erreur pendant le téléchargement de « {nom} » ({type(erreur).__name__}) : {erreur}\n"
                "Si le réseau ou Hugging Face est en cause, relance la même commande : elle "
                "reprendra au dernier fragment écrit, sans doublon.",
                file=sys.stderr,
            )
            return 1
    print(f"Textes prêts dans {racine}.")
    return 0


def _ajouter_donnees(sous_parseurs) -> None:
    commande = _nouvelle_commande(
        sous_parseurs,
        "donnees",
        "Télécharge en flux le français du web, Wikipédia et du code Python, avec reprise.",
    )
    commande.add_argument(
        "--octets",
        required=True,
        type=taille_en_octets,
        metavar="TAILLE",
        help="volume total de texte, par exemple 300M, réparti selon le mélange (75 %% web, 10 %% Wikipédia, 15 %% code)",
    )
    commande.add_argument(
        "--dossier",
        required=True,
        metavar="NOM",
        help="nom du dossier, sous FORGE_DONNEES/textes (celui de « forge tokenizer --donnees »)",
    )
    commande.set_defaults(fonction=_commande_donnees)


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


def _commande_encoder(choix: argparse.Namespace) -> int:
    """`forge encoder` : encode les textes téléchargés en fragments de jetons, en parallèle."""
    # Imports ici : les autres commandes n'ont pas besoin de l'encodage.
    from forge.chemins import PlaceInsuffisante, racine_donnees
    from forge.donnees import jetons
    from forge.donnees.melange import MELANGE_PAR_DEFAUT
    from forge.donnees.telechargement import dossier_des_textes
    from forge.tokenizer.apprentissage import DonneesManquantes, verifier_dossier
    from forge.tokenizer.bpe_octets import TokenizerOctets

    def journal(message: str) -> None:
        print(message, flush=True)

    racine = dossier_des_textes(Path(choix.donnees))
    sortie = racine_donnees() / "jetons" / Path(choix.donnees).name
    try:
        verifier_dossier(racine)  # chaque source est là, avec son .complet
        tokenizer = TokenizerOctets.charger(choix.tokenizer)
        resume = jetons.encoder_corpus(
            [racine / source for source in MELANGE_PAR_DEFAUT], tokenizer, sortie, choix.processus, journal
        )
    except (DonneesManquantes, PlaceInsuffisante, FileNotFoundError, ValueError) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(
            "Interrompu. Relance la même commande : les fragments déjà encodés sont gardés, "
            "seuls ceux en cours seront refaits.",
            file=sys.stderr,
        )
        return 130
    except Exception as erreur:  # disque, mémoire, processus tué…
        print(
            f"Erreur pendant l'encodage ({type(erreur).__name__}) : {erreur}\n"
            "Relance la même commande : elle reprendra au dernier fragment encodé.",
            file=sys.stderr,
        )
        return 1
    octets_par_jeton = f"{resume['octets_par_jeton']:.2f}".replace(".", ",")
    print(
        f"Jetons prêts dans {sortie} : {resume['jetons_train']} jetons d'entraînement, "
        f"{resume['jetons_val']} de validation, {octets_par_jeton} octets par jeton."
    )
    return 0


def _ajouter_encoder(sous_parseurs) -> None:
    commande = _nouvelle_commande(
        sous_parseurs,
        "encoder",
        "Encode les textes téléchargés en fragments de jetons (uint16), en parallèle, avec reprise.",
    )
    commande.add_argument(
        "--donnees",
        required=True,
        metavar="NOM",
        help="dossier des textes, sous FORGE_DONNEES/textes (celui de « forge donnees --dossier »)",
    )
    commande.add_argument(
        "--tokenizer",
        required=True,
        type=Path,
        metavar="CHEMIN",
        help="fichier JSON du tokenizer (celui de « forge tokenizer --sortie »)",
    )
    commande.add_argument(
        "--processus",
        type=int,
        default=None,
        metavar="N",
        help="nombre de processus qui encodent en même temps (tous les cœurs par défaut)",
    )
    commande.set_defaults(fonction=_commande_encoder)


def _commande_entrainer(choix: argparse.Namespace) -> int:
    """`forge entrainer` : entraîne ton IA ; Ctrl+C met en pause, `--reprendre` repart de là."""
    # Imports ici : PyTorch est long à charger, les autres commandes n'en ont pas besoin.
    from forge.chemins import PlaceInsuffisante
    from forge.entrainement import CompilationImpossible, entrainer, lire_config
    from forge.tokenizer.apprentissage import DonneesManquantes

    reprise = f"python -m forge entrainer --config {choix.config} --reprendre"
    try:
        entrainer(lire_config(choix.config), reprendre=choix.reprendre)
    except PlaceInsuffisante as erreur:
        print(f"Erreur : {erreur}\nUne fois la place libérée : {reprise}", file=sys.stderr)
        return 1
    except (FileExistsError, FileNotFoundError, DonneesManquantes, CompilationImpossible, ValueError) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(
            "Arrêt immédiat par Ctrl+C : le pas en cours est perdu, la dernière sauvegarde "
            f"complète reste bonne. Pour reprendre : {reprise}",
            file=sys.stderr,
        )
        return 130
    return 0


def _ajouter_entrainer(sous_parseurs) -> None:
    commande = _nouvelle_commande(
        sous_parseurs,
        "entrainer",
        "Entraîne ton IA sur les jetons encodés. Ctrl+C met en pause (avec sauvegarde) ; "
        "--reprendre repart de la dernière sauvegarde.",
    )
    commande.add_argument(
        "--config",
        required=True,
        metavar="FICHIER",
        help="fichier TOML de l'entraînement, par exemple configs/mini.toml",
    )
    commande.add_argument(
        "--reprendre",
        action="store_true",
        help="reprendre à la dernière sauvegarde (après une pause, un plantage ou une coupure)",
    )
    commande.set_defaults(fonction=_commande_entrainer)


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
    _ajouter_donnees(sous_parseurs)
    _ajouter_tokenizer(sous_parseurs)
    _ajouter_encoder(sous_parseurs)
    _ajouter_entrainer(sous_parseurs)
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
