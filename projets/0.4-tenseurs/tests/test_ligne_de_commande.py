"""`python -m tenseurs formes …` et `python -m tenseurs mesurer …` : sorties, fichiers et codes de sortie."""

import json
import os
import pathlib
import subprocess
import sys

import pytest

from tenseurs.__main__ import lire_forme, main

PROJET = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def sans_variable(monkeypatch):
    monkeypatch.delenv("FORGE_APPAREIL", raising=False)


def lancer(capsys, *arguments: str) -> tuple[int, list[str], str]:
    """Lance main() ; rend (code, lignes affichées, sortie d'erreur)."""
    code = main(list(arguments))
    lu = capsys.readouterr()
    return code, lu.out.splitlines(), lu.err


def test_formes_les_deux_regles(capsys):
    code, lignes, erreur = lancer(capsys, "formes", "(3, 1)", "(4,)")
    assert (code, erreur) == (0, "")
    assert lignes == [
        "Diffusion\u202f: (3, 1) + (4,) donne (3, 4).",
        "Produit matriciel\u202f: (3, 1) @ (4,) est impossible\u202f: la dernière dimension de gauche, 1, "
        "n’est pas l’avant-dernière de droite, 4 (la seule d’un vecteur).",
    ]


def test_formes_produit_possible_diffusion_impossible(capsys):
    code, lignes, _ = lancer(capsys, "formes", "(2, 3)", "(3, 2)")
    assert code == 0
    assert lignes == [
        "Diffusion\u202f: (2, 3) + (3, 2) est impossible\u202f: alignées par la droite, deux dimensions "
        "diffèrent sans que l’une vaille 1.",
        "Produit matriciel\u202f: (2, 3) @ (3, 2) donne (2, 2).",
    ]


def test_formes_produit_de_deux_vecteurs(capsys):
    _, lignes, _ = lancer(capsys, "formes", "(3,)", "(3,)")
    assert lignes == [
        "Diffusion\u202f: (3,) + (3,) donne (3,).",
        "Produit matriciel\u202f: (3,) @ (3,) donne () (un nombre seul).",
    ]


def test_formes_lots_qui_ne_se_diffusent_pas(capsys):
    _, lignes, _ = lancer(capsys, "formes", "(2, 3, 4)", "(3, 4, 5)")
    assert lignes[1] == (
        "Produit matriciel\u202f: (2, 3, 4) @ (3, 4, 5) est impossible\u202f: les dimensions de lot, (2,) et (3,), "
        "ne se diffusent pas."
    )


def test_formes_nombre_seul(capsys):
    _, lignes, _ = lancer(capsys, "formes", "()", "(3,)")
    assert lignes == [
        "Diffusion\u202f: () + (3,) donne (3,).",
        "Produit matriciel\u202f: () @ (3,) est impossible\u202f: un nombre seul n’a pas de produit matriciel.",
    ]


@pytest.mark.parametrize(
    ("texte", "forme"),
    [("(3, 1)", (3, 1)), ("(4,)", (4,)), ("(4)", (4,)), ("()", ()), ("3, 1", (3, 1)), (" ( 2,3 , 4 ) ", (2, 3, 4))],
)
def test_lire_forme(texte, forme):
    assert lire_forme(texte) == forme


@pytest.mark.parametrize("texte", ["(a, 2)", "(3, -1)", "(3,, 1)", "[3, 1]", "(2.5,)", ""])
def test_forme_illisible(capsys, texte):
    assert main(["formes", texte, "(3,)"]) == 2
    erreur = capsys.readouterr().err
    assert "Forme illisible" in erreur and "(4,)" in erreur and "Traceback" not in erreur


def test_sans_commande(capsys):
    with pytest.raises(SystemExit) as fin:
        main([])
    assert fin.value.code == 2


def test_mesurer_ecrit_le_fichier(capsys, tmp_path):
    sortie = tmp_path / "sous-dossier" / "processeur.json"
    code, lignes, erreur = lancer(capsys, "mesurer", "--appareil", "cpu", "--tailles", "32", "64", "--sortie", str(sortie))
    assert (code, erreur) == (0, "")
    octets = sortie.read_bytes()
    assert b"\r" not in octets and octets.endswith(b"}\n")
    m = json.loads(octets.decode("utf-8"))
    assert m["appareil"] == "cpu" and sorted({x["taille"] for x in m["mesures"]}) == [32, 64]
    # La sortie affichée : l'en-tête, une ligne par taille, puis le fichier écrit.
    assert lignes[0].startswith("Produit de deux matrices en float32, sur le processeur (")
    assert lignes[1].startswith("  32 × 32\u202f: ") and lignes[2].startswith("  64 × 64\u202f: ")
    assert "ms avec 1 fil" in lignes[1]
    assert lignes[-1] == f"Mesures écrites dans {sortie}."


def test_mesurer_sans_fichier(capsys):
    code, lignes, _ = lancer(capsys, "mesurer", "--appareil", "cpu", "--tailles", "16")
    assert code == 0 and len(lignes) == 2


def test_carte_absente_dans_un_vrai_processus(tmp_path):
    # Le lecteur sans carte qui demande `--appareil cuda` : un vrai processus, une console
    # Windows en cp1252, et pas de trace Python. CUDA_VISIBLE_DEVICES vide cache la carte
    # quand il y en a une (à la porte, avec la roue gpu).
    sortie = tmp_path / "carte.json"
    resultat = subprocess.run(
        [sys.executable, "-m", "tenseurs", "mesurer", "--appareil", "cuda", "--sortie", str(sortie)],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        cwd=PROJET,
        env={**os.environ, "PYTHONIOENCODING": "cp1252", "CUDA_VISIBLE_DEVICES": "", "FORGE_APPAREIL": ""},
        timeout=120,
    )
    assert resultat.returncode == 2
    assert "Traceback" not in resultat.stderr + resultat.stdout
    assert "FORGE_APPAREIL=cpu" in resultat.stderr
    assert not sortie.exists()


def test_formes_sans_pytorch():
    # Les règles de forme sont en Python pur : `formes` marche même si PyTorch ne s'importe pas.
    script = (
        "import runpy, sys\n"
        "sys.modules['torch'] = None\n"
        "sys.argv = ['tenseurs', 'formes', '(3, 1)', '(4,)']\n"
        "runpy.run_module('tenseurs', run_name='__main__')\n"
    )
    resultat = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        encoding="utf-8",
        cwd=PROJET,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=60,
    )
    assert resultat.returncode == 0, resultat.stderr
    assert resultat.stdout.startswith("Diffusion")

