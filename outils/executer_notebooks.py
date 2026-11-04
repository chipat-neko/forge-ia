"""Exécute les notebooks comme sur Colab, sans carte graphique.

Usage, depuis la racine du dépôt (voir la section « Notebooks » du README) :

    .colab\\Scripts\\python outils\\executer_notebooks.py [notebooks…]

Sans argument : tous les notebooks/*.ipynb. Le Python qui lance ce script est
celui de l'environnement .colab, qui reproduit l'image de Colab sans carte
(Python 3.13, torch 2.11.0+cpu, numpy 2.4.6 : voir outils/colab-sans-carte.txt).
Chaque notebook est exécuté dans une copie en mémoire (le fichier du dépôt reste
sans sorties), dans le noyau « python3 » de ce même Python, avec FORGE_IA_LOCAL
à la racine du dépôt : il prend le code du dépôt, et n'installe ni ne
télécharge rien.

Un notebook échoue si une cellule lève une erreur, ou si une de ses sorties
contient une ligne « Même … que la page du site : X » où X n'est pas « oui ».
Le script affiche une ligne par notebook (nom, durée, ok ou ÉCHEC) et se
termine avec le code 1 si un notebook échoue.
"""

import os
import pathlib
import platform
import re
import sys
import tempfile
import time
import warnings

import nbformat
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

RACINE = pathlib.Path(__file__).resolve().parents[1]
DELAI_PAR_CELLULE = 600  # secondes

# « Même résultat que la page du site : oui », avec une espace ordinaire ou
# fine insécable (U+202F) avant les deux-points.
COMPARAISON = re.compile(r"^(Même .+ que la page du site)[ \u202F]*:[ \u202F]*(.*?)\s*$")
# Les codes de couleur du terminal, dans les traces d'erreur d'IPython.
COULEURS = re.compile(r"\x1b\[[0-9;]*m")


def version(module: str) -> str:
    """La version d'un module de cet environnement, ou « absent » s'il ne s'importe pas."""
    try:
        return __import__(module).__version__
    except (ImportError, OSError):  # OSError : une bibliothèque de PyTorch qui ne se charge pas
        return "absent"


def verifier_noyau() -> None:
    """Le noyau « python3 » doit être ce Python : sinon les versions affichées mentent."""
    commande = KernelSpecManager().get_kernel_spec("python3").argv[0]
    # jupyter_client remplace « python », « python3 » ou « python3.13 » par ce Python.
    alias = {"python", f"python{sys.version_info[0]}", f"python{sys.version_info[0]}.{sys.version_info[1]}"}
    if commande not in alias and pathlib.Path(commande).resolve() != pathlib.Path(sys.executable).resolve():
        raise SystemExit(
            f"Le noyau « python3 » lance {commande}, et non ce Python ({sys.executable}). "
            "Supprime ce noyau (jupyter kernelspec remove python3), puis relance ce script."
        )


def textes_affiches(cellule) -> list[str]:
    """Tout le texte affiché par une cellule de code : flux et résultats."""
    textes = []
    for sortie in cellule.get("outputs", []):
        if sortie.get("output_type") == "stream":
            textes.append(sortie.get("text", ""))
        elif sortie.get("output_type") in ("execute_result", "display_data"):
            textes.append(sortie.get("data", {}).get("text/plain", ""))
    return textes


def derniere_ligne_d_erreur(nb) -> tuple[int, str]:
    """Le numéro (à partir de 1, cellules Markdown comprises) et la dernière ligne
    de la première cellule en erreur."""
    for numero, cellule in enumerate(nb.cells, start=1):
        for sortie in cellule.get("outputs", []):
            if sortie.get("output_type") == "error":
                lignes = [COULEURS.sub("", ligne).strip() for ligne in sortie.get("traceback", [])]
                lignes = [ligne for ligne in "\n".join(lignes).splitlines() if ligne.strip()]
                return numero, lignes[-1] if lignes else f"{sortie.get('ename')}: {sortie.get('evalue')}"
    return 0, "erreur sans cellule fautive (voir la trace ci-dessus)"


def executer(chemin: pathlib.Path) -> list[str]:
    """Exécute une copie en mémoire du notebook ; renvoie ses fautes (vide si tout va bien)."""
    nom = chemin.name
    nb = nbformat.read(chemin, as_version=4)
    # Un dossier de travail jetable, comme /content sur Colab : rien n'est écrit dans le dépôt.
    with tempfile.TemporaryDirectory(prefix="forge-ia-notebook-", ignore_cleanup_errors=True) as dossier:
        client = NotebookClient(
            nb,
            timeout=DELAI_PAR_CELLULE,
            kernel_name="python3",
            resources={"metadata": {"path": dossier}},
        )
        try:
            client.execute()
        except CellExecutionError:
            numero, ligne = derniere_ligne_d_erreur(nb)
            return [f"{nom}, cellule {numero} : {ligne}"]
        except Exception as erreur:  # délai dépassé, noyau arrêté…
            return [f"{nom} : l'exécution s'est arrêtée ({type(erreur).__name__} : {erreur})"]

    fautes = []
    for numero, cellule in enumerate(nb.cells, start=1):
        if cellule.cell_type != "code":
            continue
        for texte in textes_affiches(cellule):
            for ligne in texte.splitlines():
                trouve = COMPARAISON.match(ligne)
                if trouve and trouve.group(2) != "oui":
                    fautes.append(
                        f"{nom}, cellule {numero} : « {trouve.group(1)} : {trouve.group(2)} » "
                        "au lieu de « oui » : le notebook ne retrouve pas le résultat du site."
                    )
    return fautes


def main(arguments: list[str]) -> int:
    # La console Windows écrit en cp1252, qui ne connaît pas tous les caractères
    # qu'un notebook peut afficher (l'espace fine U+202F, par exemple).
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    notebooks = [pathlib.Path(a) for a in arguments] or sorted((RACINE / "notebooks").glob("*.ipynb"))
    if not notebooks:
        print("Aucun notebook à exécuter dans notebooks/.", file=sys.stderr)
        return 1
    # Deux avertissements sans conséquence, qui noieraient le résultat : celui du
    # débogueur d'ipykernel (modules figés de Python), ici et dans le noyau, et, sous
    # Windows, celui de pyzmq sur la boucle d'événements.
    os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"
    warnings.filterwarnings("ignore", message="Proactor event loop", category=RuntimeWarning)
    verifier_noyau()
    # Le notebook prend le code de ce dépôt au lieu de le télécharger.
    os.environ["FORGE_IA_LOCAL"] = str(RACINE)

    print(f"Python {platform.python_version()}, PyTorch {version('torch')}, numpy {version('numpy')}", flush=True)
    echecs = 0
    for chemin in notebooks:
        debut = time.perf_counter()
        fautes = [f"{chemin} : fichier introuvable."] if not chemin.is_file() else executer(chemin)
        duree = f"{time.perf_counter() - debut:.1f}".replace(".", ",")
        print(f"{chemin.name}  {duree} s  {'ÉCHEC' if fautes else 'ok'}", flush=True)
        for faute in fautes:
            print(f"  {faute}", file=sys.stderr, flush=True)
        echecs += bool(fautes)
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
