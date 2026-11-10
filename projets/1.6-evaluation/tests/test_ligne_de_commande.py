"""`python -m evaluation_pas_a_pas resumer|qcm-exemples|cartes|suivants` : sorties, fichiers et codes de sortie.

Aucun test ici n'ouvre la carte graphique : les cas `cuda` cachent la carte (CUDA_VISIBLE_DEVICES vide, ou
`torch.cuda.is_available` simulé, avec un modèle déjà sur le processeur) et simulent les pannes. Aucun ne
touche le réseau : les questions de MMMLU sont données à la main.
"""

import ast
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys

import pytest
import torch
from modele_factice import CONFIG, petit_modele, sauvegarder
from test_resumer import RAPPORT, ecrire

import evaluation_pas_a_pas.__main__ as script
from evaluation_pas_a_pas.__main__ import carte_inutilisable, main

PROJET = pathlib.Path(__file__).resolve().parents[1]
RACINE = pathlib.Path(__file__).resolve().parents[3]
PHRASE = "Le forgeron dit qu'il frappe le fer"
JEU = [
    {"Question": f"Combien font {i} + {i} ?", "A": str(i), "B": str(2 * i), "C": str(3 * i), "D": str(4 * i), "Answer": "B", "Subject": "x"}
    for i in range(1, 30)
]


@pytest.fixture(autouse=True)
def sans_variable(monkeypatch):
    monkeypatch.delenv("FORGE_APPAREIL", raising=False)


@pytest.fixture
def sauvegarde(tmp_path):
    return sauvegarder(petit_modele(), tmp_path / "entrainements" / "ton-ia-factice" / "sauvegardes" / "etape-0000007.pt")


@pytest.fixture
def sans_reseau(monkeypatch):
    from evaluation_pas_a_pas import qcm_exemples

    monkeypatch.setattr(script, "exemples_mmmlu", lambda n, graine: qcm_exemples.exemples_mmmlu(n, graine, lignes=JEU))


def ecrit_comme_les_autres(chemin: pathlib.Path) -> dict:
    octets = chemin.read_bytes()
    assert b"\r" not in octets and octets.endswith(b"}\n")
    donnees = json.loads(octets)
    assert octets.decode("utf-8") == json.dumps(donnees, ensure_ascii=False, allow_nan=False, indent=1) + "\n"
    return donnees


# --- resumer ---------------------------------------------------------------------------------------


def test_resumer_ecrit_le_json(tmp_path, capsys):
    sortie = tmp_path / "mesures" / "evaluation-factice.json"
    assert main(["resumer", "--rapport", str(ecrire(tmp_path, RAPPORT)), "--json", str(sortie)]) == 0
    donnees = ecrit_comme_les_autres(sortie)
    assert list(donnees) == ["nom", "releve_le", "pas", "perte_val", "perplexite", "bits_par_octet", "qcm", "echantillons"]
    assert donnees["nom"] == "ton-ia-factice" and donnees["releve_le"] == "2026-11-03"
    lu = capsys.readouterr().out.replace("\u202f", " ")
    assert "perplexité 33,1" in lu and "au-dessus" in lu and "pas-different" in lu


def test_resumer_sans_rapport_le_dit(tmp_path, capsys):
    assert main(["resumer", "--rapport", str(tmp_path / "rien.json")]) == 2
    lu = capsys.readouterr()
    assert "n'existe pas" in lu.err and lu.out == ""


def test_resumer_n_ecrit_rien_quand_le_rapport_est_faux(tmp_path, capsys):
    chemin = ecrire(tmp_path, {**RAPPORT, "version": 7})
    sortie = tmp_path / "relevé.json"
    assert main(["resumer", "--rapport", str(chemin), "--json", str(sortie)]) == 2
    assert "version 1" in capsys.readouterr().err and not sortie.exists()


# --- qcm-exemples, cartes, suivants ------------------------------------------------------------


def test_qcm_exemples_ecrit_le_json(sauvegarde, sans_reseau, tmp_path, capsys):
    sortie = tmp_path / "mesures" / "qcm.json"
    assert main(["qcm-exemples", "--sauvegarde", str(sauvegarde), "--appareil", "cpu", "--n", "3", "--json", str(sortie)]) == 0
    donnees = ecrit_comme_les_autres(sortie)
    assert list(donnees)[:3] == ["nom", "releve_le", "appareil"]
    assert donnees["nom"] == "ton-ia-factice" and donnees["appareil"] == "cpu" and donnees["releve_le"] == datetime.date.today().isoformat()
    assert donnees["jeu"]["licence"] == "MIT" and donnees["jeu"]["adresse"] == "https://huggingface.co/datasets/openai/MMMLU"
    assert donnees["n"] == 3 and len(donnees["questions"]) == 3
    lu = capsys.readouterr().out.replace("\u202f", " ")
    assert "licence MIT" in lu and "justes sur 3" in lu


