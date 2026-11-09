"""Le notebook Colab du chapitre 1.2 doit s'exécuter de bout en bout.

Rien n'est publié sans avoir tourné : le test exécute une copie en mémoire du
notebook (le fichier du dépôt reste sans sorties) dans le noyau « python3 » de
l'environnement uv, avec FORGE_IA_LOCAL à la racine du dépôt : le notebook
prend le code du projet et lit les exemples, sans rien télécharger.
"""

import pathlib

import nbformat
from nbclient import NotebookClient

RACINE = pathlib.Path(__file__).resolve().parents[3]
NOTEBOOK = RACINE / "notebooks" / "1.2-donnees.ipynb"
# La ligne de l'exercice au-dessus de laquelle le lecteur écrit sa fonction.
REPERE = "# Ne change rien en dessous"


def sorties_de(nb) -> str:
    """Tout le texte affiché par les cellules de code, avec des espaces ordinaires."""
    texte = "".join(o.get("text", "") for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []))
    return texte.replace("\u202f", " ")


def test_notebook_s_execute_de_bout_en_bout(monkeypatch):
    monkeypatch.setenv("FORGE_IA_LOCAL", str(RACINE))
    nb = nbformat.read(NOTEBOOK, as_version=4)
    NotebookClient(nb, timeout=300, kernel_name="python3").execute()
    sorties = sorties_de(nb)
    assert "exemples du projet" in sorties  # en local, il lit les exemples et le dit
    assert "trop court" in sorties and "doublon" in sorties
    # La fonction de départ de l'exercice ne trouve rien : le défi n'est pas encore relevé.
    assert "Pas encore" in sorties
    assert "Défi réussi" not in sorties
    assert "Même résultat que la page du site : oui" in sorties


def test_la_correction_de_l_exercice_reussit_le_defi(monkeypatch):
    # La correction repliée est du texte : on recopie sa fonction dans la cellule de
    # l'exercice, à la place de celle du lecteur, et on vérifie qu'elle relève le défi.
    monkeypatch.setenv("FORGE_IA_LOCAL", str(RACINE))
    nb = nbformat.read(NOTEBOOK, as_version=4)
    correction = next(c for c in nb.cells if c.cell_type == "markdown" and "<details>" in c.source)
    fonction = correction.source.split("```python\n", 1)[1].split("```", 1)[0]
    assert fonction.startswith("def compter_les_raisons(")
    exercice = next(c for c in nb.cells if c.cell_type == "code" and "Défi réussi" in c.source)
    debut = exercice.source.index("def compter_les_raisons(")
    fin = exercice.source.index(REPERE)
    exercice.source = exercice.source[:debut] + fonction + "\n\n" + exercice.source[fin:]
    NotebookClient(nb, timeout=300, kernel_name="python3").execute()
    sorties = sorties_de(nb)
    assert "Défi réussi" in sorties
    assert "Pas encore" not in sorties
    assert "Même résultat que la page du site : oui" in sorties


def test_notebook_est_enregistre_sans_sorties():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    codes = [c for c in nb.cells if c.cell_type == "code"]
    assert codes
    assert all(c.outputs == [] and c.execution_count is None for c in codes)
    assert "torch" not in "\n".join(c.source for c in codes)
