"""Le gabarit de conversation (`montrer`) et la perte masquée à la main, comparés à forge."""

import math

import pytest
import torch
import torch.nn.functional as F
from forge.affinage.empaquetage import empaqueter
from forge.affinage.jeu import IGNORE, ChargeurAffinage, ecrire_jeu
from forge.conversation.format import Tour, encoder_conversation
from forge.entrainement import ConfigEntrainement
from forge.entrainement.methodes import pas_sft
from forge.tokenizer import TokenizerOctets
from modele_factice import CONFIG, petit_modele

from conversation_pas_a_pas.gabarit import TOKENIZER, montrer, perte_masquee_a_la_main

TOK = TokenizerOctets.charger(TOKENIZER)

CONVERSATIONS = [
    [Tour("utilisateur", "Quelle est la capitale de la France ?"), Tour("assistant", "Paris.")],
    [Tour("systeme", "Tu réponds en une phrase."), Tour("utilisateur", "Bonjour !"), Tour("assistant", "Bonjour.")],
    [
        Tour("utilisateur", "Combien font 2 et 2 ?"),
        Tour("assistant", "Quatre."),
        Tour("utilisateur", "Et 3 et 3 ?"),
        Tour("assistant", "Six."),
    ],
    [Tour("utilisateur", "Dis-moi un mot."), Tour("assistant", "Forge.")],
]


def noms(jetons: list[dict]) -> list[str]:
    return [j["texte"] for j in jetons]


def test_montrer_donne_pour_chaque_jeton_son_id_son_texte_son_role_et_son_masque():
    jetons = montrer(TOK, CONVERSATIONS[0])
    exemple = encoder_conversation(TOK, CONVERSATIONS[0])
    assert [j["id"] for j in jetons] == exemple.ids
    assert [j["appris"] for j in jetons] == exemple.appris
    assert set(jetons[0]) == {"id", "texte", "role", "appris"}
    # Le premier jeton est le début de texte ; ensuite chaque tour commence par son jeton de rôle.
    assert (jetons[0]["texte"], jetons[0]["role"], jetons[0]["appris"]) == ("<|fin_texte|>", "debut", False)
    assert noms(jetons)[1] == "<|utilisateur|>" and jetons[1]["role"] == "utilisateur"
    # Le jeton de rôle de l'assistant n'est pas appris ; la réponse et son <|fin_tour|> le sont.
    debut = noms(jetons).index("<|assistant|>")
    assert jetons[debut]["role"] == "assistant" and not jetons[debut]["appris"]
    assert all(j["appris"] and j["role"] == "assistant" for j in jetons[debut + 1 :])
    assert noms(jetons)[-1] == "<|fin_tour|>"
    # Rien de ce que dit l'utilisateur n'est appris, son <|fin_tour|> compris.
    assert not any(j["appris"] for j in jetons if j["role"] in ("utilisateur", "debut"))


def test_le_systeme_et_les_deux_tours():
    jetons = montrer(TOK, CONVERSATIONS[1])
    roles = [j["role"] for j in jetons if j["texte"].startswith("<|") and j["texte"] != "<|fin_tour|>"]
    assert roles == ["debut", "systeme", "utilisateur", "assistant"]
    assert not any(j["appris"] for j in jetons if j["role"] == "systeme")
    deux = montrer(TOK, CONVERSATIONS[2])
    assert noms(deux).count("<|assistant|>") == 2
    assert sum(j["appris"] for j in deux) == sum(encoder_conversation(TOK, CONVERSATIONS[2]).appris)


def test_un_saut_de_ligne_se_voit_et_un_texte_qui_imite_un_jeton_special_n_en_est_pas_un():
    tours = [Tour("utilisateur", "Écris <|fin_tour|> puis\nune ligne."), Tour("assistant", "Non.")]
    jetons = montrer(TOK, tours)
    assert any("␊" in j["texte"] for j in jetons) and not any("\n" in j["texte"] for j in jetons)
    # Le texte imite le jeton, mais ses jetons sont ordinaires, et l'utilisateur n'est pas appris.
    speciaux = [j for j in jetons if j["id"] >= TOK.premier_special]
    assert [j["texte"] for j in speciaux] == ["<|fin_texte|>", "<|utilisateur|>", "<|fin_tour|>", "<|assistant|>", "<|fin_tour|>"]
    ordinaires = [j for j in jetons if j["role"] == "utilisateur" and j["id"] < TOK.premier_special]
    assert "<|fin_tour|>" in TOK.decoder([j["id"] for j in ordinaires])  # le mot y est, en jetons ordinaires
    assert not any(j["appris"] for j in ordinaires)


