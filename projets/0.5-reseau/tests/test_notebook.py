"""Le notebook Colab du chapitre 0.5 doit s'exécuter de bout en bout.

Rien n'est publié sans avoir tourné : le test exécute une copie en mémoire du
notebook (le fichier du dépôt reste sans sorties) dans le noyau « python3 » de
l'environnement uv, avec FORGE_IA_LOCAL à la racine du dépôt : le notebook
prend le code du projet, sans rien télécharger. Ici, il tourne sans carte
(roue cpu) ; à la porte, avec la roue gpu, il tourne aussi sur la carte et le dit.

Les lignes attendues sont recalculées ici avec les fonctions du paquet : si le
code change, le notebook doit changer avec lui.
"""

import json
import pathlib

import nbformat
import pytest
import torch
from nbclient import NotebookClient

from premier_reseau.a_la_main import (
    DONNEES,
    GRAINE,
    NB_PAS,
    TAUX,
    entrainer,
    gradient_moyen,
    initialiser,
    nb_poids,
    predictions,
)
from premier_reseau.attendus import CHEMIN_ATTENDUS
from premier_reseau.avec_pytorch import construire, gradients_pytorch, plus_grand_ecart
from premier_reseau.neurone import POINTS, PORTES, bien_classes, meilleur_reglage, sortie_seuil
from premier_reseau.nombres import en_francais, en_puissance_de_dix

RACINE = pathlib.Path(__file__).resolve().parents[3]
NOTEBOOK = RACINE / "notebooks" / "0.5-reseau.ipynb"
# La ligne de l'exercice que le lecteur remplace par sa réponse.
REPONSE = "ma_reponse = None"


@pytest.fixture(autouse=True)
def environnement(monkeypatch):
    # Le noyau hérite de ces variables : le dépôt local, et aucun FORGE_APPAREIL de la machine.
    monkeypatch.setenv("FORGE_IA_LOCAL", str(RACINE))
    monkeypatch.delenv("FORGE_APPAREIL", raising=False)


def sorties_de(nb) -> str:
    """Tout le texte affiché par les cellules de code."""
    return "".join(o.get("text", "") for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []))


def executer(nb) -> str:
    NotebookClient(nb, timeout=600, kernel_name="python3").execute()
    return sorties_de(nb)


def code_du_notebook() -> str:
    return "".join(c.source for c in nbformat.read(NOTEBOOK, 4).cells if c.cell_type == "code")


def reponses(historique) -> list[str]:
    """Les lignes des réponses d'un réseau entraîné, comme les écrit le notebook."""
    return [
        f"{x}\u202f: {p:.3f}, arrondi à {round(p)}, il faudrait {y}\n"
        for (x, y), p in zip(DONNEES, predictions(historique.reseau, DONNEES))
    ]


def lignes_attendues() -> list[str]:
    """Les lignes que le notebook doit afficher, tirées du paquet."""
    lignes = [f"{x}\u202f: le neurone répond {sortie_seuil((1.0, 1.0), -1.5, x)}\n" for x in POINTS]
    lignes.append(f"Points bien classés pour la porte ET\u202f: {bien_classes((1.0, 1.0), -1.5, 'et')} sur 4\n")
    for porte in PORTES:
        compte, poids, biais = meilleur_reglage(porte)
        lignes.append(f"{porte}\u202f: {compte} points sur 4 au mieux, avec les poids {poids} et le biais {biais}\n")
    depart = initialiser(GRAINE)
    lignes.append(f"{nb_poids(depart)} poids, tirés au hasard avec la graine {GRAINE}\u202f:\n")
    historique = entrainer(depart, DONNEES, TAUX, NB_PAS)
    lignes.append(f"Perte au départ\u202f: {en_francais(historique.pertes[0], 3)}\n")
    for numero in range(0, NB_PAS + 1, 250):
        perte = historique.pertes[numero]
        lignes.append(f"pas {en_francais(numero):>5}\u202f: {'█' * round(perte * 50):<45}{en_francais(perte, 3)}\n")
    lignes += reponses(historique)
    coince = entrainer(initialiser(1234), DONNEES, TAUX, NB_PAS)
    lignes.append(f"Graine 1234\u202f: perte finale {en_francais(coince.pertes[-1], 3)}\n")
    lignes += reponses(coince)
    ecart = plus_grand_ecart(gradient_moyen(depart, DONNEES), gradients_pytorch(construire(depart), DONNEES))
    lignes.append(f"PyTorch {torch.__version__}, plus grand écart avec les dérivées à la main\u202f: {en_puissance_de_dix(ecart)}\n")
    graines = json.loads(CHEMIN_ATTENDUS.read_text(encoding="utf-8"))["graines"]
    lignes.append(f"Graines qui apprennent le OU exclusif\u202f: {sum(g['reussit'] for g in graines)} sur {len(graines)}.\n")
    lignes.append(f"{en_francais(NB_PAS + 1)} pertes comparées à 10⁻⁹ près, et le reste au bit près.\n")
    return lignes


