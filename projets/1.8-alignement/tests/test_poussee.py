"""Ce que la DPO pousse : une paire, un modèle minuscule, quelques pas, avec le vrai code de forge."""

import json
import math

import pytest
import torch

from forge.affinage.dpo import logps_des_rangees
from forge.entrainement.boucle import ReglagesDPO
from forge.tokenizer import TokenizerOctets

from alignement_pas_a_pas.perte_dpo import perte_dpo_a_la_main, terme_sft_a_la_main
from alignement_pas_a_pas.poussee import PAIRE_FABRIQUEE, TOKENIZER, lot_de_la_paire, modele_minuscule, paire_du_notebook, pousser

TOK = TokenizerOctets.charger(TOKENIZER)


def test_le_lot_a_deux_rangees_et_ne_masque_que_la_reponse():
    lot = lot_de_la_paire(TOK, PAIRE_FABRIQUEE)
    assert lot.ids.shape == lot.cibles.shape == lot.documents.shape and lot.ids.shape[0] == 2
    appris = (lot.cibles != -100).sum(dim=1).tolist()
    choisie = TOK.encoder(PAIRE_FABRIQUEE["choisie"]["texte"])
    rejetee = TOK.encoder(PAIRE_FABRIQUEE["rejetee"]["texte"])
    assert appris == [len(choisie) + 1, len(rejetee)]  # la choisie finit son tour (<|fin_tour|> appris), la rejetée est coupée
    # La première cible apprise est le premier jeton de la réponse, juste après <|assistant|>.
    assistant = TOK.id_special("<|assistant|>")
    for rang, reponse in enumerate((choisie, rejetee)):
        debut = (lot.cibles[rang] != -100).nonzero()[0].item()
        assert lot.ids[rang, debut].item() == assistant and lot.cibles[rang, debut].item() == reponse[0]
    # Le bourrage est le document -1, et n'est jamais une cible.
    assert lot.documents.min().item() == -1
    assert ((lot.documents == -1) <= (lot.cibles == -100)).all()


def test_avant_le_premier_pas_la_politique_est_la_reference():
    modele = modele_minuscule(128)
    lot = lot_de_la_paire(TOK, PAIRE_FABRIQUEE)
    releves = pousser(modele, lot, ReglagesDPO(beta=0.1, poids_sft=0.0), 0, 1e-3)
    assert len(releves) == 1 and releves[0]["pas"] == 0
    assert releves[0]["marge"] == pytest.approx(0.0, abs=1e-12)
    assert releves[0]["perte"] == pytest.approx(math.log(2), abs=1e-6)  # z = 0 : -ln σ(0) = ln 2


def test_le_releve_du_pas_0_est_calcule_a_la_main_avec_le_terme_sft():
    modele = modele_minuscule(128)
    lot = lot_de_la_paire(TOK, PAIRE_FABRIQUEE)
    releves = pousser(modele, lot, ReglagesDPO(beta=0.1, poids_sft=1.0), 0, 1e-3)
    with torch.no_grad():
        somme, appris = logps_des_rangees(modele, lot, torch.device("cpu"))
    pc, lc = somme[0].item(), appris[0].item()
    attendu = perte_dpo_a_la_main(pc, somme[1].item(), pc, somme[1].item(), 0.1) + terme_sft_a_la_main(pc, lc)
    assert releves[0]["perte"] == pytest.approx(attendu, abs=1e-5)
    assert releves[0]["logps_choisie"] == pytest.approx(pc / lc, abs=1e-6)


def test_quelques_pas_creusent_la_marge_et_font_baisser_la_perte():
    modele = modele_minuscule(128)
    lot = lot_de_la_paire(TOK, PAIRE_FABRIQUEE)
    releves = pousser(modele, lot, ReglagesDPO(beta=0.1, poids_sft=0.0), 20, 1e-3)
    assert [r["pas"] for r in releves] == list(range(21))
    assert releves[-1]["marge"] > releves[0]["marge"] + 1.0
    assert releves[-1]["perte"] < releves[0]["perte"]
    assert set(releves[0]) == {"pas", "logps_choisie", "logps_rejetee", "marge", "perte"}
    assert json.loads(json.dumps(releves, allow_nan=False)) == releves


def test_le_modele_de_depart_est_reproductible():
    a = pousser(modele_minuscule(128, graine=3), lot_de_la_paire(TOK, PAIRE_FABRIQUEE), ReglagesDPO(poids_sft=0.0), 3, 1e-3)
    b = pousser(modele_minuscule(128, graine=3), lot_de_la_paire(TOK, PAIRE_FABRIQUEE), ReglagesDPO(poids_sft=0.0), 3, 1e-3)
    assert a == b


def test_sans_fichier_la_paire_est_fabriquee(tmp_path):
    paire, reelle = paire_du_notebook(tmp_path / "paires-exemples.json")
    assert paire is PAIRE_FABRIQUEE and reelle is False


def test_avec_un_fichier_la_paire_est_la_premiere_reelle(tmp_path):
    reelle = {
        "invite": [{"role": "utilisateur", "texte": "Dis bonjour en minuscules."}],
        "contraintes": [["minuscules", {}]],
        "attendu": None,
        "choisie": {"texte": "bonjour !", "terminee": True, "note": {}},
        "rejetee": {"texte": "Bonjour !", "terminee": True, "note": {}},
    }
    chemin = tmp_path / "paires-exemples.json"
    chemin.write_text(json.dumps([reelle, {**reelle, "invite": []}]), encoding="utf-8")
    paire, est_reelle = paire_du_notebook(chemin)
    assert est_reelle is True
    assert paire["invite"][0]["texte"] == "Dis bonjour en minuscules." and paire["choisie"]["texte"] == "bonjour !"
    assert set(paire) == {"invite", "choisie", "rejetee", "contraintes", "attendu"}
    # Une vraie paire se pousse comme la fabriquée.
    lot = lot_de_la_paire(TOK, paire)
    assert lot.ids.shape[0] == 2


def test_un_fichier_sans_paire_donne_la_paire_fabriquee(tmp_path):
    chemin = tmp_path / "paires-exemples.json"
    chemin.write_text("[]", encoding="utf-8")
    assert paire_du_notebook(chemin) == (PAIRE_FABRIQUEE, False)
