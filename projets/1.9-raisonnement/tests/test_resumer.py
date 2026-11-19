"""Les relevés que le projet tire des mesures du plan 7 : un rapport d'étape, le contrôle de départ, les courbes.

Le rapport d'étape est fabriqué au format de `forge.evaluation.etape.evaluer_etape` (`version_du_rapport` 1) : ton-ia-1.9
n'existe pas encore quand ces tests s'écrivent. Le contrôle de départ est écrit par `forge.raisonnement.grpo` lui-même
(`controle_de_depart` puis `ecrire_controle`), un « refusé » (un modèle tiré au hasard ne réussit aucun problème) et un
« lancé » (la récompense est remplacée par la parité du premier jeton, comme dans les tests de forge). Le journal est
fabriqué avec les clés que `pas_grpo` écrit.
"""

import json
import math

import pytest
import torch
from forge.entrainement.boucle import ReglagesGRPO
from forge.evaluation.etape import MESURES_PAR_ETAPE, VERSION_DU_RAPPORT_D_ETAPE
from forge.modele import ConfigModele, Transformer
from forge.raisonnement import grpo
from forge.raisonnement.problemes import generer_problemes
from forge.tokenizer import TokenizerOctets
from pre_entrainement.journal import lire, serie

from raisonnement_pas_a_pas.problemes import TOKENIZER
from raisonnement_pas_a_pas.resumer import CLES_DES_COURBES, controle, courbes_grpo, resumer_etape

TOK = TokenizerOctets.charger(TOKENIZER)
ECHANTILLONS_19 = [
    {"invite": "Léa a 12 pommes. Elle en donne 5. Combien de pommes Léa a-t-elle maintenant ?", "texte": "La réponse est 7.", "pensee": "12 − 5 = 7", "terminee": True},
    {"invite": "Dis bonjour.", "texte": "Bonjour", "pensee": None, "terminee": False},
]


def mesures(echantillons: list[dict]) -> dict:
    """Les mesures de l'étape 1.9, avec les clés de `forge evaluer-etape` (voir MESURES_PAR_ETAPE)."""
    return {
        "ifeval_fr": {"invite_stricte": 0.12, "consigne_stricte": 0.2, "n": 541},
        "tenue": {"terminee": 0.9, "fr": 0.95, "autre": 0.03, "indetermine": 0.02, "mots_moyens": 41.5, "n": 641},
        "oubli": {"perte": 2.6, "bits_par_octet": 0.9, "n": 64},
        "problemes": {"exactitude": 0.31, "n": 300, "par_famille": {"addition": {"exactitude": 0.5, "n": 50}}},
        "mgsm_fr": {"absente": "les problèmes traduits ne sont pas téléchargés"},
        "gsm8k_platinum_fr": {"absente": "les problèmes traduits ne sont pas téléchargés"},
        "echantillons": echantillons,
    }


def un_rapport() -> dict:
    return {
        "version_du_rapport": VERSION_DU_RAPPORT_D_ETAPE,
        "version": "ton-ia-1.9",
        "empreinte": "a" * 64,
        "mesures": mesures(ECHANTILLONS_19),
        "secondes": 812.4,
        "etape": "1.9",
        "date": "2026-12-03T09:15:31+01:00",
        "appareil": "cuda",
        "n_max": None,
        "reference": {"version": "ton-ia-1.5", "empreinte": "b" * 64, "mesures": mesures([]), "secondes": 790.0},
    }


def ecrire(tmp_path, rapport: dict, nom: str = "rapport.json"):
    chemin = tmp_path / nom
    chemin.write_text(json.dumps(rapport), encoding="utf-8")
    return chemin


# --- Le rapport d'étape ---


def test_resumer_etape(tmp_path):
    releve = resumer_etape(ecrire(tmp_path, un_rapport()))
    assert list(releve) == ["version", "etape", "releve_le", "mesures", "echantillons"]
    assert (releve["version"], releve["etape"], releve["releve_le"]) == ("ton-ia-1.9", "1.9", "2026-12-03")
    # Les mesures de l'étape 1.9 de forge, sans les échantillons, rangés à part.
    assert list(releve["mesures"]) == [m for m in MESURES_PAR_ETAPE["1.9"] if m != "echantillons"]
    assert releve["echantillons"] == ECHANTILLONS_19


