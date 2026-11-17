"""Tests des écritures atomiques, des formats à la française et des chemins sous FORGE_DONNEES."""

import os
from pathlib import Path

import pytest

from forge import fichiers
from forge.chemins import racine_donnees, sous_forge_donnees
from forge.fichiers import ESPACE_FINE, duree, scientifique, ecrire_atomique, ecrire_atomique_vers, ecrire_texte, entier, nombre, remplacer


def test_ecrire_atomique_ecrit_et_ne_laisse_pas_de_tmp(tmp_path):
    chemin = tmp_path / "etat.json"
    ecrire_atomique(chemin, lambda fichier: fichier.write(b"abc"))
    assert chemin.read_bytes() == b"abc"
    assert [f.name for f in tmp_path.iterdir()] == ["etat.json"]


def test_ecrire_atomique_force_les_octets_sur_le_disque(tmp_path, monkeypatch):
    forces = []
    vrai_fsync = os.fsync
    monkeypatch.setattr(fichiers.os, "fsync", lambda descripteur: (forces.append(descripteur), vrai_fsync(descripteur)))
    ecrire_atomique(tmp_path / "a.bin", lambda fichier: fichier.write(b"x"))
    ecrire_texte(tmp_path / "b.txt", "x")
    ecrire_atomique_vers(tmp_path / "c.bin", lambda temporaire: temporaire.write_bytes(b"x"))
    assert len(forces) == 3


@pytest.mark.parametrize("erreur", [OSError("disque plein"), KeyboardInterrupt()])
def test_erreur_au_milieu_garde_l_ancien_fichier_et_efface_le_tmp(tmp_path, erreur):
    chemin = tmp_path / "etat.json"
    chemin.write_bytes(b"ancien")

    def ecrire(fichier):
        fichier.write(b"a moitie")
        raise erreur

    with pytest.raises(type(erreur)):
        ecrire_atomique(chemin, ecrire)
    assert chemin.read_bytes() == b"ancien"
    assert [f.name for f in tmp_path.iterdir()] == ["etat.json"]


def test_erreur_dans_ecrire_atomique_vers_efface_le_tmp(tmp_path):
    chemin = tmp_path / "poids.safetensors"

    def ecrire(temporaire):
        temporaire.write_bytes(b"a moitie")
        raise OSError("coupure")

    with pytest.raises(OSError, match="coupure"):
        ecrire_atomique_vers(chemin, ecrire)
    assert list(tmp_path.iterdir()) == []


def test_fichier_verrouille_simule_est_reessaye_puis_ecrit(tmp_path, monkeypatch):
    vrai_replace = os.replace
    refus = []

    def replace_bloque_deux_fois(source, cible):
        if len(refus) < 2:
            refus.append(cible)
            raise PermissionError(13, "Accès refusé")
        vrai_replace(source, cible)

    monkeypatch.setattr(fichiers.os, "replace", replace_bloque_deux_fois)
    monkeypatch.setattr(fichiers.time, "sleep", lambda secondes: None)
    ecrire_texte(tmp_path / "rapport.md", "bonjour\n")
    assert len(refus) == 2
    assert (tmp_path / "rapport.md").read_text(encoding="utf-8") == "bonjour\n"


def test_fichier_toujours_verrouille_leve_un_message_clair_et_efface_le_tmp(tmp_path, monkeypatch):
    def refuse(source, cible):
        raise PermissionError(13, "Accès refusé")

    monkeypatch.setattr(fichiers.os, "replace", refuse)
    monkeypatch.setattr(fichiers.time, "sleep", lambda secondes: None)
    cible = tmp_path / "rapport.json"
    with pytest.raises(PermissionError, match="Windows refuse de remplacer") as erreur:
        ecrire_atomique(cible, lambda fichier: fichier.write(b"x"), conseil="Relance avec --reprendre.")
    assert "Relance avec --reprendre." in str(erreur.value)
    assert list(tmp_path.iterdir()) == []


def test_remplacer_remplace(tmp_path):
    (tmp_path / "a").write_text("1")
    (tmp_path / "b").write_text("2")
    remplacer(tmp_path / "a", tmp_path / "b")
    assert (tmp_path / "b").read_text() == "1" and not (tmp_path / "a").exists()


def test_ecrire_texte_garde_les_fins_de_ligne_lf(tmp_path):
    ecrire_texte(tmp_path / "t.md", "a\nb\né\n")
    assert (tmp_path / "t.md").read_bytes() == "a\nb\né\n".encode("utf-8")


def test_formats_a_la_francaise():
    assert nombre(1234.5678, 2) == "1234,57"
    assert nombre(1234.5, 1, milliers=" ") == "1 234,5"
    assert nombre(1234567.0, 0, milliers=ESPACE_FINE) == "1" + ESPACE_FINE + "234" + ESPACE_FINE + "567"
    assert scientifique(0.0003) == "3,0e-04"
    assert entier(52000.4) == "52 000"
    assert entier(52000, milliers=ESPACE_FINE) == "52" + ESPACE_FINE + "000"
    assert [duree(s) for s in (-3, 12, 250, 3900, 183600)] == ["0 s", "12 s", "4 min 10 s", "1 h 05 min", "2 j 3 h"]


def test_un_nom_va_sous_forge_donnees_un_chemin_absolu_reste_tel_quel(monkeypatch, tmp_path):
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path / "donnees"))
    assert sous_forge_donnees("essai", "jetons") == racine_donnees() / "jetons" / "essai"
    assert sous_forge_donnees(Path("a") / "b", "entrainements") == racine_donnees() / "entrainements" / "a" / "b"
    absolu = tmp_path / "ailleurs"
    assert sous_forge_donnees(str(absolu), "jetons") == absolu
    assert sous_forge_donnees(absolu, "jetons") == absolu
