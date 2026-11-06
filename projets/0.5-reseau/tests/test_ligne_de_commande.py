"""`python -m premier_reseau entrainer [--appareil …] [--enregistrer FICHIER]` : sorties, fichier et codes de sortie."""

import datetime
import os
import pathlib
import re
import subprocess
import sys

import pytest
import torch

from premier_reseau.__main__ import lignes_a_la_main, lignes_du_neurone, main
from premier_reseau.a_la_main import DONNEES, GRAINE, NB_PAS, TAUX, entrainer, initialiser, predictions
from premier_reseau.neurone import PORTES, meilleur_reglage
from premier_reseau.nombres import EXPOSANTS, en_francais, simple_en_francais

PROJET = pathlib.Path(__file__).resolve().parents[1]
SORTIE_PROCESSEUR = PROJET / "sorties" / "processeur.txt"
SORTIE_CARTE = PROJET / "sorties" / "rtx-5070-ti.txt"
NOMBRE = r"[0-9\u202f]+(?:,[0-9]+)?"
PUISSANCE = r"(?:0|[0-9],[0-9] × 10[⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+)"


@pytest.fixture(autouse=True)
def sans_variable(monkeypatch):
    monkeypatch.delenv("FORGE_APPAREIL", raising=False)


def lire_puissance(texte: str) -> float:
    """« 3,1 × 10⁻¹⁷ » donne 3.1e-17, « 0 » donne 0.0 : l'inverse de en_puissance_de_dix."""
    if texte == "0":
        return 0.0
    mantisse, exposant = texte.split(" × 10")
    chiffres = {v: k for k, v in zip("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")}
    return float(mantisse.replace(",", ".")) * 10 ** int("".join(chiffres[c] for c in exposant))


def test_lire_puissance():
    assert "".join(chr(EXPOSANTS[ord(c)]) for c in "-17") == "⁻¹⁷"
    assert lire_puissance("3,1 × 10⁻¹⁷") == pytest.approx(3.1e-17) and lire_puissance("0") == 0.0


def lignes_du_neurone_attendues() -> list[str]:
    """Ce que doit dire le neurone, d'après meilleur_reglage."""
    lignes = []
    for porte, attendus in PORTES.items():
        compte, (w1, w2), b = meilleur_reglage(porte)
        nom = porte.replace("_", " ")
        reglage = f"w1 = {simple_en_francais(w1)}, w2 = {simple_en_francais(w2)} et b = {simple_en_francais(b)}"
        if compte == len(attendus):
            lignes.append(f"  {nom}\u202f: les {compte} points bien classés, avec {reglage}.")
        else:
            lignes.append(f"  {nom}\u202f: {compte} points sur 4 au mieux, avec {reglage}\u202f: aucun réglage ne les classe tous.")
    return lignes


def test_lignes_du_neurone():
    lignes = lignes_du_neurone()
    assert lignes[0] == "Le neurone à seuil, réglé au mieux sur la grille de −2 à 2 par pas de 0,5 (729 réglages)"
    assert lignes[1:] == lignes_du_neurone_attendues()
    assert lignes[1] == "  et\u202f: les 4 points bien classés, avec w1 = 0,5, w2 = 0,5 et b = −0,5."


def test_lignes_a_la_main():
    lignes = lignes_a_la_main()
    h = entrainer(initialiser(GRAINE), DONNEES, TAUX, NB_PAS)
    assert lignes[:2] == [
        "Le réseau 2-2-1, entraîné à la main sur le OU exclusif",
        f"  9 poids tirés au hasard (graine {GRAINE}), taux 1, 3\u202f000 pas sur les 4 points.",
    ]
    # La perte au départ, tous les 500 pas, et à la fin.
    assert lignes[2:9] == [f"  pas {en_francais(n)}\u202f: perte {en_francais(h.pertes[n], 3)}" for n in range(0, 3001, 500)]
    assert lignes[2] == f"  pas 0\u202f: perte {en_francais(h.pertes[0], 3)}"
    assert lignes[8].startswith("  pas 3\u202f000\u202f: perte 0,00")
    assert lignes[9:] == [
        f"  {x}\u202f: {p:.3f}, arrondi à {round(p)} (attendu\u202f: {y})".replace(".", ",")
        for (x, y), p in zip(DONNEES, predictions(h.reseau, DONNEES))
    ]
    assert [ligne.split("arrondi à ")[1][0] for ligne in lignes[9:]] == ["0", "1", "1", "0"]


