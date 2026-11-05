"""Le notebook Colab du chapitre 0.4 doit s'exécuter de bout en bout.

Rien n'est publié sans avoir tourné : le test exécute une copie en mémoire du
notebook (le fichier du dépôt reste sans sorties) dans le noyau « python3 » de
l'environnement uv, avec FORGE_IA_LOCAL à la racine du dépôt : le notebook
prend le code du projet, sans rien télécharger. Ici, il tourne sans carte
(roue cpu) ; à la porte, avec la roue gpu, il tourne aussi sur la carte et le dit.
"""

import pathlib

import nbformat
import torch
from nbclient import NotebookClient

from tenseurs.exemples import exemple_calculer, exemple_creer, exemple_lire

RACINE = pathlib.Path(__file__).resolve().parents[3]
NOTEBOOK = RACINE / "notebooks" / "0.4-tenseurs.ipynb"
# La ligne de l'exercice que le lecteur remplace par sa prédiction.
PREDICTION = "ma_prediction = ()"


def sorties_de(nb) -> str:
    """Tout le texte affiché par les cellules de code."""
    return "".join(o.get("text", "") for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []))


def executer(nb) -> str:
    NotebookClient(nb, timeout=600, kernel_name="python3").execute()
    return sorties_de(nb)


def code_du_notebook() -> str:
    return "".join(c.source for c in nbformat.read(NOTEBOOK, 4).cells if c.cell_type == "code")


# Les étiquettes du notebook pour les valeurs d'exemple_calculer().
ETIQUETTES_CALCULER = {
    "somme": "a + b",
    "produit_case_par_case": "a * b",
    "produit_matriciel": "a @ b",
    "total": "a.sum()",
    "moyenne_par_colonne": "a.mean(dim=0)",
    "diffusion": "a + (100, 200)",
}


def lignes_attendues() -> list[str]:
    """Les lignes que le notebook doit afficher pour créer, lire et calculer, tirées d'exemples.py :
    si les exemples changent, le notebook doit changer avec eux."""
    lignes = [
        f"{nom}\u202f: forme {tuple(t.shape)}, {t.dim()} dimension(s), type {t.dtype}\n"
        for nom, t in exemple_creer().items()
    ]
    lignes += [f"{cle}\u202f: {valeur}\n" for cle, valeur in exemple_lire().items()]
    calcul = exemple_calculer()
    assert list(calcul) == list(ETIQUETTES_CALCULER), "une valeur d'exemple_calculer() n'a pas d'étiquette dans ce test"
    lignes += [f"{ETIQUETTES_CALCULER[cle]}\u202f: {valeur}\n" for cle, valeur in calcul.items()]
    return lignes


def test_notebook_s_execute_de_bout_en_bout(monkeypatch):
    monkeypatch.setenv("FORGE_IA_LOCAL", str(RACINE))
    nb = nbformat.read(NOTEBOOK, as_version=4)
    sorties = executer(nb)
    # Créer, lire, calculer : les mêmes valeurs que tenseurs/exemples.py, que montre le chapitre.
    for ligne in lignes_attendues():
        assert ligne in sorties, ligne
    # La diffusion et le produit : la règle du projet et PyTorch, côte à côte.
    assert "(3, 1) + (4,)\u202f: (3, 4) selon la règle, (3, 4) selon PyTorch." in sorties
    assert "(2, 3) + (3, 2)\u202f: impossible selon la règle, impossible selon PyTorch." in sorties
    assert "(3,) @ (3,)\u202f: () selon la règle, () selon PyTorch." in sorties
    # La mémoire.
    assert "(4096, 4096) en torch.float32\u202f: 67\u202f108\u202f864 octets, soit 64 Mo" in sorties
    assert "(4096, 4096) en torch.bfloat16\u202f: 33\u202f554\u202f432 octets, soit 32 Mo" in sorties
    # Les chronos : le processeur toujours, la carte seulement si elle est là.
    for taille in ["256 × 256", "1\u202f024 × 1\u202f024", "2\u202f048 × 2\u202f048"]:
        assert f"{taille}\u202f: processeur " in sorties
    if torch.cuda.is_available():
        assert ", carte " in sorties
        assert f"Ce carnet a tourné sur\u202f: la carte graphique, {torch.cuda.get_device_name(0)}." in sorties
    else:
        assert ", carte " not in sorties
        assert "Exécution > Modifier le type d’exécution > GPU" in sorties
        assert "Ce carnet a tourné sur\u202f: le processeur." in sorties
    # La prédiction de départ est vide : le défi n'est pas encore relevé.
    assert "Pas encore" in sorties and "Défi réussi" not in sorties
    assert "1\u202f521 paires de formes comparées" in sorties
    assert "Même règle que la page du site\u202f: oui" in sorties
    assert "Traceback" not in sorties
    # Le carnet finit par la phrase que lit la porte (tâche 16).
    assert sorties.rstrip("\n").splitlines()[-1].startswith("Ce carnet a tourné sur\u202f: ")


def test_la_correction_de_l_exercice_reussit_le_defi(monkeypatch):
    # La correction repliée est du texte : on recopie sa ligne dans la cellule de
    # l'exercice, à la place de celle du lecteur, et on vérifie qu'elle relève le défi.
    monkeypatch.setenv("FORGE_IA_LOCAL", str(RACINE))
    nb = nbformat.read(NOTEBOOK, as_version=4)
    correction = next(c for c in nb.cells if c.cell_type == "markdown" and "<details>" in c.source)
    reponse = correction.source.split("```python\n", 1)[1].split("```", 1)[0].strip()
    assert reponse == "ma_prediction = (2, 4, 3)"
    exercice = next(c for c in nb.cells if c.cell_type == "code" and "Défi réussi" in c.source)
    assert exercice.source.count(PREDICTION) == 1
    exercice.source = exercice.source.replace(PREDICTION, reponse)
    sorties = executer(nb)
    assert "Défi réussi\u202f: (2, 1, 3) + (4, 1) donne bien (2, 4, 3)." in sorties
    assert "Pas encore" not in sorties


def test_notebook_sans_installation_de_torch_ni_api_recente():
    code = code_du_notebook()
    assert "pip install torch" not in code and "torch.accelerator" not in code and "torch.compile" not in code
    # Rien à installer du tout : Colab a déjà PyTorch.
    assert "pip install" not in code and "%pip" not in code


def test_notebook_est_enregistre_sans_sorties():
    # Un fichier sans sorties ni numéros d'exécution : les différences git restent lisibles.
    nb = nbformat.read(NOTEBOOK, as_version=4)
    codes = [c for c in nb.cells if c.cell_type == "code"]
    assert codes
    assert all(c.outputs == [] and c.execution_count is None for c in codes)
