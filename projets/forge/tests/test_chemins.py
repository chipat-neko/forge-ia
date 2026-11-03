"""Tests des chemins des données : dossier racine et place disponible."""

from pathlib import Path

import pytest

from forge.chemins import PlaceInsuffisante, dossier, racine_donnees, verifier_place


def test_racine_par_defaut(monkeypatch, tmp_path):
    monkeypatch.delenv("FORGE_DONNEES", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert racine_donnees() == tmp_path / "forge-ia-donnees"


def test_racine_variable(monkeypatch, tmp_path):
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path / "x"))
    assert dossier("tokens", "train") == tmp_path / "x" / "tokens" / "train"
    assert (tmp_path / "x" / "tokens" / "train").is_dir()


def test_place_insuffisante(tmp_path):
    with pytest.raises(PlaceInsuffisante, match="Il manque"):
        verifier_place(10**18, tmp_path)