def verifier_partie_pytorch(lignes: list[str], appareil: str, nom: str, version: str = torch.__version__) -> None:
    """Les 4 lignes de PyTorch : les écarts restent minuscules ; la durée n'est pas vérifiée."""
    assert lignes[0] == f"Le même réseau dans PyTorch {version}, en float64, avec les mêmes poids de départ"
    gradients = re.fullmatch(rf"  Gradients de départ, à la main et par autograd\u202f: plus grand écart ({PUISSANCE})\.", lignes[1])
    assert gradients and lire_puissance(gradients.group(1)) < 1e-12, lignes[1]
    assert re.fullmatch(rf"  3\u202f000 pas sur {nom} \({appareil}\)\u202f: {NOMBRE} ms\.", lignes[2]), lignes[2]
    h = entrainer(initialiser(GRAINE), DONNEES, TAUX, NB_PAS)
    finale = re.fullmatch(
        rf"  Perte finale ({NOMBRE}), et plus grand écart des poids finaux avec la main\u202f: ({PUISSANCE})\.", lignes[3]
    )
    assert finale, lignes[3]
    assert finale.group(1) == en_francais(h.pertes[-1], 3)
    assert lire_puissance(finale.group(2)) < 1e-6


def test_entrainer_sur_le_processeur(capsys, tmp_path):
    fichier = tmp_path / "sous-dossier" / "sortie.txt"
    assert main(["entrainer", "--appareil", "cpu", "--enregistrer", str(fichier)]) == 0
    lu = capsys.readouterr()
    assert lu.err == ""
    lignes = lu.out.splitlines()
    n, m = lignes_du_neurone(), lignes_a_la_main()
    assert lignes[: len(n) + 1 + len(m) + 1] == [*n, "", *m, ""]
    verifier_partie_pytorch(lignes[len(n) + len(m) + 2 :], "cpu", "le processeur")
    assert len(lignes) == len(n) + len(m) + 6
    # Le fichier : la même sortie, précédée de la date du relevé, en UTF-8 et LF.
    octets = fichier.read_bytes()
    assert b"\r" not in octets
    assert octets.decode("utf-8") == f"# relevé le {datetime.date.today().isoformat()}\n" + lu.out


def test_cuda_demande_sans_carte_message_francais(monkeypatch, capsys):
    # Carte cachée, comme en 0.3.
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert main(["entrainer", "--appareil", "cuda"]) == 2
    lu = capsys.readouterr()
    assert "FORGE_APPAREIL=cpu" in lu.err and "Traceback" not in lu.err
    # Rien n'est affiché avant le message : le script s'arrête tout de suite.
    assert lu.out == ""


def test_appareil_inconnu(capsys):
    assert main(["entrainer", "--appareil", "tpu"]) == 2
    lu = capsys.readouterr()
    assert "«\u202ftpu\u202f»" in lu.err and lu.out == ""


def test_sans_commande(capsys):
    with pytest.raises(SystemExit) as fin:
        main([])
    assert fin.value.code == 2


