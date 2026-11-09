"""`python -m pre_entrainement courbe|essai` : sorties, fichiers et codes de sortie.

Aucun test ici n'ouvre la carte graphique : les cas `cuda` cachent la carte (CUDA_VISIBLE_DEVICES vide,
ou `torch.cuda.is_available` simulé) et simulent la panne de l'essai.
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

import pre_entrainement.__main__ as script
from pre_entrainement.__main__ import carte_inutilisable, main

PROJET = pathlib.Path(__file__).resolve().parents[1]
RACINE = pathlib.Path(__file__).resolve().parents[3]
FACTICE = PROJET / "tests" / "journal-factice.jsonl"
CONFIG_TOML = """\
donnees = "factice"
jetons_total = 10_240
taille_lot_jetons = 1024
micro_lot = 16
taux_max = 1e-3
echauffement = 2
evaluation_tous_pas = 5
appareil = "cpu"
compiler = "non"
sortie = "ton-ia-factice"

[preset]
dim = 64
couches = 2
tetes = 4
longueur_contexte = 64
"""
RESULTAT = {
    "appareil": "cpu",
    "pas_total": 60,
    "pas_de_la_pause": 30,
    "perte_un_trait": 7.123456,
    "perte_reprise": 7.123456,
    "ecart": 0.0,
    "pertes_identiques": True,
    "secondes": 12.34,
}


@pytest.fixture(autouse=True)
def sans_variable(monkeypatch):
    monkeypatch.delenv("FORGE_APPAREIL", raising=False)


@pytest.fixture
def config(tmp_path):
    chemin = tmp_path / "factice.toml"
    chemin.write_text(CONFIG_TOML, encoding="utf-8")
    return chemin


# --- courbe ----------------------------------------------------------------------------------------


def test_courbe_ecrit_le_json(config, tmp_path, capsys):
    sortie = tmp_path / "mesures" / "factice.json"
    assert main(["courbe", "--journal", str(FACTICE), "--config", str(config), "--json", str(sortie)]) == 0
    octets = sortie.read_bytes()
    assert b"\r" not in octets and octets.endswith(b"}\n")
    donnees = json.loads(octets)
    assert list(donnees) == ["nom", "releve_le", "resume", "sessions", "courbe"]
    assert donnees["nom"] == "ton-ia-factice"
    assert donnees["releve_le"] == datetime.date.today().isoformat()
    assert donnees["resume"]["pas_faits"] == 10 and donnees["resume"]["pauses"] == 1
    assert [s["fin"] for s in donnees["sessions"]] == ["pause", "fin"]
    assert len(donnees["courbe"]["pertes"]) == 10 and donnees["courbe"]["validations"] == [[5, 10.0], [10, 9.1]]
    # Le JSON est écrit comme les autres mesures du dépôt : ensure_ascii=False, indent=1.
    assert octets.decode("utf-8") == json.dumps(donnees, ensure_ascii=False, allow_nan=False, indent=1) + "\n"
    assert "10 pas sur 10" in capsys.readouterr().out.replace("\u202f", " ")  # un résumé à l'écran


def test_courbe_sans_journal_le_dit(config, tmp_path, capsys):
    assert main(["courbe", "--journal", str(tmp_path / "rien.jsonl"), "--config", str(config)]) == 2
    assert "n’existe pas" in capsys.readouterr().err


def test_courbe_sans_configuration_le_dit(tmp_path, capsys):
    assert main(["courbe", "--journal", str(FACTICE), "--config", str(tmp_path / "rien.toml")]) == 2
    assert "Fichier de configuration introuvable" in capsys.readouterr().err


# --- essai -----------------------------------------------------------------------------------------


def test_essai_ecrit_le_texte_et_le_json(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(script, "essai_pause_reprise", lambda appareil, racine: dict(RESULTAT))
    txt, js = tmp_path / "sorties" / "essai.txt", tmp_path / "mesures" / "essai.json"
    assert main(["essai", "--appareil", "cpu", "--enregistrer", str(txt), "--json", str(js)]) == 0
    lu = capsys.readouterr()
    assert lu.err == ""
    octets = txt.read_bytes()
    assert b"\r" not in octets and octets.endswith(b"\n")
    assert octets.decode("utf-8") == f"# relevé le {datetime.date.today().isoformat()}\n" + lu.out
    assert lu.out.splitlines()[-1].endswith("oui")
    donnees = json.loads(js.read_text(encoding="utf-8"))
    assert donnees == {"releve_le": datetime.date.today().isoformat(), **RESULTAT}


def test_essai_non_exact_sur_le_processeur_rend_1(monkeypatch, capsys):
    monkeypatch.setattr(script, "essai_pause_reprise", lambda appareil, racine: {**RESULTAT, "ecart": 1e-3})
    assert main(["essai", "--appareil", "cpu"]) == 1
    assert capsys.readouterr().out.splitlines()[-1].endswith("non")


def test_essai_sur_la_carte_ne_demande_pas_l_egalite(monkeypatch, capsys):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "get_device_name", lambda *a: "Carte de test")
    monkeypatch.setattr(
        script, "essai_pause_reprise", lambda appareil, racine: {**RESULTAT, "appareil": "cuda", "ecart": 2e-3}
    )
    assert main(["essai", "--appareil", "cuda"]) == 0
    assert "Carte de test" in capsys.readouterr().out


def test_cuda_absente_message_francais(monkeypatch, capsys):
    monkeypatch.setenv("FORGE_APPAREIL", "cuda")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert main(["essai"]) == 2
    lu = capsys.readouterr()
    assert "Tu as demandé la carte graphique (FORGE_APPAREIL=cuda), mais PyTorch ne la voit pas" in lu.err
    assert "Traceback" not in lu.err and lu.out == ""


def test_appareil_inconnu(capsys):
    assert main(["essai", "--appareil", "tpu"]) == 2
    assert "Appareil inconnu" in capsys.readouterr().err


def test_cuda_demandee_sans_carte_dans_un_vrai_processus(tmp_path):
    sortie = tmp_path / "carte.txt"
    resultat = subprocess.run(
        [sys.executable, "-m", "pre_entrainement", "essai", "--appareil", "cuda", "--enregistrer", str(sortie)],
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
    assert resultat.stdout == "" and not sortie.exists()


def test_carte_vue_mais_inutilisable(monkeypatch, capsys, tmp_path):
    # Une carte que PyTorch voit, mais pour laquelle sa version n'a pas de code : le premier calcul
    # lève une RuntimeError. Le script le dit en français, rend 2, sans trace, et n'enregistre rien.
    def en_panne(appareil, racine):
        raise RuntimeError(
            "CUDA error: no kernel image is available for execution on the device\n"
            "CUDA kernel errors might be asynchronously reported at some other API call."
        )

    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "get_device_name", lambda *a: "Carte de test")
    monkeypatch.setattr(script, "essai_pause_reprise", en_panne)
    fichier = tmp_path / "carte.txt"
    assert main(["essai", "--appareil", "cuda", "--enregistrer", str(fichier)]) == 2
    lu = capsys.readouterr()
    assert lu.err == (
        "La carte graphique n’a pas pu calculer avec cette version de PyTorch\u202f: CUDA error: no kernel "
        "image is available for execution on the device. Pour savoir pourquoi, lance `uv run --extra gpu "
        "python -m poste` dans le dossier projets/0.3-poste. Pour calculer sur le processeur, relance avec "
        "`--appareil cpu` (ou, sans `--appareil`, mets FORGE_APPAREIL=cpu).\n"
    )
    assert not fichier.exists()


def test_carte_sans_memoire_libre(monkeypatch, capsys):
    def sans_memoire(appareil, racine):
        raise torch.OutOfMemoryError("CUDA out of memory. Tried to allocate 2.00 MiB.")

    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "get_device_name", lambda *a: "Carte de test")
    monkeypatch.setattr(script, "essai_pause_reprise", sans_memoire)
    assert main(["essai", "--appareil", "cuda"]) == 2
    assert capsys.readouterr().err.startswith(
        "La carte graphique n’a plus assez de mémoire libre\u202f: CUDA out of memory."
    )


def test_erreur_sur_le_processeur_non_masquee(monkeypatch):
    # Seule la carte a droit au message : sur le processeur, une RuntimeError est un défaut du projet.
    def en_panne(appareil, racine):
        raise RuntimeError("panne")

    monkeypatch.setattr(script, "essai_pause_reprise", en_panne)
    with pytest.raises(RuntimeError, match="panne"):
        main(["essai", "--appareil", "cpu"])


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
    copie = fonction_du_fichier(PROJET / "pre_entrainement" / "__main__.py", "carte_inutilisable")
    assert copie == fonction_du_fichier(original, "carte_inutilisable"), (
        "carte_inutilisable n'est plus la copie exacte de celle de projets/0.5-reseau. Une correction "
        "se fait dans 0.5, puis se recopie ici (et dans 1.6)."
    )


def test_appareil_est_la_copie_de_0_3():
    original = RACINE / "projets" / "0.3-poste" / "poste" / "appareil.py"
    if not original.exists():
        pytest.skip("Projet téléchargé seul : projets/0.3-poste n'est pas là pour comparer la copie.")
    assert (PROJET / "pre_entrainement" / "appareil.py").read_bytes() == original.read_bytes()


def test_carte_inutilisable_dit_quoi_faire():
    message = carte_inutilisable(RuntimeError("CUDA error: boom.\nautre ligne"))
    assert "CUDA error: boom." in message and "autre ligne" not in message
    assert re.search(r"FORGE_APPAREIL=cpu", message)


# --- Les journaux qu'on ne peut pas relever -------------------------------------------------------


def ecrire_journal(chemin, lignes):
    chemin.write_text("".join(json.dumps(ligne) + "\n" for ligne in lignes), encoding="utf-8")


def pas_de_journal(numero, **champs):
    return {"pas": numero, "jetons_vus": 1024 * numero, "perte": 5.0, "taux": 0.001, "secondes": float(numero), **champs}


@pytest.mark.parametrize(
    "lignes, attendu",
    [
        ([{"evenement": "debut", "pas": 0}], "il n’a aucun pas"),
        ([{"evenement": "debut", "pas": 0}, pas_de_journal(1, perte=float("nan")), pas_de_journal(2)], "au premier pas"),
        ([{"evenement": "debut", "pas": 0}, pas_de_journal(1), pas_de_journal(2, perte=float("inf"))], "au dernier pas"),
        ([{"evenement": "debut", "pas": 0}, pas_de_journal(1), {"pas": 2, "perte": 5.0, "secondes": 2.0}], "n’a pas de `jetons_vus`"),
        ([{"evenement": "debut", "pas": 0}, pas_de_journal(1), pas_de_journal(2, perte_val=float("nan"))], "à la dernière validation"),
    ],
)
def test_journal_impossible_a_relever(config, tmp_path, capsys, lignes, attendu):
    journal = tmp_path / "journal.jsonl"
    ecrire_journal(journal, lignes)
    sortie = tmp_path / "relevé.json"
    assert main(["courbe", "--journal", str(journal), "--config", str(config), "--json", str(sortie)]) == 2
    lu = capsys.readouterr()
    assert attendu in lu.err and "ne se relève pas" in lu.err
    assert "Traceback" not in lu.err and lu.out == "" and not sortie.exists()
