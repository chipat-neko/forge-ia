"""Tests de `forge discuter` : converser avec une version publiée (plan 7, tâche 11).

La saisie est simulée (`input` remplacé par une liste de lignes). Les réponses viennent soit d'un faux
`repondre_lot` qui note ce qu'on lui demande (pour vérifier l'historique), soit d'un vrai petit modèle.
"""

import pytest

from forge.__main__ import main
from forge.conversation.format import Reponse, Tour
from forge.evaluation import reponses as module_reponses

from test_etape import CONFIG, publier

pytestmark = pytest.mark.filterwarnings("ignore:Le tokenizer de .* n'a pas pu être vérifié")


class Saisie:
    """Rend les lignes une à une ; à court de lignes, lève `EOFError` comme un terminal fermé."""

    def __init__(self, lignes):
        self.lignes = list(lignes)
        self.invites = []

    def __call__(self, invite=""):
        self.invites.append(invite)
        if not self.lignes:
            raise EOFError
        return self.lignes.pop(0)


@pytest.fixture
def appels(monkeypatch):
    """Un faux `repondre_lot` : répond « Réponse k. » et note les conversations reçues."""
    notes = []

    def faux(modele, tok, conversations, n_nouveaux=512, temperature=0.0, top_k=50, graine=0, lot=32):
        notes.append({"tours": list(conversations[0]), "n": n_nouveaux, "temperature": temperature, "graine": graine})
        return [Reponse(texte=f"Réponse {len(notes)}.", pensee=None, ids=[], terminee=True)]

    monkeypatch.setattr(module_reponses, "repondre_lot", faux)
    return notes


def discuter(tmp_path, monkeypatch, lignes, *options):
    saisie = Saisie(lignes)
    monkeypatch.setattr("builtins.input", saisie)
    code = main(["discuter", "--modele", str(publier(tmp_path)), "--appareil", "cpu", *options])
    return code, saisie


def test_deux_tours_puis_nouveau_puis_quitter(tmp_path, monkeypatch, capsys, appels):
    code, _ = discuter(tmp_path, monkeypatch, ["Bonjour", "Et toi ?", "/nouveau", "Salut", "/quitter"])
    assert code == 0
    assert [[t.role for t in a["tours"]] for a in appels] == [
        ["utilisateur"],
        ["utilisateur", "assistant", "utilisateur"],
        ["utilisateur"],  # /nouveau : repart de zéro
    ]
    assert appels[1]["tours"][1] == Tour("assistant", "Réponse 1.")
    sortie = capsys.readouterr().out
    assert "Réponse 1." in sortie and "Réponse 2." in sortie and "Réponse 3." in sortie
    assert "/nouveau" in sortie and "/quitter" in sortie  # l'accueil dit comment s'en servir


def test_systeme_est_le_premier_tour_et_survit_a_nouveau(tmp_path, monkeypatch, appels):
    code, _ = discuter(tmp_path, monkeypatch, ["Bonjour", "/nouveau", "Salut", "/quitter"], "--systeme", "Réponds en vers.")
    assert code == 0
    assert appels[0]["tours"][0] == Tour("systeme", "Réponds en vers.")
    assert appels[1]["tours"][0] == Tour("systeme", "Réponds en vers.") and len(appels[1]["tours"]) == 2


def test_la_temperature_est_celle_de_l_option(tmp_path, monkeypatch, appels):
    discuter(tmp_path, monkeypatch, ["Bonjour", "/quitter"], "--temperature", "0.3")
    assert appels[0]["temperature"] == 0.3
    discuter(tmp_path, monkeypatch, ["Bonjour", "/quitter"])
    assert appels[1]["temperature"] == 0.7  # le défaut


def test_une_ligne_vide_n_appelle_pas_le_modele(tmp_path, monkeypatch, appels):
    code, _ = discuter(tmp_path, monkeypatch, ["", "   ", "/quitter"])
    assert code == 0 and appels == []


def test_la_fin_de_la_saisie_quitte_proprement(tmp_path, monkeypatch, appels):
    code, _ = discuter(tmp_path, monkeypatch, ["Bonjour"])  # puis EOFError
    assert code == 0 and len(appels) == 1


