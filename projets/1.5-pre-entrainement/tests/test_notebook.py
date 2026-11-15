"""Le notebook Colab du chapitre 1.5 doit s'exécuter de bout en bout.

Rien n'est publié sans avoir tourné : le test exécute une copie en mémoire du
notebook (le fichier du dépôt reste sans sorties) dans le noyau « python3 » de
l'environnement uv, avec FORGE_IA_LOCAL à la racine du dépôt : le notebook
prend le code du projet et de forge, sans rien télécharger. Pour l'étape 6, à la
place des poids de la version publiée ton-ia-1.5, FORGE_IA_MODELE lui donne un
petit modèle tiré au hasard, publié de la même façon par forge.exporter. Il tourne
sur le processeur : la carte graphique est cachée, et le notebook le dit.
"""

import dataclasses
import json
import pathlib
import re

import nbformat
import pytest
import torch
from forge.entrainement.boucle import VERSION_DE_LA_SAUVEGARDE
from forge.evaluation.echantillons import INVITES
from forge.exporter import exporter
from forge.modele import ConfigModele, Transformer, nombre_parametres
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

PROJET = pathlib.Path(__file__).resolve().parents[1]
RACINE = pathlib.Path(__file__).resolve().parents[3]
NOTEBOOK = RACINE / "notebooks" / "1.5-pre-entrainement.ipynb"
MINI_MD = RACINE / "docs" / "mesures" / "ton-ia-mini.md"
# La ligne de l'exercice au-dessus de laquelle le lecteur écrit sa fonction.
REPERE = "# Ne change rien en dessous"
# Le modèle factice de l'étape 6 : minuscule, mais avec le vocabulaire du tokenizer de ton IA.
CONFIG_FACTICE = ConfigModele(dim=32, couches=2, tetes=4, longueur_contexte=64)


@pytest.fixture(scope="module")
def ton_ia_factice(tmp_path_factory) -> pathlib.Path:
    """Un petit modèle tiré au hasard, publié par forge.exporter comme la version ton-ia-1.5.

    Les mêmes trois fichiers (configuration, poids en bf16 sans `sortie.weight`, tokenizer de ton IA),
    pour que le notebook le charge par le même chemin que les vrais poids, sans les télécharger.
    """
    racine = tmp_path_factory.mktemp("ton-ia-factice")
    with torch.random.fork_rng():
        torch.manual_seed(0)
        modele = Transformer(CONFIG_FACTICE)
    sauvegarde = racine / "meilleur.pt"
    torch.save(
        {
            "version": VERSION_DE_LA_SAUVEGARDE,
            "pas": 7,
            "modele": modele.state_dict(),
            "config_modele": dataclasses.asdict(CONFIG_FACTICE),
        },
        sauvegarde,
    )
    dossier = racine / "ton-ia-1.5"
    exporter(sauvegarde, dossier)
    return dossier


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
    # 6. Ton IA : le dossier de FORGE_IA_MODELE (ici le modèle factice), rien de téléchargé, le tokenizer
    # vérifié, le relevé de son entraînement, puis trois suites écrites sur le processeur.
    assert "Téléchargement de" not in sorties
    assert "Empreinte SHA-256 du tokenizer : 3001e7ab…21ba, la même que celle de forge : True" in sorties
    assert f"Ton IA a {entier(nombre_parametres(CONFIG_FACTICE))} paramètres, chargés sur le processeur en" in sorties
    assert "16 540 pas sur 16 540, 8 671 723 520 jetons vus." in sorties
    assert "139,1 h de calcul, pauses non comptées, à 17 316 jetons par seconde." in sorties
    assert "13 sessions : 12 pauses, et 12 reprises avec --reprendre." in sorties
    suites = sorties.split("Température 0,8, tirage parmi les 50 jetons les plus probables, graine 0.", 1)[1]
    for invite in INVITES[:3]:
        assert f"  {invite!r} → " in suites, invite
    assert "3 suites de 30 jetons au plus, écrites en " in suites and " s sur le processeur." in suites
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


def test_notebook_telecharge_ton_ia_une_seule_fois_et_la_charge_par_le_projet_1_6():
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
    # Le chargement est celui du projet 1.6 (charger_ton_ia vérifie l'empreinte du tokenizer), sans copie.
    assert '"projets" / "1.6-evaluation"' in code
    assert "from evaluation_pas_a_pas.ton_ia import" in code and "charger_ton_ia(dossier_ton_ia, appareil)" in code
    assert "load_file" not in code and "safetensors" not in code


def test_lance_par_les_tests_sans_forge_ia_modele_il_ne_telecharge_rien(monkeypatch):
    # Avec FORGE_IA_LOCAL et sans FORGE_IA_MODELE, la cellule de l'étape 6 s'arrête et dit quoi faire,
    # au lieu de télécharger les poids de ton IA pendant les tests.
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