def test_notebook_s_execute_de_bout_en_bout():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    sorties = executer(nb)
    for ligne in lignes_attendues():
        assert ligne in sorties, ligne
    # PyTorch, sur le processeur : la durée n'est pas vérifiée, les écarts si.
    assert f"{en_francais(NB_PAS)} pas sur le processeur en " in sorties
    assert "Plus grand écart des poids finaux avec la main\u202f: " in sorties
    # L'appareil : la carte seulement si elle est là.
    if torch.cuda.is_available():
        assert "pas sur la carte graphique, " in sorties
        assert f"Ce carnet a tourné sur\u202f: la carte graphique, {torch.cuda.get_device_name(0)}." in sorties
    else:
        assert "Pas de carte graphique ici\u202f: PyTorch a tout calculé sur le processeur." in sorties
        assert "Exécution > Modifier le type d’exécution > GPU" in sorties
        assert "Ce carnet a tourné sur\u202f: le processeur." in sorties
    # La réponse de départ est vide : le défi n'est pas encore relevé.
    assert "Pas encore. Remplace None par True ou par False" in sorties and "Défi réussi" not in sorties
    assert "Même résultat que la page du site\u202f: oui" in sorties
    assert "Traceback" not in sorties
    # Le carnet finit par la phrase que lit la porte (tâche 16).
    if torch.cuda.is_available():
        attendue = f"Ce carnet a tourné sur\u202f: la carte graphique, {torch.cuda.get_device_name(0)}."
    else:
        attendue = "Ce carnet a tourné sur\u202f: le processeur."
    assert sorties.rstrip("\n").splitlines()[-1] == attendue


def test_la_correction_de_l_exercice_reussit_le_defi():
    # La correction repliée est du texte : on recopie sa ligne dans la cellule de
    # l'exercice, à la place de celle du lecteur, et on vérifie qu'elle relève le défi.
    nb = nbformat.read(NOTEBOOK, as_version=4)
    correction = next(c for c in nb.cells if c.cell_type == "markdown" and "<details>" in c.source)
    reponse = correction.source.split("```python\n", 1)[1].split("```", 1)[0].strip()
    assert reponse == "ma_reponse = False"
    exercice = next(c for c in nb.cells if c.cell_type == "code" and "Défi réussi" in c.source)
    assert exercice.source.count(REPONSE) == 1
    exercice.source = exercice.source.replace(REPONSE, reponse)
    sorties = executer(nb)
    # Un seul neurone caché coupe le plan par une seule droite : 3 points sur 4 au mieux, quelle que soit la graine.
    assert "Défi réussi\u202f: avec un seul neurone caché, le réseau classe au mieux " in sorties
    meilleur = int(sorties.split("le réseau classe au mieux ", 1)[1].split(" ", 1)[0])
    assert meilleur <= 3
    assert "Pas encore" not in sorties


def test_une_mauvaise_reponse_ne_releve_pas_le_defi():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    exercice = next(c for c in nb.cells if c.cell_type == "code" and "Défi réussi" in c.source)
    exercice.source = exercice.source.replace(REPONSE, "ma_reponse = True")
    sorties = executer(nb)
    assert "Pas encore. Avec un seul neurone caché, le réseau classe au mieux " in sorties
    assert "Défi réussi" not in sorties


def test_notebook_sans_installation_de_torch_ni_api_recente():
    code = code_du_notebook()
    assert "pip install torch" not in code and "torch.accelerator" not in code and "torch.compile" not in code
    # Rien à installer du tout : Colab a déjà PyTorch.
    assert "pip install" not in code and "%pip" not in code
    # nvidia-smi n'est pas lancé par « ! » : sans carte, la commande échouerait sans le dire clairement.
    assert "!nvidia-smi" not in code


def test_notebook_est_enregistre_sans_sorties():
    # Un fichier sans sorties ni numéros d'exécution : les différences git restent lisibles.
    nb = nbformat.read(NOTEBOOK, as_version=4)
    codes = [c for c in nb.cells if c.cell_type == "code"]
    assert codes
    assert all(c.outputs == [] and c.execution_count is None for c in codes)
