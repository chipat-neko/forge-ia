"""Les courbes d'une DPO, relevées dans un journal fabriqué au format de `forge entrainer` (méthode `dpo`)."""

import json
import math

import pytest
from pre_entrainement.journal import lire, serie

from alignement_pas_a_pas.courbes import CLES_DES_COURBES, courbes_dpo


def un_journal(tmp_path, pas: int = 50, avec_dpo: bool = True, refaire: bool = False):
    """Un journal : un début, `pas` lignes de pas (les mesures de `perte_dpo`), une fin."""
    lignes = [{"evenement": "debut", "pas": 0, "message": "départ"}]
    for p in range(1, pas + 1):
        ligne = {"pas": p, "perte": 0.7 - 0.01 * p, "secondes": float(p)}
        if avec_dpo:
            ligne |= {"logps_choisie": -2.0 + 0.01 * p, "logps_rejetee": -2.1 - 0.02 * p, "exactitude": min(1.0, 0.4 + 0.02 * p)}
        lignes.append(ligne)
    if refaire:  # un pas refait après un plantage : la dernière valeur compte
        lignes.append({"pas": pas, "perte": 0.1, "logps_choisie": -9.0, "logps_rejetee": -9.0, "exactitude": 1.0, "secondes": 99.0})
    lignes.append({"evenement": "fin", "pas": pas})
    chemin = tmp_path / "journal.jsonl"
    chemin.write_text("".join(json.dumps(ligne) + "\n" for ligne in lignes), encoding="utf-8")
    return chemin


def test_les_trois_courbes_sont_celles_de_serie(tmp_path):
    journal = un_journal(tmp_path)
    courbes = courbes_dpo(journal)
    assert list(courbes) == list(CLES_DES_COURBES) == ["logps_choisie", "logps_rejetee", "exactitude"]
    lignes = lire(journal)
    for cle, points in courbes.items():
        assert points == serie(lignes, cle, 600, None)
        assert len(points) == 50  # moins de 600 pas : un point par pas
    assert courbes["logps_choisie"][0] == [1, -2.0 + 0.01]
    assert courbes["exactitude"][-1][1] == 1.0


def test_les_points_sont_reduits_comme_le_site(tmp_path):
    journal = un_journal(tmp_path, pas=50)
    points = courbes_dpo(journal, points=10)["logps_choisie"]
    assert len(points) == 10  # des paquets de 5 pas, posés au milieu : 3, 8, 13…
    assert [p for p, _ in points][:3] == [3, 8, 13]
    assert points[0][1] == pytest.approx(sum(-2.0 + 0.01 * p for p in range(1, 6)) / 5)


def test_un_pas_refait_garde_sa_derniere_valeur(tmp_path):
    points = courbes_dpo(un_journal(tmp_path, refaire=True))["logps_choisie"]
    assert points[-1] == [50, -9.0] and len(points) == 50


def test_le_nombre_total_de_pas_de_la_configuration_fixe_le_lissage(tmp_path):
    journal = un_journal(tmp_path, pas=30)
    # 300 pas prévus, 10 points : des paquets de 30 pas, donc un seul point pour les 30 pas déjà faits ; sans `pas_total`, 10 points.
    assert courbes_dpo(journal, points=10, pas_total=300)["exactitude"] == [[15.5, pytest.approx(sum(min(1.0, 0.4 + 0.02 * p) for p in range(1, 31)) / 30)]]
    assert len(courbes_dpo(journal, points=10)["exactitude"]) == 10


def test_les_courbes_s_ecrivent_en_json(tmp_path):
    courbes = courbes_dpo(un_journal(tmp_path))
    assert json.loads(json.dumps(courbes, allow_nan=False)) == courbes
    assert all(math.isfinite(v) for points in courbes.values() for _, v in points)


def test_un_journal_absent_vide_ou_qui_n_est_pas_celui_d_une_dpo_le_dit(tmp_path):
    with pytest.raises(FileNotFoundError, match="n'existe pas ou est vide"):
        courbes_dpo(tmp_path / "absent.jsonl")
    with pytest.raises(ValueError, match="« logps_choisie » : ce n'est pas le journal d'une DPO"):
        courbes_dpo(un_journal(tmp_path, avec_dpo=False))


def test_un_paquet_sans_valeur_finie_est_refuse(tmp_path):
    chemin = tmp_path / "journal.jsonl"
    lignes = [{"pas": p, "perte": 0.5, "logps_choisie": -1.0, "logps_rejetee": -2.0, "exactitude": 0.5} for p in range(1, 5)]
    lignes[2]["exactitude"] = float("nan")
    lignes[3]["exactitude"] = float("inf")
    chemin.write_text("".join(json.dumps(ligne) + "\n" for ligne in lignes), encoding="utf-8")
    with pytest.raises(ValueError, match="sans aucune valeur finie"):
        courbes_dpo(chemin, points=2)  # paquets de 2 pas : le deuxième n'a que du non-fini
