"""Le tout petit affinage : un modèle minuscule apprend à finir son tour, sur le processeur."""

import json

import pytest
from forge.affinage.jeu import ChargeurAffinage, lire_index
from forge.conversation.format import Tour, encoder_conversation
from forge.modele import nombre_parametres
from forge.publication import charger_publication
from forge.tokenizer import TokenizerOctets

from conversation_pas_a_pas.gabarit import TOKENIZER
from conversation_pas_a_pas.petit_affinage import (
    CONVERSATIONS,
    CONTEXTE,
    INVITES,
    MODELE,
    VALIDATION,
    config_affinage,
    config_pre_entrainement,
    essai_affinage,
    preparer_jeu,
    preparer_pre_entrainement,
    tours_de,
)

TOK = TokenizerOctets.charger(TOKENIZER)


@pytest.fixture(scope="module")
def essai():
    return essai_affinage("cpu", pas=80)


def test_petit_affinage_apprend_a_s_arreter(essai):
    r = essai
    assert r["fin_de_tour_apres"] > r["fin_de_tour_avant"] and r["pertes"][-1] < r["pertes"][0]


def test_le_modele_ne_s_arretait_jamais_avant_et_s_arrete_le_plus_souvent_apres(essai):
    assert essai["fin_de_tour_avant"] == 0.0
    assert essai["fin_de_tour_apres"] >= 0.5


def test_l_essai_rend_ce_que_le_chapitre_montre(essai):
    assert essai["appareil"] == "cpu" and essai["pas"] == 80 and len(essai["pertes"]) == 80
    assert all(p > 0 for p in essai["pertes"])
    assert [r["invite"] for r in essai["reponses_avant"]] == list(INVITES) == [r["invite"] for r in essai["reponses_apres"]]
    assert sum(r["terminee"] for r in essai["reponses_apres"]) / len(INVITES) == essai["fin_de_tour_apres"]
    assert essai["exemples"] == len(CONVERSATIONS) and essai["parametres"] == nombre_parametres(MODELE)
    assert essai["jetons_appris"] < essai["jetons"] and essai["secondes"] > 0
    # Tout se garde en JSON, sans NaN : c'est ce que `essai --json` écrit.
    json.dumps(essai, allow_nan=False)


def test_les_questions_d_essai_sont_neuves_et_les_conversations_bien_formees():
    questions = {q for q, _ in CONVERSATIONS}
    assert len(CONVERSATIONS) == 24 and len(questions) == 24
    assert not questions & set(INVITES) and len(INVITES) == 8
    for q, r in CONVERSATIONS:
        exemple = encoder_conversation(TOK, tours_de(q, r))
        assert len(exemple.ids) < CONTEXTE and any(exemple.appris)


def test_le_jeu_est_un_jeu_sft_de_forge(tmp_path):
    dossier = preparer_jeu(tmp_path, TOK)
    index = lire_index(dossier)
    assert index["sorte"] == "sft" and index["longueur"] == CONTEXTE and index["exemples"] == 24
    assert index["ecartes"] == 0 and index["rangees"]["train"] >= 1 and index["rangees"]["val"] >= 1
    # Plusieurs conversations par rangée : moins de rangées que d'exemples.
    assert index["rangees"]["train"] + index["rangees"]["val"] < 24
    lot = ChargeurAffinage(dossier, "train", 2, graine=0).lot()
    assert (lot.cibles != -100).any() and (lot.cibles == -100).any()
    assert VALIDATION == 4


def test_les_jetons_de_depart_portent_l_empreinte_du_tokenizer(tmp_path):
    dossier = preparer_pre_entrainement(tmp_path, TOK)
    index = json.loads((dossier / "index.json").read_text(encoding="utf-8"))
    assert index["tokenizer"]["taille_vocabulaire"] == 32768 and index["tokenizer"]["empreinte"]
    assert (dossier / ".complet").exists() and (dossier / "train" / "fragment-00000.bin").exists()


def test_les_deux_configurations(tmp_path):
    pre, affinage = config_pre_entrainement("cpu", tmp_path), config_affinage("cpu", tmp_path, 80)
    assert pre.methode == "pre_entrainement" and pre.pas_total == 40 and pre.modele.longueur_contexte == CONTEXTE
    assert affinage.methode == "sft" and affinage.pas_total == 80 and affinage.depart is not None
    assert (pre.modele.dim, pre.modele.couches, pre.modele.tetes) == (64, 2, 4)


def test_le_depart_est_publie_comme_une_vraie_version(tmp_path):
    racine = tmp_path / "essai"
    essai_affinage("cpu", pas=4, racine=racine)
    publication = charger_publication(racine / "ton-ia-essai")
    assert publication.version == "ton-ia-essai" and publication.modele.config.dim == 64
    assert (racine / "ton-ia-essai" / "config.json").exists()


def test_sans_racine_rien_ne_reste_ecrit(tmp_path, monkeypatch):
    monkeypatch.setenv("TMP", str(tmp_path))
    monkeypatch.setenv("TEMP", str(tmp_path))
    monkeypatch.setattr("tempfile.tempdir", None)
    essai_affinage("cpu", pas=2)
    assert list(tmp_path.iterdir()) == []


def test_un_texte_du_site_introuvable_est_dit(tmp_path, monkeypatch):
    monkeypatch.setattr("conversation_pas_a_pas.petit_affinage.TEXTE_DU_SITE", tmp_path / "absent.txt")
    with pytest.raises(FileNotFoundError, match="projets/1.1-modele-de-langage"):
        preparer_pre_entrainement(tmp_path, TOK)


def test_tours_de():
    assert tours_de("Q", "R") == [Tour("utilisateur", "Q"), Tour("assistant", "R")]
