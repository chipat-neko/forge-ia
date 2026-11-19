"""La note expliquée est celle de forge, et chaque critère dit pourquoi, en français."""

import random
from fractions import Fraction

import pytest
from forge.conversation.format import Reponse
from forge.evaluation.consignes import CONTRAINTES
from forge.preferences.invites import InvitePreference
from forge.preferences.noter import Note, noter, raison_de_la_paire

from alignement_pas_a_pas.attendus import CONSIGNES, TEXTES
from alignement_pas_a_pas.noter import CRITERES, _nombre_lu, expliquer_note, note_de

QUESTION = InvitePreference("q", (), (("mots_max", {"n": 20}), ("minuscules", {}), ("sans_virgule", {})), None)
PROBLEME = InvitePreference("probleme:1", (), (), 84)
SANS_CONSIGNE = InvitePreference("v", (), (), None)

FRAGMENTS = (
    "La capitale de la France est Paris.",
    "paris est la capitale, et elle est belle.",
    "The capital of France is Paris and it is beautiful.",
    "12 fois 7 font 84.",
    "12 fois 7 font 85.",
    "C'est tout pour aujourd'hui.",
    "- Paris\n- Lyon\n- Marseille",
    "« Titre »\nUn texte.",
    "Oui.",
    "",
    "2026",
    "Voilà ce que je peux dire pour le moment, et je m'arrête ici.",
)


def cinquante_reponses() -> list[tuple[str, bool, InvitePreference]]:
    """Cinquante réponses fabriquées, de façon déterministe : un ou deux fragments, terminée ou coupée, une invite."""
    hasard = random.Random(8)
    invites = [QUESTION, PROBLEME, SANS_CONSIGNE]
    invites += [InvitePreference(f"c{i}", (), ((nom, kwargs),), None) for i, (nom, kwargs) in enumerate(CONSIGNES)]
    reponses = []
    for _ in range(50):
        texte = " ".join(hasard.choice(FRAGMENTS) for _ in range(hasard.randint(1, 2)))
        reponses.append((texte, hasard.random() < 0.75, hasard.choice(invites)))
    return reponses


def test_la_note_expliquee_est_celle_de_forge_sur_cinquante_reponses():
    reponses = cinquante_reponses()
    assert len(reponses) == 50
    for texte, terminee, invite in reponses:
        attendue = noter(Reponse(texte=texte, pensee=None, ids=[], terminee=terminee), invite)
        explication = expliquer_note(texte, terminee, invite)
        assert note_de(explication) == attendue, (texte, terminee, invite.id)
        assert tuple(explication["note"].values()) == tuple(attendue)


def test_la_note_expliquee_est_celle_de_forge_sur_les_textes_de_reference():
    for nom, texte in TEXTES:
        for terminee in (True, False):
            for invite in (QUESTION, PROBLEME):
                attendue = noter(Reponse(texte=texte, pensee=None, ids=[], terminee=terminee), invite)
                assert note_de(expliquer_note(texte, terminee, invite)) == attendue, (nom, terminee, invite.id)


def test_les_criteres_sont_ceux_de_forge_dans_l_ordre():
    explication = expliquer_note("La capitale de la France est Paris.", True, QUESTION)
    assert CRITERES == Note._fields == ("terminee", "juste", "consignes", "francais", "longueur")
    assert [c["nom"] for c in explication["criteres"]] == list(CRITERES)
    assert list(explication) == ["note", "criteres", "consignes", "mots", "langue"]
    for critere in explication["criteres"]:
        assert set(critere) == {"nom", "valeur", "maximum", "verdict", "raison"}
        assert critere["verdict"] == (critere["valeur"] == critere["maximum"])
        assert critere["raison"].strip() == critere["raison"] != ""


def test_une_reponse_qui_respecte_tout_dit_pourquoi():
    explication = expliquer_note("paris est la capitale de la france et elle est belle.", True, QUESTION)
    raisons = {c["nom"]: c["raison"] for c in explication["criteres"]}
    assert raisons["consignes"] == "3 consignes sur 3"
    assert raisons["francais"] == "en français"
    assert raisons["longueur"] == "11 mots"
    assert raisons["terminee"] == "la réponse a fini son tour"
    assert "question" in raisons["juste"]
    assert all(c["verdict"] for c in explication["criteres"])
    assert [c["respectee"] for c in explication["consignes"]] == [True, True, True]
    assert explication["consignes"][0]["consigne"] == "Réponds en 20 mots au plus."
    assert (explication["mots"], explication["langue"]) == (11, "fr")


def test_les_consignes_non_respectees_se_comptent_et_se_nomment():
    explication = expliquer_note("La capitale de la France est Paris, une belle ville.", True, QUESTION)
    consignes = explication["criteres"][2]
    assert consignes["raison"] == "1 consigne sur 3"  # seule la longueur de 20 mots est respectée
    assert (consignes["valeur"], consignes["maximum"], consignes["verdict"]) == (1, 3, False)
    assert [c["id"] for c in explication["consignes"] if not c["respectee"]] == ["minuscules", "sans_virgule"]
    deux = InvitePreference("z", (), (("minuscules", {}), ("titre", {})), None)
    assert expliquer_note("Oui.", True, deux)["criteres"][2]["raison"] == "0 consigne sur 2"


