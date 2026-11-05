"""Les faits du poste : ce que disent Python, PyTorch et nvidia-smi."""

import subprocess
import sys

import pytest
import torch

from poste import faits as module_faits
from poste.faits import decrire_faits, lire_cuda_max, lire_pilote, relever_faits

# L'en-tête de nvidia-smi, tel que l'écrivent les pilotes jusqu'à la série 58x…
ENTETE_ANCIENNE = """\
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 551.86                 Driver Version: 551.86         CUDA Version: 12.4     |
|-----------------------------------------+------------------------+----------------------+
"""
# … et tel que l'écrit le pilote 621.01 de la RTX 5070 Ti (relevé le 05/11/2026).
ENTETE_RECENTE = """\
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 621.01                 KMD Version: 621.01        CUDA UMD Version: 13.5     |
+-----------------------------------------+------------------------+----------------------+
"""


def test_relever_faits_ici():
    f = relever_faits()
    assert f.torch and f.fils_processeur >= 1


def test_relever_faits_ici_en_detail():
    f = relever_faits()
    assert f.torch == torch.__version__
    assert f.cuda_compilee == torch.version.cuda
    assert f.cuda_disponible == torch.cuda.is_available()
    assert f.fils_torch == torch.get_num_threads()
    assert f.python == ".".join(str(n) for n in sys.version_info[:3])
    assert isinstance(f.architectures, tuple)


def test_lire_l_entete_de_nvidia_smi():
    assert lire_cuda_max(ENTETE_ANCIENNE) == "12.4"
    assert lire_cuda_max(ENTETE_RECENTE) == "13.5"
    assert lire_cuda_max("pas d'en-tête ici") is None
    assert lire_pilote("621.01\n") == "621.01"
    # Deux cartes : on garde la première.
    assert lire_pilote("580.82.07\n580.82.07\n") == "580.82.07"
    assert lire_pilote("\n") is None


def test_sans_nvidia_smi_ni_pilote(monkeypatch):
    def introuvable(*args, **kwargs):
        raise FileNotFoundError("nvidia-smi")

    monkeypatch.setattr(module_faits.subprocess, "run", introuvable)
    f = relever_faits()
    assert (f.pilote, f.cuda_max_pilote) == (None, None)


def test_nvidia_smi_trop_lent(monkeypatch):
    def trop_lent(commande, *args, **kwargs):
        assert kwargs["timeout"] == 5
        raise subprocess.TimeoutExpired(commande, kwargs["timeout"])

    monkeypatch.setattr(module_faits.subprocess, "run", trop_lent)
    f = relever_faits()
    assert (f.pilote, f.cuda_max_pilote) == (None, None)


def test_nvidia_smi_en_erreur(monkeypatch):
    # nvidia-smi est là, mais le pilote ne répond pas : il rend un code d'erreur.
    def en_erreur(commande, *args, **kwargs):
        return subprocess.CompletedProcess(commande, 9, stdout="", stderr="NVIDIA-SMI has failed")

    monkeypatch.setattr(module_faits.subprocess, "run", en_erreur)
    assert relever_faits().pilote is None


def test_nvidia_smi_present(monkeypatch):
    def repond(commande, *args, **kwargs):
        sortie = "621.01\n" if any(o.startswith("--query-gpu") for o in commande) else ENTETE_RECENTE
        return subprocess.CompletedProcess(commande, 0, stdout=sortie, stderr="")

    monkeypatch.setattr(module_faits.subprocess, "run", repond)
    f = relever_faits()
    assert (f.pilote, f.cuda_max_pilote) == ("621.01", "13.5")


def test_pas_de_contexte_cuda_sans_carte(monkeypatch):
    # Sans carte visible, relever_faits ne touche à rien d'autre de torch.cuda.
    def interdit(*args, **kwargs):
        raise AssertionError("relever_faits a interrogé la carte alors que CUDA n'est pas disponible")

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    for nom in ["get_device_name", "get_device_capability", "get_arch_list", "init", "current_device"]:
        monkeypatch.setattr(torch.cuda, nom, interdit)
    f = relever_faits()
    assert (f.cuda_disponible, f.carte, f.capacite, f.architectures) == (False, None, None, ())


def test_carte_vue(monkeypatch):
    # Ce que relever_faits garde d'une carte visible (simulée : ce test passe aussi sans carte).
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "get_device_name", lambda i=0: "NVIDIA GeForce RTX 5070 Ti")
    monkeypatch.setattr(torch.cuda, "get_device_capability", lambda i=0: (12, 0))
    monkeypatch.setattr(torch.cuda, "get_arch_list", lambda: ["sm_75", "sm_120"])
    f = relever_faits()
    assert (f.cuda_disponible, f.carte, f.capacite, f.architectures) == (
        True,
        "NVIDIA GeForce RTX 5070 Ti",
        (12, 0),
        ("sm_75", "sm_120"),
    )


def test_sans_torch(monkeypatch):
    # Un module à None dans sys.modules fait échouer son import (ImportError).
    monkeypatch.setitem(sys.modules, "torch", None)
    f = relever_faits()
    assert (f.torch, f.cuda_compilee, f.cuda_disponible, f.fils_torch) == (None, None, False, 0)
    assert f.fils_processeur >= 1


@pytest.mark.parametrize("nom", ["windows_pypi_rtx5070ti", "windows_cu132_rtx5070ti", "sans_carte"])
def test_decrire_faits(nom):
    from poste.diagnostic import SITUATIONS

    lignes = decrire_faits(SITUATIONS[nom])
    texte = "\n".join(lignes)
    assert lignes[0] == "Ton poste"
    assert "Système\u202f: Windows 11" in texte
    assert "Fils du processeur\u202f: 16" in texte
    if nom == "windows_pypi_rtx5070ti":
        assert "CUDA dans PyTorch\u202f: aucune" in texte
        assert "Pilote NVIDIA\u202f: 621.01, jusqu’à CUDA 13.5" in texte
    if nom == "windows_cu132_rtx5070ti":
        assert "Carte vue par PyTorch\u202f: NVIDIA GeForce RTX 5070 Ti, capacité 12.0" in texte
        assert "sm_120" in texte
    if nom == "sans_carte":
        assert "Pilote NVIDIA\u202f: aucun" in texte


def test_decrire_faits_sans_torch():
    from dataclasses import replace

    from poste.diagnostic import SITUATIONS

    texte = "\n".join(decrire_faits(replace(SITUATIONS["sans_carte"], torch=None, fils_torch=0)))
    assert "PyTorch\u202f: ne s’importe pas" in texte
    assert "CUDA dans PyTorch" not in texte
