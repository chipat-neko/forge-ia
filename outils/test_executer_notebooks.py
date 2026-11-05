"""Les messages d'échec d'executer_notebooks.py : où le notebook a échoué, et quoi faire.

Lancé par le job notebooks-colab (.github/workflows/python.yml), avec le Python de
l'environnement .colab, qui a pytest comme l'image de Colab :

    .colab\\Scripts\\python -m pytest -q outils

Aucun noyau n'est lancé : l'exécution de nbclient est remplacée par une fausse,
qui échoue avant la première cellule ou pendant l'une d'elles.
"""

import pathlib

import nbformat
import pytest
from nbclient.exceptions import DeadKernelError

import executer_notebooks


def notebook(dossier: pathlib.Path) -> pathlib.Path:
    """Un petit notebook : une cellule de texte, puis deux de code."""
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_markdown_cell("# Essai"),
        nbformat.v4.new_code_cell("print(1)"),
        nbformat.v4.new_code_cell("print(2)"),
    ]
    chemin = dossier / "essai.ipynb"
    nbformat.write(nb, chemin)
    return chemin


def faux_execute(index: int | None):
    """Une exécution qui commence la cellule `index` (aucune si None), puis voit le noyau s'arrêter."""

    def execute(self, **_):
        if index is not None:
            self.on_cell_start(cell=self.nb.cells[index], cell_index=index)
        raise DeadKernelError("Kernel died")

    return execute


def test_le_noyau_s_arrete_avant_la_premiere_cellule(monkeypatch, tmp_path):
    # Revue finale (T2) : un échec qui précède la première cellule (le noyau qui ne
    # démarre pas, par exemple) ne donne pas de numéro de cellule, jamais « cellule 0 ».
    monkeypatch.setattr(executer_notebooks.NotebookClient, "execute", faux_execute(None))
    [faute] = executer_notebooks.executer(notebook(tmp_path))
    assert "cellule 0" not in faute and "La cellule a peut-être" not in faute
    assert faute.startswith("essai.ipynb : le noyau s'est arrêté (DeadKernelError: Kernel died).")
    assert "avant la première cellule" in faute


def test_le_noyau_s_arrete_pendant_une_cellule(monkeypatch, tmp_path):
    # Pendant une cellule, son numéro (à partir de 1, cellules de texte comprises).
    monkeypatch.setattr(executer_notebooks.NotebookClient, "execute", faux_execute(2))
    [faute] = executer_notebooks.executer(notebook(tmp_path))
    assert faute == (
        "essai.ipynb, cellule 3 : le noyau s'est arrêté (DeadKernelError: Kernel died). "
        "La cellule a peut-être épuisé la mémoire : allège-la, puis relance."
    )


@pytest.mark.parametrize("numero", [0, 1, 12])
def test_lieu(numero):
    attendu = "essai.ipynb" if numero == 0 else f"essai.ipynb, cellule {numero}"
    assert executer_notebooks.lieu("essai.ipynb", numero) == attendu
