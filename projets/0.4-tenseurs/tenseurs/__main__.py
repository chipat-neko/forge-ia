"""`python -m tenseurs` : les règles de forme, et les chronos du processeur et de la carte.

    uv run --extra cpu python -m tenseurs formes "(3, 1)" "(4,)"
    uv run --extra cpu python -m tenseurs mesurer --appareil cpu --sortie mesures/processeur.json
    uv run --extra gpu python -m tenseurs mesurer --appareil cuda --sortie mesures/rtx-5070-ti.json

`formes` dit quelle forme donnent a + b (la diffusion) et a @ b (le produit
matriciel), ou pourquoi c'est impossible. `mesurer` chronomètre un produit de
matrices et, avec `--sortie`, écrit les mesures en JSON (UTF-8, LF). Sans
carte, `--appareil cuda` dit quoi faire, sans trace Python, et rend le code 2.
"""

import argparse
import re
import sys
from pathlib import Path

from tenseurs.formes import forme_diffusee, forme_produit

ENTIER = re.compile(r"\d+", re.ASCII)


def lire_forme(texte: str) -> tuple[int, ...]:
    """« (3, 1) » donne (3, 1), « (4,) » ou « (4) » donne (4,), « () » donne (). ValueError sinon."""
    t = texte.strip()
    if t.startswith("(") and t.endswith(")"):
        t = t[1:-1]
    morceaux = [m.strip() for m in t.split(",")]
    if morceaux[-1] == "":
        morceaux.pop()  # la virgule de (4,), ou une forme vide
    if not texte.strip() or not all(ENTIER.fullmatch(m) for m in morceaux):
        raise ValueError(
            f"Forme illisible\u202f: «\u202f{texte}\u202f». Écris-la comme en Python, entre guillemets\u202f: "
            '"(3, 1)", "(4,)" pour un vecteur, ou "()" pour un nombre seul.'
        )
    return tuple(int(m) for m in morceaux)


def raison_sans_produit(a: tuple[int, ...], b: tuple[int, ...]) -> str:
    """Pourquoi a @ b est impossible."""
    if not a or not b:
        return "un nombre seul n’a pas de produit matriciel."
    interieure = b[-2] if len(b) >= 2 else b[0]
    if a[-1] != interieure:
        seule = " (la seule d’un vecteur)" if len(b) == 1 else ""
        return f"la dernière dimension de gauche, {a[-1]}, n’est pas l’avant-dernière de droite, {interieure}{seule}."
    return f"les dimensions de lot, {a[:-2]} et {b[:-2]}, ne se diffusent pas."


def lignes_des_formes(a: tuple[int, ...], b: tuple[int, ...]) -> list[str]:
    """Les deux règles pour a et b, une ligne chacune."""
    diffusion = forme_diffusee(a, b)
    if diffusion is None:
        ligne_diffusion = (
            f"Diffusion\u202f: {a} + {b} est impossible\u202f: alignées par la droite, deux dimensions "
            "diffèrent sans que l’une vaille 1."
        )
    else:
        ligne_diffusion = f"Diffusion\u202f: {a} + {b} donne {diffusion}."
    produit = forme_produit(a, b)
    if produit is None:
        ligne_produit = f"Produit matriciel\u202f: {a} @ {b} est impossible\u202f: {raison_sans_produit(a, b)}"
    else:
        seul = " (un nombre seul)" if produit == () else ""
        ligne_produit = f"Produit matriciel\u202f: {a} @ {b} donne {produit}{seul}."
    return [ligne_diffusion, ligne_produit]


def commande_formes(options: argparse.Namespace) -> int:
    try:
        a, b = lire_forme(options.a), lire_forme(options.b)
    except ValueError as erreur:
        print(erreur, file=sys.stderr)
        return 2
    print("\n".join(lignes_des_formes(a, b)))
    return 0


def commande_mesurer(options: argparse.Namespace) -> int:
    # PyTorch ne sert qu'ici : `formes` marche sans lui.
    from tenseurs.appareil import AppareilIndisponible, choisir_appareil
    from tenseurs.attendus import vers_json
    from tenseurs.chrono import TAILLES, decrire_mesures, entete, mesurer

    try:
        ou = choisir_appareil(options.appareil)
    except (AppareilIndisponible, ValueError) as erreur:
        print(erreur, file=sys.stderr)
        return 2
    print(entete(ou.type), flush=True)
    m = mesurer(ou.type, tailles=tuple(options.tailles or TAILLES))
    print("\n".join(decrire_mesures(m)))
    if options.sortie:
        chemin = Path(options.sortie)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        with open(chemin, "w", encoding="utf-8", newline="\n") as fichier:
            fichier.write(vers_json(m))
        print(f"Mesures écrites dans {chemin}.")
    return 0


def taille_positive(texte: str) -> int:
    if not ENTIER.fullmatch(texte) or int(texte) == 0:
        raise argparse.ArgumentTypeError(f"«\u202f{texte}\u202f» n’est pas une taille (un entier de 1 ou plus).")
    return int(texte)


def ecrire_en_utf8() -> None:
    """Une console Windows redirigée vers un fichier écrit en cp1252, qui ne connaît pas
    l'espace fine (U+202F) : on passe alors la sortie en UTF-8, plutôt que de planter."""
    for flux in (sys.stdout, sys.stderr):
        try:
            "\u202f’".encode(flux.encoding or "ascii")
        except (UnicodeEncodeError, LookupError):
            if hasattr(flux, "reconfigure"):
                flux.reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    lecteur = argparse.ArgumentParser(
        prog="python -m tenseurs",
        description="Les règles de forme de PyTorch, et les chronos du processeur et de la carte graphique.",
    )
    commandes = lecteur.add_subparsers(dest="nom_commande", required=True, metavar="{formes,mesurer}")
    formes = commandes.add_parser("formes", help="la forme de a + b et de a @ b")
    formes.add_argument("a", help='une forme, comme "(3, 1)"')
    formes.add_argument("b", help='une forme, comme "(4,)"')
    formes.set_defaults(executer=commande_formes)
    chronos = commandes.add_parser("mesurer", help="chronométrer un produit de matrices")
    chronos.add_argument(
        "--appareil", help="auto (par défaut, sauf si FORGE_APPAREIL est réglée), cpu ou cuda", default=None
    )
    chronos.add_argument("--sortie", metavar="FICHIER", help="écrit aussi les mesures dans FICHIER (JSON, UTF-8)")
    chronos.add_argument(
        "--tailles", type=taille_positive, nargs="+", metavar="N", help="les tailles des matrices (64 256 1024 2048 4096)"
    )
    chronos.set_defaults(executer=commande_mesurer)
    options = lecteur.parse_args(argv)
    ecrire_en_utf8()
    return options.executer(options)


if __name__ == "__main__":
    sys.exit(main())
