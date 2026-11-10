"""`resumer` lit un rapport d'évaluation de forge sans rien recalculer, et le relevé de « mini » dit ce que dit le document.

Le rapport factice a le format de `forge.evaluation.rapport.evaluer` (`VERSION_DU_RAPPORT = 1`).
"""

import copy
import json
import pathlib

import pytest
from forge.evaluation.rapport import VERSION_DU_RAPPORT
from forge.evaluation.rapport import verdict as verdict_de_forge

from evaluation_pas_a_pas.resumer import nom_de_l_entrainement, resumer

PROJET = pathlib.Path(__file__).resolve().parents[1]
RACINE = pathlib.Path(__file__).resolve().parents[3]
MINI_MD = RACINE / "docs" / "mesures" / "ton-ia-mini.md"

RAPPORT = {
    "version": VERSION_DU_RAPPORT,
    "date": "2026-11-03T15:43:18+01:00",
    "sauvegarde": "D:\\forge-ia-donnees\\entrainements\\ton-ia-factice\\sauvegardes\\etape-0000100.pt",
    "pas": 100,
    "modele": {"taille_vocabulaire": 32768, "dim": 64, "couches": 2, "tetes": 4, "longueur_contexte": 64, "base_rope": 10000.0, "parametres": 2_000_000},
    "tokenizer": {"nom": "ton-ia-v1", "taille_vocabulaire": 32768, "fichier": "tokenizer.json"},
    "donnees": "jetons",
    "appareil": "cuda",
    "morceaux_val": 8,
    "longueur_val": 64,
    "perte_val": 3.5,
    "perte_hasard": 10.39720770839918,
    "perplexite": 33.11545195869231,
    "octets_par_jeton": 4.4,
    "bits_par_octet": 1.147,
    "n_qcm": None,
    "qcm": {
        "hellaswag": {
            "exactitude": 0.26,
            "exactitude_normalisee": 0.272,
            "hasard": 0.25,
            "n": 9338,
            "marge_95": 0.0089,
            "marge_95_normalisee": 0.009,
            "marge_hasard": 0.0088,
            "total_du_test": 9338,
        },
        "arc": {
            "exactitude": 0.175,
            "exactitude_normalisee": 0.236,
            "hasard": 0.25,
            "n": 1169,
            "marge_95": 0.0218,
            "marge_95_normalisee": 0.0243,
            "marge_hasard": 0.0248,
            "total_du_test": 1169,
        },
    },
    "generation": {"temperature": 0.8, "top_k": 50, "n_nouveaux": 60, "graine": 0},
    "echantillons": [{"invite": "Il était une fois", "suite": ", un jour", "graine": 0, "n_jetons": 60, "s_arrete": False}],
    "secondes": 26.0,
}


