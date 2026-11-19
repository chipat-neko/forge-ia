"""Le petit GRPO : un modèle minuscule affiné à répéter un chiffre, puis des pas de GRPO de forge.

Le test ne demande pas que la récompense monte (vingt pas sur un modèle minuscule ne le garantissent pas, et rien ne
triche pour qu'elle monte) : seulement des nombres finis, la forme des résultats, et ce qui doit être vrai quoi qu'il
arrive, un groupe sans signal n'apprend rien. Tout tourne sur le processeur.
"""

import dataclasses
import math

import pytest
import torch
from forge.entrainement.boucle import ConfigEntrainement, ReglagesGRPO
from forge.entrainement.methodes import pas_grpo
from forge.raisonnement import grpo
from forge.tokenizer import TokenizerOctets

from raisonnement_pas_a_pas.petit_grpo import (
    CHIFFRES,
    REGLAGES,
    ChargeurDeChiffres,
    affiner_a_repeter,
    essai_grpo,
    modele_minuscule,
    probleme_de_chiffre,
)
from raisonnement_pas_a_pas.problemes import TOKENIZER

TOK = TokenizerOctets.charger(TOKENIZER)
CPU = torch.device("cpu")


@pytest.fixture(scope="module")
def modele_affine():
    modele = modele_minuscule()
    affiner_a_repeter(modele, TOK)
    return modele


# region: test-grpo
def test_l_essai_rend_des_nombres_finis_pas_a_pas():
    resultat = essai_grpo("cpu", pas=4)
    assert resultat["appareil"] == "cpu" and resultat["pas"] == 4
    assert len(resultat["recompense_moyenne"]) == len(resultat["groupes_sans_signal"]) == 4
    for cle in ("recompense_moyenne", "groupes_sans_signal", "perte_affinage"):
        assert all(isinstance(x, float) and math.isfinite(x) for x in resultat[cle]), cle
    assert all(0 <= r <= 1 for r in resultat["recompense_moyenne"])
    # Huit chiffres par pas, huit réponses chacun : la part de groupes sans signal est un multiple de 1/8.
    assert all(math.isclose(s * 8, round(s * 8), abs_tol=1e-9) and 0 <= s <= 1 for s in resultat["groupes_sans_signal"])
    assert 0 <= resultat["reussite_avant"] <= 1 and 0 <= resultat["reussite_apres"] <= 1
    assert resultat["secondes"] >= 0


def test_un_groupe_sans_signal_n_apprend_rien(modele_affine):
    modele = modele_affine
    reglages = ReglagesGRPO(pas=1, **REGLAGES)
    tirage = grpo.tirer(modele, TOK, [probleme_de_chiffre(7), probleme_de_chiffre(3)], 8, 5, reglages)
    # Des récompenses toutes égales dans chaque groupe : ni les réponses ni leur texte n'y changent rien.
    sans_signal = dataclasses.replace(tirage, recompenses=torch.tensor([[1.0] * 8, [0.0] * 8]))
    modele.zero_grad(set_to_none=True)
    perte = grpo.apprendre(modele, sans_signal, grpo.avantages(sans_signal.recompenses), 8, CPU)
    assert perte.item() == 0
    assert all(p.grad is None or not p.grad.any() for p in modele.parameters())
    # Un groupe qui a un signal, lui, en laisse un : le gradient n'est pas nul.
    avec_signal = dataclasses.replace(tirage, recompenses=torch.tensor([[1.0, 0.0] * 4, [0.0] * 8]))
    modele.zero_grad(set_to_none=True)
    grpo.apprendre(modele, avec_signal, grpo.avantages(avec_signal.recompenses), 8, CPU)
    assert any(p.grad is not None and p.grad.any() for p in modele.parameters())
    modele.zero_grad(set_to_none=True)
# fin: test-grpo


def test_un_pas_sans_aucun_signal_ne_bouge_pas_les_poids():
    # Un modèle qui ne répète jamais : la récompense est toujours 0, tous les groupes sont sans signal.
    modele = modele_minuscule(graine=3)
    avant = [p.detach().clone() for p in modele.parameters()]
    reglages = ReglagesGRPO(pas=1, **REGLAGES)
    config = ConfigEntrainement(
        methode="grpo", depart="essai", preset=modele.config, donnees="essai", sortie="essai", micro_lot=16, taux_max=1e-2,
        echauffement=0, evaluation_tous_pas=1000, appareil="cpu", compiler="non", graine=0, grpo=reglages,
    )
    optimiseur = torch.optim.AdamW(modele.parameters(), lr=1e-2, weight_decay=0.0)
    mesures = pas_grpo(modele, optimiseur, ChargeurDeChiffres(8), config, 1e-2, CPU, {"tokenizer": TOK}, numero=1)
    assert mesures["recompense_moyenne"] == 0.0 and mesures["groupes_sans_signal"] == 1.0
    assert all(torch.equal(a, p) for a, p in zip(avant, modele.parameters(), strict=True))


def test_le_chargeur_prend_les_chiffres_a_la_suite_en_boucle():
    chargeur = ChargeurDeChiffres(4)
    reponses = [[p.reponse for p in chargeur.lot()] for _ in range(4)]
    assert reponses == [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 0, 1], [2, 3, 4, 5]]
    p = probleme_de_chiffre(7)
    assert (p.enonce, p.reponse, p.etapes) == ("Répète : 7", 7, ())


def test_l_affinage_apprend_la_reponse_et_jamais_l_enonce():
    modele = modele_minuscule()
    pertes = affiner_a_repeter(modele, TOK, pas=30)
    assert len(pertes) == 30 and all(math.isfinite(x) for x in pertes)
    assert pertes[-1] < pertes[0]  # il apprend quelque chose, même en trente pas
    # Les dix chiffres sont des conversations différentes : la perte ne porte que sur la réponse et son <|fin_tour|>.


def test_la_recompense_est_la_justesse_de_forge():
    reponses = {"7": True, "8": False, "Je répète 7": True, "": False}
    for texte, juste in reponses.items():
        ids = [*TOK.encoder(texte), TOK.id_special("<|fin_tour|>")]
        assert grpo.recompense(grpo.lire_reponse(TOK, ids), probleme_de_chiffre(7)) == float(juste), texte
    coupee = grpo.lire_reponse(TOK, TOK.encoder("7"))  # pas de <|fin_tour|> : coupée
    assert grpo.recompense(coupee, probleme_de_chiffre(7)) == 0.0


def test_l_essai_sur_une_carte_absente_est_refuse():
    if torch.cuda.is_available():
        pytest.skip("la carte graphique est là : rien à refuser")
    with pytest.raises(RuntimeError, match="PyTorch ne la voit pas"):
        essai_grpo("cuda", pas=1)


def test_il_y_a_dix_chiffres():
    assert CHIFFRES == tuple(range(10))