def test_une_invite_sans_consigne_a_zero_sur_zero():
    critere = expliquer_note("La capitale de la France est Paris.", True, SANS_CONSIGNE)["criteres"][2]
    assert (critere["raison"], critere["valeur"], critere["maximum"], critere["verdict"]) == ("0 consigne sur 0", 0, 0, True)


def test_une_reponse_coupee_perd_et_le_dit():
    explication = expliquer_note("La capitale de la France", False, QUESTION)
    assert explication["note"]["terminee"] == 0
    assert explication["criteres"][0]["raison"] == "la réponse est coupée par la limite de jetons"
    assert not explication["criteres"][0]["verdict"]


def test_la_justesse_d_un_probleme():
    juste = expliquer_note("12 fois 7 font 84.", True, PROBLEME)["criteres"][1]
    assert juste["valeur"] == 1 and juste["raison"] == "le dernier nombre de la réponse est 84, la réponse attendue"
    faux = expliquer_note("12 fois 7 font 85.", True, PROBLEME)["criteres"][1]
    assert faux["valeur"] == 0 and faux["raison"] == "le dernier nombre de la réponse est 85, pas 84"
    sans_nombre = expliquer_note("Je ne sais pas.", True, PROBLEME)["criteres"][1]
    assert sans_nombre["valeur"] == 0 and sans_nombre["raison"] == "aucun nombre dans la réponse"
    coupee = expliquer_note("12 fois 7 font 84.", False, PROBLEME)["criteres"][1]
    assert coupee["valeur"] == 0 and "coupée" in coupee["raison"]


def test_la_langue_et_la_longueur_disent_pourquoi():
    anglais = expliquer_note("The capital of France is Paris and it is beautiful.", True, SANS_CONSIGNE)
    assert anglais["note"]["francais"] == 0 and anglais["criteres"][3]["raison"] == "dans une autre langue que le français"
    court = expliquer_note("Oui.", True, SANS_CONSIGNE)
    assert court["note"]["francais"] == 1 and court["criteres"][3]["raison"] == "moins de 3 mots outils : la langue ne se juge pas, il passe"
    assert court["criteres"][4]["raison"] == "1 mot, moins de 3" and court["note"]["longueur"] == 0
    assert expliquer_note(" ".join(["mot"] * 301), True, SANS_CONSIGNE)["criteres"][4]["raison"] == "301 mots, plus de 300"
    assert expliquer_note(" ".join(["mot"] * 300), True, SANS_CONSIGNE)["criteres"][4]["raison"] == "300 mots"


def test_un_long_texte_sans_mots_outils_ne_dit_pas_qu_il_est_court():
    long_sans_outils = " ".join(f"mot{chr(97 + i % 26)}" for i in range(200)).replace("mot", "zorb")  # 200 mots, aucun mot outil
    explication = expliquer_note(long_sans_outils, True, SANS_CONSIGNE)
    assert explication["langue"] == "indetermine" and explication["mots"] == 200
    raison = explication["criteres"][3]["raison"]
    assert raison == "moins de 3 mots outils : la langue ne se juge pas, il passe" and "court" not in raison
    assert explication["criteres"][4]["raison"] == "200 mots"
    chiffres = expliquer_note(" ".join(["2026"] * 50), True, SANS_CONSIGNE)["criteres"][3]
    assert chiffres["valeur"] == 1 and "court" not in chiffres["raison"]


def test_une_fraction_s_ecrit_arrondie():
    assert _nombre_lu(Fraction(1, 3)) == "0,3333"
    assert _nombre_lu(Fraction(5, 2)) == "2,5" and _nombre_lu(Fraction(12, 1)) == "12"


def test_deux_notes_se_comparent_dans_l_ordre_des_criteres():
    invite = InvitePreference("v", (), (("minuscules", {}),), None)
    bonne = note_de(expliquer_note("paris est la capitale de la france.", True, invite))
    mauvaise = note_de(expliquer_note("Paris est la capitale de la France.", True, invite))
    assert bonne > mauvaise and raison_de_la_paire(bonne, mauvaise) == "consignes"
    coupee = note_de(expliquer_note("paris est la capitale de la france.", False, invite))
    assert coupee < mauvaise  # une réponse coupée perd toujours, même si elle respecte les consignes


def test_une_consigne_inconnue_est_refusee_comme_dans_forge():
    invite = InvitePreference("x", (), (("inconnue", {}),), None)
    with pytest.raises(ValueError, match="« inconnue » de l'invite x est inconnue") as erreur:
        expliquer_note("Bonjour.", True, invite)
    assert all(c.id in str(erreur.value) for c in CONTRAINTES)
    with pytest.raises(ValueError, match="est inconnue"):
        noter(Reponse(texte="Bonjour.", pensee=None, ids=[], terminee=True), invite)


def test_un_texte_vide_de_chiffres_ou_tres_long_ne_leve_rien():
    invite = InvitePreference("v", (), tuple(CONSIGNES), None)
    for texte in ("", "2026 12 31", "x" * 10_000):
        explication = expliquer_note(texte, True, invite)
        assert all(isinstance(c["valeur"], int) for c in explication["criteres"])
