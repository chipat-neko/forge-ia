"""Le notebook Colab du chapitre 1.6 doit s'exécuter de bout en bout.

Rien n'est publié sans avoir tourné : le test exécute une copie en mémoire du
notebook (le fichier du dépôt reste sans sorties) dans le noyau « python3 » de
l'environnement uv, avec FORGE_IA_LOCAL à la racine du dépôt : le notebook
prend le code des projets 1.5 et 1.6 et de forge, sans rien télécharger. Pour
l'étape 6, à la place des poids de la version publiée ton-ia-1.5, FORGE_IA_MODELE
lui donne le petit modèle de `modele_factice`, publié de la même façon par
forge.exporter. Il tourne sur le processeur : la carte graphique est cachée, et
le notebook le dit.
"""

import json
import pathlib
import re

import nbformat
import pytest
from forge.evaluation.echantillons import INVITES
from forge.modele import nombre_parametres
from modele_factice import CONFIG, exporter_comme_la_release, petit_modele
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

PROJET = pathlib.Path(__file__).resolve().parents[1]
RACINE = pathlib.Path(__file__).resolve().parents[3]
NOTEBOOK = RACINE / "notebooks" / "1.6-evaluation.ipynb"
MESURES = PROJET / "mesures"


@pytest.fixture(scope="module")
def ton_ia_factice(tmp_path_factory) -> pathlib.Path:
    """Le petit modèle des tests, publié comme la version ton-ia-1.5 : les mêmes trois fichiers, sans les télécharger."""
    return exporter_comme_la_release(petit_modele(), tmp_path_factory.mktemp("ton-ia-factice") / "ton-ia-1.5")


@pytest.fixture(autouse=True)
def environnement(monkeypatch, ton_ia_factice):
    # Le noyau hérite de ces variables : le dépôt local, le modèle factice, et aucune carte visible.
    monkeypatch.setenv("FORGE_IA_LOCAL", str(RACINE))
    monkeypatch.setenv("FORGE_IA_MODELE", str(ton_ia_factice))
    # CUDA_VISIBLE_DEVICES=-1 cache la carte quand il y en a une (avec l'extra gpu), comme dans 0.4 et 0.5.
    # Une valeur vide ne suffit pas : sous Windows, une variable vide compte comme absente.
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "-1")
    monkeypatch.setenv("FORGE_APPAREIL", "cpu")


def entier(n: int) -> str:
    """Un entier comme le notebook l'écrit, avec une espace ordinaire entre les milliers (voir sorties_de)."""
    return f"{n:,}".replace(",", " ")


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
    assert "Bits par octet de « mini » : 1,134" in sorties
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
    # 6. Ton IA : le dossier de FORGE_IA_MODELE (ici le modèle factice), rien de téléchargé, le tokenizer
    # vérifié, le relevé de son évaluation, puis trois suites et ses jetons suivants, sur le processeur.
    assert "Téléchargement de" not in sorties
    assert "Empreinte SHA-256 du tokenizer : 3001e7ab…21ba, la même que celle de forge : True" in sorties
    assert f"Ton IA a {entier(nombre_parametres(CONFIG))} paramètres, chargés sur le processeur en" in sorties
    assert "Son évaluation, au pas 16 540, relevée le 2026-11-17 :" in sorties
    assert "perte de validation 2,419, perplexité 11,2 (« mini » : 30,8)" in sorties
    assert "bits par octet 0,803 (« mini » : 1,134)" in sorties
    assert "hellaswag : 34,8 % sur 9 338 questions, hasard 25,0 %, verdict : au-dessus (celui du relevé : au-dessus)" in sorties
    assert "arc : 25,1 % sur 1 169 questions, hasard 25,0 %, verdict : pas-different (celui du relevé : pas-different)" in sorties
    suites = sorties.split("Ton IA, sur le processeur (température 0,8, tirage parmi les 50 jetons les plus probables, graine 0) :", 1)[1]
    for invite in INVITES[:3]:
        assert f"  {invite!r} → " in suites, invite
    assert "3 suites de 30 jetons au plus, écrites en " in suites
    assert "Les 5 jetons les plus probables après « Il était une » pour ton IA :" in suites


