"""Tests des jeux d'affinage sur disque (plan 7, tâche 5) : empaquetage BFD, format, chargeur."""

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from forge.affinage.empaquetage import Rangee, empaqueter
from forge.affinage.jeu import (
    VERSION_DU_JEU,
    ChargeurAffinage,
    ecrire_jeu,
    lire_index,
)
from forge.chemins import PlaceInsuffisante
from forge.conversation.format import ExempleMasque
from forge.donnees import jetons as module_jetons
from forge.erreurs import DonneesManquantes
from forge.modele.transformer import masque_des_documents
from forge.tokenizer import TokenizerOctets

TOKENIZER = Path(__file__).parent.parent / "forge" / "ressources" / "tokenizer-ton-ia-v1.json"
TOK = TokenizerOctets.charger(TOKENIZER)
B = TOK.id_special("<|fin_texte|>")


def ex(n: int, depart: int = 100, appris: bool = True) -> ExempleMasque:
    """Un exemple de `n` jetons (depart, depart + 1, …), dont le dernier est appris (ou aucun)."""
    return ExempleMasque(ids=list(range(depart, depart + n)), appris=[False] * (n - 1) + [appris])


def longueurs_des_documents(rangee: Rangee) -> list[int]:
    numeros = [d for d in rangee.documents if d >= 0]
    return [numeros.count(k) for k in sorted(set(numeros))]


def test_bfd_exact():
    rangees, ecartes = empaqueter([ex(5), ex(4), ex(3), ex(2), ex(1)], longueur=5, bourrage=B)  # capacité 6
    assert [longueurs_des_documents(r) for r in rangees] == [[5, 1], [4, 2], [3]] and ecartes == 0


def test_rangees_completees_par_du_bourrage():
    rangees, _ = empaqueter([ex(4), ex(1)], longueur=5, bourrage=B)
    (r,) = rangees
    assert len(r.ids) == len(r.appris) == len(r.documents) == 6
    assert r.documents == [0, 0, 0, 0, 1, -1] and r.ids[-1] == B and r.appris[-1] is False


def test_egalite_de_longueur_par_rang_d_origine():
    a, b = ex(3, depart=100), ex(3, depart=200)
    rangees, _ = empaqueter([a, b], longueur=5, bourrage=B)  # 3 + 3 = 6 : une seule rangée, a puis b
    assert rangees[0].ids[:6] == a.ids + b.ids
    rangees, _ = empaqueter([b, a], longueur=5, bourrage=B)
    assert rangees[0].ids[:6] == b.ids + a.ids


def test_trop_long_et_sans_appris_ecartes():
    rangees, ecartes = empaqueter([ex(7), ex(3, appris=False), ex(6), ex(2)], longueur=5, bourrage=B)
    assert ecartes == 2  # ex(6) tient : longueur + 1 = 6
    assert [longueurs_des_documents(r) for r in rangees] == [[6], [2]]


def test_rien_a_empaqueter():
    assert empaqueter([], longueur=5, bourrage=B) == ([], 0)
    assert empaqueter([ex(9)], longueur=5, bourrage=B) == ([], 1)


def _jeu(tmp_path: Path, sorte: str = "sft", train: int = 12, val: int = 2) -> Path:
    exemples = [ex(2 + i % 4, depart=100 + 10 * i) for i in range(train * 3)]
    rangees, ecartes = empaqueter(exemples, longueur=7, bourrage=B)
    val_rangees, _ = empaqueter([ex(3, depart=500 + i) for i in range(val * 2)], longueur=7, bourrage=B)
    assert len(rangees) >= train and len(val_rangees) >= val
    dossier = tmp_path / "jeu"
    ecrire_jeu(
        dossier,
        rangees[:train],
        val_rangees[:val],
        sorte,
        {"ecartes": ecartes, "sources": {"essai": {"exemples": 36, "licence": "CC0", "lien": "x"}}},
        TOK,
    )
    return dossier


def _rangees_du_disque(dossier: Path, partie: str = "train", largeur: int = 8):
    ids = np.fromfile(dossier / partie / "ids.bin", dtype="<u2").reshape(-1, largeur)
    appris = np.fromfile(dossier / partie / "appris.bin", dtype="u1").reshape(-1, largeur).astype(bool)
    return ids, appris


