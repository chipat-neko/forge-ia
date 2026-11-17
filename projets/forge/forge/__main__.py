"""Point d'entrée en ligne de commande : `python -m forge <commande>`.

Les commandes `donnees`, `tokenizer`, `compression`, `encoder`, `mesurer`,
`entrainer`, `evaluer`, `exporter`, `publication`, `suivi`, `conversations` et `problemes` s'y branchent une par une, au fil des
tâches du plan (chacune ajoute son sous-parseur dans `construire_parseur`). Toutes sont là.
"""

import argparse
import os
import re
import sys
import warnings
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


def _premiere_ligne(erreur: BaseException) -> str:
    """« RuntimeError : CUDA error: … » : le type et la première ligne d'une erreur imprévue, sans trace."""
    lignes = str(erreur).strip().splitlines()
    return f"{type(erreur).__name__} : {lignes[0] if lignes else 'sans message'}"


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
    from forge.erreurs import DonneesManquantes

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
        except (telechargement.EtatDuFluxRefuse, DonneesManquantes) as erreur:
            # Relancer tel quel échouerait de nouveau : le message dit quoi faire, rien d'autre.
            print(f"Erreur : {erreur}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print(
                f"Interrompu pendant « {nom} ». Relance la même commande : les fragments déjà écrits sont "
                "gardés. La reprise repart du fichier et du groupe de lignes où le flux s'était arrêté. "
                "Seul un téléchargement commencé avant cette version relit le flux depuis le début du jeu "
                "(18 minutes pour 15,6 millions de documents), tant qu'il n'a pas écrit de nouveau "
                "fragment : ensuite, ses reprises ne relisent rien non plus.",
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
    from forge.erreurs import DonneesManquantes
    from forge.tokenizer.apprentissage import apprendre_depuis_dossier

    def journal(message: str) -> None:
        print(message, flush=True)

    try:
        tokenizer = apprendre_depuis_dossier(
            Path(choix.donnees), choix.taille, choix.nom, choix.sortie, choix.octets_max, journal
        )
    except (DonneesManquantes, ValueError) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(
            f"Apprentissage interrompu : {choix.sortie} n'est écrit qu'à la fin, d'un coup, il n'a pas été "
            "touché. Relance la même commande : l'apprentissage repart du début.",
            file=sys.stderr,
        )
        return 130
    except Exception as erreur:  # disque plein ou débranché, mémoire…
        print(
            f"Erreur pendant l'apprentissage du tokenizer ({_premiere_ligne(erreur)}).\n"
            f"{choix.sortie} n'est jamais écrit à moitié. Vérifie la place sur le disque et le chemin de "
            "--sortie, puis relance la même commande : l'apprentissage repart du début.",
            file=sys.stderr,
        )
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
    from forge.erreurs import DonneesManquantes
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
    from forge.donnees.jetons import FragmentInaccessible
    from forge.donnees.melange import MELANGE_PAR_DEFAUT
    from forge.donnees.telechargement import dossier_des_textes
    from forge.erreurs import DonneesManquantes
    from forge.tokenizer.apprentissage import verifier_dossier
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
    except (DonneesManquantes, PlaceInsuffisante, FragmentInaccessible, FileNotFoundError, ValueError) as erreur:
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
    from forge.fichiers import nombre

    octets_par_jeton = nombre(resume["octets_par_jeton"], 2)
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


def _numero_de_pas(texte: str) -> int:
    try:
        valeur = int(texte)
    except ValueError:
        valeur = -1
    if valeur < 0:
        raise argparse.ArgumentTypeError(f"numéro de pas illisible : {texte!r}. Écris un entier, 0 ou plus.")
    return valeur


def _commande_entrainer(choix: argparse.Namespace) -> int:
    """`forge entrainer` : entraîne ton IA ; Ctrl+C met en pause, `--reprendre` repart de là."""
    # Imports ici : PyTorch est long à charger, les autres commandes n'en ont pas besoin.
    from forge.chemins import PlaceInsuffisante
    from forge.entrainement import CompilationImpossible, entrainer, lire_config
    from forge.erreurs import DonneesManquantes

    reprise = f"python -m forge entrainer --config {choix.config} --reprendre"
    try:
        entrainer(lire_config(choix.config), reprendre=choix.reprendre, arreter_apres=choix.arreter_apres)
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
    except Exception as erreur:  # CUDA après une mise en veille, carte trop ancienne, disque…
        if "no kernel image" in str(erreur):
            conseil = (
                "PyTorch n'a pas de code pour cette carte graphique, trop ancienne pour ses roues CUDA 13.2 "
                "(il faut une carte Turing, RTX 20xx, ou plus récente : voir le README). Mets "
                f'appareil = "cpu" dans {choix.config}, puis, pour reprendre : '
            )
        else:
            conseil = (
                "La dernière sauvegarde complète reste bonne. Si la carte graphique est en cause (après une "
                "mise en veille, par exemple) et que l'erreur revient, redémarre le PC. Puis, pour reprendre : "
            )
        print(f"Erreur imprévue pendant l'entraînement ({_premiere_ligne(erreur)}).\n{conseil}{reprise}", file=sys.stderr)
        return 1
    return 0


def _ajouter_entrainer(sous_parseurs) -> None:
    commande = _nouvelle_commande(
        sous_parseurs,
        "entrainer",
        "Entraîne ton IA : pré-entraînement sur les jetons encodés, ou affinage (methode = \"sft\") "
        "depuis une version publiée. Ctrl+C met en pause (avec sauvegarde) ; --reprendre repart de la "
        "dernière sauvegarde.",
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
    commande.add_argument(
        "--arreter-apres",
        type=_numero_de_pas,
        default=None,
        metavar="N",
        help="s'arrêter (avec sauvegarde) au pas N, pour un essai chronométré ; --reprendre continue ensuite",
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
    from forge.erreurs import DonneesManquantes

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


def _exporter_en_francais(sauvegarde: Path, sortie: Path, poids: str) -> list[Path]:
    """`exporter`, dont l'avertissement « tokenizer non vérifié » s'écrit « Attention : … », en français.

    Sans cela, `warnings` l'afficherait sous sa forme brute : le fichier, la ligne, `UserWarning`
    et la ligne de code. Les avertissements des bibliothèques s'affichent comme avant.
    """
    from forge.exporter import TokenizerNonVerifie, exporter

    avertissements: list[warnings.WarningMessage] = []
    try:
        with warnings.catch_warnings(record=True) as avertissements:
            warnings.simplefilter("always", TokenizerNonVerifie)
            return exporter(sauvegarde, sortie, poids)
    finally:
        for avertissement in avertissements:
            if issubclass(avertissement.category, TokenizerNonVerifie):
                print(f"Attention : {avertissement.message}", file=sys.stderr)
            else:
                warnings.showwarning(
                    avertissement.message, avertissement.category, avertissement.filename, avertissement.lineno
                )


def _commande_exporter(choix: argparse.Namespace) -> int:
    """`forge exporter` : les fichiers à publier (poids en safetensors bf16, configuration, tokenizer)."""
    # Imports ici : PyTorch est long à charger, les autres commandes n'en ont pas besoin.
    from forge.chemins import PlaceInsuffisante
    from forge.exporter import empreinte_sha256

    try:
        ecrits = _exporter_en_francais(Path(choix.sauvegarde), choix.sortie, choix.poids)
    except (FileNotFoundError, PermissionError, PlaceInsuffisante, ValueError) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Export interrompu : aucun fichier n'est à moitié écrit. Relance la même commande.", file=sys.stderr)
        return 130
    except Exception as erreur:  # le disque qui se remplit pendant l'écriture des poids, par exemple
        print(
            f"Erreur pendant l'export ({_premiere_ligne(erreur)}).\n"
            f"Aucun fichier n'est à moitié écrit. Vérifie la place sur le disque de {choix.sortie} (libère-en "
            "s'il est plein), puis relance la même commande.",
            file=sys.stderr,
        )
        return 1
    print(f"Fichiers écrits dans {choix.sortie} :")
    for chemin in ecrits:
        octets = chemin.stat().st_size
        from forge.fichiers import ESPACE_FINE, entier, nombre

        en_octets = entier(octets, milliers=ESPACE_FINE)  # espace fine entre les milliers
        en_mo = nombre(octets / 1024**2, 1)
        print(f"  {chemin.name} : {en_octets} octets ({en_mo} Mo), SHA-256 {empreinte_sha256(chemin)}")
    return 0


def _ajouter_exporter(sous_parseurs) -> None:
    commande = _nouvelle_commande(
        sous_parseurs,
        "exporter",
        "Prépare les fichiers à publier d'une sauvegarde de ton IA : les poids en safetensors (bf16), "
        "config.json et le tokenizer, vérifié par son empreinte SHA-256.",
    )
    commande.add_argument(
        "--sauvegarde",
        required=True,
        metavar="FICHIER",
        help="sauvegarde de l'entraînement (meilleur.pt ou etape-*.pt), ou son dossier sauvegardes/ (dernière étape)",
    )
    commande.add_argument(
        "--sortie",
        required=True,
        type=Path,
        metavar="DOSSIER",
        help="dossier où écrire les trois fichiers (créé au besoin ; un fichier du même nom est remplacé)",
    )
    commande.add_argument(
        "--poids",
        default="ton-ia-1.5.safetensors",
        metavar="NOM",
        help="nom du fichier des poids, qui finit par .safetensors (ton-ia-1.5.safetensors par défaut)",
    )
    commande.set_defaults(fonction=_commande_exporter)


def _commande_publication(choix: argparse.Namespace) -> int:
    """`forge publication` : télécharge une version publiée de ton IA et affiche ses fichiers."""
    from forge.exporter import NOM_DE_LA_CONFIG, empreinte_sha256
    from forge.fichiers import ESPACE_FINE, entier
    from forge.publication import NOM_DU_TOKENIZER, nom_des_poids, telecharger_publication

    try:
        dossier = telecharger_publication(choix.etiquette, choix.dossier)
    except (FileNotFoundError, PermissionError, ConnectionError, ValueError) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Téléchargement interrompu : aucun fichier n'est à moitié écrit. Relance la même commande.", file=sys.stderr)
        return 130
    print(f"Fichiers de {choix.etiquette} dans {dossier} :")
    for nom in (nom_des_poids(choix.etiquette), NOM_DE_LA_CONFIG, NOM_DU_TOKENIZER):  # seulement ceux de la version
        en_octets = entier((dossier / nom).stat().st_size, milliers=ESPACE_FINE)
        print(f"  {nom} : {en_octets} octets, SHA-256 {empreinte_sha256(dossier / nom)}")
    return 0


def _ajouter_publication(sous_parseurs) -> None:
    commande = _nouvelle_commande(
        sous_parseurs,
        "publication",
        "Télécharge une version publiée de ton IA (poids, config.json, tokenizer) depuis sa Release GitHub, "
        "puis affiche chaque fichier avec sa taille et son empreinte SHA-256.",
    )
    commande.add_argument(
        "--etiquette",
        required=True,
        metavar="ETIQUETTE",
        help="l'étiquette de la Release, par exemple ton-ia-1.5",
    )
    commande.add_argument(
        "--dossier",
        type=Path,
        default=None,
        metavar="DOSSIER",
        help="où ranger les fichiers (par défaut publications/<étiquette> sous FORGE_DONNEES ; ignoré si FORGE_IA_MODELES est posée)",
    )
    commande.set_defaults(fonction=_commande_publication)


def _commande_suivi(choix: argparse.Namespace) -> int:
    """`forge suivi` : où en est l'entraînement, lu dans son journal."""
    # Le suivi n'importe pas PyTorch : il reste léger, on peut le lancer pendant l'entraînement.
    from forge.suivi import afficher, suivre

    try:
        texte = suivre(choix.config)
    except (FileNotFoundError, PermissionError, ValueError) as erreur:
        afficher(f"Erreur\u202f: {erreur}", sys.stderr)
        return 1
    afficher(texte)
    return 0


def _ajouter_suivi(sous_parseurs) -> None:
    commande = _nouvelle_commande(
        sous_parseurs,
        "suivi",
        "Montre où en est un entraînement, d'après son journal\u202f: état, pas, perte, débit, temps "
        "restant estimé et dernière sauvegarde. Ne fait que lire\u202f: on peut le lancer pendant "
        "l'entraînement.",
    )
    commande.add_argument(
        "--config",
        required=True,
        metavar="FICHIER",
        help="fichier TOML de l'entraînement, par exemple configs/principal.toml",
    )
    commande.set_defaults(fonction=_commande_suivi)


def _commande_conversations(choix: argparse.Namespace) -> int:
    """`forge conversations` : télécharge une source de conversations ou d'évaluation, ou les liste."""
    # Imports ici : les autres commandes n'ont pas besoin des sources de conversations.
    from forge.chemins import PlaceInsuffisante
    from forge.conversation import telechargement
    from forge.conversation.sources import SOURCES_CONVERSATIONS
    from forge.donnees.telechargement import EtatDuFluxRefuse
    from forge.erreurs import DonneesManquantes
    from forge.fichiers import ESPACE_FINE, entier
    from forge.fragments import lire_elements

    fine = ESPACE_FINE

    if choix.liste:
        for nom, source in SOURCES_CONVERSATIONS.items():
            usage = "évaluation" if source.usage == "evaluation" else "entraînement"
            print(f"{nom}\u202f: {usage}, licence {source.licence}, https://huggingface.co/datasets/{source.depot}")
        return 0
    if choix.source is None:
        choix.parseur.error("donne --source NOM (la source à télécharger) ou --liste (les sources connues).")
    if choix.source not in SOURCES_CONVERSATIONS:
        choix.parseur.error(
            f"source inconnue\u202f: {choix.source!r}. Les sources sont {', '.join(SOURCES_CONVERSATIONS)}."
        )
    if choix.exemples_max is not None and choix.exemples_max < 1:
        choix.parseur.error("--exemples-max doit être au moins 1.")
    source = SOURCES_CONVERSATIONS[choix.source]

    def journal(message: str) -> None:
        print(message, flush=True)

    # Cette commande a besoin du réseau : si la session coupe Hugging Face, on le permet pour ce processus.
    _lever_le_mode_hors_ligne(journal, "ce téléchargement")
    try:
        dossier = telechargement.telecharger_source(source, choix.exemples_max, journal=journal)
    except telechargement.TelechargementEnPause as pause:
        print(pause, file=sys.stderr)
        return 130
    except (PlaceInsuffisante, EtatDuFluxRefuse, DonneesManquantes, RuntimeError) as erreur:
        # Relancer tel quel échouerait de nouveau : le message dit quoi faire, rien d'autre.
        print(f"Erreur{fine}: {erreur}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(
            f"Interrompu pendant «{fine}{source.nom}{fine}». Relance la même commande{fine}: les fragments "
            "déjà validés sont gardés, la reprise repart de la position du flux enregistrée avec le dernier.",
            file=sys.stderr,
        )
        return 130
    except Exception as erreur:  # réseau coupé, Hugging Face indisponible, disque…
        print(
            f"Erreur pendant le téléchargement de «{fine}{source.nom}{fine}» ({type(erreur).__name__}){fine}: "
            f"{erreur}\nSi le réseau ou Hugging Face est en cause, relance la même commande{fine}: elle "
            "reprendra au dernier fragment validé, sans doublon.",
            file=sys.stderr,
        )
        return 1
    n = sum(1 for _ in lire_elements(dossier, telechargement.PREFIXE))
    print(f"{entier(n, milliers=fine)} éléments dans {dossier}.")
    return 0


def _ajouter_conversations(sous_parseurs) -> None:
    commande = _nouvelle_commande(
        sous_parseurs,
        "conversations",
        "Télécharge en flux une source de conversations (affinage) ou d'évaluation de la vague 2, par "
        "fragments repris après une coupure, avec sa licence et son usage. Les jeux d'évaluation ne vont "
        "jamais dans un entraînement.",
    )
    commande.add_argument("--source", default=None, metavar="NOM", help="la source à télécharger (voir --liste)")
    commande.add_argument(
        "--exemples-max",
        type=int,
        default=None,
        metavar="N",
        help="s'arrête après N éléments gardés (par exemple 20, pour vérifier les colonnes) ; sans lui, jusqu'au bout",
    )
    commande.add_argument(
        "--liste",
        action="store_true",
        help="liste les sources avec leur usage, leur licence et leur lien, puis quitte",
    )
    commande.set_defaults(fonction=_commande_conversations, parseur=commande)


def _liste_d_entiers(texte: str, nom: str) -> list[int]:
    """Lit « 1,2 » : une liste d'entiers séparés par des virgules ; `ValueError` dit quoi écrire à la place."""
    try:
        return [int(x) for x in texte.split(",") if x.strip()]
    except ValueError:
        raise ValueError(f"{nom} illisible : {texte!r}. Écris des entiers séparés par des virgules, par exemple 1,2.") from None


def _commande_problemes(choix: argparse.Namespace) -> int:
    """`forge problemes` : génère des problèmes de calcul en français, par fragments, avec leur réponse et leur trace."""
    # Imports ici : les autres commandes n'ont pas besoin des problèmes.
    import json

    from forge.chemins import sous_forge_donnees
    from forge.fichiers import ESPACE_FINE, ecrire_texte, entier
    from forge.fragments import SortieParFragments
    from forge.raisonnement.problemes import DIFFICULTES, FAMILLES, generer_problemes, usage_de_la_graine

    fine = ESPACE_FINE

    def erreur(message: str) -> int:
        print(f"Erreur{fine}: {message}", file=sys.stderr)
        return 1

    try:
        difficultes = _liste_d_entiers(choix.difficultes, "--difficultes") if choix.difficultes else list(DIFFICULTES)
        familles = [f.strip() for f in choix.familles.split(",") if f.strip()] if choix.familles else list(FAMILLES)
        if choix.nombre < 1:
            return erreur("--nombre doit être au moins 1.")
        problemes = generer_problemes(choix.nombre, choix.graine_depart, familles, difficultes)
    except ValueError as probleme:
        return erreur(str(probleme))
    usage = usage_de_la_graine(choix.graine_depart)
    index = {
        "usage": usage,
        "graine_depart": choix.graine_depart,
        "nombre": choix.nombre,
        "familles": familles,
        "difficultes": difficultes,
        "elements": len(problemes),
    }
    dossier = sous_forge_donnees(choix.sortie, "problemes")
    chemin_de_l_index = dossier / "index.json"
    if chemin_de_l_index.is_file():
        ancien = json.loads(chemin_de_l_index.read_text(encoding="utf-8"))
        if ancien != index:
            return erreur(
                f"{dossier} contient déjà des problèmes d'autres réglages (graine de départ {ancien.get('graine_depart')}, "
                f"{ancien.get('nombre')} demandés). Donne un autre nom à --sortie, ou supprime ce dossier pour recommencer."
            )
    sortie = SortieParFragments(dossier, "problemes")
    if sortie.complet:
        print(f"Déjà fait{fine}: {entier(sortie.deja, milliers=fine)} problèmes dans {dossier}, rien à refaire.")
        return 0
    ecrire_texte(chemin_de_l_index, json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    try:
        for p in problemes[sortie.deja:]:
            sortie.ajouter({
                "id": p.id, "famille": p.famille, "difficulte": p.difficulte,
                "enonce": p.enonce, "etapes": list(p.etapes), "reponse": p.reponse,
            })
            if sortie.plein:
                sortie.valider()
    except KeyboardInterrupt:
        sortie.valider()
        print(
            f"Interrompu{fine}: {entier(sortie.deja, milliers=fine)} problèmes sur "
            f"{entier(len(problemes), milliers=fine)} sont écrits dans {dossier}. Relance la même commande{fine}: "
            "elle reprend là, sans doublon.",
            file=sys.stderr,
        )
        return 130
    sortie.terminer({"usage": usage, "elements": len(problemes), "graine_depart": choix.graine_depart})
    mot = "évaluation" if usage == "evaluation" else "entraînement"
    print(
        f"{entier(len(problemes), milliers=fine)} problèmes ({mot}) dans {dossier}, "
        f"{entier(choix.nombre - len(problemes), milliers=fine)} énoncés en double retirés."
    )
    return 0


def _ajouter_problemes(sous_parseurs) -> None:
    commande = _nouvelle_commande(
        sous_parseurs,
        "problemes",
        "Génère des problèmes de calcul en français (plus faciles que GSM8K), avec leur réponse et leur trace, "
        "par fragments sous FORGE_DONNEES/problemes/NOM. Les graines de 1 000 000 à 1 999 999 sont celles "
        "de l'évaluation : ces problèmes ne vont jamais dans un entraînement.",
    )
    commande.add_argument("--sortie", required=True, metavar="NOM", help="le dossier du jeu, sous FORGE_DONNEES/problemes")
    commande.add_argument("--nombre", required=True, type=int, metavar="N", help="combien de problèmes (les doublons sont retirés)")
    commande.add_argument(
        "--graine-depart",
        required=True,
        type=int,
        metavar="G",
        help="la graine du premier problème : le i-ème vient de G + i (évaluation : de 1000000 à 1999999)",
    )
    commande.add_argument("--difficultes", default=None, metavar="1,2", help="les difficultés permises (par défaut 1,2,3)")
    commande.add_argument(
        "--familles",
        default=None,
        metavar="a,b",
        help="les familles permises, parmi addition, soustraction, multiplication, partage, achats, ages (par défaut toutes)",
    )
    commande.set_defaults(fonction=_commande_problemes, parseur=commande)


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
    _ajouter_exporter(sous_parseurs)
    _ajouter_publication(sous_parseurs)
    _ajouter_suivi(sous_parseurs)
    _ajouter_conversations(sous_parseurs)
    _ajouter_problemes(sous_parseurs)
    return parseur


# Des signes que les commandes écrivent et que cp1252 (Windows) n'a pas : « ≈ » et l'espace fine.
_SIGNES_NON_ASCII = "\u2248\u202f"


def _proteger_les_sorties() -> None:
    """Qu'aucun signe écrit à l'écran ne fasse planter une commande dont la sortie est redirigée.

    Sous Windows, sans `PYTHONUTF8=1`, Python écrit une sortie redirigée (`> journal.txt`,
    `| Tee-Object`, `Start-Process` avec redirection) en cp1252, qui n'a ni « ≈ » ni l'espace
    fine : le premier `print` qui en contient lève `UnicodeEncodeError`, et la commande s'arrête
    (un entraînement, dès le pas 1). Une sortie qui ne sait pas écrire ces signes est donc
    reconfigurée :

    - redirigée vers un fichier ou un tube, elle passe en UTF-8, comme avec `PYTHONUTF8=1` ;
    - branchée sur une console, elle garde l'encodage que la console affiche, et un signe
      absent devient « ? » au lieu de tout arrêter.

    Une sortie qui sait déjà tout écrire (UTF-8, la console de Windows) n'est pas touchée.
    """
    for flux in (sys.stdout, sys.stderr):
        reconfigurer = getattr(flux, "reconfigure", None)
        if reconfigurer is None:
            continue  # sortie remplacée par un objet sans `reconfigure` : on n'y touche pas
        try:
            _SIGNES_NON_ASCII.encode(flux.encoding or "ascii")
            continue
        except (UnicodeEncodeError, LookupError):
            pass
        try:
            if flux.isatty():
                reconfigurer(errors="replace")
            else:
                reconfigurer(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass  # sortie déjà fermée, ou déjà lue : on la laisse telle quelle


def main(arguments: list[str] | None = None) -> int:
    """Lance la commande demandée ; renvoie le code de sortie du programme."""
    _proteger_les_sorties()
    parseur = construire_parseur()
    choix = parseur.parse_args(arguments)
    fonction = getattr(choix, "fonction", None)
    if fonction is None:
        parseur.print_help()
        return 0
    return fonction(choix)


if __name__ == "__main__":
    sys.exit(main())