def test_carte_absente_dans_un_vrai_processus(tmp_path):
    # Le lecteur sans carte qui demande `--appareil cuda` : un vrai processus, une console
    # Windows en cp1252, et pas de trace Python. CUDA_VISIBLE_DEVICES=-1 cache la carte
    # quand il y en a une (à la porte, avec la roue gpu). Une valeur vide ne suffit pas :
    # sous Windows, une variable vide compte comme absente, et PyTorch voit encore la carte.
    sortie = tmp_path / "carte.txt"
    resultat = subprocess.run(
        [sys.executable, "-m", "premier_reseau", "entrainer", "--appareil", "cuda", "--enregistrer", str(sortie)],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        cwd=PROJET,
        env={**os.environ, "PYTHONIOENCODING": "cp1252", "CUDA_VISIBLE_DEVICES": "-1", "FORGE_APPAREIL": ""},
        timeout=120,
    )
    assert resultat.returncode == 2
    assert "Traceback" not in resultat.stderr + resultat.stdout
    assert "FORGE_APPAREIL=cpu" in resultat.stderr
    assert resultat.stdout == "" and not sortie.exists()


def test_carte_vue_mais_inutilisable(monkeypatch, capsys, tmp_path):
    # Revue finale, I1 : une carte que PyTorch voit, mais pour laquelle sa version n'a pas de code
    # (une GTX 1080 avec la roue cu132, par exemple). Le premier calcul sur elle lève une
    # RuntimeError : le script le dit en français, rend le code 2, sans trace Python, et
    # n'enregistre rien. Le neurone et l'entraînement à la main, déjà affichés, restent.
    import premier_reseau.avec_pytorch

    def en_panne(*arguments, **options):
        raise RuntimeError(
            "CUDA error: no kernel image is available for execution on the device\n"
            "CUDA kernel errors might be asynchronously reported at some other API call."
        )

    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(premier_reseau.avec_pytorch, "entrainer_pytorch", en_panne)
    fichier = tmp_path / "carte.txt"
    assert main(["entrainer", "--appareil", "cuda", "--enregistrer", str(fichier)]) == 2
    lu = capsys.readouterr()
    assert lu.err == (
        "La carte graphique n’a pas pu calculer avec cette version de PyTorch\u202f: CUDA error: no kernel "
        "image is available for execution on the device. Pour savoir pourquoi, lance `uv run --extra gpu "
        "python -m poste` dans le dossier projets/0.3-poste. Pour calculer sur le processeur, relance avec "
        "`--appareil cpu` (ou, sans `--appareil`, mets FORGE_APPAREIL=cpu).\n"
    )
    n, m = lignes_du_neurone(), lignes_a_la_main()
    assert lu.out.splitlines() == [*n, "", *m]
    assert not fichier.exists()


def test_erreur_sur_le_processeur_non_masquee(monkeypatch):
    # Seule la carte a droit au message : sur le processeur, une RuntimeError est un défaut du
    # projet, qui doit se voir en entier.
    import premier_reseau.avec_pytorch

    def en_panne(*arguments, **options):
        raise RuntimeError("panne")

    monkeypatch.setattr(premier_reseau.avec_pytorch, "entrainer_pytorch", en_panne)
    with pytest.raises(RuntimeError, match="panne"):
        main(["entrainer", "--appareil", "cpu"])


def test_carte_sans_memoire_libre(monkeypatch, capsys):
    # Un manque de mémoire sur la carte n'est pas une affaire de version de PyTorch : le message le
    # dit, sans renvoyer au diagnostic du chapitre 0.3.
    import premier_reseau.avec_pytorch

    def sans_memoire(*arguments, **options):
        raise torch.OutOfMemoryError("CUDA out of memory. Tried to allocate 2.00 MiB.")

    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(premier_reseau.avec_pytorch, "entrainer_pytorch", sans_memoire)
    assert main(["entrainer", "--appareil", "cuda"]) == 2
    assert capsys.readouterr().err == (
        "La carte graphique n’a plus assez de mémoire libre\u202f: CUDA out of memory. Tried to allocate "
        "2.00 MiB. Un autre programme s’en sert peut-être\u202f: ferme-le, puis relance le script. Pour "
        "calculer sur le processeur, relance avec `--appareil cpu` (ou, sans `--appareil`, mets "
        "FORGE_APPAREIL=cpu).\n"
    )


