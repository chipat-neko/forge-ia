"""`python -m poste [--enregistrer FICHIER]` : le rapport, son code de sortie et sa sortie enregistrée."""

import datetime
import os
import pathlib
import re
import subprocess
import sys
from dataclasses import replace

import pytest

from poste import __main__ as ligne_de_commande
from poste.diagnostic import SITUATIONS, decrire_constat, diagnostiquer

PROJET = pathlib.Path(__file__).resolve().parents[1]
DERNIERE_LIGNE = re.compile(r"^Diagnostic terminé\u202f: (\d+) problème\(s\)\.$")


def lancer(monkeypatch, capsys, faits=None, arguments=()):
    """Lance main() ; avec `faits`, à la place de ceux du poste. Rend (code, lignes affichées)."""
    if faits is not None:
        monkeypatch.setattr(ligne_de_commande, "relever_faits", lambda: faits)
    code = ligne_de_commande.main(list(arguments))
    sortie = capsys.readouterr()
    assert sortie.err == ""
    return code, sortie.out.splitlines()


def test_sortie_processeur_enregistree():
    t = (PROJET / "sorties" / "processeur.txt").read_text(encoding="utf-8")
    assert t.startswith("# relevé le ") and "Diagnostic terminé" in t and "\r" not in t


def test_sortie_processeur_enregistree_en_detail():
    octets = (PROJET / "sorties" / "processeur.txt").read_bytes()
    assert b"\r" not in octets and octets.endswith(b".\n")
    lignes = octets.decode("utf-8").splitlines()
    assert re.fullmatch(r"# relevé le \d{4}-\d{2}-\d{2}", lignes[0])
    datetime.date.fromisoformat(lignes[0].removeprefix("# relevé le "))
    # Relevée avec la roue cpu, sur un PC qui a une carte NVIDIA : deux attentions, aucun problème.
    texte = "\n".join(lignes)
    assert "attention\u202f: Une carte NVIDIA est là" in texte
    assert "PyTorch\u202f: 2.15.0+cpu" in texte
    assert "processeur (cpu)\u202f:" in texte
    assert lignes[-1] == "Diagnostic terminé\u202f: 0 problème(s)."


def test_sortie_carte_enregistree():
    """La sortie relevée sur la RTX 5070 Ti, avec la roue gpu, à la porte de la Partie 0 : le test ne fait
    que lire le fichier, et tourne donc sans carte. Si le texte du diagnostic change, il échoue : la
    sortie est à relever de nouveau, carte au repos."""
    octets = (PROJET / "sorties" / "rtx-5070-ti.txt").read_bytes()
    assert b"\r" not in octets and octets.endswith(b".\n")
    lignes = octets.decode("utf-8").splitlines()
    assert re.fullmatch(r"# relevé le \d{4}-\d{2}-\d{2}", lignes[0])
    datetime.date.fromisoformat(lignes[0].removeprefix("# relevé le "))
    texte = "\n".join(lignes)
    assert "PyTorch\u202f: 2.15.0+cu132" in texte
    # La carte est prête, et seuls les fils restent en « attention » : les constats d'aujourd'hui, mot pour mot.
    prete = diagnostiquer(SITUATIONS["windows_cu132_rtx5070ti"])
    assert [c.cle for c in prete] == ["carte_prete"]
    fils = [c for c in diagnostiquer(SITUATIONS["fils_par_defaut"]) if c.cle == "fils"]
    assert len(fils) == 1
    for constat in (*prete, *fils):
        for ligne in decrire_constat(constat):
            assert ligne in lignes, ligne
    assert "Une carte NVIDIA est là" not in texte
    # L'essai de calcul a tourné sur le processeur, puis sur la carte.
    assert any(ligne.startswith("  processeur (cpu)\u202f: ") for ligne in lignes)
    assert any(ligne.startswith("  carte graphique (cuda)\u202f: ") for ligne in lignes)
    assert lignes[-1] == "Diagnostic terminé\u202f: 0 problème(s)."


def test_rapport_ici(monkeypatch, capsys, tmp_path):
    fichier = tmp_path / "sortie.txt"
    code, lignes = lancer(monkeypatch, capsys, arguments=["--enregistrer", str(fichier)])
    probleme = DERNIERE_LIGNE.match(lignes[-1])
    assert probleme, lignes[-1]
    assert code == (1 if int(probleme.group(1)) else 0)
    assert lignes[0] == "Ton poste"
    assert "Diagnostic" in lignes and any(ligne.startswith("Essai de calcul") for ligne in lignes)
    assert any(ligne.strip().startswith("processeur (cpu)\u202f:") for ligne in lignes)
    # Le fichier : la même sortie, précédée de la date du relevé, en UTF-8 et LF.
    octets = fichier.read_bytes()
    assert b"\r" not in octets
    assert octets.decode("utf-8") == f"# relevé le {datetime.date.today().isoformat()}\n" + "\n".join(lignes) + "\n"


