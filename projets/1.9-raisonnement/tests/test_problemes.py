"""Un problème, sa trace et sa conversation, comparés à forge ; la vérification d'une réponse.

`montrer_probleme` ne refait pas le générateur : il montre celui de forge. Les tests le comparent donc à
`forge.raisonnement.problemes` sur tous les couples (famille, difficulté) permis et vingt graines, et contrôlent
ce que la conversation encodée apprend (la pensée et la réponse de ton IA, jamais l'énoncé).
"""

import pytest
from forge.conversation.format import Reponse
from forge.raisonnement.problemes import FORMES, conversation_de_probleme, generer_probleme
from forge.raisonnement.verification import est_juste, extraire_nombre
from forge.tokenizer import TokenizerOctets

from raisonnement_pas_a_pas.problemes import TOKENIZER, montrer_probleme, verifier_reponse

TOK = TokenizerOctets.charger(TOKENIZER)
COUPLES = [(famille, difficulte) for famille, difficultes in FORMES.items() for difficulte in difficultes]


def test_il_y_a_quatorze_couples():
    assert len(COUPLES) == 14


@pytest.mark.parametrize(("famille", "difficulte"), COUPLES)
def test_le_probleme_est_celui_de_forge(famille, difficulte):
    for graine in range(20):
        montre = montrer_probleme(famille, difficulte, graine)
        de_forge = generer_probleme(famille, difficulte, graine)
        assert (montre["id"], montre["enonce"], montre["etapes"], montre["reponse"]) == (
            de_forge.id,
            de_forge.enonce,
            list(de_forge.etapes),
            de_forge.reponse,
        )
        assert (montre["famille"], montre["difficulte"], montre["graine"]) == (famille, difficulte, graine)


def test_la_trace_calcule_la_reponse_etape_par_etape():
    p = montrer_probleme("achats", 3, 7)
    assert len(p["etapes"]) == 3
    # Chaque étape est « a op b = c », et la dernière donne la réponse.
    for etape in p["etapes"]:
        gauche, egal, c = etape.partition(" = ")
        assert egal and gauche.count(" ") == 2
    assert p["etapes"][-1].endswith(f" = {p['reponse']}")


def test_la_conversation_encodee_apprend_la_pensee_et_la_reponse():
    p = montrer_probleme("addition", 2, 3)
    c = p["conversation"]
    assert len(c["ids"]) == len(c["appris"]) == len(c["pieces"])
    tours = conversation_de_probleme(generer_probleme("addition", 2, 3))
    assert tours[0].texte == p["enonce"]
    assert tours[1].texte == f"La réponse est {p['reponse']}." and tours[1].pensee == "\n".join(p["etapes"])
    pieces = c["pieces"]
    assert pieces[0] == "<|fin_texte|>" and pieces[1] == "<|utilisateur|>"
    assert pieces[-1] == "<|fin_tour|>" and c["appris"][-1] is True
    # L'énoncé n'est jamais appris ; l'assistant l'est, à partir de la pensée.
    debut_assistant = pieces.index("<|assistant|>")
    assert not any(c["appris"][: debut_assistant + 1])
    assert pieces[debut_assistant + 1] == "<|pensee|>" and all(c["appris"][debut_assistant + 1 :])
    assert TOK.decoder(c["ids"][2 : debut_assistant - 1]) == p["enonce"]  # entre <|utilisateur|> et son <|fin_tour|>
    assert TOK.decoder([i for i in c["ids"] if i < TOK.premier_special]).endswith(f"La réponse est {p['reponse']}.")


def test_un_couple_qui_n_existe_pas_est_refuse():
    with pytest.raises(ValueError, match="Famille inconnue"):
        montrer_probleme("division", 1, 0)
    with pytest.raises(ValueError, match="La difficulté 3 n'existe pas pour la famille « partage »"):
        montrer_probleme("partage", 3, 0)
    with pytest.raises(ValueError, match="La graine"):
        montrer_probleme("addition", 1, -1)


# Les écritures d'un nombre : verifier_reponse dit le nombre lu et le verdict de forge.
def test_verifier_une_reponse_juste_fausse_ou_coupee():
    assert verifier_reponse("12 fois 7 font 84.", True, 84) == {"lu": "84", "terminee": True, "juste": True}
    assert verifier_reponse("12 fois 7 font 84.", True, 85)["juste"] is False
    # Le dernier nombre du texte compte, pas le premier.
    assert verifier_reponse("3 puis 7", True, 7)["juste"] is True and verifier_reponse("3 puis 7", True, 3)["juste"] is False
    # Une réponse coupée n'est jamais juste, même si le nombre lu est le bon : « 84 » peut venir de « 840 ».
    assert verifier_reponse("La réponse est 84", False, 84) == {"lu": "84", "terminee": False, "juste": False}
    assert verifier_reponse("rien", True, 4) == {"lu": None, "terminee": True, "juste": False}
    assert verifier_reponse("12,5", True, 12)["lu"] == "25/2"


def test_verifier_une_reponse_est_ce_que_dit_forge():
    for texte in ("La réponse est 84.", "1 234 567", "-3", "5-3", "3, puis 4", "12 3456", "x = 3.5", "", "trois"):
        for terminee in (True, False):
            for attendu in (84, 1234567, -3, 3, 4, 12, 0):
                reponse = Reponse(texte=texte, pensee=None, ids=[], terminee=terminee)
                assert verifier_reponse(texte, terminee, attendu)["juste"] is est_juste(reponse, attendu)
                lu = extraire_nombre(texte)
                assert (verifier_reponse(texte, terminee, attendu)["lu"] is None) == (lu is None)
