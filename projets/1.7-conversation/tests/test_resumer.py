"""Les relevés que le projet tire des mesures du plan 7 : un rapport d'étape, et les longueurs des exemples d'un jeu.

Le rapport d'étape est fabriqué au format de `forge.evaluation.etape.evaluer_etape` (`version_du_rapport` 1) :
ton-ia-1.7 n'est pas encore évaluée quand ces tests s'écrivent.
"""

import json

import numpy as np
import pytest
from forge.affinage.empaquetage import Rangee, empaqueter
from forge.affinage.jeu import ecrire_jeu
from forge.conversation.format import ExempleMasque
from forge.evaluation.etape import MESURES_PAR_ETAPE, VERSION_DU_RAPPORT_D_ETAPE
from forge.tokenizer import TokenizerOctets

from conversation_pas_a_pas.gabarit import TOKENIZER
from conversation_pas_a_pas.resumer import developper, longueurs, resumer_etape

TOK = TokenizerOctets.charger(TOKENIZER)

ECHANTILLONS_17 = [
    {"invite": "Quelle est la capitale de la France ?", "texte": "Paris.", "pensee": None, "terminee": True},
    {"invite": "Qui es-tu ?", "texte": "Je suis ton IA, un modèle", "pensee": None, "terminee": False},
]
ECHANTILLONS_15 = [
    {"invite": "Quelle est la capitale de la France ?", "texte": "La France est un pays de l'Europe", "pensee": None, "terminee": False},
    {"invite": "Qui es-tu ?", "texte": "", "pensee": None, "terminee": False},
]


def mesures(perte: float, echantillons: list[dict]) -> dict:
    """Les mesures de l'étape 1.7, avec les clés de `forge evaluer-etape` (voir le README de forge)."""
    return {
        "perte_conversation": {"perte": perte, "n": 64},
        "ifeval_fr": {"invite_stricte": 0.12, "consigne_stricte": 0.2, "n": 541},
        "tenue": {"terminee": 0.9, "fr": 0.95, "autre": 0.03, "indetermine": 0.02, "mots_moyens": 41.5, "n": 641},
        "oubli": {"perte": 2.6, "bits_par_octet": 0.9, "n": 64},
        "echantillons": echantillons,
    }


def un_rapport(avec_reference: bool = True) -> dict:
    rapport = {
        "version_du_rapport": VERSION_DU_RAPPORT_D_ETAPE,
        "version": "ton-ia-1.7",
        "empreinte": "a" * 64,
        "mesures": mesures(1.43, ECHANTILLONS_17),
        "secondes": 812.4,
        "etape": "1.7",
        "date": "2026-11-20T09:15:31+01:00",
        "appareil": "cuda",
        "n_max": None,
    }
    if avec_reference:
        rapport["reference"] = {
            "version": "ton-ia-1.5",
            "empreinte": "b" * 64,
            "mesures": mesures(3.9, ECHANTILLONS_15),
            "secondes": 790.0,
        }
    return rapport


def ecrire(tmp_path, rapport: dict):
    chemin = tmp_path / "rapport.json"
    chemin.write_text(json.dumps(rapport), encoding="utf-8")
    return chemin


def test_resumer_etape(tmp_path):
    releve = resumer_etape(ecrire(tmp_path, un_rapport()))
    assert list(releve) == ["version", "etape", "releve_le", "mesures", "echantillons"]
    assert (releve["version"], releve["etape"], releve["releve_le"]) == ("ton-ia-1.7", "1.7", "2026-11-20")
    # Les mesures de l'étape 1.7 de forge, sans les échantillons, rangés à part.
    assert list(releve["mesures"]) == [m for m in MESURES_PAR_ETAPE["1.7"] if m != "echantillons"]
    assert releve["echantillons"] == ECHANTILLONS_17


def test_resumer_etape_ne_recalcule_rien(tmp_path):
    rapport = un_rapport()
    releve = resumer_etape(ecrire(tmp_path, rapport))
    assert releve["mesures"] == {nom: m for nom, m in rapport["mesures"].items() if nom != "echantillons"}
    assert releve["mesures"]["perte_conversation"]["perte"] == 1.43  # le nombre du rapport, à l'identique


def test_la_reference_est_resumee_a_son_tour(tmp_path):
    releve = resumer_etape(ecrire(tmp_path, un_rapport()), reference=True)
    assert (releve["version"], releve["etape"], releve["releve_le"]) == ("ton-ia-1.5", "1.7", "2026-11-20")
    assert releve["mesures"]["perte_conversation"]["perte"] == 3.9
    assert releve["echantillons"] == ECHANTILLONS_15  # telles quelles : une réponse vide ou coupée n'est pas retouchée