def test_qcm_exemples_sans_reseau_le_dit(sauvegarde, monkeypatch, tmp_path, capsys):
    def coupe(n, graine):
        raise ConnectionError("pas de réseau")

    monkeypatch.setattr(script, "exemples_mmmlu", coupe)
    sortie = tmp_path / "qcm.json"
    assert main(["qcm-exemples", "--sauvegarde", str(sauvegarde), "--appareil", "cpu", "--json", str(sortie)]) == 2
    lu = capsys.readouterr()
    assert "MMMLU n'a pas pu être lu sur Hugging Face" in lu.err and "pas de réseau" in lu.err
    assert "Traceback" not in lu.err and not sortie.exists()


def test_cartes_ecrivent_les_poids_d_une_tete(sauvegarde, tmp_path, capsys):
    sortie = tmp_path / "cartes.json"
    assert main(["cartes", "--sauvegarde", str(sauvegarde), "--phrase", PHRASE, "--couche", "1", "--tete", "2", "--appareil", "cpu", "--json", str(sortie)]) == 0
    donnees = ecrit_comme_les_autres(sortie)
    assert list(donnees) == ["nom", "releve_le", "appareil", "phrase", "jetons", "couche", "couches", "tete", "tetes", "poids"]
    assert (donnees["couche"], donnees["couches"], donnees["tete"], donnees["tetes"]) == (1, 2, 2, 4)
    assert donnees["phrase"] == PHRASE and donnees["appareil"] == "cpu"
    jetons, poids = donnees["jetons"], donnees["poids"]
    assert jetons[0] == "<|fin_texte|>" and "".join(jetons[1:]) == PHRASE
    assert len(poids) == len(jetons) and all(len(ligne) == len(jetons) for ligne in poids)  # n × n
    for i, ligne in enumerate(poids):
        assert sum(ligne) == pytest.approx(1.0, abs=1e-4)  # chaque ligne totalise 1 (6 décimales gardées)
        assert all(x == 0.0 for x in ligne[i + 1 :]) and all(0 <= x <= 1 for x in ligne)  # jamais de regard en avant
    assert "tête 2" in capsys.readouterr().out


def test_cartes_valent_celles_de_regarder(sauvegarde, tmp_path):
    from evaluation_pas_a_pas.regarder import cartes_attention, jetons_de_la_phrase
    from modele_factice import tokenizer

    sortie = tmp_path / "cartes.json"
    assert main(["cartes", "--sauvegarde", str(sauvegarde), "--phrase", PHRASE, "--couche", "0", "--tete", "3", "--appareil", "cpu", "--json", str(sortie)]) == 0
    ids = torch.tensor(jetons_de_la_phrase(tokenizer(), PHRASE, CONFIG.longueur_contexte))
    attendu = cartes_attention(petit_modele(), ids, 0)[3]
    lu = torch.tensor(json.loads(sortie.read_text(encoding="utf-8"))["poids"])
    assert (lu - attendu).abs().max().item() <= 1e-6


@pytest.mark.parametrize("option, valeur, attendu", [("--couche", "2", "La couche 2 n'existe pas"), ("--tete", "4", "La tête 4 n'existe pas")])
def test_cartes_d_une_couche_ou_d_une_tete_inexistante(sauvegarde, tmp_path, capsys, option, valeur, attendu):
    sortie = tmp_path / "cartes.json"
    assert main(["cartes", "--sauvegarde", str(sauvegarde), "--phrase", PHRASE, option, valeur, "--appareil", "cpu", "--json", str(sortie)]) == 2
    lu = capsys.readouterr()
    assert attendu in lu.err and "Corrige" in lu.err and "Traceback" not in lu.err and not sortie.exists()


def test_suivants_ecrivent_les_jetons_les_plus_probables(sauvegarde, tmp_path, capsys):
    sortie = tmp_path / "suivants.json"
    assert main(["suivants", "--sauvegarde", str(sauvegarde), "--phrase", PHRASE, "--k", "5", "--appareil", "cpu", "--json", str(sortie)]) == 0
    donnees = ecrit_comme_les_autres(sortie)
    assert list(donnees) == ["nom", "releve_le", "appareil", "phrase", "suivants"]
    probas = [s["probabilite"] for s in donnees["suivants"]]
    assert len(probas) == 5 and probas == sorted(probas, reverse=True) and all(set(s) == {"jeton", "probabilite"} for s in donnees["suivants"])
    assert "5 jetons les plus probables" in capsys.readouterr().out


