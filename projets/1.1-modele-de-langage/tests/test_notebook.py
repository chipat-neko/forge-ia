"""Le notebook Colab du chapitre 1.1 doit s'exécuter de bout en bout.

Rien n'est publié sans avoir tourné : le test exécute une copie en mémoire du
notebook (le fichier du dépôt reste sans sorties) dans le noyau « python3 » de
l'environnement uv, avec FORGE_IA_LOCAL à la racine du dépôt : le notebook
prend le code du projet, sans rien télécharger.
"""

import pathlib

import nbformat
from nbclient import NotebookClient

RACINE = pathlib.Path(__file__).resolve().parents[3]
NOTEBOOK = RACINE / "notebooks" / "1.1-modele-de-langage.ipynb"
# La ligne de l'exercice au-dessus de laquelle le lecteur écrit sa fonction.
REPERE = "# Ne change rien en dessous"


def sorties_de(nb) -> str:
    """Tout le texte affiché par les cellules de code, avec des espaces ordinaires."""
    texte = "".join(o.get("text", "") for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []))
    # Le notebook écrit l'espace fine insécable (U+202F) de la typographie française
    # avant les deux-points et entre les milliers ; on la compare à une espace ordinaire.
    return texte.replace("\u202f", " ")


def test_notebook_s_execute_de_bout_en_bout(monkeypatch):
    monkeypatch.setenv("FORGE_IA_LOCAL", str(RACINE))
    nb = nbformat.read(NOTEBOOK, as_version=4)
    NotebookClient(nb, timeout=300, kernel_name="python3").execute()
    sorties = sorties_de(nb)
    assert "Le texte du site fait" in sorties
    assert "perplexité" in sorties
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
    assert fonction.startswith("def le_plus_probable(")
    exercice = next(c for c in nb.cells if c.cell_type == "code" and "Défi réussi" in c.source)
    debut = exercice.source.index("def le_plus_probable(")
    fin = exercice.source.index(REPERE)
    exercice.source = exercice.source[:debut] + fonction + "\n\n" + exercice.source[fin:]
    NotebookClient(nb, timeout=300, kernel_name="python3").execute()
    sorties = sorties_de(nb)
    assert "Défi réussi" in sorties
    assert "Pas encore" not in sorties
    assert "Même résultat que la page du site : oui" in sorties


def test_notebook_est_enregistre_sans_sorties():
    # Un fichier sans sorties ni numéros d'exécution : les différences git restent lisibles.
    nb = nbformat.read(NOTEBOOK, as_version=4)
    codes = [c for c in nb.cells if c.cell_type == "code"]
    assert codes
    assert all(c.outputs == [] and c.execution_count is None for c in codes)