def test_resumer_etape_ne_recalcule_rien_et_garde_une_mesure_absente(tmp_path):
    rapport = un_rapport()
    releve = resumer_etape(ecrire(tmp_path, rapport))
    assert releve["mesures"] == {nom: m for nom, m in rapport["mesures"].items() if nom != "echantillons"}
    assert releve["mesures"]["mgsm_fr"] == {"absente": "les problèmes traduits ne sont pas téléchargés"}
    assert releve["mesures"]["problemes"]["exactitude"] == 0.31


def test_la_reference_est_resumee_a_son_tour(tmp_path):
    releve = resumer_etape(ecrire(tmp_path, un_rapport()), reference=True)
    assert (releve["version"], releve["etape"], releve["releve_le"]) == ("ton-ia-1.5", "1.9", "2026-12-03")
    assert releve["echantillons"] == []


@pytest.mark.parametrize(
    ("changement", "message"),
    [
        (lambda r: r.update(version_du_rapport=2), "version 1"),
        (lambda r: r.pop("etape"), "pas de « etape »"),
        (lambda r: r["mesures"].pop("echantillons"), "pas d'« echantillons »"),
        (lambda r: r.update(date="hier"), "pas une date ISO"),
    ],
)
def test_un_rapport_abime_dit_quoi_refaire(tmp_path, changement, message):
    rapport = un_rapport()
    changement(rapport)
    with pytest.raises(ValueError, match=message) as erreur:
        resumer_etape(ecrire(tmp_path, rapport))
    assert "evaluer-etape" in str(erreur.value) or message == "pas de « etape »"


def test_sans_reference_le_rapport_le_dit(tmp_path):
    rapport = un_rapport()
    del rapport["reference"]
    with pytest.raises(ValueError, match="n'a pas de version de référence"):
        resumer_etape(ecrire(tmp_path, rapport), reference=True)


def test_un_rapport_qui_manque_ou_qui_n_est_pas_du_json(tmp_path):
    with pytest.raises(FileNotFoundError, match="n'existe pas"):
        resumer_etape(tmp_path / "absent.json")
    (tmp_path / "abime.json").write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="pas un fichier JSON lisible"):
        resumer_etape(tmp_path / "abime.json")


# --- Le contrôle de départ ---

REGLAGES = ReglagesGRPO(pas=2, invites_par_pas=2, reponses_par_invite=4, jetons_max_reponse=3, lot_de_generation=8, controle_invites=3, controle_reponses=2)


def un_controle_ecrit_par_forge(dossier, lance: bool, monkeypatch):
    """Le `controle.json` que forge écrit : celui d'un modèle tiré au hasard (refusé), ou, la récompense remplacée par la parité
    du premier jeton, d'un modèle qui a un signal (lancé)."""
    if lance:
        monkeypatch.setattr(grpo, "recompense", lambda reponse, probleme: float(bool(reponse.ids) and reponse.ids[0] % 2 == 0))
    problemes = generer_problemes(3, 2_000_000, difficultes=(1, 2))
    # Les énoncés de forge font une quarantaine de jetons : un contexte de 128, pas celui du petit GRPO.
    torch.manual_seed(0)
    modele = Transformer(ConfigModele(dim=16, couches=1, tetes=2, longueur_contexte=128))
    resultat = {**grpo.controle_de_depart(modele, TOK, problemes, REGLAGES, 7, "ton-ia-1.7"), "depart": "ton-ia-1.7"}
    grpo.ecrire_controle(dossier / grpo.NOM_DU_CONTROLE, resultat)
    return resultat


def test_un_controle_refuse(tmp_path, monkeypatch):
    ecrit = un_controle_ecrit_par_forge(tmp_path, False, monkeypatch)
    releve = controle(tmp_path)
    assert releve["lance"] is False and releve["justes"] == 0 and releve["taux"] == 0.0
    assert (releve["invites"], releve["reponses"]) == (3, 6)
    assert releve == ecrit  # rien n'est recalculé ni retiré
    assert list(releve) == ["depart", "invites", "reponses", "justes", "taux", "lance", "secondes"]