def test_une_mesure_absente_reste_absente(tmp_path):
    rapport = un_rapport()
    rapport["mesures"]["ifeval_fr"] = {"absente": "IFEval-FR n'est pas téléchargé"}
    assert resumer_etape(ecrire(tmp_path, rapport))["mesures"]["ifeval_fr"] == {"absente": "IFEval-FR n'est pas téléchargé"}


def test_le_releve_s_ecrit_comme_les_autres_mesures(tmp_path):
    releve = resumer_etape(ecrire(tmp_path, un_rapport()))
    assert json.loads(json.dumps(releve, ensure_ascii=False, allow_nan=False)) == releve


@pytest.mark.parametrize(
    ("changement", "message"),
    [
        (lambda r: r.update(version_du_rapport=2), "version 1"),
        (lambda r: r.pop("etape"), "pas de « etape »"),
        (lambda r: r.pop("mesures"), "pas de « mesures »"),
        (lambda r: r["mesures"].pop("echantillons"), "pas d'« echantillons »"),
        (lambda r: r.update(date="hier"), "pas une date ISO"),
    ],
)
def test_un_rapport_abime_dit_quoi_refaire(tmp_path, changement, message):
    rapport = un_rapport()
    changement(rapport)
    with pytest.raises(ValueError, match=message) as erreur:
        resumer_etape(ecrire(tmp_path, rapport))
    assert "evaluer-etape" in str(erreur.value)


def test_sans_reference_le_rapport_le_dit(tmp_path):
    with pytest.raises(ValueError, match="pas de version de référence"):
        resumer_etape(ecrire(tmp_path, un_rapport(avec_reference=False)), reference=True)


def test_un_rapport_qui_manque_ou_qui_n_est_pas_du_json(tmp_path):
    with pytest.raises(FileNotFoundError, match="n'existe pas"):
        resumer_etape(tmp_path / "absent.json")
    (tmp_path / "faux.json").write_text("{pas du json", encoding="utf-8")
    with pytest.raises(ValueError, match="pas un fichier JSON lisible"):
        resumer_etape(tmp_path / "faux.json")


# --- Les longueurs des exemples ----------------------------------------------------------------------------


def un_jeu(dossier, longueurs_des_exemples: list[int], longueur: int = 63):
    """Un jeu `sft` dont les exemples ont les longueurs données (des ids sans importance, tout est appris sauf le premier)."""
    exemples = [ExempleMasque(ids=[5] * n, appris=[False] + [True] * (n - 1)) for n in longueurs_des_exemples]
    train, ecartes = empaqueter(exemples, longueur, 0)
    val = [Rangee(ids=[5] * (longueur + 1), appris=[False] + [True] * longueur, documents=[0] * (longueur + 1))]
    ecrire_jeu(dossier, train, val, "sft", {"ecartes": ecartes, "sources": {}}, TOK)
    return dossier


def test_longueurs_compte_les_exemples_de_chaque_rangee(tmp_path):
    tailles = [10, 20, 20, 30, 5, 64, 64, 7, 7, 7]
    dossier = un_jeu(tmp_path / "jeu", tailles)
    avant = {p: p.stat().st_mtime_ns for p in dossier.rglob("*") if p.is_file()}
    releve = longueurs(dossier)
    assert releve["exemples"] == len(tailles) and releve["jetons"] == sum(tailles)
    assert releve["histogramme"] == [[5, 1], [7, 3], [10, 1], [20, 2], [30, 1], [64, 2]]
    assert developper(releve["histogramme"]) == sorted(tailles)
    assert (releve["min"], releve["max"], releve["longueur_des_rangees"]) == (5, 64, 63)
    assert releve["mediane"] == 15.0 and releve["moyenne"] == round(sum(tailles) / len(tailles), 2)
    assert releve["jeu"] == "jeu" and len(releve["releve_le"]) == 10
    # Le jeu n'est que lu.
    assert avant == {p: p.stat().st_mtime_ns for p in dossier.rglob("*") if p.is_file()}


def test_longueurs_ne_compte_que_train(tmp_path):
    dossier = un_jeu(tmp_path / "jeu", [10, 12])
    assert longueurs(dossier)["exemples"] == 2  # la rangée de validation (un exemple de 64) n'y est pas


def test_longueurs_refuse_un_jeu_absent_coupe_ou_vide(tmp_path):
    with pytest.raises(FileNotFoundError, match="n'existe pas"):
        longueurs(tmp_path / "absent")
    dossier = un_jeu(tmp_path / "jeu", [10, 12])
    (dossier / "train" / "documents.bin").write_bytes(np.zeros(5, dtype="<i2").tobytes())
    with pytest.raises(ValueError, match="a changé ou a été coupé"):
        longueurs(dossier)
    (dossier / ".complet").unlink()
    with pytest.raises(FileNotFoundError, match="pas fini"):
        longueurs(dossier)