def test_sauvegarde_introuvable_le_dit(tmp_path, capsys):
    assert main(["suivants", "--sauvegarde", str(tmp_path / "rien.pt"), "--phrase", PHRASE, "--appareil", "cpu"]) == 2
    lu = capsys.readouterr()
    assert "Sauvegarde introuvable" in lu.err and "Traceback" not in lu.err and lu.out == ""


# --- La carte graphique ------------------------------------------------------------------------------


@pytest.mark.parametrize("commande", [["qcm-exemples"], ["cartes", "--phrase", PHRASE], ["suivants", "--phrase", PHRASE]])
def test_cuda_absente_message_francais(commande, sauvegarde, monkeypatch, capsys):
    monkeypatch.setenv("FORGE_APPAREIL", "cuda")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert main([*commande, "--sauvegarde", str(sauvegarde)]) == 2
    lu = capsys.readouterr()
    assert "Tu as demandé la carte graphique (FORGE_APPAREIL=cuda), mais PyTorch ne la voit pas" in lu.err
    assert "Traceback" not in lu.err and lu.out == ""


def test_appareil_inconnu(sauvegarde, capsys):
    assert main(["suivants", "--sauvegarde", str(sauvegarde), "--phrase", PHRASE, "--appareil", "tpu"]) == 2
    assert "Appareil inconnu" in capsys.readouterr().err


def test_cuda_demandee_sans_carte_dans_un_vrai_processus(sauvegarde, tmp_path):
    resultat = subprocess.run(
        [sys.executable, "-m", "evaluation_pas_a_pas", "cartes", "--sauvegarde", str(sauvegarde), "--phrase", PHRASE, "--appareil", "cuda", "--json", str(tmp_path / "c.json")],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        cwd=PROJET,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONIOENCODING": "cp1252"},
        timeout=120,
    )
    assert resultat.returncode == 2
    assert "Traceback" not in resultat.stderr + resultat.stdout
    assert "FORGE_APPAREIL=cpu" in resultat.stderr
    assert resultat.stdout == "" and not (tmp_path / "c.json").exists()


@pytest.fixture
def carte_simulee(monkeypatch):
    """La carte est « vue » par PyTorch, mais le modèle reste sur le processeur : aucun contexte CUDA n'est ouvert."""
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(script, "charger_sauvegarde", lambda chemin, appareil: (petit_modele(), CONFIG))


def test_carte_vue_mais_inutilisable(carte_simulee, sauvegarde, monkeypatch, capsys, tmp_path):
    def en_panne(*arguments):
        raise RuntimeError(
            "CUDA error: no kernel image is available for execution on the device\n"
            "CUDA kernel errors might be asynchronously reported at some other API call."
        )

    monkeypatch.setattr(script, "cartes_attention", en_panne)
    sortie = tmp_path / "cartes.json"
    assert main(["cartes", "--sauvegarde", str(sauvegarde), "--phrase", PHRASE, "--appareil", "cuda", "--json", str(sortie)]) == 2
    lu = capsys.readouterr()
    assert lu.err == (
        "La carte graphique n’a pas pu calculer avec cette version de PyTorch\u202f: CUDA error: no kernel "
        "image is available for execution on the device. Pour savoir pourquoi, lance `uv run --extra gpu "
        "python -m poste` dans le dossier projets/0.3-poste. Pour calculer sur le processeur, relance avec "
        "`--appareil cpu` (ou, sans `--appareil`, mets FORGE_APPAREIL=cpu).\n"
    )
    assert not sortie.exists()


def test_carte_vue_mais_inutilisable_des_le_chargement(sauvegarde, monkeypatch, capsys):
    def en_panne(chemin, appareil):
        raise RuntimeError("CUDA error: boom")

    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(script, "charger_sauvegarde", en_panne)
    assert main(["suivants", "--sauvegarde", str(sauvegarde), "--phrase", PHRASE, "--appareil", "cuda"]) == 2
    assert "La carte graphique n’a pas pu calculer" in capsys.readouterr().err


def test_carte_sans_memoire_libre(carte_simulee, sauvegarde, monkeypatch, capsys):
    def sans_memoire(*arguments):
        raise torch.OutOfMemoryError("CUDA out of memory. Tried to allocate 2.00 MiB.")

    monkeypatch.setattr(script, "suivants", sans_memoire)
    assert main(["suivants", "--sauvegarde", str(sauvegarde), "--phrase", PHRASE, "--appareil", "cuda"]) == 2
    assert capsys.readouterr().err.startswith("La carte graphique n’a plus assez de mémoire libre\u202f: CUDA out of memory.")