def test_attention_sans_probleme(monkeypatch, capsys):
    code, lignes = lancer(monkeypatch, capsys, replace(SITUATIONS["windows_pypi_rtx5070ti"], fils_torch=8))
    assert code == 0
    texte = "\n".join(lignes)
    assert "  attention\u202f: Une carte NVIDIA est là (pilote 621.01)" in texte
    assert "    À faire\u202f: Lance `uv sync --extra gpu`, puis relance `uv run --extra gpu python -m poste`." in texte
    assert "  attention\u202f: PyTorch n’utilise que 8 fils" in texte
    assert lignes[-1] == "Diagnostic terminé\u202f: 0 problème(s)."


def test_probleme_code_1(monkeypatch, capsys):
    code, lignes = lancer(monkeypatch, capsys, SITUATIONS["pilote_ancien"])
    assert code == 1
    assert any(ligne.startswith("  problème\u202f: Ton pilote NVIDIA (551.86)") for ligne in lignes)
    # PyTorch ne voit pas la carte : pas d'essai sur elle.
    assert not any("carte graphique (cuda)" in ligne for ligne in lignes)
    assert lignes[-1] == "Diagnostic terminé\u202f: 1 problème(s)."


def test_carte_trop_recente_sans_essai_sur_la_carte(monkeypatch, capsys):
    code, lignes = lancer(monkeypatch, capsys, SITUATIONS["windows_cu126_rtx5070ti"])
    assert code == 1
    assert "  carte graphique (cuda)\u202f: pas d’essai, à cause du problème ci-dessus." in lignes


def test_carte_annoncee_mais_absente_sans_trace(monkeypatch, capsys):
    # Des faits qui annoncent une carte prête, alors que PyTorch ne la voit pas : l'essai
    # sur la carte échoue, et le rapport le dit en une ligne, sans trace Python.
    import torch

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    code, lignes = lancer(monkeypatch, capsys, SITUATIONS["windows_cu132_rtx5070ti"])
    assert code == 0
    ligne = next(ligne for ligne in lignes if "carte graphique (cuda)" in ligne)
    assert ligne.startswith("  carte graphique (cuda)\u202f: essai impossible")
    assert "Traceback" not in "\n".join(lignes)


def test_torch_absent_sans_trace(monkeypatch, capsys):
    # PyTorch ne s'importe plus : ni le relevé, ni le rapport ne doivent l'importer.
    monkeypatch.setitem(sys.modules, "torch", None)
    for module in ["poste.essai", "poste.appareil"]:
        monkeypatch.delitem(sys.modules, module, raising=False)
    code, lignes = lancer(monkeypatch, capsys)
    assert code == 1
    texte = "\n".join(lignes)
    assert "PyTorch\u202f: ne s’importe pas" in texte
    assert "  problème\u202f: PyTorch ne s’importe pas" in texte
    assert "Essai de calcul\u202f: impossible sans PyTorch." in texte
    assert lignes[-1] == "Diagnostic terminé\u202f: 1 problème(s)."


def test_sans_torch_dans_un_vrai_processus(tmp_path):
    # Le cas du lecteur qui lance `uv run python -m poste` sans extra : torch n'est pas
    # installé. On le simule dans un vrai processus, et on vérifie qu'aucune trace ne sort.
    script = (
        "import runpy, sys\n"
        "sys.modules['torch'] = None\n"
        "sys.argv = ['poste']\n"
        "runpy.run_module('poste', run_name='__main__')\n"
    )
    resultat = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        encoding="utf-8",
        cwd=PROJET,
        # Une console Windows redirigée vers un fichier écrit en cp1252, qui ne connaît pas l'espace fine.
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        timeout=60,
    )
    assert resultat.returncode == 1
    assert "Traceback" not in resultat.stderr + resultat.stdout
    assert "Diagnostic terminé" in resultat.stdout


@pytest.mark.parametrize("arguments", [["--aide"], ["--enregistrer"]])
def test_arguments_faux(monkeypatch, capsys, arguments):
    with pytest.raises(SystemExit) as fin:
        ligne_de_commande.main(arguments)
    assert fin.value.code == 2