def test_ecriture_et_index(tmp_path):
    dossier = _jeu(tmp_path)
    index = lire_index(dossier)
    assert index["version"] == VERSION_DU_JEU == 1
    assert index["sorte"] == "sft" and index["longueur"] == 7
    assert index["rangees"] == {"train": 12, "val": 2}
    assert 0 < index["jetons_appris"] <= index["jetons"]
    assert index["ecartes"] == 0 and index["exemples"] >= 14
    assert index["sources"]["essai"]["licence"] == "CC0"
    assert (dossier / ".complet").is_file()
    assert (dossier / "train" / "ids.bin").stat().st_size == 12 * 8 * 2
    assert (dossier / "train" / "appris.bin").stat().st_size == 12 * 8
    assert (dossier / "train" / "documents.bin").stat().st_size == 12 * 8 * 2


def test_lire_index_sans_complet_ou_version_inconnue(tmp_path):
    dossier = _jeu(tmp_path)
    (dossier / ".complet").unlink()
    with pytest.raises(DonneesManquantes, match="forge preparer"):
        lire_index(dossier)
    (dossier / ".complet").write_text("")
    index = json.loads((dossier / "index.json").read_text(encoding="utf-8"))
    index["version"] = 99
    (dossier / "index.json").write_text(json.dumps(index), encoding="utf-8")
    with pytest.raises(ValueError, match="forge preparer"):
        lire_index(dossier)


def test_ecriture_refuse_sans_place(tmp_path, monkeypatch):
    def refuser(*_args, **_kw):
        raise PlaceInsuffisante("plein")

    monkeypatch.setattr("forge.affinage.jeu.verifier_place", refuser)
    with pytest.raises(PlaceInsuffisante):
        _jeu(tmp_path)
    assert not (tmp_path / "jeu" / ".complet").exists()


def test_cibles_masquees(tmp_path):
    dossier = _jeu(tmp_path)
    ids, appris = _rangees_du_disque(dossier)
    lot = ChargeurAffinage(dossier, "train", taille_lot=12, graine=0).lot()
    assert lot.ids.shape == lot.cibles.shape == lot.documents.shape == (12, 7)
    assert lot.reference is None
    # Le lot contient chaque rangée du disque une fois ; les ids de départ identifient la rangée.
    debuts = {int(ids[k, 0]): k for k in range(12)}
    assert len(debuts) == 12
    for i in range(12):
        origine = debuts[int(lot.ids[i, 0])]
        assert lot.ids[i].tolist() == ids[origine, :-1].tolist()
        attendu = np.where(appris[origine, 1:], ids[origine, 1:].astype(np.int64), -100)
        assert lot.cibles[i].tolist() == attendu.tolist()
    # Le bourrage n'est jamais appris, et ses documents valent -1.
    assert ((lot.documents == -1) <= (lot.cibles == -100)).all()
    assert (lot.cibles == -100).any() and (lot.cibles != -100).any()


def test_bourrage_jamais_appris(tmp_path):
    rangees, _ = empaqueter([ex(3), ex(2)], longueur=7, bourrage=B)  # 5 jetons, 3 de bourrage
    ecrire_jeu(tmp_path / "j", rangees, rangees, "sft", {}, TOK)
    lot = ChargeurAffinage(tmp_path / "j", "train", taille_lot=1, graine=0).lot()
    assert lot.documents.tolist() == [[0, 0, 0, 1, 1, -1, -1]]
    assert lot.ids[0, -1].item() == B
    assert lot.cibles[0, -3:].tolist() == [-100, -100, -100] and lot.cibles[0, 3].item() == 101


def test_documents_utilisables_par_le_masque(tmp_path):
    lot = ChargeurAffinage(_jeu(tmp_path), "train", taille_lot=4, graine=1).lot()
    masque = masque_des_documents(lot.documents)
    assert masque.shape == (4, 1, 7, 7)
    assert masque.diagonal(dim1=-2, dim2=-1).all()  # jamais de ligne vide : pas de NaN


def test_reprise_du_chargeur(tmp_path):
    dossier = _jeu(tmp_path)
    chargeur = ChargeurAffinage(dossier, "train", taille_lot=5, graine=3)
    for _ in range(5):
        chargeur.lot()
    etat = chargeur.etat()
    suite = [chargeur.lot().ids for _ in range(5)]  # franchit une fin d'époque (12 rangées)
    autre = ChargeurAffinage(dossier, "train", taille_lot=5, graine=3)
    autre.restaurer(json.loads(json.dumps(etat)))
    assert all((a == b).all() for a, b in zip(suite, [autre.lot().ids for _ in range(5)]))
    with pytest.raises(ValueError, match="graine"):
        ChargeurAffinage(dossier, "train", taille_lot=5, graine=4).restaurer(etat)


