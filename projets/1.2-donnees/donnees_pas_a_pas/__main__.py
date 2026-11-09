"""Trier des textes comme « ton IA », compter ce que les sources donnent, relever les volumes du corpus.

Exemples (dans projets/1.2-donnees) :

    uv run python -m donnees_pas_a_pas trier exemples/web.jsonl
    uv run python -m donnees_pas_a_pas trier exemples/code.jsonl --source code_python
    uv run python -m donnees_pas_a_pas apercu --octets 5M --enregistrer sorties/apercu.txt --json mesures/apercu.json
    uv run python -m donnees_pas_a_pas volumes --donnees principal --json mesures/corpus-principal.json

`trier` donne un verdict par ligne d'un fichier `.jsonl` : gardé, trop court, doublon, licence
ou langage. `apercu` lit chaque source en flux sur Hugging Face jusqu'à `--octets` octets de
texte gardé, et compte ce que le tri en fait (il lui faut le réseau). `volumes` lit, sans rien
écrire, `.complet` et `index.json` d'un corpus déjà encodé (`FORGE_DONNEES/jetons/<nom>/`).

La première ligne de chaque sortie est `# relevé le AAAA-MM-JJ`.
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from typing import NoReturn

from forge.chemins import racine_donnees
from forge.donnees.sources import SOURCES

from donnees_pas_a_pas.apercu import apercu, en_octets
from donnees_pas_a_pas.trier import compter_raisons, lire_jsonl, trier
from donnees_pas_a_pas.volumes import volumes

FINE = "\u202f"  # l'espace fine insécable de la typographie française


def arreter(message: str) -> NoReturn:
    """Affiche le message sur la sortie d'erreur et arrête le programme (code 1)."""
    print(message, file=sys.stderr)
    raise SystemExit(1)


def lever_le_mode_hors_ligne() -> None:
    """Lève, pour ce processus seulement, le mode hors ligne de Hugging Face (`HF_HUB_OFFLINE=1`).

    Cette variable est souvent posée pour les autres projets (c'est le cas sur le PC de ce dépôt).
    `apercu` a besoin du réseau : la variable est levée avant que `datasets` ne la lise à son import,
    comme le fait `python -m forge donnees`.
    """
    for variable in ("HF_HUB_OFFLINE", "HF_DATASETS_OFFLINE"):
        if os.environ.get(variable, "").strip().upper() in {"1", "ON", "YES", "TRUE"}:
            print(f"{variable} est à 1 : levé pour cette commande seulement, qui a besoin du réseau.", file=sys.stderr)
            os.environ[variable] = "0"


def nombre(n: int) -> str:
    """Un entier à la française : les milliers séparés par une espace fine."""
    return f"{n:,}".replace(",", FINE)


def virgule(x: float, decimales: int) -> str:
    """Un nombre à décimales avec la virgule française."""
    return f"{x:,.{decimales}f}".replace(",", FINE).replace(".", ",")


def en_mio(octets: int) -> str:
    """Une taille en Mio (1024² octets), avec une décimale."""
    return f"{virgule(octets / 1024**2, 1)}{FINE}Mio"


def en_gio(octets: int) -> str:
    """Une taille en Gio (1024³ octets), avec une décimale."""
    return f"{virgule(octets / 1024**3, 1)}{FINE}Gio"


def entete() -> str:
    """La première ligne de chaque sortie."""
    return f"# relevé le {datetime.date.today().isoformat()}"


def lire_arguments(arguments: list[str] | None = None) -> argparse.Namespace:
    analyseur = argparse.ArgumentParser(prog="donnees_pas_a_pas", description=__doc__.split("\n\n")[0])
    commandes = analyseur.add_subparsers(dest="commande", required=True)

    tri = commandes.add_parser("trier", help="un verdict par ligne d'un fichier .jsonl")
    tri.add_argument("fichier", type=Path, help="le fichier .jsonl, par exemple exemples/web.jsonl")
    tri.add_argument("--source", choices=list(SOURCES), default="web_fr", help="la source dont le fichier imite les lignes (web_fr)")

    ape = commandes.add_parser("apercu", help="lire chaque source en flux et compter ce que le tri en fait")
    ape.add_argument("--octets", default="5M", help="le texte gardé à lire par source, par exemple 5M (5M)")
    ape.add_argument("--enregistrer", type=Path, help="écrire aussi le texte affiché dans ce fichier")
    ape.add_argument("--json", type=Path, help="écrire les chiffres dans ce fichier JSON")

    vol = commandes.add_parser("volumes", help="les volumes d'un corpus déjà encodé (lecture seule)")
    vol.add_argument("--donnees", default="principal", help="le dossier sous FORGE_DONNEES/jetons (principal)")
    vol.add_argument("--json", type=Path, help="écrire les chiffres dans ce fichier JSON")
    return analyseur.parse_args(arguments)


def ecrire_texte(chemin: Path, texte: str) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(texte)


def ecrire_json(chemin: Path, donnees: dict) -> None:
    # Pas de commentaire dans un .json : la date du relevé est la clé « releve_le ».
    ecrire_texte(chemin, json.dumps(donnees, ensure_ascii=False, allow_nan=False, indent=1) + "\n")


