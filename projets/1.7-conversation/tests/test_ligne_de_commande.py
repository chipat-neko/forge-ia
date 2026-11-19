"""La ligne de commande `python -m conversation_pas_a_pas` : ses sorties, ses fichiers, ses codes de sortie."""

import json

import pytest
import torch

from conversation_pas_a_pas import __main__ as cli
from test_resumer import un_essai, un_jeu, un_rapport


def lancer(capsys, *arguments) -> tuple[int, str, str]:
    code = cli.main(list(arguments))
    sortie = capsys.readouterr()
    return code, sortie.out, sortie.err


def test_montrer_ecrit_la_conversation_jeton_par_jeton(capsys):
    code, sortie, _ = lancer(capsys, "montrer", "Quelle est la capitale de la France ?", "--reponse", "Paris.")
    assert code == 0
    lignes = sortie.splitlines()
    assert lignes[0].split() == ["id", "jeton", "rôle", "appris"]
    assert "'<|fin_texte|>'" in lignes[1] and "debut" in lignes[1]
    assert any("'<|assistant|>'" in ligne and "*" not in ligne for ligne in lignes)
    assert any("'<|fin_tour|>'" in ligne and ligne.rstrip().endswith("*") for ligne in lignes)
    assert "dont" in lignes[-1] and "appris" in lignes[-1]


def test_montrer_avec_un_systeme(capsys):
    code, sortie, _ = lancer(capsys, "montrer", "Bonjour", "--systeme", "Réponds en une phrase.", "--reponse", "Bonjour.")
    assert code == 0 and "'<|systeme|>'" in sortie


def test_montrer_refuse_une_reponse_vide_sans_trace(capsys):
    code, sortie, erreur = lancer(capsys, "montrer", "Bonjour", "--reponse", "")
    assert code == 2 and sortie == "" and "vide" in erreur and "Traceback" not in erreur


def test_fuite_ecrit_la_sortie_et_les_mesures(capsys, tmp_path):
    texte, mesures = tmp_path / "sorties" / "fuite.txt", tmp_path / "mesures" / "fuite.json"
    code, sortie, _ = lancer(capsys, "fuite", "--enregistrer", str(texte), "--json", str(mesures))
    assert code == 0
    assert "avec le masque par document\u202f: " in sortie and "sans le masque\u202f: " in sortie
    assert "B voit A sans le masque\u202f: oui" in sortie
    enregistre = texte.read_text(encoding="utf-8")
    assert enregistre.startswith("# relevé le 20") and enregistre.splitlines()[1:] == sortie.splitlines()
    assert "\r" not in enregistre
    releve = json.loads(mesures.read_text(encoding="utf-8"))
    assert releve["avec_masque"] <= 1e-5 < 1e-3 < releve["sans_masque"] and len(releve["releve_le"]) == 10


def test_essai_ecrit_la_sortie_et_les_mesures(capsys, tmp_path, monkeypatch):
    # L'essai complet dure quelques minutes (voir test_petit_affinage) : ici, un résultat fabriqué.
    resultat = {
        "appareil": "cpu", "pas": 80, "pertes": [6.2, 5.0, 1.5], "fin_de_tour_avant": 0.0, "fin_de_tour_apres": 0.875,
        "reponses_avant": [], "reponses_apres": [{"invite": "Dis au revoir.", "texte": "Au revoir.", "terminee": True}] * 3,
        "exemples": 24, "rangees": 9, "jetons": 900, "jetons_appris": 400, "parametres": 4_300_000, "secondes": 61.5,
    }
    monkeypatch.setattr(cli, "essai_affinage", lambda appareil, pas=80: {**resultat, "appareil": appareil, "pas": pas})
    texte, mesures = tmp_path / "essai.txt", tmp_path / "essai.json"
    code, sortie, _ = lancer(capsys, "essai", "--appareil", "cpu", "--enregistrer", str(texte), "--json", str(mesures))
    assert code == 0
    assert "Un tout petit affinage, sur le processeur" in sortie
    assert "0\u202f% avant, 88\u202f% après" in sortie and "le modèle a appris à finir son tour\u202f: oui" in sortie
    # Le taux de l'affinage, et pourquoi il n'est pas celui du pré-entraînement.
    assert "taux d’affinage\u202f: 0,003, 3 fois celui du pré-entraînement (0,001)\u202f; au taux du pré-entraînement, 80 pas ne lui apprenaient pas" in sortie
    assert texte.read_text(encoding="utf-8").startswith("# relevé le 20")
    assert json.loads(mesures.read_text(encoding="utf-8"))["fin_de_tour_apres"] == 0.875


def test_essai_rend_1_si_le_modele_n_a_pas_appris(capsys, monkeypatch):
    rien = {
        "appareil": "cpu", "pas": 2, "pertes": [6.0, 6.0], "fin_de_tour_avant": 0.0, "fin_de_tour_apres": 0.0, "reponses_avant": [],
        "reponses_apres": [], "exemples": 24, "rangees": 9, "jetons": 900, "jetons_appris": 400, "parametres": 1, "secondes": 1.0,
    }
    monkeypatch.setattr(cli, "essai_affinage", lambda appareil, pas=80: rien)
    code, sortie, _ = lancer(capsys, "essai", "--appareil", "cpu", "--pas", "2")
    assert code == 1 and "le modèle a appris à finir son tour\u202f: non" in sortie


@pytest.mark.skipif(torch.cuda.is_available(), reason="cette carte voit CUDA : le refus ne se produit pas")
def test_sans_carte_cuda_dit_quoi_faire_sans_trace(capsys):
    code, sortie, erreur = lancer(capsys, "essai", "--appareil", "cuda")
    assert code == 2 and sortie == "" and "ne la voit pas" in erreur and "Traceback" not in erreur