def test_chargeur_deterministe_et_graine(tmp_path):
    dossier = _jeu(tmp_path)
    a = ChargeurAffinage(dossier, "train", 4, 7).lot().ids
    b = ChargeurAffinage(dossier, "train", 4, 7).lot().ids
    c = ChargeurAffinage(dossier, "train", 4, 8).lot().ids
    assert (a == b).all() and not (a == c).all()
    assert ChargeurAffinage(dossier, "val", 2, 0).rangees == 2


def test_paires_restent_ensemble(tmp_path):
    dossier = _jeu(tmp_path, sorte="dpo", train=12)
    ids, _ = _rangees_du_disque(dossier)
    debuts = {int(ids[k, 0]): k for k in range(12)}
    chargeur = ChargeurAffinage(dossier, "train", taille_lot=4, graine=2)
    assert chargeur.rangees == 12
    vues = []
    for _ in range(9):  # plus d'une époque
        lot = chargeur.lot()
        for k in range(0, 4, 2):
            choisie, rejetee = debuts[int(lot.ids[k, 0])], debuts[int(lot.ids[k + 1, 0])]
            assert choisie % 2 == 0 and rejetee == choisie + 1
            vues.append(choisie)
    assert len(set(vues[:6])) == 6  # une époque : chaque paire une fois
    with pytest.raises(ValueError, match="pair"):
        ChargeurAffinage(dossier, "train", taille_lot=3, graine=0)


def test_dpo_exige_un_nombre_pair_de_rangees(tmp_path):
    rangees, _ = empaqueter([ex(3)], longueur=7, bourrage=B)
    with pytest.raises(ValueError, match="paires"):
        ecrire_jeu(tmp_path / "x", rangees, [], "dpo", {}, TOK)


def test_reference_lue_si_presente(tmp_path):
    dossier = _jeu(tmp_path)
    valeurs = np.arange(12, dtype="<f8") / 4
    valeurs.tofile(dossier / "train" / "reference.bin")
    ids, _ = _rangees_du_disque(dossier)
    debuts = {int(ids[k, 0]): k for k in range(12)}
    lot = ChargeurAffinage(dossier, "train", taille_lot=12, graine=0).lot()
    assert lot.reference.dtype == torch.float64
    for i in range(12):
        assert lot.reference[i].item() == valeurs[debuts[int(lot.ids[i, 0])]]
    np.arange(3, dtype="<f8").tofile(dossier / "train" / "reference.bin")
    with pytest.raises(ValueError, match="reference.bin"):
        ChargeurAffinage(dossier, "train", taille_lot=12, graine=0)


def test_index_partage_le_bloc_tokenizer(tmp_path):
    index = lire_index(_jeu(tmp_path))
    empreinte = module_jetons.empreinte_du_tokenizer(TOK)
    attendu = module_jetons._assembler_l_index({}, [], TOK, empreinte)["tokenizer"]
    assert index["tokenizer"] == attendu
    assert set(attendu) == {"nom", "taille_vocabulaire", "empreinte"}


def test_reecriture_efface_l_ancienne_reference(tmp_path):
    dossier = _jeu(tmp_path)
    for partie in ("train", "val"):
        np.zeros(12 if partie == "train" else 2, dtype="<f8").tofile(dossier / partie / "reference.bin")
        (dossier / partie / "reference.json").write_text("{}", encoding="utf-8")
    dossier = _jeu(tmp_path)  # même jeu, réécrit
    for partie in ("train", "val"):
        assert not (dossier / partie / "reference.bin").exists()
        assert not (dossier / partie / "reference.json").exists()
    assert ChargeurAffinage(dossier, "train", taille_lot=4, graine=0).lot().reference is None


def test_pas_de_cible_a_la_frontiere_de_deux_documents(tmp_path):
    premier_appris = ExempleMasque(ids=[1, 2, 3], appris=[True, True, True])
    rangees, _ = empaqueter([premier_appris, premier_appris], longueur=5, bourrage=B)
    ecrire_jeu(tmp_path / "j", rangees, rangees, "sft", {}, TOK)
    lot = ChargeurAffinage(tmp_path / "j", "train", taille_lot=1, graine=0).lot()
    assert lot.cibles[0].tolist() == [2, 3, -100, 2, 3]  # le 1 qui ouvre le 2e document n'est pas visé


def test_identifiant_trop_grand_refuse(tmp_path):
    rangees, _ = empaqueter([ExempleMasque(ids=[70000], appris=[True])], longueur=3, bourrage=B)
    with pytest.raises(ValueError, match="16 bits"):
        ecrire_jeu(tmp_path / "j", rangees, [], "sft", {}, TOK)