def test_un_controle_lance(tmp_path, monkeypatch):
    ecrit = un_controle_ecrit_par_forge(tmp_path, True, monkeypatch)
    releve = controle(tmp_path)
    assert releve["lance"] is True and 0 < releve["justes"] <= releve["reponses"] == 6
    assert releve["taux"] == releve["justes"] / 6 and releve["depart"] == "ton-ia-1.7"
    assert releve == ecrit


def test_un_controle_a_la_main_sans_depart_ni_secondes(tmp_path):
    (tmp_path / "controle.json").write_text(json.dumps({"invites": 200, "reponses": 1600, "justes": 12, "taux": 0.0075, "lance": True}), encoding="utf-8")
    assert controle(tmp_path) == {"invites": 200, "reponses": 1600, "justes": 12, "taux": 0.0075, "lance": True}


def test_le_controle_s_ecrit_en_json(tmp_path, monkeypatch):
    un_controle_ecrit_par_forge(tmp_path, False, monkeypatch)
    releve = controle(tmp_path)
    assert json.loads(json.dumps(releve, ensure_ascii=False, allow_nan=False)) == releve


@pytest.mark.parametrize(
    ("changement", "message"),
    [
        (lambda c: c.pop("justes"), "pas de « justes »"),
        (lambda c: c.update(justes=-1), "« justes » vaut -1"),
        (lambda c: c.update(reponses=2.5), "« reponses » vaut 2.5"),
        (lambda c: c.update(justes=9), "9 réponses justes sur 6"),
        (lambda c: c.update(lance=True), "« lance » vaut True pour 0 réponses justes"),
        (lambda c: c.update(taux=0.5), "« taux » vaut 0.5"),
    ],
)
def test_un_controle_abime_dit_quoi_refaire(tmp_path, monkeypatch, changement, message):
    ecrit = un_controle_ecrit_par_forge(tmp_path, False, monkeypatch)
    changement(ecrit)
    (tmp_path / "controle.json").write_text(json.dumps(ecrit), encoding="utf-8")
    with pytest.raises(ValueError, match=message) as erreur:
        controle(tmp_path)
    assert "forge entrainer" in str(erreur.value)


def test_un_controle_absent_ou_illisible_dit_quoi_lancer(tmp_path):
    with pytest.raises(FileNotFoundError, match="controle.json n'existe pas.*forge entrainer"):
        controle(tmp_path)
    (tmp_path / "controle.json").write_text("[1]", encoding="utf-8")
    with pytest.raises(ValueError, match="n'est pas un objet JSON"):
        controle(tmp_path)


# --- Les courbes du journal ---


def un_journal(tmp_path, pas: int = 50, evaluation_tous_pas: int = 10, refaire: bool = False, avec_pas: bool = True):
    """Un journal au format de `forge entrainer` (méthode `grpo`), `pas` pas, une validation tous les `evaluation_tous_pas`."""
    lignes = [{"evenement": "debut", "pas": 0, "message": "départ"}]
    if not avec_pas:  # le contrôle de départ n'a rien trouvé : forge a écrit « recompense_nulle » et s'est arrêté
        lignes += [{"evenement": "recompense_nulle", "pas": 0, "controle": {"invites": 3, "reponses": 6, "justes": 0, "taux": 0.0, "lance": False}}]
    for p in range(1, pas + 1) if avec_pas else ():
        ligne = {
            "pas": p,
            "perte": 0.1 / p,
            "recompense_moyenne": min(1.0, 0.05 + 0.01 * p),
            "groupes_sans_signal": max(0.0, 0.9 - 0.01 * p),
            "longueur_moyenne": 12.0,
            "secondes_generation": 1.5,
            "secondes_apprentissage": 0.5,
            "secondes": 2.0 * p,
        }
        if p % evaluation_tous_pas == 0:
            ligne["reussite_val"] = 0.01 * p
        lignes.append(ligne)
    if refaire:  # un pas refait après un plantage : la dernière valeur compte
        lignes.append({"pas": pas, "perte": 0.1, "recompense_moyenne": 0.9, "groupes_sans_signal": 0.1, "reussite_val": 0.99, "secondes": 99.0})
    lignes.append({"evenement": "fin", "pas": pas if avec_pas else 0})
    chemin = tmp_path / "journal.jsonl"
    chemin.write_text("".join(json.dumps(ligne) + "\n" for ligne in lignes), encoding="utf-8")
    return chemin


