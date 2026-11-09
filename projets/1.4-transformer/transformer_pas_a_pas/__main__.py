"""Comparer le transformer refait pièce par pièce à celui de forge, et compter ses paramètres.

Exemples (dans projets/1.4-transformer) :

    uv run --extra cpu python -m transformer_pas_a_pas comparer
    uv run --extra cpu python -m transformer_pas_a_pas comparer --enregistrer sorties/comparaison.txt
    uv run --extra cpu python -m transformer_pas_a_pas compter --preset tres_grand

`comparer` construit un petit transformer de forge (dim 32, 2 couches, 4 têtes) en float64 sur le
processeur, refait chacune de ses pièces avec `pieces.py`, et affiche le plus grand écart de
chaque pièce, puis le verdict « identique à forge à 10⁻¹² près ». Il rend le code 1 si une pièce
s'écarte de plus. `compter` donne les paramètres d'une taille de forge, famille par famille.
Avec `--enregistrer FICHIER`, `comparer` écrit aussi sa sortie dans FICHIER (UTF-8), précédée de
la date du relevé.
"""

import argparse
import datetime
import os
import sys
from pathlib import Path

import torch
from forge.modele.config import PRESETS, ConfigModele, nombre_parametres

from transformer_pas_a_pas.compter import repartition

FINE = "\u202f"  # l'espace fine insécable de la typographie française
SEUIL = 1e-12
CONFIG_DE_COMPARAISON = ConfigModele(dim=32, couches=2, tetes=4, longueur_contexte=16, taille_vocabulaire=50)
GRAINE = 0
NOMS_DES_PIECES = {
    "rmsnorm": "RMSNorm",
    "rope": "RoPE",
    "attention": "attention",
    "swiglu": "SwiGLU",
    "bloc": "un bloc",
    "modele": "le modèle entier",
}
NOMS_DES_FAMILLES = {
    "plongement": "plongement (et sortie, liée)",
    "attention": "attention",
    "mlp": "MLP SwiGLU",
    "normes": "RMSNorm",
}


def nombre(n: int) -> str:
    """Un entier à la française : les milliers séparés par une espace fine."""
    return f"{n:,}".replace(",", FINE)


def ecart_en_francais(x: float) -> str:
    """Un écart en notation scientifique à la française (« 4,4e-16 »), ou « 0 » s'il est nul."""
    return "0" if x == 0 else f"{x:.1e}".replace(".", ",")


def pourcent(part: int, total: int) -> str:
    return f"{100 * part / total:.1f}".replace(".", ",") + f"{FINE}%"


def lignes_de_comparaison() -> tuple[list[str], bool]:
    """Les lignes de la sortie de `comparer`, et si toutes les pièces sont sous le seuil."""
    from transformer_pas_a_pas.comparer import ecarts

    c = CONFIG_DE_COMPARAISON
    resultat = ecarts(c, GRAINE)
    identique = all(e <= SEUIL for e in resultat.values())
    lignes = [
        "Le transformer de ton IA refait pièce par pièce, comparé au module correspondant de forge",
        f"  modèle de comparaison{FINE}: {c.couches} couches, dim {c.dim}, {c.tetes} têtes, "
        f"contexte {c.longueur_contexte}, vocabulaire {c.taille_vocabulaire} (graine {GRAINE}, poids tirés avec un écart-type de 0,2)",
        f"  calculé en float64 sur le processeur, avec PyTorch {torch.__version__.split('+')[0]}, "
        f"{os.cpu_count()} cœurs logiques",
        f"  forge calcule RMSNorm et RoPE en float32, même dans un modèle en float64{FINE}: les pièces le refont aux mêmes endroits",
        "Plus grand écart avec forge, pièce par pièce",
    ]
    largeur = max(len(nom) for nom in NOMS_DES_PIECES.values())
    for cle, nom in NOMS_DES_PIECES.items():
        lignes.append(f"  {nom.ljust(largeur)}{FINE}: {ecart_en_francais(resultat[cle])}")
    lignes.append(f"identique à forge à 10⁻¹² près{FINE}: {'oui' if identique else 'non'}")
    return lignes, identique


def lignes_de_comptage(nom: str) -> list[str]:
    config = PRESETS[nom]
    r = repartition(config)
    total = sum(r.values())
    lignes = [
        f"Les paramètres du preset «{FINE}{nom}{FINE}» de forge{FINE}: {config.couches} couches, dim {config.dim}, "
        f"{config.tetes} têtes, vocabulaire {nombre(config.taille_vocabulaire)}"
    ]
    largeur = max(len(n) for n in NOMS_DES_FAMILLES.values())
    for cle, famille in NOMS_DES_FAMILLES.items():
        lignes.append(f"  {famille.ljust(largeur)}{FINE}: {nombre(r[cle]).rjust(14)}  ({pourcent(r[cle], total)})")
    lignes.append(f"  total{FINE}: {nombre(total)}")
    egal = total == nombre_parametres(config)
    lignes.append(f"égal au nombre de paramètres de forge{FINE}: {'oui' if egal else 'non'}")
    return lignes


def ecrire_en_utf8() -> None:
    """La sortie en UTF-8 (sous Windows, la console redirigée écrit sinon en cp1252)."""
    for flux in (sys.stdout, sys.stderr):
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8")


def commande_comparer(options: argparse.Namespace) -> int:
    lignes, identique = lignes_de_comparaison()
    print("\n".join(lignes))
    if options.enregistrer:
        chemin = Path(options.enregistrer)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        with chemin.open("w", encoding="utf-8", newline="\n") as fichier:
            fichier.write(f"# relevé le {datetime.date.today().isoformat()}\n" + "\n".join(lignes) + "\n")
    return 0 if identique else 1


def commande_compter(options: argparse.Namespace) -> int:
    print("\n".join(lignes_de_comptage(options.preset)))
    return 0


def main(argv: list[str] | None = None) -> int:
    ecrire_en_utf8()
    lecteur = argparse.ArgumentParser(
        prog="python -m transformer_pas_a_pas",
        description="Compare le transformer refait pièce par pièce à celui de forge, et compte ses paramètres.",
    )
    commandes = lecteur.add_subparsers(dest="commande", required=True)
    comparer = commandes.add_parser("comparer", help="compare chaque pièce au module de forge")
    comparer.add_argument("--enregistrer", metavar="FICHIER", help="écrit aussi la sortie dans FICHIER (UTF-8), précédée de la date du relevé")
    comparer.set_defaults(fonction=commande_comparer)
    compter = commandes.add_parser("compter", help="compte les paramètres d'une taille de forge")
    compter.add_argument("--preset", choices=list(PRESETS), default="tres_grand", help="la taille de forge (par défaut tres_grand)")
    compter.set_defaults(fonction=commande_compter)
    options = lecteur.parse_args(argv)
    return options.fonction(options)


if __name__ == "__main__":
    raise SystemExit(main())
