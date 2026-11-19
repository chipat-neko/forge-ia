"""Le notebook Colab du chapitre 1.8 doit s'exécuter de bout en bout.

Rien n'est publié sans avoir tourné : le test exécute une copie en mémoire du notebook (le fichier du dépôt
reste sans sorties) dans le noyau « python3 » de l'environnement uv, avec FORGE_IA_LOCAL à la racine du dépôt :
le notebook prend le code du projet et de forge, sans rien télécharger ni installer. Il tourne sur le
processeur : la carte graphique est cachée.

Le notebook ne parle pas encore à ton-ia-1.8, qui n'est pas publiée : sa section vient avec la parution du
chapitre. Aucune vraie paire n'existe non plus (`mesures/paires-exemples.json`) : l'étape 4 travaille sur une paire
fabriquée, et le dit.
"""

import json
import pathlib
import re

import nbformat
import pytest
from nbclient import NotebookClient

PROJET = pathlib.Path(__file__).resolve().parents[1]
RACINE = pathlib.Path(__file__).resolve().parents[3]
NOTEBOOK = RACINE / "notebooks" / "1.8-alignement.ipynb"


@pytest.fixture(autouse=True)
def environnement(monkeypatch):
    # Le noyau hérite de ces variables : le dépôt local, et aucune carte visible.
    monkeypatch.setenv("FORGE_IA_LOCAL", str(RACINE))
    # CUDA_VISIBLE_DEVICES=-1 cache la carte quand il y en a une (avec l'extra gpu), comme dans 0.4 et 0.5.
    # Une valeur vide ne suffit pas : sous Windows, une variable vide compte comme absente.
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "-1")
    monkeypatch.setenv("FORGE_APPAREIL", "cpu")


def sorties_de(nb) -> str:
    """Tout le texte affiché par les cellules de code, avec des espaces ordinaires."""
    texte = "".join(o.get("text", "") for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []))
    # Le notebook écrit l'espace fine insécable (U+202F) de la typographie française avant les deux-points.
    return texte.replace("\u202f", " ")


def executer(nb) -> str:
    # Le noyau démarre lentement quand le disque est occupé (D: est un disque USB) : on lui laisse cinq minutes, pas une.
    NotebookClient(nb, timeout=900, startup_timeout=300, kernel_name="python3").execute()
    return sorties_de(nb)


def correction_de_l_exercice(nb) -> str:
    """La fonction de la correction repliée (`<details>`), telle qu'on la copie dans la cellule de l'exercice."""
    correction = next(c for c in nb.cells if c.cell_type == "markdown" and "<details>" in c.source)
    return re.search(r"```python\n(def finit_par.*?)\n```", correction.source, re.DOTALL).group(1)


def avec_la_correction(nb) -> None:
    """Remplace, dans la cellule de l'exercice, la fonction à écrire par la correction."""
    exercice = next(c for c in nb.cells if c.cell_type == "code" and "Défi réussi" in c.source)
    correction = correction_de_l_exercice(nb)
    exercice.source = re.sub(
        r"def finit_par\(reponse, phrase\):.*?return False\n", lambda _: correction + "\n", exercice.source, count=1, flags=re.DOTALL
    )
    assert "return False\n" not in exercice.source.split("cas = [")[0]


def test_notebook_s_execute_de_bout_en_bout_avec_la_correction():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    avec_la_correction(nb)
    sorties = executer(nb)
    assert "Ce carnet calcule sur le processeur, avec PyTorch" in sorties
    assert "Ce carnet a tourné sur le processeur." in sorties
    # 1. Deux réponses, leur note, et la même note que la forge.
    assert "Même note que la forge : True" in sorties and "Même note que la forge : False" not in sorties
    assert "2 consignes sur 2" in sorties and "1 consigne sur 2" in sorties
    assert "A gagne : le premier critère qui diffère est « consignes »." in sorties
    # L'exercice.
    assert "Défi réussi" in sorties and "Pas encore" not in sorties
    # 2. Une paire, et deux jeux de notes qui n'en donnent pas.
    assert "La paire : la choisie est la réponse 0, la rejetée la réponse 3." in sorties
    assert "sans_paire donne « egalite »" in sorties and "sans_paire donne « aucune_bonne_reponse »" in sorties
    # 3. La perte DPO à la main égale celle de la forge.
    assert "Elles sont égales à 10⁻¹² près : True" in sorties
    assert "(DPO + SFT)" in sorties and "True (DPO + SFT)" in sorties
    # 4. Ce que la DPO pousse, sur une paire fabriquée : le carnet le dit.
    assert "Aucune vraie paire n’est encore publiée : ce carnet travaille sur une paire fabriquée." in sorties
    assert "DPO seule (β 0,1, 40 pas" in sorties and "DPO et terme SFT (β 0,1, 40 pas" in sorties
    assert sorties.count("La choisie a ") == 2 and sorties.count("la rejetée a ") == 2
    # La page du site retrouve les mêmes résultats.
    assert "40 textes et 27 points de la grille comparés." in sorties
    assert "Même résultat que la page du site : oui" in sorties


def test_sans_la_correction_le_defi_n_est_pas_encore_reussi():
    # Seules la cellule de départ et celle de l'exercice tournent (avec l'invite de l'étape 1 : l'exercice n'en dépend pas).
    nb = nbformat.read(NOTEBOOK, as_version=4)
    codes = [c for c in nb.cells if c.cell_type == "code"]
    exercice = next(c for c in codes if "Défi réussi" in c.source)
    nb.cells = [codes[0], exercice]
    sorties = executer(nb)
    assert "Pas encore" in sorties and "Défi réussi" not in sorties


def test_la_correction_est_une_fonction_de_l_exercice():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    correction = correction_de_l_exercice(nb)
    assert correction.startswith("def finit_par(reponse, phrase):") and "fin_imposee" not in correction


def test_notebook_est_enregistre_sans_sorties():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    codes = [c for c in nb.cells if c.cell_type == "code"]
    assert codes
    assert all(c.outputs == [] and c.execution_count is None for c in codes)


def test_notebook_n_installe_ni_torch_ni_forge_et_ne_force_pas_la_carte():
    brut = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code = "\n".join("".join(c["source"]) for c in brut["cells"] if c["cell_type"] == "code")
    for interdit in ("pip install torch", "torch.accelerator", "torch.compile", ".cuda(", "mps", "cuda", "datasets", "transformers", "tomli_w", "forge.mesure"):
        assert interdit not in code, interdit
    # Seules installations permises : git clone du dépôt, qui apporte forge, et la petite bibliothèque regex.
    assert code.count("!git clone") == 1
    assert re.findall(r"!pip install.*", code) == ["!pip install --quiet regex"]
    # Il calcule sur le processeur, toujours (le modèle de l'étape 4 est minuscule).
    assert 'appareil = "cpu"' in code and "modele_minuscule(contexte)" in code


def test_notebook_n_importe_pas_le_projet_de_la_cinq():
    # Le carnet ne touche ni au journal d'un entraînement ni à pre_entrainement : sur Colab, seul ce projet et forge sont sur sys.path.
    brut = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code = "\n".join("".join(c["source"]) for c in brut["cells"] if c["cell_type"] == "code")
    assert "pre_entrainement" not in code and "courbes" not in code


def test_les_fichiers_que_le_notebook_lit_existent():
    assert (PROJET / "tests" / "attendus.json").exists()