def test_les_courbes_sont_celles_de_serie_et_la_validation_garde_ses_pas(tmp_path):
    journal = un_journal(tmp_path)
    courbes = courbes_grpo(journal)
    assert list(courbes) == [*CLES_DES_COURBES, "reussite_val"] == ["recompense_moyenne", "groupes_sans_signal", "reussite_val"]
    lignes = lire(journal)
    for cle in CLES_DES_COURBES:
        assert courbes[cle] == serie(lignes, cle, 600, None)
        assert len(courbes[cle]) == 50  # moins de 600 pas : un point par pas
    assert courbes["recompense_moyenne"][0] == [1, 0.05 + 0.01]
    # La validation n'a pas de mesure à chaque pas : chacune reste à son pas (10, 20, 30…), sans lissage.
    assert courbes["reussite_val"] == [[p, 0.01 * p] for p in (10, 20, 30, 40, 50)]


def test_les_points_sont_reduits_comme_le_site(tmp_path):
    points = courbes_grpo(un_journal(tmp_path, pas=50), points=10)["recompense_moyenne"]
    assert len(points) == 10 and [p for p, _ in points][:3] == [3, 8, 13]  # des paquets de 5 pas, posés au milieu
    assert points[0][1] == pytest.approx(sum(0.05 + 0.01 * p for p in range(1, 6)) / 5)


def test_un_pas_refait_garde_sa_derniere_valeur(tmp_path):
    courbes = courbes_grpo(un_journal(tmp_path, refaire=True))
    assert courbes["recompense_moyenne"][-1] == [50, 0.9] and courbes["reussite_val"][-1] == [50, 0.99]


def test_le_nombre_total_de_pas_de_la_configuration_fixe_le_lissage(tmp_path):
    journal = un_journal(tmp_path, pas=30)
    # 300 pas prévus, 10 points : des paquets de 30 pas, donc un seul point pour les 30 pas déjà faits.
    assert len(courbes_grpo(journal, points=10, pas_total=300)["groupes_sans_signal"]) == 1
    assert len(courbes_grpo(journal, points=10)["groupes_sans_signal"]) == 10


def test_un_rl_non_lance_est_un_releve_sans_courbe(tmp_path):
    # Le journal d'un contrôle de départ refusé : des évènements, aucun pas. Ce n'est pas une erreur, c'est un résultat.
    assert courbes_grpo(un_journal(tmp_path, avec_pas=False)) == {"lance": False}


def test_un_journal_absent_ou_vide_le_dit(tmp_path):
    with pytest.raises(FileNotFoundError, match="n'existe pas ou est vide.*grpo"):
        courbes_grpo(tmp_path / "absent.jsonl")
    (tmp_path / "vide.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="n'existe pas ou est vide"):
        courbes_grpo(tmp_path / "vide.jsonl")


def test_un_paquet_sans_valeur_finie_reste_absent_et_ne_plante_pas(tmp_path):
    # Un RL qui diverge : la récompense devient NaN sur les derniers pas. Le paquet reste `None`, montré comme absent par le site.
    chemin = tmp_path / "journal.jsonl"
    lignes = [{"pas": p, "perte": 0.5, "recompense_moyenne": 0.25, "groupes_sans_signal": 0.5} for p in range(1, 5)]
    lignes[2]["recompense_moyenne"] = float("nan")
    lignes[3]["recompense_moyenne"] = float("inf")
    chemin.write_text("".join(json.dumps(ligne) + "\n" for ligne in lignes), encoding="utf-8")
    courbes = courbes_grpo(chemin, points=2)  # paquets de 2 pas : le deuxième n'a que du non-fini
    assert courbes["recompense_moyenne"] == [[1.5, 0.25], [3.5, None]]
    assert courbes["groupes_sans_signal"] == [[1.5, 0.5], [3.5, 0.5]]
    assert courbes["reussite_val"] == []
    # Le fichier s'écrit en JSON : le `None` devient `null`, jamais NaN.
    assert json.loads(json.dumps(courbes, allow_nan=False)) == courbes


def test_les_courbes_s_ecrivent_en_json(tmp_path):
    courbes = courbes_grpo(un_journal(tmp_path))
    assert json.loads(json.dumps(courbes, allow_nan=False)) == courbes
    assert all(math.isfinite(v) for points in courbes.values() for _, v in points)