def test_notebook_telecharge_ton_ia_une_seule_fois_et_la_charge_par_le_projet():
    brut = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code = "\n".join("".join(c["source"]) for c in brut["cells"] if c["cell_type"] == "code")
    # Une seule adresse de téléchargement, celle de la version publiée ; un fichier déjà là est sauté.
    assert code.count("releases/download/") == 1
    assert "https://github.com/chipat-neko/forge-ia/releases/download/{VERSION}/{nom}" in code
    assert 'VERSION = "ton-ia-1.5"' in code
    assert "if chemin.exists():" in code
    # Une connexion figée s'arrête au bout d'une minute au lieu de bloquer la cellule, et le délai d'avant revient.
    assert "socket.setdefaulttimeout(60)" in code and "socket.setdefaulttimeout(delai_d_avant)" in code
    # Avec FORGE_IA_MODELE, le dossier déjà téléchargé est pris tel quel.
    assert 'os.environ.get("FORGE_IA_MODELE")' in code
    # Le chargement est celui du projet (charger_ton_ia vérifie l'empreinte du tokenizer), sans copie, sur le processeur.
    assert "from evaluation_pas_a_pas.ton_ia import" in code and "charger_ton_ia(dossier_ton_ia, appareil)" in code
    assert "load_file" not in code and "safetensors" not in code


def test_lance_par_les_tests_sans_forge_ia_modele_il_ne_telecharge_rien(monkeypatch):
    # Avec FORGE_IA_LOCAL et sans FORGE_IA_MODELE, la cellule de l'étape 6 s'arrête et dit quoi faire,
    # au lieu de télécharger les poids de ton IA pendant les tests. La première cellule entraîne le
    # petit modèle (quelques secondes) : elle définit ce que la cellule de l'étape 6 utilise.
    monkeypatch.delenv("FORGE_IA_MODELE")
    nb = nbformat.read(NOTEBOOK, as_version=4)
    codes = [c for c in nb.cells if c.cell_type == "code"]
    ton_ia = next(c for c in codes if "charger_ton_ia(" in c.source)
    nb.cells = [codes[0], ton_ia]
    with pytest.raises(CellExecutionError) as erreur:
        executer(nb)
    assert "FORGE_IA_MODELE" in str(erreur.value) and "gh release download ton-ia-1.5" in str(erreur.value)
    assert "Téléchargement de" not in sorties_de(nb)


def test_une_coupure_du_reseau_dit_de_relancer_la_cellule(monkeypatch, tmp_path):
    # Revue finale du plan 5, m5 : le réseau coupe pendant le téléchargement de la version publiée. La cellule
    # annonce la taille du fichier avant le premier octet, puis dit en français de la relancer, sans trace de
    # urllib. Une cellule ajoutée remplace urlretrieve par une coupure, après l'annonce de 5 Mo.
    monkeypatch.delenv("FORGE_IA_MODELE")
    nb = nbformat.read(NOTEBOOK, as_version=4)
    codes = [c for c in nb.cells if c.cell_type == "code"]
    ton_ia = next(c for c in codes if "charger_ton_ia(" in c.source)
    coupure = nbformat.v4.new_code_cell(
        "import urllib.error\n"
        "import urllib.request\n"
        f"os.chdir({str(tmp_path)!r})\n"
        "depot_local = None  # le carnet se croit dans Colab : il télécharge\n"
        "def coupe(adresse, fichier, annoncer):\n"
        "    annoncer(0, 8192, 5 * 1024**2)\n"
        "    raise urllib.error.ContentTooShortError('retrieval incomplete: got only 8192 out of 5242880 bytes', None)\n"
        "urllib.request.urlretrieve = coupe\n"
    )
    nb.cells = [codes[0], coupure, ton_ia]
    with pytest.raises(CellExecutionError) as erreur:
        executer(nb)
    message = str(erreur.value).replace("\u202f", " ")
    assert "Le téléchargement de config.json a été coupé (<urlopen error retrieval incomplete" in message
    assert "Relance la cellule : les fichiers déjà complets ne se retéléchargent pas." in message
    assert "Téléchargement de config.json (5,0 Mo)…" in sorties_de(nb)
    # Rien n'a pris le nom d'un fichier complet : seul le .partiel pourrait rester.
    assert not (tmp_path / "ton-ia-1.5" / "config.json").exists()


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
