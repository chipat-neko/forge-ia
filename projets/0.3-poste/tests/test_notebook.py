"""Le notebook Colab du chapitre 0.3 doit s'exécuter de bout en bout.

Rien n'est publié sans avoir tourné : le test exécute une copie en mémoire du
notebook (le fichier du dépôt reste sans sorties) dans le noyau « python3 » de
l'environnement uv, avec FORGE_IA_LOCAL à la racine du dépôt : le notebook
prend le code du projet, sans rien télécharger. Ici, il tourne sans carte
(roue cpu) ; à la porte, avec la roue gpu, il tourne sur la carte et le dit.
"""

import pathlib
import re
import subprocess

import nbformat
import torch
from nbclient import NotebookClient

RACINE = pathlib.Path(__file__).resolve().parents[3]
NOTEBOOK = RACINE / "notebooks" / "0.3-poste.ipynb"
# La ligne de l'exercice au-dessus de laquelle le lecteur écrit sa fonction.
REPERE = "# Ne change rien en dessous"
DERNIERE_LIGNE = re.compile(r"^Diagnostic terminé : \d+ problème\(s\)\.$")


def sorties_de(nb) -> str:
    """Tout le texte affiché par les cellules de code, avec des espaces ordinaires."""
    texte = "".join(o.get("text", "") for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []))
    # Le notebook écrit l'espace fine insécable (U+202F) de la typographie française
    # avant les deux-points ; on la compare à une espace ordinaire.
    return texte.replace("\u202f", " ")


def executer(nb) -> str:
    NotebookClient(nb, timeout=300, kernel_name="python3").execute()
    return sorties_de(nb)


def code_du_notebook() -> str:
    return "".join(c.source for c in nbformat.read(NOTEBOOK, 4).cells if c.cell_type == "code")


def test_notebook_s_execute_de_bout_en_bout(monkeypatch):
    monkeypatch.setenv("FORGE_IA_LOCAL", str(RACINE))
    nb = nbformat.read(NOTEBOOK, as_version=4)
    sorties = executer(nb)
    assert "Ton poste" in sorties
    assert "Diagnostic" in sorties
    assert "processeur (cpu) :" in sorties
    if torch.cuda.is_available():
        assert "carte graphique (cuda) :" in sorties
        assert f"Ce carnet a tourné sur : la carte graphique, {torch.cuda.get_device_name(0)}." in sorties
    else:
        assert "Exécution > Modifier le type d’exécution > GPU" in sorties
        assert "Ce carnet a tourné sur : le processeur." in sorties
    # La fonction de départ de l'exercice ne fait rien : le défi n'est pas encore relevé.
    assert "Pas encore" in sorties
    assert "Même diagnostic que la page du site : oui" in sorties
    assert "Traceback" not in sorties
    # Le carnet finit par « Diagnostic terminé ».
    assert DERNIERE_LIGNE.match(sorties.rstrip("\n").splitlines()[-1])


def test_la_correction_de_l_exercice_reussit_le_defi(monkeypatch):
    # La correction repliée est du texte : on recopie sa fonction dans la cellule de
    # l'exercice, à la place de celle du lecteur, et on vérifie qu'elle relève le défi.
    monkeypatch.setenv("FORGE_IA_LOCAL", str(RACINE))
    nb = nbformat.read(NOTEBOOK, as_version=4)
    correction = next(c for c in nb.cells if c.cell_type == "markdown" and "<details>" in c.source)
    fonction = correction.source.split("```python\n", 1)[1].split("```", 1)[0]
    assert fonction.startswith("def nom_d_architecture(")
    exercice = next(c for c in nb.cells if c.cell_type == "code" and "Défi réussi" in c.source)
    debut = exercice.source.index("def nom_d_architecture(")
    fin = exercice.source.index(REPERE)
    exercice.source = exercice.source[:debut] + fonction + "\n\n" + exercice.source[fin:]
    sorties = executer(nb)
    assert "Défi réussi" in sorties
    assert "Pas encore" not in sorties


def test_notebook_sans_installation_de_torch_ni_api_recente():
    code = code_du_notebook()
    assert "pip install torch" not in code and "torch.accelerator" not in code and "torch.compile" not in code


def test_nvidia_smi_sans_trace_quand_il_manque(monkeypatch, capsys):
    # La cellule de nvidia-smi passe par subprocess, dans un try : sans pilote (Colab
    # sans carte, Mac, PC sans carte NVIDIA), elle le dit en une phrase.
    nb = nbformat.read(NOTEBOOK, as_version=4)
    cellule = next(c for c in nb.cells if c.cell_type == "code" and '"nvidia-smi"' in c.source)
    assert "!nvidia-smi" not in cellule.source and "except FileNotFoundError" in cellule.source

    def introuvable(*args, **kwargs):
        raise FileNotFoundError("nvidia-smi")

    monkeypatch.setattr(subprocess, "run", introuvable)
    exec(compile(cellule.source, "cellule nvidia-smi", "exec"), {})
    sortie = capsys.readouterr().out.replace("\u202f", " ")
    assert "nvidia-smi est introuvable" in sortie
    assert "Exécution > Modifier le type d’exécution > GPU" in sortie


def test_notebook_est_enregistre_sans_sorties():
    # Un fichier sans sorties ni numéros d'exécution : les différences git restent lisibles.
    nb = nbformat.read(NOTEBOOK, as_version=4)
    codes = [c for c in nb.cells if c.cell_type == "code"]
    assert codes
    assert all(c.outputs == [] and c.execution_count is None for c in codes)
