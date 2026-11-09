"""Le notebook Colab du chapitre 1.5 doit s'exécuter de bout en bout.

Rien n'est publié sans avoir tourné : le test exécute une copie en mémoire du
notebook (le fichier du dépôt reste sans sorties) dans le noyau « python3 » de
l'environnement uv, avec FORGE_IA_LOCAL à la racine du dépôt : le notebook
prend le code du projet et de forge, sans rien télécharger. Il tourne sur le
processeur : la carte graphique est cachée, et le notebook le dit.
"""

import json
import pathlib
import re

import nbformat
import pytest
from nbclient import NotebookClient

PROJET = pathlib.Path(__file__).resolve().parents[1]
RACINE = pathlib.Path(__file__).resolve().parents[3]
NOTEBOOK = RACINE / "notebooks" / "1.5-pre-entrainement.ipynb"
MINI_MD = RACINE / "docs" / "mesures" / "ton-ia-mini.md"
# La ligne de l'exercice au-dessus de laquelle le lecteur écrit sa fonction.
REPERE = "# Ne change rien en dessous"


@pytest.fixture(autouse=True)
def environnement(monkeypatch):
    # Le noyau hérite de ces variables : le dépôt local, et aucune carte visible.
    monkeypatch.setenv("FORGE_IA_LOCAL", str(RACINE))
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")
    monkeypatch.setenv("FORGE_APPAREIL", "cpu")


def sorties_de(nb) -> str:
    """Tout le texte affiché par les cellules de code, avec des espaces ordinaires."""
    texte = "".join(o.get("text", "") for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []))
    return texte.replace("\u202f", " ")


def executer(nb) -> str:
    NotebookClient(nb, timeout=600, kernel_name="python3").execute()
    return sorties_de(nb)


def correction_de_l_exercice(nb) -> str:
    cellule = next(c for c in nb.cells if c.cell_type == "markdown" and "<details>" in c.source)
    return cellule.source.split("```python\n", 1)[1].split("```", 1)[0]


def test_notebook_s_execute_de_bout_en_bout():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    sorties = executer(nb)
    # Il dit sur quoi il a tourné : sans carte, le processeur.
    assert "Ce carnet calcule sur le processeur, avec PyTorch" in sorties
    assert "Ce carnet a tourné sur le processeur." in sorties
    # 1. La perte d'un modèle neuf est proche de ln V.
    assert "ln V = ln 32 768 = 10,397" in sorties
    assert "Elle est proche du hasard : True" in sorties
    # 2. Le planning du taux : 60 pas, échauffement de 6, descente jusqu'au dixième du maximum.
    assert "60 pas, taux maximal 0,0010, échauffement de 6 pas" in sorties
    assert "Le taux final est le dixième du maximum : True" in sorties
    # 3. Un entraînement de 60 pas, raconté par son journal.
    assert "Pas faits : 60 sur 60, 61 440 jetons vus." in sorties
    assert "Une session, fin : fin." in sorties
    # 4. La pause et la reprise : la même perte, au bit près sur le processeur.
    assert "Écart des deux pertes : 0.0" in sorties
    assert "Les 30 pertes de la seconde moitié sont les mêmes une à une : True" in sorties
    assert "La reprise est exacte : oui" in sorties
    # 5. La version d'une heure, relevée dans le dépôt.
    assert "6 370 pas sur 6 370, 834 928 640 jetons vus, 0 pause." in sorties
    # L'exercice, dans son état de départ, n'est pas encore réussi.
    assert "Pas encore" in sorties
    assert "Défi réussi" not in sorties


def test_la_correction_de_l_exercice_reussit_le_defi():
    # La correction repliée est du texte : on recopie sa fonction dans la cellule de
    # l'exercice, à la place de celle du lecteur, et on vérifie qu'elle relève le défi.
    nb = nbformat.read(NOTEBOOK, as_version=4)
    fonction = correction_de_l_exercice(nb)
    assert fonction.startswith("def pas_de_la_pause(")
    exercice = next(c for c in nb.cells if c.cell_type == "code" and "Défi réussi" in c.source)
    debut = exercice.source.index("def pas_de_la_pause(")
    fin = exercice.source.index(REPERE)
    exercice.source = exercice.source[:debut] + fonction + "\n\n" + exercice.source[fin:]
    # Pas besoin de refaire les entraînements des étapes 3 et 4 : la préparation (la première cellule de code)
    # l'exercice et le nettoyage suffisent, et ménagent le processeur.
    preparation = next(c for c in nb.cells if c.cell_type == "code")
    nettoyage = [c for c in nb.cells if c.cell_type == "code"][-1]  # efface le dossier temporaire
    nb.cells = [preparation, exercice, nettoyage]
    sorties = executer(nb)
    assert "Défi réussi" in sorties
    assert "Pas encore" not in sorties


def test_la_correction_ne_passe_pas_par_les_sessions():
    # L'exercice se vérifie avec `journal.sessions` : sa correction ne doit pas s'en servir.
    nb = nbformat.read(NOTEBOOK, as_version=4)
    assert "sessions" not in correction_de_l_exercice(nb)


def test_les_commandes_du_notebook_sont_celles_de_la_version_courte():
    # Chaque commande « python -m forge … » du notebook est une ligne de docs/mesures/ton-ia-mini.md.
    nb = nbformat.read(NOTEBOOK, as_version=4)
    texte = "\n".join(c.source for c in nb.cells if c.cell_type == "markdown")
    commandes = re.findall(r"^uv run --extra gpu (python -m forge .+)$", texte, flags=re.M)
    assert [c.split()[3] for c in commandes] == ["donnees", "encoder", "entrainer", "evaluer", "entrainer"]
    lignes_du_document = MINI_MD.read_text(encoding="utf-8").splitlines()
    for commande in commandes[:4]:
        assert commande in lignes_du_document, commande
    # La reprise est la commande d'entraînement avec --reprendre.
    assert commandes[4] == commandes[2] + " --reprendre"


def test_notebook_est_enregistre_sans_sorties():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    codes = [c for c in nb.cells if c.cell_type == "code"]
    assert codes
    assert all(c.outputs == [] and c.execution_count is None for c in codes)


def test_notebook_n_installe_ni_torch_ni_forge_et_ne_force_pas_la_carte():
    brut = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code = "\n".join("".join(c["source"]) for c in brut["cells"] if c["cell_type"] == "code")
    for interdit in ("pip install torch", "torch.accelerator", "torch.compile", ".cuda(", "mps"):
        assert interdit not in code, interdit
    # Seules installations permises : git clone du dépôt, qui apporte forge, et la petite bibliothèque regex.
    assert code.count("!git clone") == 1
    assert re.findall(r"!pip install.*", code) == ["!pip install --quiet regex"]
    # Il choisit la carte seulement si PyTorch la voit (choisir_appareil), jamais de force.
    assert "choisir_appareil()" in code and '"cuda"' in code
