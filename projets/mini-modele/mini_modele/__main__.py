"""La ligne de commande du mini-modèle.

    uv run python -m mini_modele entrainer [--preset complet|avant-gout] [--pas N] [--taux X]

Elle entraîne le mini-modèle sur le processeur, en Python pur, exactement
comme la démo du site : mêmes réglages, mêmes nombres, au bit près. Elle
affiche l'erreur du lot tous les 50 pas et au dernier pas
(« pas 50 : erreur 2,734 »), puis l'erreur de validation et des prénoms
inventés.

- --preset : complet (3 000 pas, par défaut) ou avant-gout (600 pas) ;
- --pas N : entraîner N pas au lieu de ceux du préréglage (le taux monte et
  redescend sur ces N pas) ;
- --taux X : le taux maximal (0,01 par défaut ; le site propose 0,001, 0,003,
  0,01, 0,03, 0,1 et 0,3). La virgule et le point sont acceptés.
"""

import argparse
import dataclasses
import sys
import time
from collections.abc import Sequence

from mini_modele.entrainement import PRESETS_MINI, Entraineur, ReglagesMini
from mini_modele.modele import nombre_parametres

AFFICHER_TOUS = 50  # une ligne d'erreur tous les AFFICHER_TOUS pas, plus le dernier


def formater_erreur(x: float) -> str:
    """L'erreur avec 3 décimales et une virgule : 2,734."""
    return f"{x:.3f}".replace(".", ",")


def formater_nombre(x: float) -> str:
    """Un nombre court, avec une virgule : 0,01."""
    return f"{x:g}".replace(".", ",")


def formater_entier(n: int) -> str:
    """Un entier, les milliers séparés par une espace : 4 608."""
    return f"{n:,}".replace(",", " ")


def entier_positif(texte: str) -> int:
    """Un entier d'au moins 1, pour --pas."""
    try:
        valeur = int(texte)
    except ValueError:
        raise argparse.ArgumentTypeError(f"« {texte} » n'est pas un nombre entier de pas (par exemple 3000).") from None
    if valeur < 1:
        raise argparse.ArgumentTypeError(f"il faut au moins 1 pas (reçu {valeur}).")
    return valeur


def nombre_decimal(texte: str) -> float:
    """Un nombre à virgule ou à point, pour --taux."""
    try:
        return float(texte.replace(",", "."))
    except ValueError:
        raise argparse.ArgumentTypeError(f"« {texte} » n'est pas un nombre (par exemple 0,01).") from None


def entrainer(reglages: ReglagesMini, nom_preset: str) -> int:
    """Entraîne, affiche la progression, puis l'erreur de validation et des prénoms inventés.

    Renvoie 0, ou 1 si l'erreur a explosé.
    """
    debut = time.perf_counter()
    e = Entraineur(reglages)
    d = e.donnees
    print(
        f"Mini-modèle : {formater_entier(nombre_parametres(e.config))} paramètres, "
        f"{len(d.vocabulaire)} caractères, {formater_entier(len(d.entrainement))} prénoms d'entraînement."
    )
    print(
        f"Réglages : préréglage {nom_preset}, {formater_entier(reglages.pas_total)} pas, "
        f"taux maximal {formater_nombre(reglages.taux_max)}."
    )
    depart = e.perte_validation()
    print(f"Erreur de validation au départ : {formater_erreur(depart)}", flush=True)
    while e.pas < reglages.pas_total:
        perte = e.faire_un_pas()
        if e.diverge:
            print(f"pas {e.pas} : erreur {formater_erreur(perte)}")
            print(
                f"L'erreur a explosé au pas {e.pas} : ce taux est trop grand. "
                "Recommence avec un taux plus petit (--taux)."
            )
            return 1
        if e.pas % AFFICHER_TOUS == 0 or e.pas == reglages.pas_total:
            print(f"pas {e.pas} : erreur {formater_erreur(perte)}", flush=True)
    print(f"Erreur de validation au pas {e.pas} : {formater_erreur(e.perte_validation())}")
    # Un prénom vide (le bord tiré en premier) s'affiche « (vide) ».
    prenoms = [(p or "(vide)") + (" (existe déjà)" if p in d.connus else "") for p in e.echantillons()]
    print("Prénoms inventés : " + ", ".join(prenoms))
    print(f"Durée : {time.perf_counter() - debut:.1f} s".replace(".", ","))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(
        prog="python -m mini_modele",
        description="Le mini-modèle qui apprend à inventer des prénoms, en Python pur.",
    )
    commandes = parseur.add_subparsers(dest="commande", required=True)
    commande = commandes.add_parser("entrainer", help="entraîne le mini-modèle, puis invente des prénoms")
    commande.add_argument("--preset", choices=list(PRESETS_MINI), default="complet", help="le préréglage (complet par défaut)")
    commande.add_argument("--pas", type=entier_positif, help="le nombre de pas (par défaut, celui du préréglage)")
    commande.add_argument("--taux", type=nombre_decimal, help="le taux maximal (0,01 par défaut)")
    arguments = parseur.parse_args(argv)
    reglages = PRESETS_MINI[arguments.preset]
    try:
        if arguments.pas is not None:
            reglages = dataclasses.replace(reglages, pas_total=arguments.pas)
        if arguments.taux is not None:
            reglages = dataclasses.replace(reglages, taux_max=arguments.taux)
    except ValueError as erreur:
        parseur.error(str(erreur))
    return entrainer(reglages, arguments.preset)


if __name__ == "__main__":
    sys.exit(main())