def test_la_fenetre_pleine_dit_de_faire_nouveau(tmp_path, monkeypatch, capsys, appels):
    long = "mot " * 100  # plus que les 96 jetons de contexte du petit modèle
    code, _ = discuter(tmp_path, monkeypatch, [long, "Bonjour", "/quitter"])
    assert code == 0
    sortie = capsys.readouterr().out
    assert "/nouveau" in sortie and "fenêtre" in sortie
    # Le message trop long n'est pas gardé : la conversation continue avec le suivant.
    assert [[t.role for t in a["tours"]] for a in appels] == [["utilisateur"]]


def test_une_conversation_qui_remplit_peu_a_peu_la_fenetre(tmp_path, monkeypatch, capsys, appels):
    # Chaque tour ajoute une vingtaine de jetons : au bout de quelques-uns, il ne reste plus de place.
    code, _ = discuter(tmp_path, monkeypatch, ["Une phrase un peu longue pour remplir."] * 6 + ["/quitter"])
    assert code == 0
    assert "/nouveau" in capsys.readouterr().out
    assert len(appels) < 6 and all(a["n"] >= 1 for a in appels)


def test_une_reponse_vide_n_entre_pas_dans_l_historique(tmp_path, monkeypatch, capsys):
    reponses = iter([Reponse("", None, [], False), Reponse("Bonjour.", None, [], True)])
    notes = []

    def faux(modele, tok, conversations, **options):
        notes.append(list(conversations[0]))
        return [next(reponses)]

    monkeypatch.setattr(module_reponses, "repondre_lot", faux)
    discuter(tmp_path, monkeypatch, ["Salut", "Re-salut", "/quitter"])
    assert [len(t) for t in notes] == [1, 1]  # la question sans réponse est retirée : la suite est valide


def test_une_reponse_coupee_est_signalee(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        module_reponses, "repondre_lot", lambda *a, **k: [Reponse("Il était une", None, [], False)]
    )
    discuter(tmp_path, monkeypatch, ["Raconte", "/quitter"])
    sortie = capsys.readouterr().out
    assert "coupée" in sortie and "n'est pas gardée" in sortie


def test_une_reponse_coupee_n_entre_pas_dans_l_historique(tmp_path, monkeypatch):
    reponses = iter([Reponse("Il était une", None, [], False), Reponse("Bonjour.", None, [], True)])
    notes = []

    def faux(modele, tok, conversations, **options):
        notes.append(list(conversations[0]))
        return [next(reponses)]

    monkeypatch.setattr(module_reponses, "repondre_lot", faux)
    discuter(tmp_path, monkeypatch, ["Raconte", "Salut", "/quitter"])
    assert [len(t) for t in notes] == [1, 1]  # ni la réponse coupée ni sa question ne restent


def test_la_pensee_s_affiche_a_part(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        module_reponses, "repondre_lot", lambda *a, **k: [Reponse("La réponse est 4.", "2 + 2 = 4", [], True)]
    )
    discuter(tmp_path, monkeypatch, ["2 + 2 ?", "/quitter"])
    sortie = capsys.readouterr().out
    assert "2 + 2 = 4" in sortie and "La réponse est 4." in sortie


def test_avec_un_vrai_modele(tmp_path, monkeypatch, capsys):
    code, saisie = discuter(tmp_path, monkeypatch, ["Bonjour", "Comment vas-tu ?", "/nouveau", "Salut", "/quitter"])
    assert code == 0 and len(saisie.invites) == 5
    assert "ton-ia-9.9" in capsys.readouterr().out


def test_un_dossier_absent_donne_un_message_et_le_code_1(tmp_path, capsys):
    code = main(["discuter", "--modele", str(tmp_path / "nulle-part")])
    assert code == 1
    erreur = capsys.readouterr().err
    assert erreur.startswith("Erreur") and "nulle-part" in erreur


def test_une_temperature_negative_est_refusee(tmp_path, capsys):
    code = main(["discuter", "--modele", str(publier(tmp_path)), "--temperature", "-1"])
    assert code == 1 and "température" in capsys.readouterr().err


def test_le_contexte_du_petit_modele():
    assert CONFIG.longueur_contexte == 96  # les tests de fenêtre pleine en dépendent
