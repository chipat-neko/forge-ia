"""Le notebook Colab du chapitre 1.9 doit s'exécuter de bout en bout.

Rien n'est publié sans avoir tourné : le test exécute une copie en mémoire du notebook (le fichier du dépôt
reste sans sorties) dans le noyau « python3 » de l'environnement uv, avec FORGE_IA_LOCAL à la racine du dépôt :
le notebook prend le code du projet et de forge, sans rien télécharger ni installer. Il tourne sur le
processeur : la carte graphique est cachée.

Le notebook ne parle pas encore à ton-ia-1.9, qui n'est pas publiée : sa section vient avec la parution du
chapitre. Les verdicts de la cellule du petit GRPO sont calculés par le code, jamais écrits dans la prose : le test
vérifie qu'ils sont imprimés (oui ou non), pas qu'ils valent « oui ».
"""

import json
import pathlib
import re

import nbformat
import pytest
from nbclient import NotebookClient

PROJET = pathlib.Path(__file__).resolve().parents[1]
RACINE = pathlib.Path(__file__).resolve().parents[3]
NOTEBOOK = RACINE / "notebooks" / "1.9-raisonnement.ipynb"


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
    return re.search(r"```python\n(def avantage.*?)\n```", correction.source, re.DOTALL).group(1)


def avec_la_correction(nb) -> None:
    """Remplace, dans la cellule de l'exercice, la fonction à écrire par la correction."""
    exercice = next(c for c in nb.cells if c.cell_type == "code" and "Défi réussi" in c.source)
    correction = correction_de_l_exercice(nb)
    exercice.source = re.sub(r"def avantage\(recompenses\):.*?return \[\]\n", lambda _: correction + "\n", exercice.source, count=1, flags=re.DOTALL)
    assert "return []\n" not in exercice.source.split("groupes = [")[0]


def test_notebook_s_execute_de_bout_en_bout_avec_la_correction():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    avec_la_correction(nb)
    sorties = executer(nb)
    assert "Ce carnet calcule sur le processeur, avec PyTorch" in sorties
    assert "Ce carnet a tourné sur le processeur." in sorties
    # 1. Un problème, sa trace, sa conversation : les verdicts viennent du code.
    assert "Problème achats-2-7 :" in sorties
    assert "Chaque étape est un calcul juste : True. La dernière étape donne la réponse : True." in sorties
    assert "L’énoncé n’est jamais appris : True. La pensée et la réponse le sont : True." in sorties
    # 2. Huit réponses, et le même verdict que la forge.
    assert len(re.findall(r"^\s+(juste|fausse)\s+lu ", sorties, re.MULTILINE)) == 8
    assert "Même verdict que la forge : True" in sorties
    # 3. L'avantage d'un groupe, à la main et dans la forge.
    assert "À la main et dans la forge, à 10⁻¹² près : True" in sorties and "Les avantages somment à zéro : True" in sorties
    assert "Un groupe de 8 réponses toutes justes : avantages [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]" in sorties
    # L'exercice.
    assert "Défi réussi" in sorties and "Pas encore" not in sorties
    # 4. Un groupe sans signal n'apprend rien : la formule et le dénombrement s'accordent.
    assert "Égaux à 10⁻¹² près : True" in sorties
    assert "Si p = 0, un groupe de 16 réponses est sans signal avec la chance 1,00" in sorties
    # 5. Le petit GRPO : les verdicts sont imprimés, pas écrits d'avance.
    assert "Le petit GRPO a tourné sur cpu, 20 pas" in sorties
    assert re.search(r"Réglages : modèle de 2 couches et de vecteurs de 32 nombres, affiné \d+ pas ; à chaque pas 8 chiffres × 8 réponses de 4 jetons au plus", sorties)
    assert len(re.findall(r"Elle a monté : (oui|non)\.", sorties)) == 1 and len(re.findall(r"Elle a baissé : (oui|non)\.", sorties)) == 1
    verdict = re.search(r"La réussite en glouton a (monté|baissé|pas bougé) \(de (\d+) % à (\d+) %\)\.", sorties)
    assert verdict, "le verdict sur la réussite en glouton manque"
    avant, apres = int(verdict[2]), int(verdict[3])
    assert verdict[1] == ("monté" if apres > avant else "baissé" if apres < avant else "pas bougé")
    assert re.search(r"Pas où aucun groupe n’avait de signal .*: \d+ sur 20\.", sorties)
    # La page du site retrouve les mêmes résultats.
    assert re.search(r"\d+ problèmes, \d+ textes, 10 groupes et 54 points de la grille comparés\.", sorties)
    assert "Même résultat que la page du site : oui" in sorties


