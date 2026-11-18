"""Le notebook Colab du chapitre 1.7 doit s'exécuter de bout en bout.

Rien n'est publié sans avoir tourné : le test exécute une copie en mémoire du notebook (le fichier du dépôt
reste sans sorties) dans le noyau « python3 » de l'environnement uv, avec FORGE_IA_LOCAL à la racine du dépôt :
le notebook prend le code du projet et de forge, sans rien télécharger ni installer. Il tourne sur le
processeur : la carte graphique est cachée.

Le notebook ne parle pas encore à ton-ia-1.7, qui n'est pas publiée : sa section vient avec la parution du
chapitre. FORGE_IA_MODELES est pourtant déjà posée sur un dossier qui a la forme de celui du dépôt
(`<dossier>/ton-ia-1.7/…`, un petit modèle publié par forge.exporter) : la section n'aura qu'à s'en servir.
"""

import json
import pathlib
import re

import nbformat
import pytest
from modele_factice import ETIQUETTE, exporter_comme_la_release, petit_modele
from nbclient import NotebookClient

PROJET = pathlib.Path(__file__).resolve().parents[1]
RACINE = pathlib.Path(__file__).resolve().parents[3]
NOTEBOOK = RACINE / "notebooks" / "1.7-conversation.ipynb"


@pytest.fixture(scope="module")
def modeles_factices(tmp_path_factory) -> pathlib.Path:
    """Un dossier à la forme de FORGE_IA_MODELES : le petit modèle des tests, publié comme la version ton-ia-1.7."""
    dossier = tmp_path_factory.mktemp("modeles")
    exporter_comme_la_release(petit_modele(), dossier / ETIQUETTE)
    return dossier


@pytest.fixture(autouse=True)
def environnement(monkeypatch, modeles_factices):
    # Le noyau hérite de ces variables : le dépôt local, les modèles factices, et aucune carte visible.
    monkeypatch.setenv("FORGE_IA_LOCAL", str(RACINE))
    monkeypatch.setenv("FORGE_IA_MODELES", str(modeles_factices))
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
    NotebookClient(nb, timeout=900, kernel_name="python3").execute()
    return sorties_de(nb)


def correction_de_l_exercice(nb) -> str:
    """La fonction de la correction repliée (`<details>`), telle qu'on la copie dans la cellule de l'exercice."""
    correction = next(c for c in nb.cells if c.cell_type == "markdown" and "<details>" in c.source)
    return re.search(r"```python\n(def jetons_appris.*?)\n```", correction.source, re.DOTALL).group(1)


def avec_la_correction(nb) -> None:
    """Remplace, dans la cellule de l'exercice, la fonction à écrire par la correction."""
    exercice = next(c for c in nb.cells if c.cell_type == "code" and "Défi réussi" in c.source)
    correction = correction_de_l_exercice(nb)
    exercice.source = re.sub(
        r"def jetons_appris\(exemple\):.*?return 0\n", lambda _: correction + "\n", exercice.source, count=1, flags=re.DOTALL
    )
    assert "return 0\n" not in exercice.source.split("exemples = [")[0]


def test_notebook_s_execute_de_bout_en_bout_avec_la_correction():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    avec_la_correction(nb)
    sorties = executer(nb)
    assert "Ce carnet calcule sur le processeur, avec PyTorch" in sorties
    assert "Ce carnet a tourné sur le processeur." in sorties
    # 1. Une conversation devient des jetons : seuls ceux de l'assistant sont appris.
    assert "<|fin_texte|>" in sorties and "ceux de l’assistant, après <|assistant|>." in sorties
    assert "Les jetons spéciaux de la conversation piégée : <|fin_texte|>, <|utilisateur|>, <|fin_tour|>, <|assistant|>, <|fin_tour|>" in sorties
    # L'exercice.
    assert "Défi réussi" in sorties and "Pas encore" not in sorties
    # 2. La perte masquée à la main égale celle de PyTorch.
    assert "Elles sont égales à 10⁻¹² près : True" in sorties
    # 3. L'empaquetage range plusieurs conversations par rangée, et la fuite se voit sans masque.
    assert "24 conversations, de " in sorties and "rangées de 129 jetons." in sorties
    assert "Sans le masque, B voit A : True" in sorties
    # 4. Un tout petit affinage : avant, aucune réponse ne finit son tour ; après, la plupart.
    assert "Réponses qui finissent par <|fin_tour|> : 0 % avant," in sorties
    assert "Perte d’affinage : " in sorties and "Les réponses du modèle affiné :" in sorties
    # La page du site retrouve les mêmes résultats.
    assert "6 conversations et 20 placements comparés." in sorties
    assert "Même résultat que la page du site : oui" in sorties


def test_sans_la_correction_le_defi_n_est_pas_encore_reussi():
    # Seules la première cellule de code (le tokenizer) et celle de l'exercice tournent : rien n'est entraîné.
    nb = nbformat.read(NOTEBOOK, as_version=4)
    codes = [c for c in nb.cells if c.cell_type == "code"]
    exercice = next(c for c in codes if "Défi réussi" in c.source)
    nb.cells = [codes[0], exercice]
    sorties = executer(nb)
    assert "Pas encore" in sorties and "Défi réussi" not in sorties


def test_la_correction_est_une_fonction_de_l_exercice():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    correction = correction_de_l_exercice(nb)
    assert correction.startswith("def jetons_appris(exemple):") and "exemple.appris" not in correction


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
    # Il calcule sur le processeur, toujours (le modèle de l'essai est minuscule).
    assert 'appareil = "cpu"' in code and 'essai_affinage(appareil, pas=80)' in code


def test_les_fichiers_que_le_notebook_lit_existent():
    assert (PROJET / "tests" / "attendus.json").exists()