def test_erreur_hors_pytorch_non_masquee_sur_la_carte(monkeypatch):
    # Le neurone et l'entraînement à la main ne calculent pas sur la carte : une RuntimeError chez
    # eux est un défaut du projet, qui doit se voir en entier, même avec --appareil cuda.
    import premier_reseau.__main__ as script

    def en_panne():
        raise RuntimeError("panne")

    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(script, "lignes_a_la_main", en_panne)
    with pytest.raises(RuntimeError, match="panne"):
        main(["entrainer", "--appareil", "cuda"])


def test_pytorch_absent_sans_trace():
    # Le lecteur qui lance `uv run python -m premier_reseau entrainer` sans extra : PyTorch
    # manque. Le script le dit en français, avec la commande à lancer, sans trace Python.
    script = (
        "import runpy, sys\n"
        "sys.modules['torch'] = None\n"
        "sys.argv = ['premier_reseau', 'entrainer']\n"
        "runpy.run_module('premier_reseau', run_name='__main__')\n"
    )
    resultat = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        cwd=PROJET,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        timeout=60,
    )
    assert resultat.returncode == 2
    assert "Traceback" not in resultat.stderr + resultat.stdout
    assert "PyTorch ne s’importe pas" in resultat.stderr and "--extra cpu" in resultat.stderr


def test_sortie_processeur_enregistree():
    octets = SORTIE_PROCESSEUR.read_bytes()
    assert b"\r" not in octets and octets.endswith(b".\n")
    lignes = octets.decode("utf-8").splitlines()
    assert re.fullmatch(r"# relevé le \d{4}-\d{2}-\d{2}", lignes[0])
    datetime.date.fromisoformat(lignes[0].removeprefix("# relevé le "))
    # Le neurone et l'entraînement à la main : ce que le code donne aujourd'hui.
    n, m = lignes_du_neurone(), lignes_a_la_main()
    assert lignes[1 : len(n) + len(m) + 3] == [*n, "", *m, ""]
    # PyTorch, relevé avec la roue cpu sur le processeur. La durée, qui dépend de la machine, n'est pas figée.
    partie = lignes[len(n) + len(m) + 3 :]
    assert len(partie) == 4
    version = re.fullmatch(r"Le même réseau dans PyTorch (2\.15\.0\+\w+), .*", partie[0])
    assert version, partie[0]
    verifier_partie_pytorch(partie, "cpu", "le processeur", version.group(1))


def test_sortie_carte_enregistree():
    """La sortie relevée sur la RTX 5070 Ti, avec la roue gpu, à la porte de la Partie 0 : le test ne fait
    que lire le fichier, et tourne donc sans carte. Si le neurone ou l'entraînement à la main changent,
    il échoue : la sortie est à relever de nouveau, carte au repos."""
    octets = SORTIE_CARTE.read_bytes()
    assert b"\r" not in octets and octets.endswith(b".\n")
    lignes = octets.decode("utf-8").splitlines()
    assert re.fullmatch(r"# relevé le \d{4}-\d{2}-\d{2}", lignes[0])
    datetime.date.fromisoformat(lignes[0].removeprefix("# relevé le "))
    # Le neurone et l'entraînement à la main : ce que le code donne aujourd'hui.
    n, m = lignes_du_neurone(), lignes_a_la_main()
    assert lignes[1 : len(n) + len(m) + 3] == [*n, "", *m, ""]
    # PyTorch, relevé avec la roue gpu sur la carte. La durée, qui dépend de la machine, n'est pas figée.
    partie = lignes[len(n) + len(m) + 3 :]
    assert len(partie) == 4
    version = re.fullmatch(r"Le même réseau dans PyTorch (2\.15\.0\+cu\d+), .*", partie[0])
    assert version, partie[0]
    verifier_partie_pytorch(partie, "cuda", re.escape("la carte graphique, NVIDIA GeForce RTX 5070 Ti"), version.group(1))
