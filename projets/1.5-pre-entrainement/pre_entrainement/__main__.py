"""`python -m pre_entrainement` : relever les courbes d'un journal d'entraînement, et faire l'essai de pause et de reprise.

    uv run --extra cpu python -m pre_entrainement courbe --journal <journal.jsonl> --config <mini.toml> --json mesures/ton-ia-mini.json
    uv run --extra cpu python -m pre_entrainement essai --appareil cpu --enregistrer sorties/essai-processeur.txt --json mesures/essai-processeur.json
    uv run --extra gpu python -m pre_entrainement essai --appareil cuda

`courbe` lit le journal d'un entraînement de forge et la configuration qui l'a lancé, affiche un
résumé, et écrit avec `--json` le résumé, les sessions et la courbe. `essai` entraîne un petit modèle de
deux façons (d'un trait, puis avec une pause et une reprise à mi-chemin) et dit si les deux pertes finales
sont les mêmes. Sans carte graphique, `--appareil cuda` dit quoi faire, sans trace Python, et rend le code
2 ; de même sans PyTorch, ou avec une carte que PyTorch voit sans savoir calculer dessus.
"""

import argparse
import datetime
import json
import os
import sys
import tempfile
from pathlib import Path

try:
    from forge.entrainement import lire_config
    from forge.modele import nombre_parametres

    from pre_entrainement.essai import config_essai, essai_pause_reprise
    from pre_entrainement.journal import courbe as courbe_du_journal
    from pre_entrainement.journal import lire, resume, sessions
except ImportError as erreur:  # PyTorch (ou forge) manque : main() le dit, sans trace
    MANQUE: ImportError | None = erreur
else:
    MANQUE = None

FINE = "\u202f"  # l'espace fine insécable de la typographie française


def nombre(n: float, decimales: int = 0) -> str:
    """Un nombre à la française : les milliers séparés par une espace fine, la virgule décimale."""
    return f"{n:,.{decimales}f}".replace(",", FINE).replace(".", ",")


def ecart_en_francais(x: float) -> str:
    """Un écart en notation scientifique à la française (« 4,4e-16 »), ou « 0 » s'il est nul."""
    return "0" if x == 0 else f"{x:.1e}".replace(".", ",")


def duree(secondes: float) -> str:
    """Une durée lisible, comme dans docs/mesures : « 60 min 17 s », « 12 s »."""
    minutes, s = divmod(round(secondes), 60)
    return f"{minutes} min {s:02d} s" if minutes else f"{s} s"


def carte_inutilisable(erreur: RuntimeError) -> str:
    """Le message quand PyTorch voit la carte, mais n'a pas pu calculer dessus : une carte trop
    ancienne ou trop récente pour sa version (le diagnostic du projet 0.3 dit laquelle), ou une
    carte dont la mémoire est déjà prise par un autre programme."""
    import torch  # déjà chargé : la carte vient d'être choisie

    texte = str(erreur).strip()
    premiere_ligne = texte.splitlines()[0].rstrip(".") if texte else type(erreur).__name__
    processeur = (
        "Pour calculer sur le processeur, relance avec `--appareil cpu` (ou, sans `--appareil`, mets FORGE_APPAREIL=cpu)."
    )
    if isinstance(erreur, torch.OutOfMemoryError):
        return (
            f"La carte graphique n’a plus assez de mémoire libre\u202f: {premiere_ligne}. "
            f"Un autre programme s’en sert peut-être\u202f: ferme-le, puis relance le script. {processeur}"
        )
    return (
        f"La carte graphique n’a pas pu calculer avec cette version de PyTorch\u202f: {premiere_ligne}. "
        f"Pour savoir pourquoi, lance `uv run --extra gpu python -m poste` dans le dossier projets/0.3-poste. {processeur}"
    )


def ecrire_en_utf8() -> None:
    """Une console Windows redirigée vers un fichier écrit en cp1252, qui ne connaît pas
    l'espace fine (U+202F) : on passe alors la sortie en UTF-8, plutôt que de planter."""
    for flux in (sys.stdout, sys.stderr):
        try:
            "\u202f’".encode(flux.encoding or "ascii")
        except (UnicodeEncodeError, LookupError):
            if hasattr(flux, "reconfigure"):
                flux.reconfigure(encoding="utf-8")