def test_erreur_sur_le_processeur_non_masquee(sauvegarde, monkeypatch):
    # Seule la carte a droit au message : sur le processeur, une RuntimeError est un défaut du projet.
    def en_panne(*arguments):
        raise RuntimeError("panne")

    monkeypatch.setattr(script, "suivants", en_panne)
    with pytest.raises(RuntimeError, match="panne"):
        main(["suivants", "--sauvegarde", str(sauvegarde), "--phrase", PHRASE, "--appareil", "cpu"])


def test_sans_commande(capsys):
    with pytest.raises(SystemExit) as fin:
        main([])
    assert fin.value.code == 2


# --- Les copies exactes ---------------------------------------------------------------------------


def fonction_du_fichier(chemin: pathlib.Path, nom: str) -> str:
    texte = chemin.read_text(encoding="utf-8")
    for noeud in ast.walk(ast.parse(texte)):
        if isinstance(noeud, ast.FunctionDef) and noeud.name == nom:
            return ast.get_source_segment(texte, noeud)
    raise AssertionError(f"{nom} est introuvable dans {chemin}")


def test_carte_inutilisable_est_la_copie_de_0_5():
    original = RACINE / "projets" / "0.5-reseau" / "premier_reseau" / "__main__.py"
    if not original.exists():
        pytest.skip("Projet téléchargé seul : projets/0.5-reseau n'est pas là pour comparer la copie.")
    copie = fonction_du_fichier(PROJET / "evaluation_pas_a_pas" / "__main__.py", "carte_inutilisable")
    assert copie == fonction_du_fichier(original, "carte_inutilisable"), (
        "carte_inutilisable n'est plus la copie exacte de celle de projets/0.5-reseau. Une correction "
        "se fait dans 0.5, puis se recopie ici (et dans 1.5)."
    )


def test_carte_inutilisable_est_la_copie_de_1_5():
    original = RACINE / "projets" / "1.5-pre-entrainement" / "pre_entrainement" / "__main__.py"
    if not original.exists():
        pytest.skip("Projet téléchargé seul : projets/1.5-pre-entrainement n'est pas là pour comparer la copie.")
    copie = fonction_du_fichier(PROJET / "evaluation_pas_a_pas" / "__main__.py", "carte_inutilisable")
    assert copie == fonction_du_fichier(original, "carte_inutilisable")


def test_appareil_est_la_copie_de_0_3():
    original = RACINE / "projets" / "0.3-poste" / "poste" / "appareil.py"
    if not original.exists():
        pytest.skip("Projet téléchargé seul : projets/0.3-poste n'est pas là pour comparer la copie.")
    assert (PROJET / "evaluation_pas_a_pas" / "appareil.py").read_bytes() == original.read_bytes()


def test_carte_inutilisable_dit_quoi_faire():
    message = carte_inutilisable(RuntimeError("CUDA error: boom.\nautre ligne"))
    assert "CUDA error: boom." in message and "autre ligne" not in message
    assert re.search(r"FORGE_APPAREIL=cpu", message)


# --- Les régions montrées par le chapitre ---------------------------------------------------------


def regions(chemin: pathlib.Path) -> list[str]:
    texte = chemin.read_text(encoding="utf-8")
    ouvertes = re.findall(r"^\s*# region: ([\w-]+)$", texte, flags=re.M)
    fermees = re.findall(r"^\s*# fin: ([\w-]+)$", texte, flags=re.M)
    assert ouvertes == fermees, f"{chemin.name} : des régions ne sont pas fermées dans l'ordre ({ouvertes} / {fermees})"
    return ouvertes


def test_les_regions_du_paquet():
    paquet = PROJET / "evaluation_pas_a_pas"
    assert regions(paquet / "pas_a_pas.py") == ["perte", "perplexite", "bits", "qcm", "marge"]
    assert regions(paquet / "regarder.py") == ["cartes", "suivants"]
    assert regions(paquet / "resumer.py") == ["resumer"]
    assert regions(paquet / "sauvegarde.py") == ["sauvegarde"]
    assert regions(paquet / "qcm_exemples.py") == ["noter-exemples"]
    assert regions(paquet / "appareil.py") == ["appareil"]
    assert regions(PROJET / "tests" / "test_regarder.py") == ["test-cartes"]
