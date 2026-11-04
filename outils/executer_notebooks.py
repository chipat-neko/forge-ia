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

Un notebook échoue s'il ne se lit pas, si une cellule lève une erreur ou
dépasse son délai, si le noyau s'arrête, ou si une de ses sorties contient une
ligne « Même … que la page du site : X » où X n'est pas « oui ». Le script
affiche une ligne par notebook (nom, durée, ok ou ÉCHEC), puis, pour un échec,
ce qui ne va pas et quoi faire ; il se termine avec le code 1 si un notebook
échoue.
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
from nbclient.exceptions import CellExecutionError, CellTimeoutError, DeadKernelError
from nbformat.reader import NotJSONError

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


def resume(erreur: BaseException) -> str:
    """Le type et la première ligne du message d'une erreur, sans point final, en
    160 caractères au plus."""
    message = str(erreur).strip().splitlines()
    texte = f"{type(erreur).__name__}: {message[0].rstrip('.')}" if message else type(erreur).__name__
    return texte if len(texte) <= 160 else texte[:159] + "…"


def verifier_noyau() -> None:
    """Le noyau « python3 » doit être ce Python : sinon les versions affichées mentent."""
    commande = KernelSpecManager().get_kernel_spec("python3").argv[0]
    # jupyter_client remplace « python », « python3 » ou « python3.13 » par ce Python.
    alias = {"python", f"python{sys.version_info[0]}", f"python{sys.version_info[0]}.{sys.version_info[1]}"}
    if commande not in alias and pathlib.Path(commande).resolve() != pathlib.Path(sys.executable).resolve():
        jupyter = pathlib.Path(sys.executable).with_name("jupyter.exe" if os.name == "nt" else "jupyter")
        raise SystemExit(
            f"Le noyau « python3 » lance {commande}, et non ce Python ({sys.executable}) : les versions "
            f"affichées ne seraient pas celles du notebook. Lance « {jupyter} kernelspec list » pour voir "
            "quel dossier fournit ce noyau, corrige ce dossier (ou la variable JUPYTER_PATH qui l'ajoute), "
            "puis relance ce script."
        )


def textes_affiches(cellule) -> list[str]:
    """Tout le texte affiché par une cellule de code : chaque flux (stdout, stderr)
    recollé d'un bloc, pour qu'une ligne écrite en plusieurs fois se lise entière,
    puis les résultats."""
    flux: dict[str, str] = {}
    resultats = []
    for sortie in cellule.get("outputs", []):
        if sortie.get("output_type") == "stream":
            nom = sortie.get("name", "stdout")
            flux[nom] = flux.get(nom, "") + sortie.get("text", "")
        elif sortie.get("output_type") in ("execute_result", "display_data"):
            resultats.append(sortie.get("data", {}).get("text/plain", ""))
    return [*flux.values(), *resultats]


def derniere_ligne_d_erreur(cellule, erreur: CellExecutionError) -> str:
    """La dernière ligne de la trace d'une cellule en erreur, comme Jupyter l'affiche."""
    for sortie in cellule.get("outputs", []) if cellule is not None else []:
        if sortie.get("output_type") == "error":
            lignes = "\n".join(COULEURS.sub("", ligne) for ligne in sortie.get("traceback", []))
            lignes = [ligne.strip() for ligne in lignes.splitlines() if ligne.strip()]
            if lignes:
                return lignes[-1]
    return f"{erreur.ename}: {erreur.evalue}"