def ecrire_json(chemin: Path, donnees: dict) -> None:
    """Un fichier de mesures : UTF-8, fins de ligne LF, comme les autres mesures du dépôt."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(json.dumps(donnees, ensure_ascii=False, allow_nan=False, indent=1) + "\n")


def lignes_de_courbe(nom: str, r: dict, parties: list[dict]) -> list[str]:
    """Ce que `courbe` affiche : le résumé du journal et ses sessions."""
    lignes = [
        f"Journal de {nom}{FINE}: {nombre(r['pas_faits'])} pas sur {nombre(r['pas_total'])}, "
        f"{nombre(r['jetons_vus'])} jetons vus, {nombre(r['parametres'])} paramètres",
        f"  {nombre(r['secondes_de_calcul'], 1)} s de calcul ({duree(r['secondes_de_calcul'])}), "
        f"{'aucune pause' if r['pauses'] == 0 else str(r['pauses']) + ' pause' + ('s' if r['pauses'] > 1 else '')}"
        + (f", {nombre(r['debit_moyen'])} jetons par seconde en moyenne" if r["debit_moyen"] else ""),
    ]
    if r["perte_dernier_pas"] is not None:
        lignes.append(
            f"  perte de {nombre(r['perte_premier_pas'], 3)} au premier pas à {nombre(r['perte_dernier_pas'], 3)} au dernier "
            f"(moyenne des 20 derniers{FINE}: {nombre(r['perte_finale'], 3)})"
            + (f", validation {nombre(r['validation_finale'], 3)}" if r["validation_finale"] is not None else "")
        )
    for numero, s in enumerate(parties, start=1):
        pas = "aucun pas" if s["premier_pas"] is None else f"pas {nombre(s['premier_pas'])} à {nombre(s['dernier_pas'])}"
        lignes.append(f"  session {numero} ({s['depart']}){FINE}: {pas}, {nombre(s['secondes'], 1)} s, fin{FINE}: {s['fin']}")
    return lignes


def commande_courbe(options: argparse.Namespace) -> int:
    journal = Path(options.journal)
    if not journal.exists():
        print(f"Le journal {journal} n’existe pas. Lance d’abord l’entraînement qui l’écrit, ou corrige le chemin de --journal.", file=sys.stderr)
        return 2
    try:
        config = lire_config(options.config)
    except (FileNotFoundError, ValueError) as erreur:
        print(erreur, file=sys.stderr)
        return 2
    lignes = lire(journal)
    nom = Path(config.sortie).name
    r = resume(lignes, config)
    parties = sessions(lignes)
    print("\n".join(lignes_de_courbe(nom, r, parties)))
    if options.json:
        donnees = {
            "nom": nom,
            "releve_le": datetime.date.today().isoformat(),
            "resume": r,
            "sessions": parties,
            "courbe": courbe_du_journal(lignes, pas_total=config.pas_total),
        }
        ecrire_json(Path(options.json), donnees)
    return 0


def lignes_d_essai(r: dict, config, materiel: str) -> list[str]:
    """Ce que `essai` affiche : la configuration, les deux pertes finales, leur écart et le verdict."""
    import torch

    modele = config.modele
    exacte = r["ecart"] == 0
    return [
        f"Pause et reprise exacte, sur {materiel}",
        f"  modèle{FINE}: dim {modele.dim}, {modele.couches} couches, {modele.tetes} têtes, contexte {modele.longueur_contexte} "
        f"({nombre(nombre_parametres(modele))} paramètres, PyTorch {torch.__version__.split('+')[0]})",
        f"  {r['pas_total']} pas de {nombre(config.taille_lot_jetons)} jetons, taux {nombre(config.taux_max, 3)}, "
        f"validation tous les {config.evaluation_tous_pas} pas",
        f"  d’un trait{FINE}: perte {nombre(r['perte_un_trait'], 6)} au pas {r['pas_total']}",
        f"  arrêté au pas {r['pas_de_la_pause']} (comme Ctrl+C), puis repris{FINE}: perte {nombre(r['perte_reprise'], 6)} au pas {r['pas_total']}",
        f"  écart des deux pertes{FINE}: {ecart_en_francais(r['ecart'])}",
        f"  {nombre(r['secondes'], 1)} s pour les trois entraînements",
        f"la reprise est exacte{FINE}: {'oui' if exacte else 'non'}",
    ]


def commande_essai(options: argparse.Namespace) -> int:
    from pre_entrainement.appareil import AppareilIndisponible, choisir_appareil

    try:
        ou = choisir_appareil(options.appareil)
    except (AppareilIndisponible, ValueError) as erreur:
        print(erreur, file=sys.stderr)
        return 2
    if ou.type == "cuda":
        import torch

        materiel = f"la carte graphique, {torch.cuda.get_device_name(ou)}"
    else:
        materiel = f"le processeur ({os.cpu_count()} cœurs logiques)"
    # Les données et les sauvegardes de l'essai vont dans un dossier temporaire, effacé ensuite.
    with tempfile.TemporaryDirectory(prefix="pre-entrainement-", ignore_cleanup_errors=True) as racine:
        try:
            r = essai_pause_reprise(ou.type, Path(racine))
        except RuntimeError as erreur:
            if ou.type != "cuda":
                raise  # sur le processeur, c'est un défaut du projet : sa trace entière doit se voir
            print(carte_inutilisable(erreur), file=sys.stderr)
            return 2
        lignes = lignes_d_essai(r, config_essai(ou.type, Path(racine)), materiel)
    print("\n".join(lignes))
    if options.enregistrer:
        chemin = Path(options.enregistrer)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        with open(chemin, "w", encoding="utf-8", newline="\n") as fichier:
            fichier.write(f"# relevé le {datetime.date.today().isoformat()}\n" + "\n".join(lignes) + "\n")
    if options.json:
        ecrire_json(Path(options.json), {"releve_le": datetime.date.today().isoformat(), **r})
    # Sur le processeur, la reprise doit être exacte ; sur la carte, deux entraînements identiques
    # peuvent différer un peu (la carte additionne dans un ordre qui varie).
    return 0 if ou.type == "cuda" or r["ecart"] == 0 else 1


def main(argv: list[str] | None = None) -> int:
    # Avant argparse, qui écrit lui-même ses messages d'erreur.
    ecrire_en_utf8()
    lecteur = argparse.ArgumentParser(
        prog="python -m pre_entrainement",
        description="Relève les courbes d'un journal d'entraînement de forge, et fait l'essai de pause et de reprise exacte.",
    )
    commandes = lecteur.add_subparsers(dest="nom_commande", required=True, metavar="{courbe,essai}")
    courbe = commandes.add_parser("courbe", help="le résumé, les sessions et la courbe d'un journal")
    courbe.add_argument("--journal", required=True, metavar="JOURNAL", help="le journal.jsonl de l'entraînement")
    courbe.add_argument("--config", required=True, metavar="CONFIG", help="le fichier TOML qui a lancé l'entraînement")
    courbe.add_argument("--json", metavar="FICHIER", help="écrit aussi le résumé, les sessions et la courbe dans FICHIER (JSON)")
    courbe.set_defaults(fonction=commande_courbe)
    essai = commandes.add_parser("essai", help="un petit entraînement, mis en pause puis repris")
    essai.add_argument(
        "--appareil", help="auto (par défaut, sauf si FORGE_APPAREIL est réglée), cpu ou cuda", default=None
    )
    essai.add_argument(
        "--enregistrer",
        metavar="FICHIER",
        help="écrit aussi la sortie dans FICHIER (UTF-8), précédée de la date du relevé",
    )
    essai.add_argument("--json", metavar="FICHIER", help="écrit aussi le résultat dans FICHIER (JSON)")
    essai.set_defaults(fonction=commande_essai)
    options = lecteur.parse_args(argv)
    if MANQUE is not None:
        print(
            f"Un module manque ({MANQUE}). Lance le script avec la version de PyTorch de ton poste\u202f: "
            "`uv run --extra cpu python -m pre_entrainement …`, ou `--extra gpu` avec une carte NVIDIA.",
            file=sys.stderr,
        )
        return 2
    return options.fonction(options)


if __name__ == "__main__":
    sys.exit(main())
