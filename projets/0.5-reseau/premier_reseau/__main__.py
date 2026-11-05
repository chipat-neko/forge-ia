"""`python -m premier_reseau entrainer` : le neurone à seuil, puis le réseau 2-2-1, à la main et avec PyTorch.

    uv run --extra cpu python -m premier_reseau entrainer --appareil cpu
    uv run --extra gpu python -m premier_reseau entrainer --appareil cuda
    … entrainer --appareil cpu --enregistrer sorties/processeur.txt

Le script affiche le meilleur réglage du neurone à seuil pour chaque porte,
l'entraînement à la main sur le OU exclusif, le plus grand écart entre les
gradients de départ calculés à la main et par PyTorch, puis l'entraînement
PyTorch sur l'appareil, sa durée, et le plus grand écart de ses poids finaux
avec ceux de la main. Sans carte, `--appareil cuda` dit quoi faire, sans
trace Python, et rend le code 2 ; de même sans PyTorch, ou avec une carte que
PyTorch voit sans savoir calculer dessus.
"""

import argparse
import datetime
import sys
from pathlib import Path

from premier_reseau.a_la_main import (
    DONNEES,
    GRAINE,
    NB_PAS,
    TAUX,
    entrainer,
    gradient_moyen,
    initialiser,
    nb_poids,
    predictions,
)
from premier_reseau.neurone import GRILLE, PORTES, meilleur_reglage
from premier_reseau.nombres import en_francais, en_puissance_de_dix, simple_en_francais

NOMS_DES_PORTES = {"et": "et", "ou": "ou", "ou_exclusif": "ou exclusif"}
NOMS_DES_APPAREILS = {"cpu": "le processeur", "cuda": "la carte graphique"}
TOUS_LES = 500  # la perte est affichée tous les 500 pas


def lignes_du_neurone() -> list[str]:
    """Le meilleur réglage de la grille pour chaque porte."""
    debut, fin = simple_en_francais(GRILLE[0]), simple_en_francais(GRILLE[-1])
    pas_de_grille = simple_en_francais(GRILLE[1] - GRILLE[0])
    lignes = [
        f"Le neurone à seuil, réglé au mieux sur la grille de {debut} à {fin} par pas de {pas_de_grille} "
        f"({en_francais(len(GRILLE) ** 3)} réglages)"
    ]
    for porte in PORTES:
        compte, (w1, w2), b = meilleur_reglage(porte)
        reglage = (
            f"w1 = {simple_en_francais(w1)}, w2 = {simple_en_francais(w2)} et b = {simple_en_francais(b)}"
        )
        if compte == len(PORTES[porte]):
            lignes.append(f"  {NOMS_DES_PORTES[porte]}\u202f: les {compte} points bien classés, avec {reglage}.")
        else:
            lignes.append(
                f"  {NOMS_DES_PORTES[porte]}\u202f: {compte} points sur {len(PORTES[porte])} au mieux, avec {reglage}"
                "\u202f: aucun réglage ne les classe tous."
            )
    return lignes


def lignes_a_la_main() -> list[str]:
    """L'entraînement à la main : la perte au départ, tous les TOUS_LES pas, à la fin, puis les prédictions."""
    depart = initialiser(GRAINE)
    historique = entrainer(depart, DONNEES, TAUX, NB_PAS)
    lignes = [
        "Le réseau 2-2-1, entraîné à la main sur le OU exclusif",
        f"  {nb_poids(depart)} poids tirés au hasard (graine {GRAINE}), taux {simple_en_francais(TAUX)}, "
        f"{en_francais(NB_PAS)} pas sur les {len(DONNEES)} points.",
    ]
    for numero in sorted({*range(0, NB_PAS + 1, TOUS_LES), NB_PAS}):
        lignes.append(f"  pas {en_francais(numero)}\u202f: perte {en_francais(historique.pertes[numero], 3)}")
    for (x, y), p in zip(DONNEES, predictions(historique.reseau, DONNEES)):
        lignes.append(f"  {x}\u202f: {f'{p:.3f}'.replace('.', ',')}, arrondi à {round(p)} (attendu\u202f: {y})")
    return lignes


