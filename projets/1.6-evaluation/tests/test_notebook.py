"""Le notebook Colab du chapitre 1.6 doit s'exécuter de bout en bout.

Rien n'est publié sans avoir tourné : le test exécute une copie en mémoire du
notebook (le fichier du dépôt reste sans sorties) dans le noyau « python3 » de
l'environnement uv, avec FORGE_IA_LOCAL à la racine du dépôt : le notebook
prend le code des projets 1.5 et 1.6 et de forge, sans rien télécharger. Il tourne
sur le processeur : la carte graphique est cachée, et le notebook le dit.
"""

import json
import pathlib
import re

import nbformat
import pytest
from nbclient import NotebookClient

PROJET = pathlib.Path(__file__).resolve().parents[1]
RACINE = pathlib.Path(__file__).resolve().parents[3]
NOTEBOOK = RACINE / "notebooks" / "1.6-evaluation.ipynb"
MESURES = PROJET / "mesures"


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


def test_notebook_s_execute_de_bout_en_bout():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    sorties = executer(nb)
    assert "Ce carnet calcule sur le processeur, avec PyTorch" in sorties
    assert "Ce carnet a tourné sur le processeur." in sorties
    assert "après 60 pas d’entraînement" in sorties
    # 1. La perte à la main égale celle de PyTorch ; la perplexité est celle de « mini » à côté.
    assert "Elles sont égales à 10⁻¹² près : True" in sorties
    assert "ln 32 768 = 10,397" in sorties
    assert "la perte de validation est 3,428 et la perplexité 30,8" in sorties
    # 2. Les bits par octet de « mini » sont ceux du document.
    assert "Bits par octet de « mini » : 1,133" in sorties
    # 3. Le QCM noté sans écrire un mot : mêmes scores que forge, et six questions de MMMLU avec leur licence.
    assert "Mêmes scores que forge, à 10⁻⁵ près en relatif : True" in sorties
    assert "6 questions de openai/MMMLU (FR_FR), licence MIT : https://huggingface.co/datasets/openai/MMMLU" in sorties
    # 4. Les verdicts de « mini » sont ceux du relevé, et le piège de la petite série est dit.
    assert "hellaswag : 27,2 % sur 9 338 questions, hasard 25,0 %" in sorties
    assert "verdict : au-dessus (celui du relevé : au-dessus)" in sorties
    assert "verdict : pas-different (celui du relevé : pas-different)" in sorties
    assert "marge de la mesure ± 0,0 point (elle s’annule)" in sorties
    assert "marge du hasard ± 38,0 points" in sorties
    assert "31 bonnes réponses sur 100 (hasard 25 %) : pas-different" in sorties
    # 5. Des échantillons de « mini » et du petit modèle.
    assert "'Il était une fois' → , un jour, il était tombé en état." in sorties
    assert "Les 5 jetons les plus probables après « Il était une » pour le petit modèle" in sorties


def test_notebook_est_enregistre_sans_sorties():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    codes = [c for c in nb.cells if c.cell_type == "code"]
    assert codes
    assert all(c.outputs == [] and c.execution_count is None for c in codes)


def test_notebook_n_installe_ni_torch_ni_forge_et_ne_force_pas_la_carte():
    brut = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code = "\n".join("".join(c["source"]) for c in brut["cells"] if c["cell_type"] == "code")
    for interdit in ("pip install torch", "torch.accelerator", "torch.compile", ".cuda(", "mps", "cuda"):
        assert interdit not in code, interdit
    # Seules installations permises : git clone du dépôt, qui apporte forge, et la petite bibliothèque regex.
    assert code.count("!git clone") == 1
    assert re.findall(r"!pip install.*", code) == ["!pip install --quiet regex"]
    # Il calcule sur le processeur, toujours (le petit modèle n'a pas besoin de la carte).
    assert 'appareil = "cpu"' in code


def test_notebook_prend_le_modele_de_l_essai_du_chapitre_1_5():
    brut = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code = "\n".join("".join(c["source"]) for c in brut["cells"] if c["cell_type"] == "code")
    assert '"projets" / "1.5-pre-entrainement"' in code
    assert "from pre_entrainement.essai import" in code and "preparer_essai" in code and "essai_pause_reprise" in code
    assert code.index("preparer_essai(racine") < code.index("essai_pause_reprise(appareil, racine)")


def test_les_chiffres_de_mini_du_notebook_viennent_des_releves():
    # Le notebook lit mesures/evaluation-mini.json et mesures/qcm-mini.json : ils doivent exister.
    for nom in ("evaluation-mini.json", "qcm-mini.json"):
        assert (MESURES / nom).exists(), f"mesures/{nom} manque : relance la commande du README du projet."