def ecrire(tmp_path, rapport) -> pathlib.Path:
    chemin = tmp_path / "evaluation" / "etape-0000100" / "rapport.json"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(rapport, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return chemin


def test_resumer_lit_le_rapport(tmp_path):
    releve = resumer(ecrire(tmp_path, RAPPORT))
    assert list(releve) == ["nom", "releve_le", "pas", "perte_val", "perplexite", "bits_par_octet", "qcm", "echantillons"]
    assert releve["nom"] == "ton-ia-factice"  # le dossier de l'entraînement, lu dans le chemin de la sauvegarde
    assert releve["releve_le"] == "2026-11-03" and releve["pas"] == 100
    # Rien n'est recalculé : les nombres sont ceux du rapport.
    assert (releve["perte_val"], releve["perplexite"], releve["bits_par_octet"]) == (3.5, 33.11545195869231, 1.147)
    assert releve["echantillons"] == RAPPORT["echantillons"]


def test_resumer_garde_les_cles_de_forge_et_ajoute_le_verdict(tmp_path):
    releve = resumer(ecrire(tmp_path, RAPPORT))
    assert list(releve["qcm"]) == ["hellaswag", "arc"]
    hella = releve["qcm"]["hellaswag"]
    assert {c: hella[c] for c in RAPPORT["qcm"]["hellaswag"]} == RAPPORT["qcm"]["hellaswag"]
    assert list(hella)[-1] == "verdict"
    assert hella["verdict"] == "au-dessus" and releve["qcm"]["arc"]["verdict"] == "pas-different"
    # Le verdict est celui du rapport de forge.
    traduction = {"au-dessus du hasard": "au-dessus", "en dessous du hasard": "en-dessous", "pas différent du hasard": "pas-different"}
    for nom, mesures in RAPPORT["qcm"].items():
        assert releve["qcm"][nom]["verdict"] == traduction[verdict_de_forge(mesures)]


def test_resumer_donne_un_nom_si_on_le_demande(tmp_path):
    assert resumer(ecrire(tmp_path, RAPPORT), nom="autre")["nom"] == "autre"


def test_nom_de_l_entrainement():
    assert nom_de_l_entrainement("D:\\forge-ia-donnees\\entrainements\\ton-ia-mini\\sauvegardes\\etape-0006370.pt") == "ton-ia-mini"
    assert nom_de_l_entrainement("/donnees/entrainements/ton-ia-1.5/sauvegardes/meilleur.pt") == "ton-ia-1.5"


def test_resumer_sans_rapport_dit_quoi_faire(tmp_path):
    with pytest.raises(FileNotFoundError, match="python -m forge evaluer"):
        resumer(tmp_path / "rien.json")


def test_resumer_refuse_un_fichier_qui_n_est_pas_un_rapport(tmp_path):
    chemin = tmp_path / "rapport.json"
    chemin.write_text("pas du json", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON lisible"):
        resumer(chemin)
    chemin.write_text(json.dumps({**RAPPORT, "version": 0}), encoding="utf-8")
    with pytest.raises(ValueError, match="version 1"):
        resumer(chemin)
    chemin.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValueError, match="version 1"):
        resumer(chemin)


def test_resumer_refuse_un_rapport_incomplet(tmp_path):
    sans_perte = {c: v for c, v in RAPPORT.items() if c != "perte_val"}
    with pytest.raises(ValueError, match="perte_val"):
        resumer(ecrire(tmp_path, sans_perte))


def test_resumer_refuse_une_perte_infinie(tmp_path):
    divergee = {**RAPPORT, "perplexite": None}  # forge écrit null pour l'infini
    with pytest.raises(ValueError, match="divergé"):
        resumer(ecrire(tmp_path, divergee))


def test_resumer_refuse_un_qcm_manquant_ou_en_erreur(tmp_path):
    sans_arc = copy.deepcopy(RAPPORT)
    del sans_arc["qcm"]["arc"]
    with pytest.raises(ValueError, match="Le QCM arc n'a pas été mesuré"):
        resumer(ecrire(tmp_path, sans_arc))
    en_erreur = copy.deepcopy(RAPPORT)
    en_erreur["qcm"]["arc"] = {"erreur": "ConnectionError : pas de réseau"}
    with pytest.raises(ValueError, match="pas de réseau"):
        resumer(ecrire(tmp_path, en_erreur))
    incomplet = copy.deepcopy(RAPPORT)
    del incomplet["qcm"]["arc"]["marge_hasard"]
    with pytest.raises(ValueError, match="marge_hasard"):
        resumer(ecrire(tmp_path, incomplet))


# --- Le relevé de « mini » ---------------------------------------------------------------------


def virgule(x: float, decimales: int) -> str:
    return f"{x:.{decimales}f}".replace(".", ",")


def test_le_releve_de_mini_dit_ce_que_dit_le_document():
    chemin = PROJET / "mesures" / "evaluation-mini.json"
    if not chemin.exists():
        pytest.skip("Le relevé de « mini » n'est pas encore écrit (voir le README du projet).")
    if not MINI_MD.exists():
        pytest.skip("Projet téléchargé seul : docs/mesures/ton-ia-mini.md n'est pas là pour comparer.")
    releve = json.loads(chemin.read_text(encoding="utf-8"))
    document = MINI_MD.read_text(encoding="utf-8").replace("\u202f", " ").replace("\u00a0", " ")
    assert releve["nom"] == "ton-ia-mini" and releve["pas"] == 6370
    assert f"perplexité **{virgule(releve['perplexite'], 1)}**" in document  # 30,8
    assert f"**{virgule(releve['bits_par_octet'], 3)} bit par octet**" in document  # 1,133
    assert f"HellaSwag {virgule(100 * releve['qcm']['hellaswag']['exactitude_normalisee'], 1)} %" in document  # 27,2 %
    assert f"ARC-Challenge {virgule(100 * releve['qcm']['arc']['exactitude_normalisee'], 1)} %" in document  # 23,6 %
    assert releve["qcm"]["hellaswag"]["verdict"] == "au-dessus" and releve["qcm"]["arc"]["verdict"] == "pas-different"
    assert len(releve["echantillons"]) == 10
    # Le relevé est écrit comme les autres mesures du dépôt.
    octets = chemin.read_bytes()
    assert b"\r" not in octets and octets.endswith(b"}\n")
    assert octets.decode("utf-8") == json.dumps(releve, ensure_ascii=False, allow_nan=False, indent=1) + "\n"
