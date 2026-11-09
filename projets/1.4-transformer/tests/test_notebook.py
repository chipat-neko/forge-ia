"""Le notebook Colab du chapitre 1.4 doit s'exécuter de bout en bout.

Rien n'est publié sans avoir tourné : le test exécute une copie en mémoire du
notebook (le fichier du dépôt reste sans sorties) dans le noyau « python3 » de
l'environnement uv, avec FORGE_IA_LOCAL à la racine du dépôt : le notebook
prend le code du projet et de forge, sans rien télécharger. Il tourne sur le
processeur, sans carte graphique, et le dit.
"""

import json
import pathlib

import nbformat
import pytest
from nbclient import NotebookClient

RACINE = pathlib.Path(__file__).resolve().parents[3]
NOTEBOOK = RACINE / "notebooks" / "1.4-transformer.ipynb"
# La ligne de l'exercice au-dessus de laquelle le lecteur écrit sa fonction.
REPERE = "# Ne change rien en dessous"


@pytest.fixture(autouse=True)
def environnement(monkeypatch):
    # Le noyau hérite de ces variables : le dépôt local, et aucune carte visible.
    monkeypatch.setenv("FORGE_IA_LOCAL", str(RACINE))
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")


def sorties_de(nb) -> str:
    """Tout le texte affiché par les cellules de code, avec des espaces ordinaires."""
    texte = "".join(o.get("text", "") for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []))
    return texte.replace("\u202f", " ")


def executer(nb) -> str:
    NotebookClient(nb, timeout=300, kernel_name="python3").execute()
    return sorties_de(nb)


def test_notebook_s_execute_de_bout_en_bout():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    sorties = executer(nb)
    # Il dit sur quoi il a tourné.
    assert "Ce carnet calcule sur le processeur, avec PyTorch" in sorties
    assert "Ce carnet a tourné sur le processeur" in sorties
    # Les étapes : plongement, masque, têtes, RoPE, SwiGLU, bloc, modèle.
    assert "Les deux vecteurs sont identiques : True" in sorties
    assert "Le jeton 0 ne regarde que lui-même : True" in sorties
    assert "Les sorties des 5 premières positions ne changent pas : True" in sorties
    assert "Forme des poids : (4, 6, 6)" in sorties
    assert "Type des angles : torch.float32" in sorties
    assert "Identique à forge à 10⁻¹² près : oui" in sorties
    assert "La somme est celle de forge pour les cinq tailles : True" in sorties
    # La fonction de départ de l'exercice ne trouve rien : le défi n'est pas encore relevé.
    assert "Pas encore" in sorties
    assert "Défi réussi" not in sorties
    assert "Même répartition des paramètres que la page du site : oui" in sorties
    assert "Même tableau d’angles de RoPE que la page du site : oui" in sorties


def test_la_correction_de_l_exercice_reussit_le_defi():
    # La correction repliée est du texte : on recopie sa fonction dans la cellule de
    # l'exercice, à la place de celle du lecteur, et on vérifie qu'elle relève le défi.
    nb = nbformat.read(NOTEBOOK, as_version=4)
    correction = next(c for c in nb.cells if c.cell_type == "markdown" and "<details>" in c.source)
    fonction = correction.source.split("```python\n", 1)[1].split("```", 1)[0]
    assert fonction.startswith("def ma_softmax(")
    exercice = next(c for c in nb.cells if c.cell_type == "code" and "Défi réussi" in c.source)
    debut = exercice.source.index("def ma_softmax(")
    fin = exercice.source.index(REPERE)
    exercice.source = exercice.source[:debut] + fonction + "\n\n" + exercice.source[fin:]
    sorties = executer(nb)
    assert "Défi réussi" in sorties
    assert "Pas encore" not in sorties
    assert "Même répartition des paramètres que la page du site : oui" in sorties


def test_la_correction_n_utilise_pas_torch_softmax():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    correction = next(c for c in nb.cells if c.cell_type == "markdown" and "<details>" in c.source)
    fonction = correction.source.split("```python\n", 1)[1].split("```", 1)[0]
    assert "softmax(" not in fonction.replace("def ma_softmax(", "")


def test_notebook_est_enregistre_sans_sorties():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    codes = [c for c in nb.cells if c.cell_type == "code"]
    assert codes
    assert all(c.outputs == [] and c.execution_count is None for c in codes)


def test_notebook_n_installe_ni_torch_ni_forge_et_n_utilise_pas_la_carte():
    brut = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code = "\n".join("".join(c["source"]) for c in brut["cells"] if c["cell_type"] == "code")
    for interdit in ("pip install", "torch.accelerator", "torch.compile", ".cuda(", "cuda", "mps"):
        assert interdit not in code, interdit
    # Seule installation permise : git clone du dépôt, qui apporte forge.
    assert code.count("!git clone") == 1
