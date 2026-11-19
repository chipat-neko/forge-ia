"""`python -m raisonnement_pas_a_pas` : les huit commandes, leur sortie et leurs codes de retour."""

import json

import pytest

from raisonnement_pas_a_pas.__main__ import lire_un_groupe, main
from test_resumer import un_controle_ecrit_par_forge, un_journal, un_rapport


def lancer(capsys, *arguments: str) -> tuple[int, str, str]:
    code = main(list(arguments))
    sortie = capsys.readouterr()
    return code, sortie.out.replace("\u202f", " "), sortie.err.replace("\u202f", " ")


def test_lire_un_groupe():
    assert lire_un_groupe("1,0,0,1") == [1.0, 0.0, 0.0, 1.0]
    assert lire_un_groupe("0.5") == [0.5]
    with pytest.raises(ValueError, match="doit être des nombres séparés par des virgules"):
        lire_un_groupe("1;0")


def test_probleme_montre_la_trace_et_ecrit_le_json(capsys, tmp_path):
    chemin = tmp_path / "probleme.json"
    code, sortie, _ = lancer(capsys, "probleme", "achats", "2", "7", "--json", str(chemin))
    assert code == 0 and "Problème achats-2-7 :" in sortie and "Trace, une étape de calcul par ligne :" in sortie
    assert "La conversation de ton IA fait" in sortie
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    assert donnees["id"] == "achats-2-7" and len(donnees["conversation"]["ids"]) == len(donnees["conversation"]["appris"])
    assert chemin.read_bytes().endswith(b"}\n") and b"\r" not in chemin.read_bytes()


def test_probleme_refuse_un_couple_qui_n_existe_pas(capsys):
    code, _, erreur = lancer(capsys, "probleme", "partage", "3", "0")
    assert code == 2 and "La difficulté 3 n'existe pas pour la famille « partage »" in erreur


def test_verifier_dit_le_nombre_lu_et_le_verdict(capsys):
    code, sortie, _ = lancer(capsys, "verifier", "12 fois 7 font 84.", "--attendu", "84")
    assert code == 0 and "Nombre lu (le dernier du texte) : 84. Réponse terminée. Juste : oui." in sortie
    code, sortie, _ = lancer(capsys, "verifier", "12 fois 7 font 84", "--attendu", "84", "--coupee")
    assert code == 1 and "Réponse coupée. Juste : non." in sortie
    code, sortie, _ = lancer(capsys, "verifier", "rien", "--attendu", "4")
    assert code == 1 and "aucun nombre" in sortie


def test_avantages_compare_a_forge(capsys):
    code, sortie, _ = lancer(capsys, "avantages", "1,0,0,1", "0,0,0,0")
    assert code == 0
    assert "avantages [0.5, -0.5, -0.5, 0.5]" in sortie and "avantages [0.0, 0.0, 0.0, 0.0] (sans signal)" in sortie
    assert "À la main et dans forge, à 10⁻¹² près : oui" in sortie


def test_avantages_de_tailles_differentes_saute_la_comparaison(capsys):
    code, sortie, _ = lancer(capsys, "avantages", "1,0", "1,0,0")
    assert code == 0 and "tailles différentes" in sortie and "À la main et dans forge" not in sortie


def test_avantages_refuse_un_groupe_illisible(capsys):
    code, _, erreur = lancer(capsys, "avantages", "1,a")
    assert code == 2 and "doit être des nombres séparés par des virgules" in erreur


def test_signal(capsys):
    code, sortie, _ = lancer(capsys, "signal", "--p", "0.5", "--n", "2")
    assert code == 0 and "Avec une chance 0,500 d'être juste, un groupe de 2 réponses est sans signal avec la chance 0,500000 (50,00 %)." in sortie
    code, _, erreur = lancer(capsys, "signal", "--p", "1.5", "--n", "2")
    assert code == 2 and "entre 0 et 1" in erreur