def executer(chemin: pathlib.Path) -> list[str]:
    """Exécute une copie en mémoire du notebook ; renvoie ses fautes (vide si tout va bien).
    Chaque faute dit ce qui ne va pas et quoi faire."""
    nom = chemin.name
    try:
        nb = nbformat.read(chemin, as_version=4)
    except NotJSONError as erreur:
        # L'erreur de json (en dessous) dit où le fichier casse : ligne et colonne.
        return [
            f"{nom} : notebook illisible (JSON invalide) : {resume(erreur.__cause__ or erreur)}. "
            "Corrige le fichier, ou reprends sa dernière version enregistrée, puis relance."
        ]
    except Exception as erreur:  # encodage, format de notebook inconnu…
        return [
            f"{nom} : notebook illisible ({resume(erreur)}). Vérifie qu'il a bien été enregistré "
            "par Jupyter ou Colab, puis relance."
        ]

    # Le numéro (à partir de 1, cellules Markdown comprises) de la cellule en cours.
    en_cours = {"numero": 0}

    def suivre(cell, cell_index, **_):
        en_cours["numero"] = cell_index + 1

    # Un dossier de travail jetable, comme /content sur Colab : rien n'est écrit dans le dépôt.
    with tempfile.TemporaryDirectory(prefix="forge-ia-notebook-", ignore_cleanup_errors=True) as dossier:
        client = NotebookClient(
            nb,
            timeout=DELAI_PAR_CELLULE,
            kernel_name="python3",
            resources={"metadata": {"path": dossier}},
            on_cell_start=suivre,
        )
        try:
            client.execute()
        except CellExecutionError as erreur:
            numero = en_cours["numero"]
            cellule = nb.cells[numero - 1] if numero else None
            return [
                f"{nom}, cellule {numero} : {derniere_ligne_d_erreur(cellule, erreur)}. "
                "Ouvre le notebook dans Jupyter ou Colab pour voir toute la trace, corrige cette cellule "
                "(ou le code du projet qu'elle appelle), puis relance."
            ]
        except CellTimeoutError:
            return [
                f"{nom}, cellule {en_cours['numero']} : plus de {DELAI_PAR_CELLULE} s sans finir. "
                "Vérifie qu'elle n'attend pas une saisie et qu'elle ne tourne pas sans fin, "
                "allège-la si elle est seulement longue, puis relance."
            ]
        except DeadKernelError as erreur:
            return [
                f"{nom}, cellule {en_cours['numero']} : le noyau s'est arrêté ({resume(erreur)}). "
                "La cellule a peut-être épuisé la mémoire : allège-la, puis relance."
            ]
        except Exception as erreur:
            return [
                f"{nom}, cellule {en_cours['numero']} : l'exécution s'est arrêtée ({resume(erreur)}). "
                "Relance ; si ça recommence, exécute le notebook dans Jupyter pour voir où il bloque."
            ]

    fautes = []
    for numero, cellule in enumerate(nb.cells, start=1):
        if cellule.cell_type != "code":
            continue
        for texte in textes_affiches(cellule):
            for ligne in texte.splitlines():
                trouve = COMPARAISON.match(ligne)
                if trouve and trouve.group(2) != "oui":
                    fautes.append(
                        f"{nom}, cellule {numero} : « {trouve.group(1)} : {trouve.group(2)} » au lieu de "
                        "« oui » : le notebook ne retrouve pas le résultat du site. Compare son code à celui "
                        "du projet et à ses attendus, corrige l'écart, puis relance."
                    )
    return fautes


def main(arguments: list[str]) -> int:
    # La console Windows écrit en cp1252, qui ne connaît pas tous les caractères
    # qu'un notebook peut afficher (l'espace fine U+202F, par exemple).
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    notebooks = [pathlib.Path(a) for a in arguments] or sorted((RACINE / "notebooks").glob("*.ipynb"))
    if not notebooks:
        print("Aucun notebook à exécuter dans notebooks/ : vérifie que le script est lancé depuis le dépôt.", file=sys.stderr)
        return 1
    # Deux avertissements sans conséquence, qui noieraient le résultat : celui du
    # débogueur d'ipykernel (modules figés de Python), ici et dans le noyau, et, sous
    # Windows, celui de pyzmq sur la boucle d'événements.
    os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"
    warnings.filterwarnings("ignore", message="Proactor event loop", category=RuntimeWarning)
    # Les noyaux de cet environnement passent avant ceux de l'utilisateur : « python3 »
    # est celui de .colab, même si un autre Jupyter en a installé un.
    os.environ["JUPYTER_PREFER_ENV_PATH"] = "1"
    verifier_noyau()
    # Le notebook prend le code de ce dépôt au lieu de le télécharger.
    os.environ["FORGE_IA_LOCAL"] = str(RACINE)

    print(f"Python {platform.python_version()}, PyTorch {version('torch')}, numpy {version('numpy')}", flush=True)
    echecs = 0
    for chemin in notebooks:
        debut = time.perf_counter()
        if chemin.is_file():
            fautes = executer(chemin)
        else:
            fautes = [f"{chemin} : fichier introuvable. Vérifie le chemin (depuis la racine du dépôt), puis relance."]
        duree = f"{time.perf_counter() - debut:.1f}".replace(".", ",")
        print(f"{chemin.name}  {duree} s  {'ÉCHEC' if fautes else 'ok'}", flush=True)
        for faute in fautes:
            print(f"  {faute}", file=sys.stderr, flush=True)
        echecs += bool(fautes)
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
