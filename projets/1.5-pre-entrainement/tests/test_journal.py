"""Lire le journal d'un entraînement : sessions, courbes et résumé.

`journal-factice.jsonl` est écrit à la main, dans le format de forge : un début, 5 pas, une pause,
une reprise, 5 pas, la fin. Les nombres attendus se lisent dans ce fichier.
"""

import json
import math
import pathlib
import re

import pytest
from forge.entrainement import ConfigEntrainement
from forge.modele import ConfigModele, nombre_parametres

from pre_entrainement import journal
from pre_entrainement.journal import courbe, lire, resume, sessions

DOSSIER = pathlib.Path(__file__).resolve().parent
FACTICE = DOSSIER / "journal-factice.jsonl"
CONFIG_FACTICE = ConfigEntrainement(
    preset=ConfigModele(dim=64, couches=2, tetes=4, longueur_contexte=64),
    donnees="factice",
    jetons_total=10 * 1024,
    taille_lot_jetons=1024,
    micro_lot=16,
    taux_max=1e-3,
    echauffement=2,
    evaluation_tous_pas=5,
    appareil="cpu",
    compiler="non",
    sortie="factice",
)


def taille_de_paquet(nb_pas: int, max_points: int = 600) -> int:
    """Recopiée de `taillePaquet(nbPas, maxPoints = 600)`, dans site/src/lib/courbe.ts :
    `Math.max(1, Math.ceil(nbPas / maxPoints))`. Le site et le projet découpent pareil."""
    return max(1, math.ceil(nb_pas / max_points))


def lignes_de_pas(nb: int, perte=lambda p: float(p)) -> list[dict]:
    """Un journal d'une seule session de `nb` pas, dont la perte du pas p est perte(p)."""
    lignes = [{"evenement": "debut", "pas": 0, "message": "Début"}]
    lignes += [
        {"pas": p, "jetons_vus": 1024 * p, "perte": perte(p), "taux": 0.001, "jetons_par_seconde": 1.0, "secondes": float(p)}
        for p in range(1, nb + 1)
    ]
    return lignes


def test_lire_un_journal_absent_est_vide(tmp_path):
    assert lire(tmp_path / "rien.jsonl") == []


def test_lire_saute_la_ligne_tronquee(tmp_path):
    chemin = tmp_path / "journal.jsonl"
    chemin.write_text(FACTICE.read_text(encoding="utf-8") + '{"pas": 11, "jetons_', encoding="utf-8")
    assert lire(chemin) == lire(FACTICE)


def test_sessions_et_pauses():
    l = lire(FACTICE)  # debut, 5 pas, pause, reprise, 5 pas, fin
    s = sessions(l)
    assert [x["fin"] for x in s] == ["pause", "fin"]
    r = resume(l, CONFIG_FACTICE)
    assert r["pauses"] == 1 and r["pas_faits"] == 10


def test_les_sessions_en_detail():
    assert sessions(lire(FACTICE)) == [
        {"depart": "debut", "premier_pas": 1, "dernier_pas": 5, "secondes": 2.5, "fin": "pause"},
        {"depart": "reprise", "premier_pas": 6, "dernier_pas": 10, "secondes": 2.6, "fin": "fin"},
    ]


def test_une_session_sans_ligne_de_fin_est_coupee():
    lignes = [l for l in lire(FACTICE) if l.get("evenement") != "fin"]
    assert sessions(lignes)[-1]["fin"] == "coupée"
    # Un plantage au milieu de la première session : pas de pause, puis une reprise.
    plantage = lire(FACTICE)[:4] + lire(FACTICE)[8:]  # le début, les pas 1 à 3, puis la reprise
    assert [x["fin"] for x in sessions(plantage)] == ["coupée", "fin"]
    assert [x["dernier_pas"] for x in sessions(plantage)] == [3, 10]


