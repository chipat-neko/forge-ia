"""Le notebook Colab du chapitre 1.7 doit s'exécuter de bout en bout.

Rien n'est publié sans avoir tourné : le test exécute une copie en mémoire du notebook (le fichier du dépôt
reste sans sorties) dans le noyau « python3 » de l'environnement uv, avec FORGE_IA_LOCAL à la racine du dépôt :
le notebook prend le code du projet et de forge, sans rien télécharger ni installer. Il tourne sur le
processeur : la carte graphique est cachée.

L'étape 6 parle à ton-ia-1.7, la version publiée. À sa place, FORGE_IA_MODELES donne au notebook un dossier qui a
la forme de celui de l'intégration continue (`<dossier>/ton-ia-1.7/…`) : un petit modèle publié par forge.exporter.
Sans FORGE_IA_MODELES, la cellule télécharge les trois fichiers de la Release ; une coupure du réseau, simulée, se
reprend en relançant la cellule, sans retélécharger les fichiers déjà complets (point à surveiller 4 du plan 8).
"""

import copy
import json
import pathlib
import re

import nbformat
import pytest
from modele_factice import ETIQUETTE, exporter_comme_la_release, petit_modele
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

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
    # 6. Ton IA 1.7, prise dans FORGE_IA_MODELES (ici, le petit modèle publié comme elle), répond à trois questions.
    assert "Ton IA 1.7 est dans le dossier" in sorties and f"Version {ETIQUETTE}, " in sorties
    assert sorties.count("Toi : ") == 3 and sorties.count("Ton IA 1.7 : ") == 3
    assert "Toi : Quelle est la capitale de la France ?" in sorties
    assert sorties.count("(Elle a fini son tour.)") + sorties.count("(Coupée à 128 jetons : elle n’avait pas fini.)") == 3
    assert "s pour les trois réponses, sur le processeur." in sorties
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


def cellule_de_ton_ia(nb):
    codes = [c for c in nb.cells if c.cell_type == "code"]
    return codes[0], next(c for c in codes if "telecharger_publication(" in c.source)


def test_la_section_de_ton_ia_1_7_telecharge_la_release_et_repond_sur_le_processeur():
    brut = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code = "\n".join("".join(c["source"]) for c in brut["cells"] if c["cell_type"] == "code")
    assert 'telecharger_publication("ton-ia-1.7"' in code and "charger_publication(dossier_17, appareil)" in code
    assert "repondre_lot(" in code and "n_nouveaux=128" in code
    # L'étape 6 est annoncée dans le programme du notebook.
    assert "6. télécharger « ton IA 1.7 »" in "".join(brut["cells"][0]["source"]).replace("\u202f", " ")


def test_lance_par_les_tests_sans_forge_ia_modeles_il_ne_telecharge_rien(monkeypatch):
    # Avec FORGE_IA_LOCAL et sans FORGE_IA_MODELES, l'étape 6 s'arrête et dit quoi faire, au lieu de télécharger les
    # poids de ton IA pendant les tests.
    monkeypatch.delenv("FORGE_IA_MODELES")
    nb = nbformat.read(NOTEBOOK, as_version=4)
    nb.cells = list(cellule_de_ton_ia(nb))
    with pytest.raises(CellExecutionError) as erreur:
        executer(nb)
    assert "FORGE_IA_MODELES" in str(erreur.value) and "gh release download ton-ia-1.7" in str(erreur.value)
    assert "Ton IA 1.7 est dans le dossier" not in sorties_de(nb)


def test_une_coupure_du_telechargement_se_reprend_en_relancant_la_cellule(monkeypatch, tmp_path, modeles_factices):
    # Point à surveiller 4 : sur Colab (sans FORGE_IA_LOCAL ni FORGE_IA_MODELES), la cellule télécharge les trois fichiers
    # de la Release. Le réseau est simulé par une cellule ajoutée : urlretrieve de forge.publication copie les fichiers
    # du petit modèle, et coupe le dernier (le tokenizer) au milieu, la première fois. La cellule de l'étape 6 tourne deux
    # fois : la première échoue et dit de la relancer ; la deuxième ne télécharge que ce qui manque.
    monkeypatch.delenv("FORGE_IA_MODELES")
    source = modeles_factices / ETIQUETTE
    nb = nbformat.read(NOTEBOOK, as_version=4)
    premiere, ton_ia = cellule_de_ton_ia(nb)
    reseau = nbformat.v4.new_code_cell(
        "import shutil\n"
        "import urllib.error\n"
        "import forge.publication as publication\n"
        f"os.chdir({str(tmp_path)!r})\n"
        "depot_local = None  # le carnet se croit sur Colab : il télécharge\n"
        "appels = []\n"
        "def copie(adresse, destination):\n"
        "    nom = adresse.rsplit('/', 1)[1]\n"
        "    appels.append(nom)\n"
        f"    origine = Path({str(source)!r}) / nom\n"
        "    if nom.startswith('tokenizer') and appels.count(nom) == 1:\n"
        "        Path(destination).write_bytes(origine.read_bytes()[:1000])  # la moitié d'un fichier, puis la coupure\n"
        "        raise urllib.error.URLError('connexion coupée')\n"
        "    shutil.copyfile(origine, destination)\n"
        "publication.urlretrieve = copie\n"
        "def sans_api(*arguments, **options):\n"
        "    raise OSError('pas d’accès à l’API de GitHub')\n"
        "publication.urlopen = sans_api\n"
    )
    relance = copy.deepcopy(ton_ia)
    relance.id = "relance-de-la-cellule"
    bilan = nbformat.v4.new_code_cell("print('Appels :', appels)\nprint('Fichiers :', sorted(f.name for f in Path('ton-ia-1.7').iterdir()))")
    nb.cells = [premiere, reseau, ton_ia, relance, bilan]
    NotebookClient(nb, timeout=900, kernel_name="python3", allow_errors=True).execute()
    erreurs = [o for o in nb.cells[2].outputs if o.output_type == "error"]
    assert len(erreurs) == 1 and erreurs[0].ename == "ConnectionError"
    assert "Relance cette cellule\u202f: les fichiers déjà complets ne se retéléchargent pas." in erreurs[0].evalue
    # La relance : plus d'erreur, et ton IA répond.
    assert not [o for o in nb.cells[3].outputs if o.output_type == "error"]
    relancee = "".join(o.get("text", "") for o in nb.cells[3].outputs).replace("\u202f", " ")
    assert "Ton IA 1.7 est dans le dossier" in relancee and relancee.count("Ton IA 1.7 : ") == 3
    # Les poids et la configuration, complets, ne sont téléchargés qu'une fois ; seul le tokenizer coupé l'est deux fois.
    texte_du_bilan = "".join(o.get("text", "") for o in nb.cells[4].outputs)
    poids, config, tokenizer = f"{ETIQUETTE}.safetensors", "config.json", "tokenizer-ton-ia-v1.json"
    assert f"Appels : {[poids, config, tokenizer, tokenizer]!r}" in texte_du_bilan
    # Aucun fichier à moitié écrit ne reste.
    assert f"Fichiers : {sorted([poids, config, tokenizer])!r}" in texte_du_bilan


def test_les_fichiers_que_le_notebook_lit_existent():
    assert (PROJET / "tests" / "attendus.json").exists()
