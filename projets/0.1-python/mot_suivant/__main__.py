"""Devine le mot suivant, en ligne de commande.

Exemple (dans projets/0.1-python) :

    uv run python -m mot_suivant le --longueur 12

Le programme affiche les mots qui suivent « le » dans le texte, avec leur
nombre d'apparitions, le mot suivant le plus probable, puis une suite de 12
mots qui commence par « le ». Avec --fichier, il lit un autre texte (UTF-8).
"""

import argparse
import sys
from pathlib import Path
from typing import NoReturn

from mot_suivant.mots import charger_texte, compter_suivants, decouper_mots, predire, suivants_tries, suivre

FINE = "\u202f"  # l'espace fine insécable de la typographie française


def citer(mot: str) -> str:
    """Un mot entre guillemets français : « le »."""
    return f"«{FINE}{mot}{FINE}»"


def arreter(message: str) -> NoReturn:
    """Affiche le message sur la sortie d'erreur et arrête le programme (code 1)."""
    print(message, file=sys.stderr)
    raise SystemExit(1)


def lire_texte(fichier: Path | None) -> str:
    """Le texte du projet, ou celui du fichier demandé."""
    if fichier is None:
        return charger_texte()
    try:
        return fichier.read_text(encoding="utf-8")
    except FileNotFoundError:
        arreter(f"Le fichier {fichier} est introuvable{FINE}: vérifie son chemin, puis relance.")
    except UnicodeDecodeError:
        arreter(f"Le fichier {fichier} n’est pas écrit en UTF-8{FINE}: enregistre-le en UTF-8, puis relance.")


def principal(arguments: list[str] | None = None) -> None:
    lecteur = argparse.ArgumentParser(
        prog="python -m mot_suivant",
        description="Compte quel mot suit quel autre dans un texte, puis devine le mot suivant.",
    )
    lecteur.add_argument("mot", help="le mot de départ, par exemple : le")
    lecteur.add_argument("--longueur", type=int, default=12, help="le nombre de mots de la suite (12 par défaut)")
    lecteur.add_argument("--fichier", type=Path, help="un autre texte à lire, en UTF-8 (par défaut : donnees/texte.txt)")
    options = lecteur.parse_args(arguments)
    if options.longueur < 1:
        arreter(f"La suite doit avoir au moins 1 mot (reçu {options.longueur}){FINE}: relance avec --longueur 12, par exemple.")

    # La console Windows n'est pas toujours en UTF-8 : sans cela, « œ » ou l'espace fine feraient planter l'affichage.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    mots = decouper_mots(lire_texte(options.fichier))
    suivants = compter_suivants(mots)
    # Le texte est mis en minuscules : le mot de départ aussi.
    mot = options.mot.lower()

    if not mots:
        print(f"Ce texte ne contient aucun mot{FINE}: choisis un texte fait de phrases, puis relance.")
        return
    if mot not in mots:
        exemple = "le" if "le" in mots else mots[0]
        print(
            f"{citer(mot)} n’est pas dans ce texte{FINE}: rien ne le suit. "
            f"Essaie un mot du texte, par exemple {citer(exemple)}."
        )
        return
    if mot not in suivants:
        print(f"Rien ne suit {citer(mot)} dans ce texte{FINE}: la suite s’arrête là.")
    else:
        print(f"Après {citer(mot)}, ce texte met{FINE}:")
        tries = suivants_tries(suivants[mot])
        largeur = max(len(suivant) for suivant, _ in tries)
        for suivant, n in tries:
            print(f"  {suivant:<{largeur}}  {n} fois")
        print(f"Le mot suivant le plus probable{FINE}: {citer(predire(suivants, mot))}.")

    suite = suivre(suivants, mot, options.longueur)
    pluriel = "mot" if len(suite.mots) == 1 else "mots"
    print(f"Une suite de {len(suite.mots)} {pluriel}{FINE}: {' '.join(suite.mots)}")
    if suite.reprise is not None:
        print(
            f"La suite revient sur {citer(suite.mots[suite.reprise])} au mot {suite.reprise + 1}{FINE}: "
            "à partir de là, elle tourne en rond."
        )


if __name__ == "__main__":
    principal()
