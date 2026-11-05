"""Les chronos : un produit de matrices sur le processeur (avec 1 fil, ou plus) et sur la carte.

Les durées dépendent de la machine : ces tests vérifient le format des mesures,
pas leurs valeurs. Les mesures enregistrées, `mesures/processeur.json`, sont
celles du PC de La Forge IA.
"""

import datetime
import json
import os
import pathlib

import pytest
import torch

from tenseurs.__main__ import main
from tenseurs.appareil import AppareilIndisponible
from tenseurs.chrono import (
    TAILLES,
    chronometrer_produit,
    chronometrer_transfert,
    en_francais,
    fils_a_mesurer,
    mesurer,
    nom_processeur,
)

PROJET = pathlib.Path(__file__).resolve().parents[1]
MESURES_PROCESSEUR = PROJET / "mesures" / "processeur.json"
CLES = ["version", "releve_le", "appareil", "nom", "torch", "fils_par_defaut", "fils_max", "mesures", "transfert_ms"]


@pytest.fixture(autouse=True)
def sans_variable(monkeypatch):
    # Les tests ne dépendent pas d'un FORGE_APPAREIL réglé sur la machine.
    monkeypatch.delenv("FORGE_APPAREIL", raising=False)


def verifier_format(m: dict, appareil: str) -> None:
    """Le format commun des mesures (version 1), sur le processeur ou sur la carte."""
    assert list(m) == CLES
    assert m["version"] == 1 and m["appareil"] == appareil
    datetime.date.fromisoformat(m["releve_le"])
    assert isinstance(m["nom"], str) and m["nom"].strip()
    assert isinstance(m["torch"], str) and m["torch"]
    assert isinstance(m["fils_par_defaut"], int) and isinstance(m["fils_max"], int)
    assert 1 <= m["fils_par_defaut"] <= m["fils_max"]
    assert m["mesures"]
    for mesure in m["mesures"]:
        assert list(mesure) == ["taille", "fils", "millisecondes"]
        assert isinstance(mesure["taille"], int) and mesure["taille"] > 0
        assert type(mesure["millisecondes"]) is float and mesure["millisecondes"] > 0
    # Une seule mesure par couple (taille, fils), rangées par taille.
    couples = [(mesure["taille"], mesure["fils"]) for mesure in m["mesures"]]
    assert len(couples) == len(set(couples))
    tailles = [mesure["taille"] for mesure in m["mesures"]]
    assert tailles == sorted(tailles)
    # Le fichier s'écrit en JSON, sans NaN.
    assert json.loads(json.dumps(m, allow_nan=False)) == m


def test_chronometrer_produit_processeur():
    assert chronometrer_produit(64, "cpu") > 0


def test_chronometrer_produit_retablit_les_fils():
    avant = torch.get_num_threads()
    assert chronometrer_produit(64, "cpu", fils=1, repetitions=3, echauffement=1) > 0
    assert torch.get_num_threads() == avant


def test_les_fils_sont_retablis_meme_en_cas_d_erreur(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    avant = torch.get_num_threads()
    with pytest.raises(AppareilIndisponible):
        chronometrer_produit(64, "cuda", fils=1)
    assert torch.get_num_threads() == avant


def test_transfert_sans_carte(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(AppareilIndisponible, match="FORGE_APPAREIL=cpu"):
        chronometrer_transfert(64)


def test_fils_a_mesurer(monkeypatch):
    # 1 fil, le réglage par défaut de PyTorch, et tous les fils du processeur, sans doublon.
    monkeypatch.setattr(torch, "get_num_threads", lambda: 8)
    monkeypatch.setattr(os, "cpu_count", lambda: 16)
    assert fils_a_mesurer() == (1, 8, 16)
    monkeypatch.setattr(torch, "get_num_threads", lambda: 16)
    assert fils_a_mesurer() == (1, 16)
    monkeypatch.setattr(torch, "get_num_threads", lambda: 1)
    monkeypatch.setattr(os, "cpu_count", lambda: 1)
    assert fils_a_mesurer() == (1,)
    # os.cpu_count() peut ne rien savoir : on garde ce que PyTorch utilise.
    monkeypatch.setattr(torch, "get_num_threads", lambda: 4)
    monkeypatch.setattr(os, "cpu_count", lambda: None)
    assert fils_a_mesurer() == (1, 4)


def test_nom_processeur():
    nom = nom_processeur()
    assert isinstance(nom, str) and nom.strip() == nom and nom


def test_mesurer_processeur_petit():
    m = mesurer("cpu", tailles=(64,))
    verifier_format(m, "cpu")
    assert m["transfert_ms"] is None
    assert m["fils_par_defaut"] == torch.get_num_threads()
    assert m["fils_max"] == (os.cpu_count() or torch.get_num_threads())
    assert m["torch"] == torch.__version__
    fils = [mesure["fils"] for mesure in m["mesures"]]
    assert fils == list(fils_a_mesurer())
    assert 1 in fils and m["fils_max"] in fils
    assert all(mesure["taille"] == 64 for mesure in m["mesures"])


def test_mesurer_avec_des_fils_choisis():
    m = mesurer("cpu", tailles=(32, 64), fils=(1, 2))
    assert [(x["taille"], x["fils"]) for x in m["mesures"]] == [(32, 1), (32, 2), (64, 1), (64, 2)]


def test_mesurer_carte_absente(monkeypatch, capsys, tmp_path):
    # La carte est cachée : le message d'AppareilIndisponible, en français, sans trace, et rien d'écrit.
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    sortie = tmp_path / "carte.json"
    assert main(["mesurer", "--appareil", "cuda", "--sortie", str(sortie)]) == 2
    lu = capsys.readouterr()
    assert "Tu as demandé la carte graphique (cuda), mais PyTorch ne la voit pas." in lu.err
    assert "FORGE_APPAREIL=cpu" in lu.err
    assert "Traceback" not in lu.err + lu.out
    assert not sortie.exists()
    assert list(tmp_path.iterdir()) == []


def test_mesures_processeur_enregistrees():
    octets = MESURES_PROCESSEUR.read_bytes()
    assert b"\r" not in octets and octets.endswith(b"}\n")
    m = json.loads(octets.decode("utf-8"))
    verifier_format(m, "cpu")
    assert m["transfert_ms"] is None
    assert sorted({x["taille"] for x in m["mesures"]}) == [64, 256, 1024, 2048, 4096] == list(TAILLES)
    # Pour chaque taille : 1 fil, le réglage par défaut et tous les fils.
    for taille in TAILLES:
        fils = [x["fils"] for x in m["mesures"] if x["taille"] == taille]
        assert fils == list(dict.fromkeys([1, m["fils_par_defaut"], m["fils_max"]])), taille


@pytest.mark.gpu
def test_mesurer_carte_petit():
    m = mesurer("cuda", tailles=(64,))
    verifier_format(m, "cuda")
    assert m["nom"] == torch.cuda.get_device_name(0)
    assert [x["fils"] for x in m["mesures"]] == [None]
    assert list(m["transfert_ms"]) == ["64"]
    assert all(type(ms) is float and ms > 0 for ms in m["transfert_ms"].values())


def test_en_francais():
    assert en_francais(2.134) == "2,1"
    assert en_francais(0.00523) == "0,0052"
    assert en_francais(4096) == "4\u202f096"
    assert en_francais(1234.5, chiffres=3) == "1\u202f234"
