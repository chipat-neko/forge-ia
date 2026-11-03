"""Point d'entrée en ligne de commande : `python -m forge <commande>`.

Les commandes `donnees`, `tokenizer`, `compression`, `encoder`, `mesurer`,
`entrainer`, `evaluer` et `suivi` s'y branchent une par une, au fil des tâches
du plan (chacune ajoute son sous-parseur dans `construire_parseur`). Déjà là :
`donnees`, `tokenizer`, `compression`, `encoder`, `mesurer`, `entrainer` et `evaluer`.
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


def parts_en_octets(texte: str) -> dict[str, int]:
    """Lit « web_fr=400M,wikipedia_fr=350M,code_python=300M » : un volume par source.

    Les trois sources du mélange doivent y être, chacune une fois ; le résultat suit l'ordre du
    mélange (c'est l'ordre du téléchargement). Chaque taille se lit comme `taille_en_octets`.
    """
    from forge.donnees.melange import MELANGE_PAR_DEFAUT

    exemple = "web_fr=400M,wikipedia_fr=350M,code_python=300M"
    lues: dict[str, int] = {}
    for morceau in (m for m in texte.split(",") if m.strip()):
        nom, egal, taille = morceau.partition("=")
        nom = nom.strip()
        if not egal:
            raise argparse.ArgumentTypeError(
                f"part illisible : {morceau.strip()!r}. Chaque part s'écrit nom=taille, par exemple {exemple}."
            )
        if nom not in MELANGE_PAR_DEFAUT:
            raise argparse.ArgumentTypeError(
                f"source inconnue : {nom!r}. Les sources sont {', '.join(MELANGE_PAR_DEFAUT)}."
            )
        if nom in lues:
            raise argparse.ArgumentTypeError(f"la source {nom!r} est écrite deux fois.")
        octets = taille_en_octets(taille)
        if octets <= 0:
            raise argparse.ArgumentTypeError(f"la taille de {nom!r} doit être positive, pas {taille.strip()!r}.")
        lues[nom] = octets
    absentes = [nom for nom in MELANGE_PAR_DEFAUT if nom not in lues]
    if absentes:
        raise argparse.ArgumentTypeError(
            f"il manque la source {', '.join(absentes)}. Donne un volume pour chacune des trois, "
            f"par exemple {exemple}."
        )
    return {nom: lues[nom] for nom in MELANGE_PAR_DEFAUT}


def _nouvelle_commande(sous_parseurs, nom: str, aide: str) -> argparse.ArgumentParser:
    """Ajoute une sous-commande, avec son aide en français."""
    commande = sous_parseurs.add_parser(
        nom, help=aide, description=aide, formatter_class=_AideFrancaise, add_help=False
    )
    commande._optionals.title = "Options"
    commande.add_argument("-h", "--help", action="help", help="Affiche cette aide, puis quitte.")
    return commande


def _lever_le_mode_hors_ligne(journal, pour: str) -> None:
    """Lève, pour ce processus seulement, le mode hors ligne de Hugging Face (`HF_HUB_OFFLINE=1`).

    Cette variable est souvent posée pour les autres projets (c'est le cas sur ce PC). Les
    commandes qui ont besoin du réseau (`donnees`, `evaluer` pour FrenchBench) la lèvent ici,
    avant que `datasets` ne la lise à son import. `pour` complète le message : « levé pour … seulement ».
    """
    for variable in ("HF_HUB_OFFLINE", "HF_DATASETS_OFFLINE"):
        if os.environ.get(variable, "").strip().upper() in {"1", "ON", "YES", "TRUE"}:
            journal(f"{variable} est à 1 : levé pour {pour} seulement, qui a besoin du réseau.")
            os.environ[variable] = "0"


def _commande_donnees(choix: argparse.Namespace) -> int:
    """`forge donnees` : télécharge les trois sources, dans les parts du mélange."""
    # Imports ici : les autres commandes n'ont pas besoin des données.
    from forge.chemins import PlaceInsuffisante
    from forge.donnees import telechargement
    from forge.donnees.melange import repartir
    from forge.donnees.sources import SOURCES

    def journal(message: str) -> None:
        print(message, flush=True)

    # Cette commande a besoin du réseau : si la session coupe Hugging Face, on le permet pour ce processus.
    _lever_le_mode_hors_ligne(journal, "ce téléchargement")
    if (choix.octets is None) == (choix.parts is None):
        choix.parseur.error(
            "donne un seul des deux : --octets TAILLE (réparti selon le mélange) "
            "ou --parts (un volume par source)."
        )
    racine = telechargement.dossier_des_textes(Path(choix.dossier))
    budgets = repartir(choix.octets) if choix.parts is None else choix.parts
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
        type=taille_en_octets,
        default=None,
        metavar="TAILLE",
        help="volume total de texte, par exemple 300M, réparti selon le mélange (75 %% web, 10 %% Wikipédia, 15 %% code)",
    )
    commande.add_argument(
        "--parts",
        type=parts_en_octets,
        default=None,
        metavar="SOURCE=TAILLE,…",
        help=(
            "au lieu de --octets, un volume par source, par exemple "
            "web_fr=400M,wikipedia_fr=350M,code_python=300M (les trois sources, dans n'importe "
            "quel ordre) : pour un volume hors mélange, comme de quoi trouver 1 Mo de validation par source"
        ),
    )
    commande.add_argument(
        "--dossier",
        required=True,
        metavar="NOM",
        help="nom du dossier, sous FORGE_DONNEES/textes (celui de « forge tokenizer --donnees »)",
    )
    commande.set_defaults(fonction=_commande_donnees, parseur=commande)


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


def _commande_compression(choix: argparse.Namespace) -> int:
    """`forge compression` : mesure les octets par jeton d'un tokenizer sur les textes téléchargés."""
    # Imports ici : les autres commandes n'ont pas besoin de la mesure.
    from forge.donnees.telechargement import dossier_des_textes
    from forge.tokenizer.apprentissage import DonneesManquantes
    from forge.tokenizer.bpe_octets import TokenizerOctets
    from forge.tokenizer.compression import mesurer_compression, tableau_de_compression

    try:
        tokenizer = TokenizerOctets.charger(choix.tokenizer)
        resultat = mesurer_compression(
            tokenizer, dossier_des_textes(Path(choix.donnees)), choix.octets, choix.partie
        )
    except (DonneesManquantes, FileNotFoundError, ValueError) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Mesure interrompue : rien n'est écrit. Relance la même commande.", file=sys.stderr)
        return 130
    print(tableau_de_compression(resultat))
    return 0


def _ajouter_compression(sous_parseurs) -> None:
    commande = _nouvelle_commande(
        sous_parseurs,
        "compression",
        "Mesure la compression du tokenizer (octets par jeton) sur ~1 Mo de documents de "
        "validation de chaque source, et pour le mélange.",
    )
    commande.add_argument(
        "--donnees",
        required=True,
        metavar="NOM",
        help="dossier des textes, sous FORGE_DONNEES/textes (celui de « forge donnees --dossier »)",
    )
    commande.add_argument(
        "--tokenizer",
        type=Path,
        default=Path(__file__).parent / "ressources" / "tokenizer-ton-ia-v1.json",
        metavar="CHEMIN",
        help="fichier JSON du tokenizer à mesurer (celui du dépôt par défaut)",
    )
    commande.add_argument(
        "--octets",
        type=taille_en_octets,
        default=1024**2,
        metavar="TAILLE",
        help="volume de texte à mesurer par source (1M par défaut), en documents entiers",
    )
    commande.add_argument(
        "--partie",
        choices=("validation", "apprentissage"),
        default="validation",
        help="documents mesurés : « validation » (mis de côté, jamais appris ; par défaut) "
        "ou « apprentissage » (tous les autres, pour comparer)",
    )
    commande.set_defaults(fonction=_commande_compression)


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
    except (
        FileExistsError,
        FileNotFoundError,
        PermissionError,
        DonneesManquantes,
        CompilationImpossible,
        ValueError,
    ) as erreur:
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


PRESETS_MESURES = "petit,moyen,grand,tres_grand"


def _noms_de_presets(texte: str) -> list[str]:
    """Lit « petit,moyen » : des noms de tailles de ton IA, séparés par des virgules."""
    from forge.modele import PRESETS

    noms = [nom.strip() for nom in texte.split(",") if nom.strip()]
    inconnus = [nom for nom in noms if nom not in PRESETS]
    if not noms or inconnus:
        raise argparse.ArgumentTypeError(
            f"taille inconnue : {', '.join(inconnus) or repr(texte)}. Les tailles sont {', '.join(PRESETS)} "
            "(séparées par des virgules)."
        )
    return noms


def _entier_strictement_positif(texte: str) -> int:
    try:
        valeur = int(texte)
    except ValueError:
        valeur = 0
    if valeur < 1:
        raise argparse.ArgumentTypeError(f"nombre illisible : {texte!r}. Écris un entier d'au moins 1.")
    return valeur


def _nombre_strictement_positif(texte: str) -> float:
    try:
        valeur = float(texte)
    except ValueError:
        valeur = 0.0
    if not valeur > 0:
        raise argparse.ArgumentTypeError(f"nombre illisible : {texte!r}. Écris un nombre plus grand que 0.")
    return valeur


def _commande_mesurer(choix: argparse.Namespace) -> int:
    """`forge mesurer` : essai chronométré de l'entraînement sur la carte graphique et le processeur."""
    # Imports ici : PyTorch est long à charger, les autres commandes n'en ont pas besoin.
    import json

    import torch

    from forge import mesure

    def journal(message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    try:
        resultats = mesure.mesurer_presets(
            choix.presets, choix.pas, choix.cpu_secondes, choix.cpu_micro_lot, choix.gpu_accumulation, journal
        )
    except mesure.GpuOccupe as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1
    except torch.cuda.OutOfMemoryError:
        print(
            "Erreur : la carte graphique manque de mémoire, même pour un micro-lot de 1. Ferme les jeux ou "
            "logiciels 3D ouverts, puis relance la même commande.",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print("Mesure interrompue : rien n'est écrit. Relance la même commande.", file=sys.stderr)
        return 130
    tableaux = mesure.tableaux_markdown(resultats)
    print(tableaux)
    try:
        if choix.json:
            Path(choix.json).write_text(json.dumps(resultats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if choix.tableau:
            Path(choix.tableau).write_text(tableaux, encoding="utf-8")
    except OSError as erreur:
        print(f"Erreur : impossible d'écrire le résultat ({erreur}).", file=sys.stderr)
        return 1
    return 0


def _ajouter_mesurer(sous_parseurs) -> None:
    commande = _nouvelle_commande(
        sous_parseurs,
        "mesurer",
        "Essai chronométré de l'entraînement : jetons par seconde sur la carte graphique et sur le "
        "processeur (tous les fils), durée pour 20 jetons par paramètre et place sur le disque.",
    )
    commande.add_argument(
        "--presets",
        type=_noms_de_presets,
        default=PRESETS_MESURES,
        metavar="NOM,…",
        help=f"tailles à mesurer, séparées par des virgules ({PRESETS_MESURES} par défaut)",
    )
    commande.add_argument(
        "--pas",
        type=_entier_strictement_positif,
        default=20,
        metavar="N",
        help="pas d'entraînement chronométrés, après 2 pas d'échauffement (20 par défaut)",
    )
    commande.add_argument(
        "--cpu-secondes",
        type=_nombre_strictement_positif,
        default=120.0,
        metavar="S",
        help="durée maximale de la mesure sur le processeur, par taille, après 1 pas d'échauffement (120 par défaut)",
    )
    commande.add_argument(
        "--cpu-micro-lot",
        type=_entier_strictement_positif,
        default=2,
        metavar="N",
        help="lignes traitées d'un coup sur le processeur (2 par défaut)",
    )
    commande.add_argument(
        "--gpu-accumulation",
        type=_entier_strictement_positif,
        default=8,
        metavar="N",
        help="micro-lots accumulés par pas sur la carte (8 par défaut) : l'écrêtage et le pas d'AdamW "
        "pèsent alors comme dans un vrai entraînement, où un pas accumule beaucoup de micro-lots",
    )
    commande.add_argument(
        "--json", type=Path, default=None, metavar="FICHIER", help="écrit aussi tous les chiffres bruts dans ce fichier JSON"
    )
    commande.add_argument(
        "--tableau", type=Path, default=None, metavar="FICHIER", help="écrit aussi les tableaux dans ce fichier Markdown"
    )
    commande.set_defaults(fonction=_commande_mesurer)


def _entier_positif_ou_nul(texte: str) -> int:
    try:
        valeur = int(texte)
    except ValueError:
        valeur = -1
    if valeur < 0:
        raise argparse.ArgumentTypeError(f"nombre de questions illisible : {texte!r}. Écris un entier, 0 ou plus.")
    return valeur


def _appareil(texte: str) -> str:
    if texte not in ("cuda", "cpu"):
        raise argparse.ArgumentTypeError(f'appareil inconnu : {texte!r}. Écris "cuda" (carte graphique) ou "cpu".')
    return texte


def _sortie_par_defaut_de_l_evaluation(sauvegarde: Path) -> Path:
    """`<entraînement>/evaluation/<nom de la sauvegarde>/` : une sauvegarde n'écrase pas le rapport d'une autre."""
    dossier = sauvegarde if sauvegarde.is_dir() else sauvegarde.parent
    racine = dossier.parent if dossier.name == "sauvegardes" else dossier
    return racine / "evaluation" / ("derniere" if sauvegarde.is_dir() else sauvegarde.stem)


def _commande_evaluer(choix: argparse.Namespace) -> int:
    """`forge evaluer` : perte, perplexité, bits par octet, QCM français et échantillons, en rapport."""

    def journal(message: str) -> None:
        print(message, flush=True)

    # FrenchBench se télécharge : on permet le réseau avant tout import de `datasets`.
    if choix.qcm != 0:
        _lever_le_mode_hors_ligne(journal, "le chargement de FrenchBench")
    # Imports ici : PyTorch est long à charger, les autres commandes n'en ont pas besoin.
    import torch

    from forge.chemins import PlaceInsuffisante
    from forge.evaluation.rapport import evaluer, resume_court
    from forge.tokenizer.apprentissage import DonneesManquantes

    sauvegarde = Path(choix.sauvegarde)
    sortie = choix.sortie or _sortie_par_defaut_de_l_evaluation(sauvegarde)
    try:
        rapport = evaluer(sauvegarde, Path(choix.donnees), choix.tokenizer, sortie, choix.qcm, choix.appareil)
    except (FileNotFoundError, PermissionError, PlaceInsuffisante, DonneesManquantes, ValueError) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1
    except torch.cuda.OutOfMemoryError:
        print(
            "Erreur : la carte graphique manque de mémoire pour l'évaluation. Ferme les jeux ou logiciels 3D "
            "ouverts (et l'entraînement, s'il tourne), ou évalue sur le processeur avec --appareil cpu.",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print("Évaluation interrompue : aucun rapport écrit. Relance la même commande.", file=sys.stderr)
        return 130
    print(resume_court(rapport))
    print(f"Rapport : {sortie / 'rapport.md'}")
    return 0


def _ajouter_evaluer(sous_parseurs) -> None:
    commande = _nouvelle_commande(
        sous_parseurs,
        "evaluer",
        "Évalue une sauvegarde de ton IA : perte, perplexité, bits par octet, QCM français et "
        "échantillons, dans rapport.json et rapport.md.",
    )
    commande.add_argument(
        "--sauvegarde",
        required=True,
        metavar="FICHIER",
        help="sauvegarde de l'entraînement (etape-*.pt ou meilleur.pt), ou son dossier sauvegardes/ (dernière étape)",
    )
    commande.add_argument(
        "--donnees",
        required=True,
        metavar="NOM",
        help="dossier des jetons, sous FORGE_DONNEES/jetons (celui de « forge encoder --donnees »), ou un chemin absolu",
    )
    commande.add_argument(
        "--tokenizer",
        type=Path,
        default=Path(__file__).parent / "ressources" / "tokenizer-ton-ia-v1.json",
        metavar="CHEMIN",
        help="fichier JSON du tokenizer de l'entraînement (celui du dépôt par défaut)",
    )
    commande.add_argument(
        "--sortie",
        type=Path,
        default=None,
        metavar="DOSSIER",
        help="dossier des rapports (par défaut : evaluation/<nom de la sauvegarde>/ à côté de sauvegardes/)",
    )
    commande.add_argument(
        "--qcm",
        type=_entier_positif_ou_nul,
        default=None,
        metavar="N",
        help="nombre de questions de chaque test FrenchBench (toutes par défaut ; 0 : aucun QCM, sans réseau)",
    )
    commande.add_argument(
        "--appareil",
        type=_appareil,
        default=None,
        metavar="cuda|cpu",
        help="où calculer (la carte graphique si PyTorch la voit, sinon le processeur)",
    )
    commande.set_defaults(fonction=_commande_evaluer)


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
    _ajouter_compression(sous_parseurs)
    _ajouter_encoder(sous_parseurs)
    _ajouter_mesurer(sous_parseurs)
    _ajouter_entrainer(sous_parseurs)
    _ajouter_evaluer(sous_parseurs)
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