def test_sans_la_correction_le_defi_n_est_pas_encore_reussi():
    # Seules la cellule de départ et celle de l'exercice tournent (l'exercice n'a besoin que de `avantages_a_la_main`).
    nb = nbformat.read(NOTEBOOK, as_version=4)
    codes = [c for c in nb.cells if c.cell_type == "code"]
    exercice = next(c for c in codes if "Défi réussi" in c.source)
    nb.cells = [codes[0], exercice]
    sorties = executer(nb)
    assert "Pas encore" in sorties and "Défi réussi" not in sorties


def test_la_correction_est_une_fonction_de_l_exercice():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    correction = correction_de_l_exercice(nb)
    assert correction.startswith("def avantage(recompenses):") and "avantages_a_la_main" not in correction


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
    # Il calcule sur le processeur, toujours (le modèle de l'étape 5 est minuscule).
    assert 'appareil = "cpu"' in code and "essai_grpo(appareil" in code


def test_notebook_n_importe_pas_le_projet_de_la_cinq():
    # Le carnet ne lit ni le journal d'un entraînement ni pre_entrainement : sur Colab, seul ce projet et forge sont sur sys.path.
    brut = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code = "\n".join("".join(c["source"]) for c in brut["cells"] if c["cell_type"] == "code")
    assert "pre_entrainement" not in code and "courbes" not in code and "resumer" not in code


def test_les_fichiers_que_le_notebook_lit_existent():
    assert (PROJET / "tests" / "attendus.json").exists()


def test_les_commentaires_du_notebook_n_ecrivent_pas_d_echappement():
    # Un commentaire est lu tel quel par l'élève : un échappement de l'espace fine s'y afficherait tel quel.
    brut = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    for c in brut["cells"]:
        if c["cell_type"] == "code":
            for ligne in "".join(c["source"]).split(chr(10)):
                if "#" in ligne:
                    assert "\\u202f" not in ligne.split("#", 1)[1], ligne


def test_les_nombres_de_la_prose_ne_sont_pas_tapes_a_la_main():
    # Les verdicts du petit GRPO sont imprimés par le code : la prose ne dit pas que la récompense monte, ni de combien.
    brut = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    prose = "\n".join("".join(c["source"]) for c in brut["cells"] if c["cell_type"] == "markdown")
    assert not re.search(r"(?i)la récompense (monte|a monté|augmente)", prose)
    assert not re.search(r"\d+\s?%", prose)  # aucun pourcentage de résultat tapé dans le texte



def test_les_reglages_du_petit_grpo_sont_lus_dans_le_code_pas_retapes_dans_le_carnet():
    # Le nombre de pas est une variable ; la taille du modèle et les réponses par chiffre viennent du résultat de essai_grpo
    # (donc de petit_grpo.py), imprimés par le carnet : la prose ne les répète pas.
    brut = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code = "\n".join("".join(c["source"]) for c in brut["cells"] if c["cell_type"] == "code")
    prose = "\n".join("".join(c["source"]) for c in brut["cells"] if c["cell_type"] == "markdown")
    assert "pas_de_grpo = 20" in code and "essai_grpo(appareil, pas=pas_de_grpo)" in code and 'resultat["reglages"]' in code
    assert not re.search(r"(?i)\b(huit|vingt|seize)\b|\d+ couches|\d+ nombres", prose)


def test_la_prose_distingue_recompense_tiree_et_reussite_en_glouton_et_ne_promet_pas_les_memes_nombres():
    brut = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    prose = "\n".join("".join(c["source"]) for c in brut["cells"] if c["cell_type"] == "markdown")
    assert "température 1" in prose and "la plus probable" in prose and "à mi-chemin" in prose
    assert "partout les mêmes nombres" not in json.dumps(brut)