def test_essai_ecrit_les_mesures(capsys, tmp_path):
    chemin = tmp_path / "essai.json"
    code, sortie, _ = lancer(capsys, "essai", "--pas", "2", "--json", str(chemin))
    assert code == 0 and "Petit GRPO sur cpu, 2 pas" in sortie and "Réussite en glouton sur les dix chiffres" in sortie
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    assert donnees["pas"] == 2 and len(donnees["recompense_moyenne"]) == 2
    code, _, erreur = lancer(capsys, "essai", "--appareil", "tpu", "--pas", "1")
    assert code == 2 and erreur  # un appareil inconnu est refusé sans trace Python


def test_resumer_ecrit_le_releve(capsys, tmp_path):
    rapport = tmp_path / "rapport.json"
    rapport.write_text(json.dumps(un_rapport()), encoding="utf-8")
    sortie_json = tmp_path / "mesures" / "etape-ton-ia-1.9.json"
    code, sortie, _ = lancer(capsys, "resumer", "--rapport", str(rapport), "--json", str(sortie_json))
    assert code == 0 and "Rapport d’étape de ton-ia-1.9 (étape 1.9), relevé le 2026-12-03" in sortie
    assert "mgsm_fr : absente, les problèmes traduits ne sont pas téléchargés" in sortie
    assert json.loads(sortie_json.read_text(encoding="utf-8"))["version"] == "ton-ia-1.9"
    assert sortie_json.read_bytes().endswith(b"}\n") and b"\r" not in sortie_json.read_bytes()
    code, _, erreur = lancer(capsys, "resumer", "--rapport", str(tmp_path / "absent.json"))
    assert code == 2 and "n'existe pas" in erreur


def test_controle_dit_si_le_rl_se_lance(capsys, tmp_path, monkeypatch):
    refuse, lance = tmp_path / "refuse", tmp_path / "lance"
    refuse.mkdir()
    lance.mkdir()
    un_controle_ecrit_par_forge(refuse, False, monkeypatch)
    sortie_json = tmp_path / "mesures" / "controle-1.9.json"
    code, sortie, _ = lancer(capsys, "controle", "--sortie", str(refuse), "--json", str(sortie_json))
    assert code == 0 and "Contrôle de départ : 0 réponses justes sur 6 (0,0 %), 3 problèmes." in sortie
    assert "Aucune réponse juste" in sortie and "code de sortie 6" in sortie
    assert json.loads(sortie_json.read_text(encoding="utf-8"))["lance"] is False
    un_controle_ecrit_par_forge(lance, True, monkeypatch)
    code, sortie, _ = lancer(capsys, "controle", "--sortie", str(lance))
    assert code == 0 and "Le RL a un signal : il peut se lancer." in sortie
    code, _, erreur = lancer(capsys, "controle", "--sortie", str(tmp_path / "vide"))
    assert code == 2 and "controle.json" in erreur and "forge entrainer" in erreur


def test_courbes_ecrit_les_series_ou_dit_que_le_rl_n_a_pas_ete_lance(capsys, tmp_path):
    sortie_json = tmp_path / "entrainement-grpo-1.9.json"
    code, sortie, _ = lancer(capsys, "courbes", "--journal", str(un_journal(tmp_path)), "--json", str(sortie_json))
    assert code == 0 and "recompense_moyenne (50 points)" in sortie and "reussite_val (5 points)" in sortie
    assert list(json.loads(sortie_json.read_text(encoding="utf-8"))) == ["recompense_moyenne", "groupes_sans_signal", "reussite_val"]
    non_lance = tmp_path / "non-lance"
    non_lance.mkdir()
    code, sortie, _ = lancer(capsys, "courbes", "--journal", str(un_journal(non_lance, avec_pas=False)), "--json", str(non_lance / "c.json"))
    assert code == 0 and "le RL n'a pas été lancé" in sortie
    assert json.loads((non_lance / "c.json").read_text(encoding="utf-8")) == {"lance": False}
    code, _, erreur = lancer(capsys, "courbes", "--journal", str(tmp_path / "absent.jsonl"))
    assert code == 2 and "n'existe pas ou est vide" in erreur
