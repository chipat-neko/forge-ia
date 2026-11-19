"""`python -m alignement_pas_a_pas` : les sept commandes, leur sortie et leurs codes de retour."""

import json

import pytest

from alignement_pas_a_pas.__main__ import lire_une_consigne, main
from test_courbes import un_journal
from test_resumer import un_essai, un_jeu_de_paires, un_rapport


def lancer(capsys, *arguments: str) -> tuple[int, str, str]:
    code = main(list(arguments))
    sortie = capsys.readouterr()
    return code, sortie.out.replace("\u202f", " "), sortie.err.replace("\u202f", " ")


def test_lire_une_consigne():
    assert lire_une_consigne("minuscules") == ("minuscules", {})
    assert lire_une_consigne("mots_max:n=20") == ("mots_max", {"n": 20})
    assert lire_une_consigne("fin_imposee:phrase=Merci.") == ("fin_imposee", {"phrase": "Merci."})
    with pytest.raises(ValueError, match="doit s'écrire"):
        lire_une_consigne("mots_max:20")


def test_noter_ecrit_chaque_critere(capsys):
    code, sortie, _ = lancer(capsys, "noter", "paris est la capitale.", "--consigne", "minuscules", "--consigne", "mots_max:n=20")
    assert code == 0
    assert "Note : terminee 1, juste 1, consignes 2, francais 1, longueur 1" in sortie
    assert "consignes" in sortie and "2 consignes sur 2" in sortie and "respectée : Écris toute ta réponse en minuscules." in sortie


def test_noter_une_reponse_coupee_a_un_probleme(capsys):
    code, sortie, _ = lancer(capsys, "noter", "12 fois 7 font 84.", "--coupee", "--attendu", "84")
    assert code == 0 and "terminee 0, juste 0" in sortie and "coupée" in sortie


def test_noter_refuse_une_consigne_inconnue(capsys):
    code, _, erreur = lancer(capsys, "noter", "Bonjour.", "--consigne", "inconnue")
    assert code == 2 and "« inconnue » de l'invite ligne-de-commande est inconnue" in erreur


def test_dpo_compare_a_forge(capsys):
    code, sortie, _ = lancer(capsys, "dpo", "--pc", "-12", "--pr", "-20", "--qc", "-14", "--qr", "-18", "--beta", "0.1")
    assert code == 0
    assert "Gain de la choisie : 2,000   gain de la rejetée : -2,000" in sortie
    assert "À la main et dans forge, à 10⁻¹² près : oui" in sortie


def test_dpo_refuse_un_beta_nul(capsys):
    code, _, erreur = lancer(capsys, "dpo", "--pc", "-1", "--pr", "-2", "--qc", "-1", "--qr", "-2", "--beta", "0")
    assert code == 2 and "beta vaut" in erreur


def test_pousser_ecrit_les_releves(capsys, tmp_path):
    chemin = tmp_path / "pousser.json"
    code, sortie, _ = lancer(capsys, "pousser", "--pas", "4", "--json", str(chemin))
    assert code == 0 and "Une paire fabriquée, 4 pas de DPO" in sortie and "Par jeton, la choisie passe de" in sortie
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    assert donnees["reelle"] is False and len(donnees["releves"]) == 5


def test_resumer_ecrit_le_releve(capsys, tmp_path):
    rapport = tmp_path / "rapport.json"
    rapport.write_text(json.dumps(un_rapport()), encoding="utf-8")
    sortie_json = tmp_path / "mesures" / "etape-ton-ia-1.8.json"
    code, sortie, _ = lancer(capsys, "resumer", "--rapport", str(rapport), "--json", str(sortie_json))
    assert code == 0 and "Rapport d’étape de ton-ia-1.8 (étape 1.8), relevé le 2026-11-25" in sortie
    assert json.loads(sortie_json.read_text(encoding="utf-8"))["version"] == "ton-ia-1.8"
    assert sortie_json.read_bytes().endswith(b"}\n") and b"\r" not in sortie_json.read_bytes()
    code, _, erreur = lancer(capsys, "resumer", "--rapport", str(tmp_path / "absent.json"))
    assert code == 2 and "n'existe pas" in erreur


def test_paires_ecrit_les_paires(capsys, tmp_path):
    jeu = un_jeu_de_paires(tmp_path / "preferences-1.8")
    sortie_json = tmp_path / "paires-exemples.json"
    code, sortie, _ = lancer(capsys, "paires", "--jeu", str(jeu), "--n", "2", "--json", str(sortie_json))
    assert code == 0 and "2 paires du jeu preferences-1.8" in sortie
    assert [p["id"] for p in json.loads(sortie_json.read_text(encoding="utf-8"))] == ["a", "probleme:7"]
    code, _, erreur = lancer(capsys, "paires", "--jeu", str(tmp_path / "absent"))
    assert code == 2 and "absent ou pas fini" in erreur


def test_balayage_ecrit_les_essais(capsys, tmp_path):
    a = un_essai(tmp_path / "a", 1e-6, 0.05, -1.0, -1.2)
    b = un_essai(tmp_path / "b", 5e-6, 0.3, -1.0, -0.8)
    sortie_json = tmp_path / "balayage-1.8.json"
    code, sortie, _ = lancer(capsys, "balayage", str(a), str(b), "--json", str(sortie_json))
    assert code == 0 and "a : taux 1e-06, β 0,05, victoire 60,0 %" in sortie
    assert [e["essai"] for e in json.loads(sortie_json.read_text(encoding="utf-8"))] == ["a", "b"]
    code, _, erreur = lancer(capsys, "balayage", str(tmp_path / "vide"))
    assert code == 2 and "rapport.json" in erreur


def test_courbes_ecrit_les_series(capsys, tmp_path):
    journal = un_journal(tmp_path)
    sortie_json = tmp_path / "entrainement-dpo-1.8.json"
    code, sortie, _ = lancer(capsys, "courbes", "--journal", str(journal), "--json", str(sortie_json))
    assert code == 0 and "logps_choisie (50 points)" in sortie
    assert list(json.loads(sortie_json.read_text(encoding="utf-8"))) == ["logps_choisie", "logps_rejetee", "exactitude"]
    code, _, erreur = lancer(capsys, "courbes", "--journal", str(tmp_path / "absent.jsonl"))
    assert code == 2 and "n'existe pas ou est vide" in erreur
