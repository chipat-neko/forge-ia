"""Tests des conversations générées par programme (plan 7, tâche 10) : messages système et identité de ton IA."""

import re
from dataclasses import replace

from forge.conversation import generees
from forge.conversation.format import Tour, verifier_conversation
from forge.conversation.generees import (
    IDENTITE,
    PERSONNAGES,
    conversations_identite,
    conversations_systeme,
)
from forge.evaluation.consignes import CONTRAINTES

LETTRES = "abcdefghijklmnopqrstuvwxyz"


def mot(i: int) -> str:
    """Un mot de lettres seulement (les chiffres ne sont pas des lettres), distinct pour chaque entier."""
    return LETTRES[i % 26] + LETTRES[(i // 26) % 26] + "ouvement" + LETTRES[(i // 676) % 26]


def base_de(n: int) -> list[list[Tour]]:
    """`n` conversations d'un tour : une question, une réponse de plusieurs phrases."""
    base = []
    for i in range(n):
        question = f"Peux-tu m'expliquer le {mot(i)} et le {mot(i + 1)} de façon simple ?"
        reponse = (
            f"Bien sûr, le {mot(i)} est une notion simple. Elle sert à comprendre le {mot(i + 1)}, "
            f"et on la voit partout. Premier exemple, le {mot(i)} du matin. Deuxième exemple, le {mot(i + 1)} du soir. "
            "Voilà, c'est tout ce qu'il faut retenir pour commencer."
        )
        base.append([Tour("utilisateur", question), Tour("assistant", reponse)])
    return base


def espionner(monkeypatch) -> list[tuple]:
    """Remplace `CONTRAINTES` par des copies qui notent leurs tirages : (contrainte, kwargs)."""
    notes: list[tuple] = []

    def espionne(c):
        def tirer(hasard, question):
            kwargs = c.tirer(hasard, question)
            if kwargs is not None:
                notes.append((c, kwargs))
            return kwargs

        return replace(c, tirer=tirer)

    monkeypatch.setattr(generees, "CONTRAINTES", tuple(espionne(c) for c in CONTRAINTES))
    return notes


# --- Les textes écrits à la main ----------------------------------------------------------------------


def test_vingt_personnages_distincts_et_soignes():
    assert len(PERSONNAGES) == 20 and len(set(PERSONNAGES)) == 20
    for texte in PERSONNAGES:
        assert texte.startswith("Tu es ") and texte.endswith(".") and texte == texte.strip()
        assert "  " not in texte and "<|" not in texte


def test_l_identite_a_trente_couples_distincts():
    assert len(IDENTITE) >= 30
    assert len({question for question, _ in IDENTITE}) == len(IDENTITE)
    for question, reponse in IDENTITE:
        assert question.strip() and reponse.strip() and "<|" not in question + reponse


def test_l_identite_ne_dit_que_des_faits_et_pas_de_miracles():
    reponses = " ".join(reponse for _, reponse in IDENTITE)
    for fait in ("ton IA", "La Forge IA", "français", "Python", "433,6 millions", "me trompe"):
        assert fait in reponses, fait
    # Elle ne répond pas encore bien et son code ne marche pas : rien ne dit le contraire.
    for faux in ("toujours juste", "sans erreur", "code fonctionne", "code marche", "meilleure", "ne me trompe jamais"):
        assert faux not in reponses.lower(), faux
    assert "mon code ne marche pas" in reponses.lower() or "mon code est souvent faux" in reponses.lower()


def test_la_typographie_du_projet_dans_les_textes_ecrits_a_la_main():
    fine = "\u202f"
    texte = " ".join(PERSONNAGES + tuple(t for couple in IDENTITE for t in couple))
    assert not re.search(r"[ \u00a0][?!:;]", texte)  # jamais d'espace ordinaire devant ? ! : ;
    assert "'" not in texte  # l'apostrophe est courbe
    assert fine in texte and "\u2019" in texte
    assert "«" in texte
    assert not re.search("«(?!\u202f)", texte) and not re.search("(?<!\u202f)»", texte)  # espace fine dans « »


# --- conversations_identite -----------------------------------------------------------------------------


def test_identite_avec_et_sans_message_systeme():
    conversations = conversations_identite()
    assert len(conversations) == 2 * len(IDENTITE) >= 60
    for tours in conversations:
        verifier_conversation(tours)
    avec = [c for c in conversations if c[0].role == "systeme"]
    sans = [c for c in conversations if c[0].role == "utilisateur"]
    assert len(avec) == len(sans) == len(IDENTITE)
    for (question, reponse), un, deux in zip(IDENTITE, sans, avec, strict=True):
        assert un == [Tour("utilisateur", question), Tour("assistant", reponse)]
        assert deux[1:] == un and deux[0].texte.strip()
    assert conversations == conversations_identite()  # pas de hasard


# --- conversations_systeme ------------------------------------------------------------------------------


def test_chaque_conversation_systeme_passe_le_format_et_sa_contrainte(monkeypatch):
    notes = espionner(monkeypatch)
    base = base_de(300)
    resultat = conversations_systeme(base, 120, graine=5)
    assert 100 <= len(resultat) <= 120
    for tours in resultat:
        verifier_conversation(tours)
        systeme, utilisateur, assistant = tours
        assert (systeme.role, utilisateur.role, assistant.role) == ("systeme", "utilisateur", "assistant")
        assert any(
            systeme.texte.endswith(c.consigne(kwargs)) and c.verifier(assistant.texte, kwargs)
            for c, kwargs in notes
        ), systeme.texte
        assert assistant.pensee is None


def test_le_message_systeme_est_personnage_espace_consigne_une_fois_sur_deux(monkeypatch):
    notes = espionner(monkeypatch)
    resultat = conversations_systeme(base_de(1000), 800, graine=11)
    avec_personnage = 0
    for tours in resultat:
        texte = tours[0].texte
        suffixes = {c.consigne(kwargs) for c, kwargs in notes}
        consigne = next(s for s in suffixes if texte.endswith(s))
        debut = texte[: len(texte) - len(consigne)]
        if debut:
            avec_personnage += 1
            assert debut.endswith(" ") and debut[:-1] in PERSONNAGES
    assert 0.4 < avec_personnage / len(resultat) < 0.6


def test_les_reponses_sont_transformees_et_les_questions_gardees():
    base = base_de(60)
    resultat = conversations_systeme(base, 40, graine=2)
    questions = {tours[0].texte for tours in base}
    assert all(tours[1].texte in questions for tours in resultat)
    assert any(tours[2].texte != next(b[1].texte for b in base if b[0].texte == tours[1].texte) for tours in resultat)


def test_conversations_systeme_est_deterministe_et_depend_de_la_graine():
    base = base_de(200)
    assert conversations_systeme(base, 50, graine=1) == conversations_systeme(base, 50, graine=1)
    assert conversations_systeme(base, 50, graine=1) != conversations_systeme(base, 50, graine=2)


def test_seules_les_conversations_a_un_tour_servent_de_base():
    deux_tours = [
        Tour("utilisateur", "Une première question assez longue ?"),
        Tour("assistant", "Une première réponse. Suivie d'une autre phrase."),
        Tour("utilisateur", "Et une deuxième question ?"),
        Tour("assistant", "Une deuxième réponse. Avec encore une phrase."),
    ]
    avec_systeme = [Tour("systeme", "Tu es poli.")] + base_de(1)[0]
    avec_pensee = [Tour("utilisateur", "Calcule vite cela ?"), Tour("assistant", "La réponse est 4.", pensee="2 + 2 = 4")]
    base = [deux_tours, avec_systeme, avec_pensee]
    assert conversations_systeme(base, 10, graine=0) == []
    copie = [list(c) for c in base_de(5)]
    conversations_systeme(copie, 3, graine=0)
    assert copie == base_de(5)  # la base n'est pas modifiée


def test_pas_plus_de_n_conversations():
    assert len(conversations_systeme(base_de(100), 7, graine=3)) == 7
    assert conversations_systeme(base_de(100), 0, graine=3) == []
    assert conversations_systeme([], 5, graine=3) == []
