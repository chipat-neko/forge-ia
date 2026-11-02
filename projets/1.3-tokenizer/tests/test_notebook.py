"""Le notebook Colab du chapitre 1.3 doit s'exécuter de bout en bout.

Rien n'est publié sans avoir tourné : le test exécute une copie en mémoire du
notebook (le fichier du dépôt reste sans sorties) dans le noyau « python3 » de
l'environnement uv, donc avec le paquet et `regex` déjà installés.
"""

import pathlib
import re

import nbformat
from nbclient import NotebookClient

RACINE = pathlib.Path(__file__).resolve().parents[3]
NOTEBOOK = RACINE / "notebooks" / "1.3-tokenizer.ipynb"


def sorties_de(nb) -> str:
    """Tout le texte affiché par les cellules de code, avec des espaces ordinaires."""
    texte = "".join(o.get("text", "") for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []))
    # Le notebook écrit l'espace fine insécable (U+202F) de la typographie française
    # avant les deux-points ; on la compare à une espace ordinaire.
    return texte.replace(" ", " ")


def test_notebook_s_execute_de_bout_en_bout(monkeypatch):
    racine = pathlib.Path(__file__).resolve().parents[3]
    monkeypatch.setenv("FORGE_IA_LOCAL", str(racine))
    nb = nbformat.read(racine / "notebooks" / "1.3-tokenizer.ipynb", as_version=4)
    NotebookClient(nb, timeout=120, kernel_name="python3").execute()
    sorties = sorties_de(nb)
    assert "18 jetons" in sorties
    assert "Même résultat que la page du site : oui" in sorties


def test_la_correction_de_l_exercice_reussit_le_defi(monkeypatch):
    # La correction repliée est du texte : on la copie dans la cellule de l'exercice
    # et on vérifie qu'elle relève bien le défi (30 caractères ou plus, 12 jetons ou moins).
    monkeypatch.setenv("FORGE_IA_LOCAL", str(RACINE))
    nb = nbformat.read(NOTEBOOK, as_version=4)
    correction = next(c for c in nb.cells if c.cell_type == "markdown" and "<details>" in c.source)
    ligne = re.search(r"^ma_phrase = .*$", correction.source, re.MULTILINE).group(0)
    exercice = next(c for c in nb.cells if c.cell_type == "code" and "Défi réussi" in c.source)
    exercice.source = re.sub(r"^ma_phrase = .*$", lambda _: ligne, exercice.source, count=1, flags=re.MULTILINE)
    NotebookClient(nb, timeout=120, kernel_name="python3").execute()
    sorties = sorties_de(nb)
    assert "Défi réussi" in sorties
    assert "Pas encore" not in sorties


def test_notebook_est_enregistre_sans_sorties():
    # Un fichier sans sorties ni numéros d'exécution : les différences git restent lisibles.
    nb = nbformat.read(NOTEBOOK, as_version=4)
    codes = [c for c in nb.cells if c.cell_type == "code"]
    assert codes
    assert all(c.outputs == [] and c.execution_count is None for c in codes)