def test_une_perte_non_finie_termine_la_session():
    # forge écrit « perte_non_finie » sans sauvegarder (suivi._FINS_DE_SESSION).
    lignes = lignes_de_pas(3) + [{"evenement": "perte_non_finie", "pas": 4, "message": "La perte est infinie."}]
    assert sessions(lignes) == [
        {"depart": "debut", "premier_pas": 1, "dernier_pas": 3, "secondes": 3.0, "fin": "perte_non_finie"}
    ]
    assert resume(lignes, CONFIG_FACTICE)["pauses"] == 0


def test_un_journal_vide_n_a_pas_de_session():
    assert sessions([]) == []
    r = resume([], CONFIG_FACTICE)
    assert r["pas_faits"] == 0 and r["pauses"] == 0 and r["secondes_de_calcul"] == 0.0
    assert r["perte_finale"] is None and r["validation_finale"] is None and r["debit_moyen"] is None


def test_le_resume_en_detail():
    r = resume(lire(FACTICE), CONFIG_FACTICE)
    assert r == {
        "parametres": nombre_parametres(CONFIG_FACTICE.modele),
        "pas_total": 10,
        "pas_faits": 10,
        "jetons_vus": 10 * 1024,
        "secondes_de_calcul": 5.1,
        "pauses": 1,
        "debit_moyen": 10 * 1024 / 5.1,
        "perte_finale": r["perte_finale"],
        "validation_finale": 9.1,
        "perte_premier_pas": 10.4,
        "perte_dernier_pas": 8.6,
    }
    # Pas de dates : le journal de forge n'en a pas (les pas portent un temps de calcul cumulé).
    assert not {"premier_pas", "dernier_pas"} & r.keys()
    # La perte finale est la moyenne des 20 derniers pas (ici les 10 pas du journal), comme dans docs/mesures.
    assert r["perte_finale"] == pytest.approx(sum([10.4, 10.3, 10.1, 9.8, 9.5, 9.3, 9.0, 8.8, 8.7, 8.6]) / 10)


def test_la_perte_finale_est_la_moyenne_des_20_derniers_pas():
    r = resume(lignes_de_pas(50), CONFIG_FACTICE)
    assert r["perte_finale"] == pytest.approx(sum(range(31, 51)) / 20)
    assert r["perte_dernier_pas"] == 50.0 and r["perte_premier_pas"] == 1.0


# --- La courbe : le même découpage que le site ----------------------------------------------------


def test_courbe_meme_decoupage_que_le_site():
    nb = 1500
    c = courbe(lignes_de_pas(nb))  # points = 600, comme taillePaquet(nbPas, 600)
    taille = taille_de_paquet(nb)
    assert taille == 3 and len(c["pertes"]) == 500
    # Chaque point : le milieu des pas de son paquet, et la moyenne de leurs pertes.
    assert c["pertes"][0] == [2, 2.0]  # pas 1 à 3
    assert c["pertes"][1] == [5, 5.0]  # pas 4 à 6
    assert c["pertes"][-1] == [1499, 1499.0]  # pas 1498 à 1500
    assert c["taille_paquet"] == taille


def test_courbe_dernier_paquet_incomplet():
    c = courbe(lignes_de_pas(7), points=3)  # paquets de 3 : 1-3, 4-6, 7
    assert c["taille_paquet"] == 3
    assert c["pertes"] == [[2, 2.0], [5, 5.0], [7, 7.0]]
    assert courbe(lignes_de_pas(4), points=2)["pertes"] == [[1.5, 1.5], [3.5, 3.5]]


def test_courbe_la_taille_suit_le_total_de_la_configuration():
    # Pendant un entraînement, la courbe garde le même lissage du début à la fin : la taille est
    # celle du nombre total de pas, pas du nombre de pas déjà faits.
    c = courbe(lignes_de_pas(10), points=2, pas_total=100)
    assert c["taille_paquet"] == 50 and c["pertes"] == [[5.5, 5.5]]