def afficher_tri(fichier: Path, nom_source: str) -> str:
    verdicts = list(trier(lire_jsonl(fichier), SOURCES[nom_source]))
    lignes = [entete(), f"{fichier.name} lu comme {nom_source} : {len(verdicts)} lignes."]
    for i, v in enumerate(verdicts, start=1):
        detail = ""
        if v.garde:
            detail = f", empreinte {v.empreinte[:8]}, {'validation' if v.validation else 'entraînement'}"
        elif v.empreinte is not None:
            detail = f", même empreinte que le texte gardé {v.empreinte[:8]}"
        lignes.append(f"{i:>3}. {v.raison}{detail}")
    lignes.append("Bilan : " + ", ".join(f"{raison} {n}" for raison, n in compter_raisons(verdicts).items() if n))
    return "\n".join(lignes) + "\n"


def afficher_apercu(resultat: dict, octets: int) -> str:
    lignes = [
        entete(),
        f"Aperçu de forge.donnees.sources : {en_mio(octets)} de texte gardé par source, lus en flux depuis Hugging Face.",
        "",
    ]
    for nom, r in resultat.items():
        source = SOURCES[nom]
        lignes.append(f"{nom} ({source.depot})")
        if r["lus"] == 0:
            lignes.append(f"  aucun document lu{FINE}: la source n'a rien donné, vérifie ta connexion")
            lignes.append("")
            continue
        lignes.append(f"  documents lus{FINE}: {nombre(r['lus'])}")
        part = 100 * r["gardes"] / r["lus"]
        lignes.append(f"  gardés{FINE}: {nombre(r['gardes'])}, soit {virgule(part, 1)}{FINE}%")
        for raison, n in r["raisons"].items():
            if raison != "gardé" and n:
                lignes.append(f"  écartés, {raison}{FINE}: {nombre(n)}")
        lignes.append(f"  texte gardé{FINE}: {nombre(r['octets_gardes'])} octets ({en_mio(r['octets_gardes'])})")
        lignes.append(f"  mis de côté pour la validation{FINE}: {nombre(r['en_validation'])}")
        lignes.append(f"  durée{FINE}: {virgule(r['secondes'], 1)}{FINE}s")
        lignes.append("")
    return "\n".join(lignes)


def afficher_volumes(v: dict, nom: str) -> str:
    total = v["jetons_train"] + v["jetons_val"]
    lignes = [
        entete(),
        f"Corpus encodé « {nom} » (tokenizer {v['tokenizer']}), lu dans .complet et index.json.",
        "",
        f"jetons d'entraînement{FINE}: {nombre(v['jetons_train'])}",
        f"jetons de validation{FINE}: {nombre(v['jetons_val'])}, soit {virgule(100 * v['jetons_val'] / total, 2)}{FINE}% du total",
        f"documents{FINE}: {nombre(v['documents_train'])} pour l'entraînement, {nombre(v['documents_val'])} pour la validation",
        f"texte d'origine{FINE}: {nombre(v['octets'])} octets ({en_gio(v['octets'])})",
        f"octets par jeton{FINE}: {virgule(v['octets_par_jeton'], 4)}",
        f"fragments encodés{FINE}: {nombre(v['fragments'])}",
    ]
    for nom_source, n in v["fragments_par_source"].items():
        lignes.append(f"  {nom_source}{FINE}: {nombre(n)} fragments")
    return "\n".join(lignes) + "\n"


def main(arguments: list[str] | None = None) -> None:
    # Les sorties contiennent des espaces fines et des accents : on écrit en UTF-8, quel que soit le terminal.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    choix = lire_arguments(arguments)
    if choix.commande == "trier":
        if not choix.fichier.exists():
            arreter(f"Le fichier {choix.fichier} n'existe pas. Donne un fichier .jsonl, par exemple exemples/web.jsonl.")
        print(afficher_tri(choix.fichier, choix.source), end="")
    elif choix.commande == "apercu":
        try:
            octets = en_octets(choix.octets)
        except ValueError as probleme:
            arreter(str(probleme))
        lever_le_mode_hors_ligne()
        try:
            resultat = apercu(octets)
        except OSError as probleme:
            arreter(
                f"La lecture en flux a échoué ({probleme}). Vérifie ta connexion, puis relance la commande : "
                "elle a besoin d'Internet pour lire Hugging Face."
            )
        texte = afficher_apercu(resultat, octets)
        print(texte, end="")
        if choix.enregistrer:
            ecrire_texte(choix.enregistrer, texte)
        if choix.json:
            ecrire_json(choix.json, {"releve_le": datetime.date.today().isoformat(), "octets_par_source": octets, "sources": resultat})
    else:
        dossier = racine_donnees() / "jetons" / choix.donnees
        try:
            v = volumes(dossier)
        except (FileNotFoundError, ValueError) as probleme:
            arreter(str(probleme))
        print(afficher_volumes(v, choix.donnees), end="")
        if choix.json:
            ecrire_json(choix.json, {"releve_le": datetime.date.today().isoformat(), "dossier": choix.donnees, **v})


if __name__ == "__main__":
    main()