def test_un_appareil_inconnu_est_refuse(capsys):
    code, _, erreur = lancer(capsys, "essai", "--appareil", "tpu")
    assert code == 2 and "Appareil inconnu" in erreur


def test_resumer_ecrit_le_releve(capsys, tmp_path):
    rapport = tmp_path / "rapport.json"
    rapport.write_text(json.dumps(un_rapport()), encoding="utf-8")
    sortie_json = tmp_path / "mesures" / "etape-ton-ia-1.7.json"
    code, sortie, _ = lancer(capsys, "resumer", "--rapport", str(rapport), "--json", str(sortie_json))
    assert code == 0 and "Rapport d’étape de ton-ia-1.7 (étape 1.7), relevé le 2026-11-20" in sortie
    assert "4 mesures dont 0 absente, 2 échantillons" in sortie
    releve = json.loads(sortie_json.read_text(encoding="utf-8"))
    assert releve["version"] == "ton-ia-1.7" and releve["etape"] == "1.7"
    code, sortie, _ = lancer(capsys, "resumer", "--rapport", str(rapport), "--reference")
    assert code == 0 and "ton-ia-1.5 (étape 1.7)" in sortie


def test_resumer_dit_les_mesures_absentes(capsys, tmp_path):
    rapport = un_rapport()
    rapport["mesures"]["oubli"] = {"absente": "les jetons de pré-entraînement manquent"}
    chemin = tmp_path / "rapport.json"
    chemin.write_text(json.dumps(rapport), encoding="utf-8")
    code, sortie, _ = lancer(capsys, "resumer", "--rapport", str(chemin))
    assert code == 0 and "4 mesures dont 1 absente" in sortie and "oubli\u202f: absente, les jetons de pré-entraînement manquent" in sortie


def test_resumer_sans_rapport_dit_quoi_refaire(capsys, tmp_path):
    code, sortie, erreur = lancer(capsys, "resumer", "--rapport", str(tmp_path / "absent.json"))
    assert code == 2 and sortie == "" and "evaluer-etape" in erreur and "Traceback" not in erreur


def test_longueurs_ecrit_l_histogramme(capsys, tmp_path):
    jeu = un_jeu(tmp_path / "sft-essai", [10, 20, 20, 30])
    sortie_json = tmp_path / "longueurs.json"
    code, sortie, _ = lancer(capsys, "longueurs", "--jeu", str(jeu), "--json", str(sortie_json))
    assert code == 0 and "Jeu sft-essai\u202f: 4 exemples" in sortie and "de 10 à 30 jetons" in sortie
    assert json.loads(sortie_json.read_text(encoding="utf-8"))["histogramme"] == [[10, 1], [20, 2], [30, 1]]


def test_longueurs_d_un_jeu_absent_dit_quoi_faire(capsys, tmp_path):
    code, sortie, erreur = lancer(capsys, "longueurs", "--jeu", str(tmp_path / "absent"))
    assert code == 2 and sortie == "" and "forge preparer" in erreur and "Traceback" not in erreur


def test_une_commande_inconnue_est_refusee_par_argparse(capsys):
    with pytest.raises(SystemExit) as sortie:
        cli.main(["dessiner"])
    assert sortie.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


def test_resumer_d_un_rapport_archive_prend_le_nom_donne(capsys, tmp_path):
    rapport = tmp_path / "rapport.json"
    rapport.write_text(json.dumps(un_rapport()), encoding="utf-8")
    sortie_json = tmp_path / "etape-ton-ia-1.7-3e-4.json"
    code, sortie, _ = lancer(capsys, "resumer", "--rapport", str(rapport), "--nom", "ton-ia-1.7-3e-4", "--json", str(sortie_json))
    assert code == 0 and "Rapport d’étape de ton-ia-1.7-3e-4 (étape 1.7, nommée ton-ia-1.7 dans le rapport)" in sortie
    releve = json.loads(sortie_json.read_text(encoding="utf-8"))
    assert (releve["version"], releve["nom_au_rapport"]) == ("ton-ia-1.7-3e-4", "ton-ia-1.7")


def test_balayage_ecrit_le_releve(capsys, tmp_path):
    dossiers = [
        un_essai(tmp_path / "sft-1.7-balayage-1e-4", 1e-4, {100: 1.422, 200: 1.317, 300: 1.279}),
        un_essai(tmp_path / "sft-1.7-balayage-3e-4", 3e-4, {100: 1.418, 200: 1.283, 300: 1.214}),
    ]
    sortie_json = tmp_path / "balayage-sft-1.7.json"
    code, sortie, _ = lancer(capsys, "balayage", *map(str, dossiers), "--json", str(sortie_json))
    assert code == 0 and "Balayage du taux d’apprentissage, 2 essais" in sortie
    assert "taux 0,0003 : validation 1,418 au pas 100, 1,283 au pas 200, 1,214 au pas 300" in sortie.replace("\u202f", " ")
    assert [e["taux_max"] for e in json.loads(sortie_json.read_text(encoding="utf-8"))["essais"]] == [1e-4, 3e-4]


def test_balayage_sans_journal_dit_quoi_faire(capsys, tmp_path):
    (tmp_path / "vide").mkdir()
    code, sortie, erreur = lancer(capsys, "balayage", str(tmp_path / "vide"))
    assert code == 2 and sortie == "" and "journal.jsonl" in erreur and "Traceback" not in erreur