def test_courbe_ignore_les_pertes_non_finies():
    lignes = lignes_de_pas(4, perte=lambda p: float("nan") if p == 2 else float(p))
    c = courbe(lignes, points=2)
    assert c["pertes"] == [[1.5, 1.0], [3.5, 3.5]]
    tout_nan = courbe(lignes_de_pas(2, perte=lambda p: float("inf")), points=1)
    assert tout_nan["pertes"] == [[1.5, None]]
    json.dumps(tout_nan, allow_nan=False)


def test_courbe_validations_et_hasard():
    c = courbe(lire(FACTICE))
    assert c["validations"] == [[5, 10.0], [10, 9.1]]
    assert c["hasard"] == math.log(32768)
    assert [p for p, _ in c["pertes"]] == list(range(1, 11))  # 10 pas : un point par pas


def test_courbe_d_un_journal_vide():
    assert courbe([]) == {"taille_paquet": 1, "pertes": [], "validations": [], "hasard": math.log(32768)}


def test_regions_de_journal():
    lignes = pathlib.Path(journal.__file__).read_text(encoding="utf-8").splitlines()
    ouvertes = [m.group(1) for ligne in lignes if (m := re.match(r"\s*# region: (\S+)", ligne))]
    fermees = [m.group(1) for ligne in lignes if (m := re.match(r"\s*# fin: (\S+)", ligne))]
    assert ouvertes == ["sessions", "courbe"]
    assert fermees == ouvertes


# --- Un plantage, puis une reprise qui refait des pas ----------------------------------------------
# `journal-factice-plantage.jsonl` : début, pas 1 à 7, sauvegarde au pas 5, plantage (aucune ligne de
# fin), reprise depuis la sauvegarde du pas 5, pas 6 à 10 (6 et 7 sont refaits), fin.
PLANTAGE = DOSSIER / "journal-factice-plantage.jsonl"


def test_sessions_apres_un_plantage():
    assert sessions(lire(PLANTAGE)) == [
        {"depart": "debut", "premier_pas": 1, "dernier_pas": 7, "secondes": 3.5, "fin": "coupée"},
        # Elle part du temps de calcul du pas 5 (2,5 s), pas de celui du pas 7 : 5,1 - 2,5.
        {"depart": "reprise", "premier_pas": 6, "dernier_pas": 10, "secondes": 2.6, "fin": "fin"},
    ]
    assert all(s["secondes"] >= 0 for s in sessions(lire(PLANTAGE)))


def test_resume_apres_un_plantage():
    r = resume(lire(PLANTAGE), CONFIG_FACTICE)
    assert r["pas_faits"] == 10  # les pas distincts : 6 et 7 ne comptent qu'une fois
    assert r["jetons_vus"] == 10 * 1024 and r["pauses"] == 0
    # Le temps réellement passé, pas refaits compris : 3,5 + 2,6.
    assert r["secondes_de_calcul"] == 6.1
    assert r["perte_dernier_pas"] == 8.6 and r["validation_finale"] == 9.1


def test_courbe_apres_un_plantage_garde_la_derniere_occurrence_de_chaque_pas():
    c = courbe(lire(PLANTAGE))
    assert c["pertes"] == [[p, v] for p, v in zip(range(1, 11), [10.4, 10.3, 10.1, 9.8, 9.5, 9.3 + 0.01, 9.0 + 0.01, 8.8, 8.7, 8.6])]
    assert c["validations"] == [[5, 10.0], [10, 9.1]]
    # Des paquets de 5 : le pas p est bien à l'indice p - 1.
    assert courbe(lire(PLANTAGE), points=2)["pertes"][1] == [8, pytest.approx((9.31 + 9.01 + 8.8 + 8.7 + 8.6) / 5)]


def test_validation_refaite_garde_la_derniere():
    lignes = lignes_de_pas(2) + [{"pas": 2, "perte": 5.0, "perte_val": 4.0}]
    lignes[2]["perte_val"] = 9.0
    assert courbe(lignes)["validations"] == [[2, 4.0]]
