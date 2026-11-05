"""Le choix de l'appareil : la carte graphique (cuda) ou le processeur (cpu).

Ces tests cachent ou montrent la carte eux-mêmes : ils passent pareil avec la
roue cpu et, à la porte, avec la roue gpu.
"""

import pathlib

import pytest
import torch

from poste.appareil import AppareilIndisponible, choisir_appareil

APPAREIL_PY = pathlib.Path(__file__).resolve().parents[1] / "poste" / "appareil.py"


@pytest.fixture(autouse=True)
def sans_variable(monkeypatch):
    # Les tests ne dépendent pas d'un FORGE_APPAREIL réglé sur la machine.
    monkeypatch.delenv("FORGE_APPAREIL", raising=False)


def test_cuda_demande_sans_carte(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(AppareilIndisponible, match="python -m poste"):
        choisir_appareil("cuda")


def test_message_sans_carte_dit_quoi_faire(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(AppareilIndisponible) as erreur:
        choisir_appareil("cuda")
    assert str(erreur.value) == (
        "Tu as demandé la carte graphique (cuda), mais PyTorch ne la voit pas. "
        "Lance `uv run --extra gpu python -m poste` pour savoir pourquoi, ou mets FORGE_APPAREIL=cpu."
    )


def test_auto_et_variable(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert str(choisir_appareil()) == "cpu"
    monkeypatch.setenv("FORGE_APPAREIL", "cpu")
    assert str(choisir_appareil()) == "cpu"
    with pytest.raises(ValueError, match="auto"):
        choisir_appareil("tpu")


def test_la_demande_passe_avant_la_variable(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setenv("FORGE_APPAREIL", "cuda")
    with pytest.raises(AppareilIndisponible):
        choisir_appareil()
    assert str(choisir_appareil("cpu")) == "cpu"
    assert str(choisir_appareil("auto")) == "cpu"


def test_auto_avec_une_carte_visible(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert choisir_appareil().type == "cuda"
    assert choisir_appareil("cuda").type == "cuda"
    assert choisir_appareil("cpu").type == "cpu"


def test_valeur_inconnue(monkeypatch):
    with pytest.raises(ValueError) as erreur:
        choisir_appareil("tpu")
    message = str(erreur.value)
    assert "«\u202ftpu\u202f»" in message
    for valeur in ["auto", "cpu", "cuda"]:
        assert valeur in message
    # Une valeur fausse dans la variable est attribuée à la variable.
    monkeypatch.setenv("FORGE_APPAREIL", "mps")
    with pytest.raises(ValueError, match="FORGE_APPAREIL"):
        choisir_appareil()


@pytest.mark.gpu
def test_auto_prend_la_carte():
    assert choisir_appareil().type == "cuda"


def test_appareil_py_ne_depend_que_de_torch():
    # appareil.py est copié tel quel dans les projets 0.4 et 0.5 : il n'importe
    # que torch et la bibliothèque standard, jamais le reste du paquet poste.
    lignes = APPAREIL_PY.read_text(encoding="utf-8").splitlines()
    imports = [ligne.strip() for ligne in lignes if ligne.lstrip().startswith(("import ", "from "))]
    assert imports == ["import os", "import torch"]