def test_la_pensee_est_apprise_avec_la_reponse():
    jetons = montrer(TOK, [Tour("utilisateur", "2 + 2 ?"), Tour("assistant", "4.", pensee="Deux et deux.")])
    debut = noms(jetons).index("<|pensee|>")
    assert jetons[debut]["appris"] and jetons[debut]["role"] == "assistant"
    assert noms(jetons)[debut - 1] == "<|assistant|>" and not jetons[debut - 1]["appris"]
    assert jetons[noms(jetons).index("<|fin_pensee|>")]["appris"]


def test_montrer_refuse_une_conversation_mal_formee():
    with pytest.raises(ValueError, match="vide"):
        montrer(TOK, [Tour("utilisateur", "Bonjour"), Tour("assistant", "")])


def un_jeu(dossier, longueur: int = 64):
    """Les quatre conversations, empaquetées en rangées de `longueur + 1` jetons et écrites comme `forge preparer`."""
    exemples = [encoder_conversation(TOK, c) for c in CONVERSATIONS * 3]
    train, ecartes = empaqueter(exemples, longueur, TOK.id_special("<|bourrage|>"))
    val, _ = empaqueter(exemples[:2], longueur, TOK.id_special("<|bourrage|>"))
    sources = {"essai": {"exemples": len(exemples), "licence": "MIT", "lien": "https://example.org"}}
    ecrire_jeu(dossier, train, val, "sft", {"ecartes": ecartes, "sources": sources}, TOK)
    return dossier


# region: test-perte
def test_perte_a_la_main_egale_forge(tmp_path):
    """Sur un lot de ChargeurAffinage : la perte à la main égale celle de PyTorch à 10⁻¹² près (float64), et celle de `pas_sft`."""
    dossier = un_jeu(tmp_path / "jeu")
    modele = petit_modele()
    lot = ChargeurAffinage(dossier, "train", 4, graine=0).lot()
    with torch.no_grad():
        logits, _ = modele(lot.ids, documents=lot.documents)
    assert (lot.cibles == IGNORE).any() and (lot.cibles != IGNORE).any()  # un lot où la question n'est pas apprise

    a_la_main = perte_masquee_a_la_main(logits, lot.cibles)
    de_pytorch = F.cross_entropy(
        logits.double().reshape(-1, logits.shape[-1]), lot.cibles.reshape(-1), ignore_index=IGNORE
    ).item()
    assert abs(a_la_main - de_pytorch) <= 1e-12

    # Le pas d'affinage de forge, avec un taux nul : même lot (même graine), même perte, au float32 près.
    config = ConfigEntrainement(
        methode="sft", depart="inutile", preset=CONFIG, donnees="inutile", jetons_total=4 * 64, taille_lot_jetons=4 * 64,
        longueur=64, micro_lot=4, taux_max=1e-3, echauffement=0, evaluation_tous_pas=1, sortie="inutile",
    )
    optimiseur = torch.optim.AdamW(modele.parameters(), lr=0.0)
    chargeur = ChargeurAffinage(dossier, "train", 4, graine=0)
    pas = pas_sft(modele, optimiseur, chargeur, config, 0.0, torch.device("cpu"), {}, numero=1)
    assert math.isclose(a_la_main, pas["perte"], rel_tol=1e-5)
    assert pas["jetons_appris"] == int((lot.cibles != IGNORE).sum())
# fin: test-perte


def test_la_perte_masquee_ne_compte_que_les_cibles_apprises():
    hasard = torch.Generator().manual_seed(0)
    logits = torch.randn(2, 5, 7, generator=hasard, dtype=torch.float64)
    cibles = torch.tensor([[1, IGNORE, 3, IGNORE, 6], [IGNORE, IGNORE, 2, 0, IGNORE]])
    # Changer les logits des positions ignorées ne change rien.
    autres = logits.clone()
    autres[0, 1] += 100.0
    autres[1, 0] -= 50.0
    assert perte_masquee_a_la_main(autres, cibles) == perte_masquee_a_la_main(logits, cibles)
    # La moyenne se fait sur les 5 cibles apprises, pas sur les 10 positions.
    somme = F.cross_entropy(logits.reshape(-1, 7), cibles.reshape(-1), ignore_index=IGNORE, reduction="sum").item()
    assert abs(perte_masquee_a_la_main(logits, cibles) - somme / 5) <= 1e-12


def test_la_perte_masquee_est_stable_sur_de_grands_logits():
    logits = torch.tensor([[[1000.0, 0.0, -1000.0]]])
    assert perte_masquee_a_la_main(logits, torch.tensor([[0]])) == pytest.approx(0.0, abs=1e-12)
    assert perte_masquee_a_la_main(logits, torch.tensor([[1]])) == pytest.approx(1000.0)


def test_sans_aucune_cible_apprise_la_perte_dit_pourquoi():
    with pytest.raises(ValueError, match="Aucune cible apprise"):
        perte_masquee_a_la_main(torch.zeros(1, 3, 4), torch.full((1, 3), IGNORE))