def lignes_avec_pytorch(appareil: str) -> list[str]:
    """Les gradients de départ comparés, puis l'entraînement PyTorch sur l'appareil, comparé à la main."""
    import torch

    from premier_reseau.avec_pytorch import construire, entrainer_pytorch, gradients_pytorch, plus_grand_ecart

    depart = initialiser(GRAINE)
    ecart_gradients = plus_grand_ecart(gradient_moyen(depart, DONNEES), gradients_pytorch(construire(depart), DONNEES))
    a_la_main = entrainer(depart, DONNEES, TAUX, NB_PAS)
    par_pytorch = entrainer_pytorch(construire(depart), DONNEES, TAUX, NB_PAS, appareil)
    nom = NOMS_DES_APPAREILS[appareil]
    if appareil == "cuda":
        nom += f", {torch.cuda.get_device_name(0)}"
    return [
        f"Le même réseau dans PyTorch {torch.__version__}, en float64, avec les mêmes poids de départ",
        f"  Gradients de départ, à la main et par autograd\u202f: plus grand écart {en_puissance_de_dix(ecart_gradients)}.",
        f"  {en_francais(NB_PAS)} pas sur {nom} ({appareil})\u202f: {en_francais(par_pytorch.millisecondes)} ms.",
        f"  Perte finale {en_francais(par_pytorch.pertes[-1], 3)}, et plus grand écart des poids finaux avec la main\u202f: "
        f"{en_puissance_de_dix(plus_grand_ecart(a_la_main.reseau, par_pytorch.reseau))}.",
    ]


def ecrire_en_utf8() -> None:
    """Une console Windows redirigée vers un fichier écrit en cp1252, qui ne connaît pas
    l'espace fine (U+202F) : on passe alors la sortie en UTF-8, plutôt que de planter."""
    for flux in (sys.stdout, sys.stderr):
        try:
            "\u202f’".encode(flux.encoding or "ascii")
        except (UnicodeEncodeError, LookupError):
            if hasattr(flux, "reconfigure"):
                flux.reconfigure(encoding="utf-8")


def carte_inutilisable(erreur: RuntimeError) -> str:
    """Le message quand PyTorch voit la carte, mais ne sait pas calculer dessus : une carte trop
    ancienne ou trop récente pour sa version (le diagnostic du projet 0.3 dit laquelle)."""
    texte = str(erreur).strip()
    premiere_ligne = texte.splitlines()[0].rstrip(".") if texte else type(erreur).__name__
    return (
        f"La carte graphique n’a pas pu calculer avec cette version de PyTorch\u202f: {premiere_ligne}. "
        "Pour savoir pourquoi, lance `uv run --extra gpu python -m poste` dans le dossier projets/0.3-poste. "
        "Pour calculer sur le processeur, relance avec `--appareil cpu` (ou, sans `--appareil`, mets FORGE_APPAREIL=cpu)."
    )


def commande_entrainer(options: argparse.Namespace) -> int:
    try:
        from premier_reseau.appareil import AppareilIndisponible, choisir_appareil
    except ImportError:
        print(
            "PyTorch ne s’importe pas. Lance le script avec la version de PyTorch de ton poste\u202f: "
            "`uv run --extra cpu python -m premier_reseau entrainer`, ou `--extra gpu` avec une carte NVIDIA.",
            file=sys.stderr,
        )
        return 2
    try:
        ou = choisir_appareil(options.appareil)
    except (AppareilIndisponible, ValueError) as erreur:
        print(erreur, file=sys.stderr)
        return 2
    lignes: list[str] = []
    for section in (lignes_du_neurone, lignes_a_la_main, lambda: lignes_avec_pytorch(ou.type)):
        try:
            nouvelles = section()
        except RuntimeError as erreur:
            if ou.type != "cuda":
                raise  # sur le processeur, c'est un défaut du projet : sa trace entière doit se voir
            print(carte_inutilisable(erreur), file=sys.stderr)
            return 2
        if lignes:
            nouvelles = ["", *nouvelles]  # une ligne vide entre deux parties
        print("\n".join(nouvelles), flush=True)
        lignes += nouvelles
    if options.enregistrer:
        chemin = Path(options.enregistrer)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        with open(chemin, "w", encoding="utf-8", newline="\n") as fichier:
            fichier.write(f"# relevé le {datetime.date.today().isoformat()}\n" + "\n".join(lignes) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    # Avant argparse, qui écrit lui-même ses messages d'erreur.
    ecrire_en_utf8()
    lecteur = argparse.ArgumentParser(
        prog="python -m premier_reseau",
        description="Un neurone à seuil, puis un réseau 2-2-1 entraîné sur le OU exclusif, à la main et avec PyTorch.",
    )
    commandes = lecteur.add_subparsers(dest="nom_commande", required=True, metavar="{entrainer}")
    entrainement = commandes.add_parser("entrainer", help="le neurone, puis le réseau entraîné à la main et avec PyTorch")
    entrainement.add_argument(
        "--appareil", help="auto (par défaut, sauf si FORGE_APPAREIL est réglée), cpu ou cuda", default=None
    )
    entrainement.add_argument(
        "--enregistrer",
        metavar="FICHIER",
        help="écrit aussi la sortie dans FICHIER (UTF-8), précédée de la date du relevé",
    )
    options = lecteur.parse_args(argv)
    return commande_entrainer(options)


if __name__ == "__main__":
    sys.exit(main())
