"""Écrire une suite de texte avec le modèle, ou refaire le texte d'apprentissage.

Exemples (dans projets/1.1-modele-de-langage) :

    uv run python -m modele_de_langage suite --n 4 --temperature 1 --graine 0 "Le forgeron "
    uv run python -m modele_de_langage extraire --commit ae8d9a4 --sortie donnees/texte-du-site.txt

`suite` apprend les comptes sur les 90 premiers % du texte du site, puis écrit
`--longueur` caractères à la suite du départ (200 par défaut), en s'appuyant sur
les `--n` derniers caractères (et sur moins quand ce groupe est inconnu), à la
température demandée (0, 0.5, 1 ou 2), parmi les caractères déjà vus. La même
graine donne toujours le même texte, ici comme dans la page du site.

`extraire` relit les chapitres du site, au commit donné, et en écrit la prose.
"""

import argparse
import sys
from pathlib import Path
from typing import NoReturn

from modele_de_langage.extraire import ecrire_texte
from modele_de_langage.ngrammes import (
    MESSAGE_TEMPERATURE,
    ORDRE_MAX,
    TEMPERATURES,
    alphabet,
    charger_texte,
    compter_par_ordre,
    couper,
    generer,
)


def arreter(message: str) -> NoReturn:
    """Affiche le message sur la sortie d'erreur et arrête le programme (code 1)."""
    print(message, file=sys.stderr)
    raise SystemExit(1)


def lire_arguments(arguments: list[str] | None = None) -> argparse.Namespace:
    analyseur = argparse.ArgumentParser(prog="modele_de_langage", description=__doc__.split("\n\n")[0])
    commandes = analyseur.add_subparsers(dest="commande", required=True)

    suite = commandes.add_parser("suite", help="écrire la suite d'un texte de départ")
    suite.add_argument("depart", help="le texte de départ, d'au moins n caractères")
    suite.add_argument("--n", type=int, default=4, help=f"le nombre de caractères de contexte, de 0 à {ORDRE_MAX} (4)")
    suite.add_argument("--temperature", type=float, default=1, help="0, 0.5, 1 ou 2 (1)")
    suite.add_argument("--graine", type=int, default=0, help="la graine du hasard (0)")
    suite.add_argument("--longueur", type=int, default=200, help="le nombre de caractères à écrire (200)")

    extraire = commandes.add_parser("extraire", help="refaire le texte d'apprentissage depuis les chapitres du site")
    extraire.add_argument("--commit", required=True, help="le commit des chapitres, par exemple ae8d9a4")
    extraire.add_argument("--sortie", type=Path, required=True, help="le fichier à écrire, par exemple donnees/texte-du-site.txt")
    return analyseur.parse_args(arguments)


def main(arguments: list[str] | None = None) -> None:
    # Le texte du site contient des espaces fines et des guillemets : on écrit en UTF-8, quel que soit le terminal.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    choix = lire_arguments(arguments)
    if choix.commande == "extraire":
        nombre = ecrire_texte(choix.commit, choix.sortie)
        print(f"Écrit : {choix.sortie} ({nombre} caractères)")
        return
    if not 0 <= choix.n <= ORDRE_MAX:
        arreter(f"Le nombre de caractères de contexte doit être de 0 à {ORDRE_MAX} (reçu {choix.n}).")
    if choix.temperature not in TEMPERATURES:
        arreter(MESSAGE_TEMPERATURE)
    texte = charger_texte()
    entrainement, _ = couper(texte)
    comptes = compter_par_ordre(entrainement, choix.n)
    try:
        print(generer(comptes, alphabet(texte), choix.n, choix.depart, choix.longueur, choix.temperature, choix.graine))
    except ValueError as probleme:
        arreter(f"{probleme} Donne un départ d'au moins {choix.n} caractères, ou baisse --n.")


if __name__ == "__main__":
    main()
