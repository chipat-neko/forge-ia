"""`python -m poste` : vérifier son poste, et dire quoi faire si quelque chose cloche.

    uv run --extra gpu python -m poste      avec une carte NVIDIA
    uv run --extra cpu python -m poste      sans carte NVIDIA
    … python -m poste --enregistrer sorties/processeur.txt

Le script affiche les faits du poste, le diagnostic, puis un essai de calcul
sur chaque appareil prêt. Il finit par « Diagnostic terminé : N problème(s). »,
et rend le code de sortie 1 s'il y a un problème. Sans PyTorch, il le dit,
sans trace Python.
"""

import argparse
import datetime
import sys

from poste.diagnostic import Constat, Niveau, decrire_constat, diagnostiquer
from poste.faits import Faits, decrire_faits, relever_faits


def lignes_de_l_essai(faits: Faits, constats: list[Constat]) -> list[str]:
    """L'essai de calcul sur le processeur, puis sur la carte si elle est prête."""
    if faits.torch is None:
        return ["Essai de calcul\u202f: impossible sans PyTorch."]
    # PyTorch est là : on peut importer ce qui s'en sert.
    from poste.appareil import AppareilIndisponible
    from poste.essai import TAILLE_ESSAI, decrire_essai, essai_de_calcul

    lignes = [
        f"Essai de calcul\u202f: deux matrices {TAILLE_ESSAI} × {TAILLE_ESSAI} multipliées en float32, "
        "comparées au calcul en float64"
    ]
    appareils = ["cpu"]
    if any(c.cle == "carte_prete" for c in constats):
        appareils.append("cuda")
    elif faits.cuda_disponible:
        lignes.append("  carte graphique (cuda)\u202f: pas d’essai, à cause du problème ci-dessus.")
    for appareil in appareils:
        try:
            lignes.append("  " + decrire_essai(essai_de_calcul(appareil)))
        except (AppareilIndisponible, RuntimeError) as erreur:
            premiere_ligne = str(erreur).strip().splitlines()[0] if str(erreur).strip() else type(erreur).__name__
            nom = "carte graphique" if appareil == "cuda" else "processeur"
            lignes.append(f"  {nom} ({appareil})\u202f: essai impossible. {premiere_ligne}")
    return lignes


def rapport() -> tuple[list[str], int]:
    """Les lignes du rapport, et le nombre de problèmes."""
    faits = relever_faits()
    constats = diagnostiquer(faits)
    problemes = sum(c.niveau == Niveau.PROBLEME for c in constats)
    lignes = [*decrire_faits(faits), "", "Diagnostic"]
    for c in constats:
        lignes.extend(decrire_constat(c))
    lignes += ["", *lignes_de_l_essai(faits, constats), "", f"Diagnostic terminé\u202f: {problemes} problème(s)."]
    return lignes, problemes


def ecrire_en_utf8() -> None:
    """Une console Windows redirigée vers un fichier écrit en cp1252, qui ne connaît pas
    l'espace fine (U+202F) : on passe alors la sortie en UTF-8, plutôt que de planter."""
    for flux in (sys.stdout, sys.stderr):
        try:
            "\u202f’".encode(flux.encoding or "ascii")
        except (UnicodeEncodeError, LookupError):
            if hasattr(flux, "reconfigure"):
                flux.reconfigure(encoding="utf-8")


def main(arguments: list[str] | None = None) -> int:
    lecteur = argparse.ArgumentParser(
        prog="python -m poste",
        description="Vérifie ton poste (Python, PyTorch, carte graphique et pilote), et dit quoi faire.",
    )
    lecteur.add_argument(
        "--enregistrer",
        metavar="FICHIER",
        help="écrit aussi la sortie dans FICHIER (UTF-8), précédée de la date du relevé",
    )
    options = lecteur.parse_args(arguments)
    ecrire_en_utf8()

    lignes, problemes = rapport()
    print("\n".join(lignes))
    if options.enregistrer:
        with open(options.enregistrer, "w", encoding="utf-8", newline="\n") as fichier:
            fichier.write(f"# relevé le {datetime.date.today().isoformat()}\n" + "\n".join(lignes) + "\n")
    return 1 if problemes else 0


if __name__ == "__main__":
    sys.exit(main())
