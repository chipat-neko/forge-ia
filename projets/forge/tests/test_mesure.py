"""Tests de la mesure GPU et CPU de l'entraînement (`forge.mesure`).

Tout tourne sur le processeur avec un modèle minuscule (vocabulaire 128, dim 32, 2 couches,
contexte 16), sauf le test marqué `gpu`. Ce qu'on vérifie : `mesurer` utilise la vraie étape
d'optimisation de l'entraînement et rend un débit positif avec tous les fils du processeur ;
`estimer` et `estimer_disque` font de l'arithmétique exacte ; la recherche du plus grand
micro-lot suit bien « puissances de 2, puis affinage ».
"""

import json
import os
import re

import psutil
import pytest
import torch

from forge.__main__ import construire_parseur, main
from forge.mesure import (
    JETONS_PAR_PARAMETRE,
    OCTETS_TEXTE_PAR_JETON,
    GpuOccupe,
    estimer,
    estimer_disque,
    gpu_occupe,
    lire_etat_gpu,
    mesurer,
    mesurer_presets,
    plus_grand_micro_lot,
    tableaux_markdown,
)
from forge.modele import PRESETS, ConfigModele, nombre_parametres

MODELE_MINUSCULE = ConfigModele(taille_vocabulaire=128, dim=32, couches=2, tetes=2, longueur_contexte=16)
GO = 1024**3


def test_mesurer_cpu_utilise_tous_les_fils():
    nombre_de_fils_avant = torch.get_num_threads()
    resultat = mesurer(MODELE_MINUSCULE, "cpu", micro_lot=2, pas=3)
    assert resultat["jetons_par_seconde"] > 0
    assert resultat["fils_utilises"] == os.cpu_count()
    assert resultat["pas_mesures"] == 3
    # La charge de chaque cœur logique pendant la mesure, en pourcentage.
    assert len(resultat["charge_par_coeur"]) == psutil.cpu_count(logical=True)
    assert all(0 <= charge <= 100 for charge in resultat["charge_par_coeur"])
    assert resultat["coeurs_occupes"] >= 0
    # Sur le processeur, il n'y a pas de pic de mémoire de carte graphique à rapporter.
    assert resultat["memoire_max_go"] is None
    # La mesure ne laisse pas son réglage de fils derrière elle.
    assert torch.get_num_threads() == nombre_de_fils_avant


def test_mesurer_cpu_fils_choisis():
    resultat = mesurer(MODELE_MINUSCULE, "cpu", micro_lot=1, pas=2, fils=1)
    assert resultat["fils_utilises"] == 1


def test_mesurer_debit_est_jetons_sur_secondes():
    resultat = mesurer(MODELE_MINUSCULE, "cpu", micro_lot=3, pas=4, accumulation=2)
    jetons = 4 * 2 * 3 * MODELE_MINUSCULE.longueur_contexte  # pas × accumulation × micro_lot × contexte
    assert resultat["jetons_mesures"] == jetons
    assert resultat["jetons_par_seconde"] == pytest.approx(jetons / resultat["secondes"])


def test_mesurer_s_arrete_au_budget_de_temps():
    # Un budget de 0 seconde : on mesure quand même 1 pas, jamais zéro (pas de division par 0).
    resultat = mesurer(MODELE_MINUSCULE, "cpu", micro_lot=1, pas=50, secondes_max=0.0)
    assert resultat["pas_mesures"] == 1
    assert resultat["jetons_par_seconde"] > 0


def test_mesurer_refuse_les_reglages_impossibles():
    with pytest.raises(ValueError, match="appareil"):
        mesurer(MODELE_MINUSCULE, "tpu", micro_lot=1)
    with pytest.raises(ValueError, match="micro_lot"):
        mesurer(MODELE_MINUSCULE, "cpu", micro_lot=0)
    with pytest.raises(ValueError, match="pas"):
        mesurer(MODELE_MINUSCULE, "cpu", micro_lot=1, pas=0)


@pytest.mark.gpu
def test_mesurer_gpu_donne_debit_et_memoire():
    resultat = mesurer(MODELE_MINUSCULE, "cuda", micro_lot=4, pas=3)
    assert resultat["jetons_par_seconde"] > 0
    assert resultat["memoire_max_go"] > 0


def test_estimer_est_de_l_arithmetique_exacte():
    # 3 600 000 jetons à 1 000 jetons par seconde : 3 600 s, soit exactement 1 heure.
    assert estimer(MODELE_MINUSCULE, 1000.0, 3_600_000) == pytest.approx(1.0)
    assert estimer(MODELE_MINUSCULE, 500.0, 3_600_000) == pytest.approx(2.0)
    # Sans nombre de jetons : 20 jetons par paramètre (la cible de la forge).
    attendu = JETONS_PAR_PARAMETRE * nombre_parametres(MODELE_MINUSCULE) / 250.0 / 3600
    assert estimer(MODELE_MINUSCULE, 250.0) == pytest.approx(attendu)
    assert JETONS_PAR_PARAMETRE == 20
    with pytest.raises(ValueError, match="jetons_par_seconde"):
        estimer(MODELE_MINUSCULE, 0.0, 1000)


def test_estimer_disque_chaque_poste():
    config = PRESETS["moyen"]
    parametres = nombre_parametres(config)
    jetons = JETONS_PAR_PARAMETRE * parametres
    disque = estimer_disque(config)
    assert disque["jetons"] == jetons
    assert disque["jetons_go"] == pytest.approx(jetons * 2 / GO)  # 2 octets par jeton (uint16)
    assert disque["texte_brut_go"] == pytest.approx(jetons * OCTETS_TEXTE_PAR_JETON / GO)
    assert OCTETS_TEXTE_PAR_JETON == 4.36  # docs/mesures/tokenizer-ton-ia-v1.md
    assert disque["sauvegardes_go"] == pytest.approx(parametres * 3 * 16 / GO)  # 3 fichiers de 16 octets par paramètre
    # Le pic compte tout en même temps : le texte brut n'est effacé qu'après l'encodage.
    assert disque["pic_go"] == pytest.approx(disque["jetons_go"] + disque["texte_brut_go"] + disque["sauvegardes_go"])
    # Dans l'ordre réel (encoder, effacer le texte, puis entraîner), les sauvegardes n'existent pas
    # en même temps que le texte brut : le pic est le plus grand des deux moments.
    assert disque["regime_etabli_go"] == pytest.approx(disque["jetons_go"] + disque["sauvegardes_go"])
    assert disque["pic_sequentiel_go"] == pytest.approx(
        max(disque["jetons_go"] + disque["texte_brut_go"], disque["jetons_go"] + disque["sauvegardes_go"])
    )
    assert disque["pic_sequentiel_go"] < disque["pic_go"]


def test_estimer_disque_avec_un_autre_nombre_de_jetons():
    disque = estimer_disque(MODELE_MINUSCULE, jetons=1_000_000)
    assert disque["jetons"] == 1_000_000
    assert disque["jetons_go"] == pytest.approx(2_000_000 / GO)
    assert disque["texte_brut_go"] == pytest.approx(4_360_000 / GO)


def test_estimer_disque_les_grandes_tailles_ne_tiennent_pas_toutes():
    # Garde-fou de l'ordre de grandeur : le pic croît avec la taille du modèle.
    pics = [estimer_disque(PRESETS[nom])["pic_go"] for nom in ("petit", "moyen", "grand", "tres_grand")]
    assert pics == sorted(pics)
    assert pics[-1] > 44.4 > pics[1]  # D: a 44,4 Go libres : « moyen » tient, « tres_grand » non


def test_plus_grand_micro_lot_puissances_de_2_puis_affinage():
    essais = []

    def tient_jusqu_a(seuil):
        def tient(micro_lot):
            essais.append(micro_lot)
            return micro_lot <= seuil

        return tient

    assert plus_grand_micro_lot(tient_jusqu_a(13), maximum=256) == 13
    # D'abord 1, 2, 4, 8, 16 (le premier qui ne tient pas), puis un affinage entre 8 et 16.
    assert essais[:5] == [1, 2, 4, 8, 16]
    assert all(8 < e < 16 for e in essais[5:])
    assert plus_grand_micro_lot(tient_jusqu_a(1), maximum=256) == 1
    assert plus_grand_micro_lot(tient_jusqu_a(64), maximum=256) == 64  # une puissance de 2 exacte
    assert plus_grand_micro_lot(tient_jusqu_a(10_000), maximum=256) == 256  # plafonné au maximum
    assert plus_grand_micro_lot(tient_jusqu_a(0), maximum=256) == 0  # même 1 ne tient pas


def test_la_commande_mesurer_existe():
    parseur = construire_parseur()
    choix = parseur.parse_args(["mesurer", "--presets", "petit,moyen", "--pas", "5"])
    assert choix.presets == ["petit", "moyen"]
    assert choix.pas == 5
    assert choix.gpu_accumulation == 8  # le pas d'AdamW ne pèse alors que comme dans un vrai entraînement
    assert choix.cpu_micro_lot == 2
    assert parseur.parse_args(["mesurer", "--gpu-accumulation", "4"]).gpu_accumulation == 4
    assert parseur.parse_args(["mesurer"]).presets == ["petit", "moyen", "grand", "tres_grand"]
    with pytest.raises(SystemExit):
        parseur.parse_args(["mesurer", "--presets", "gigantesque"])
    with pytest.raises(SystemExit):
        parseur.parse_args(["mesurer", "--gpu-accumulation", "0"])


def test_la_commande_mesurer_sur_cpu_ecrit_un_tableau(tmp_path, capsys, monkeypatch):
    # Pas de carte graphique, un modèle minuscule : seule la colonne du processeur est remplie.
    monkeypatch.setattr("forge.mesure.cuda_disponible", lambda: False)
    monkeypatch.setattr("forge.mesure.charge_au_repos", lambda *a, **k: 3.0)
    monkeypatch.setitem(PRESETS, "minuscule", MODELE_MINUSCULE)
    sortie = tmp_path / "mesures.json"
    code = main(["mesurer", "--presets", "minuscule", "--pas", "2", "--cpu-secondes", "5", "--json", str(sortie)])
    assert code == 0
    ecran = capsys.readouterr().out
    assert "minuscule" in ecran
    assert "tokens" not in ecran  # le français : « jetons par seconde »
    assert "jetons/s" in ecran
    assert " %" not in ecran  # espace fine insécable, jamais une espace ordinaire, avant le %
    assert sortie.is_file()
    brut = json.loads(sortie.read_text(encoding="utf-8"))
    assert brut["presets"]["minuscule"]["cpu"]["fils_utilises"] == os.cpu_count()
    assert brut["presets"]["minuscule"]["gpu"] is None


def test_lire_etat_gpu_et_gpu_occupe():
    etat = lire_etat_gpu("2, 1494, 16303\n")
    assert etat["utilisation_pct"] == 2.0
    assert etat["memoire_utilisee_go"] == pytest.approx(1494 / 1024)
    assert etat["memoire_totale_go"] == pytest.approx(16303 / 1024)
    assert gpu_occupe(etat) is None
    assert gpu_occupe(None) is None  # nvidia-smi muet : état inconnu, on ne bloque pas
    message = gpu_occupe(lire_etat_gpu("95, 12000, 16303"))
    assert "occupée" in message and "95" in message and "python -m forge mesurer" in message


@pytest.mark.gpu
def test_la_mesure_refuse_une_carte_occupee(monkeypatch, capsys):
    monkeypatch.setattr("forge.mesure.etat_gpu", lambda *a, **k: lire_etat_gpu("97, 12000, 16303"))
    monkeypatch.setattr("forge.mesure.charge_au_repos", lambda *a, **k: 3.0)
    with pytest.raises(GpuOccupe, match="occupée"):
        mesurer_presets(["mini"], pas=1)
    assert main(["mesurer", "--presets", "mini", "--pas", "1"]) == 1
    assert "occupée" in capsys.readouterr().err


def test_tableaux_en_francais_avec_la_typographie():
    config = PRESETS["tres_grand"]
    ligne = {
        "parametres": nombre_parametres(config),
        "gpu": {"micro_lot": 2, "jetons_par_seconde": 21234.0, "memoire_max_go": 9.1},
        "gpu_max": {"micro_lot": 5, "jetons_par_seconde": 19876.0, "memoire_max_go": 13.4},
        "cpu": {
            "fils_utilises": 16,
            "micro_lot": 2,
            "pas_mesures": 7,
            "jetons_par_seconde": 345.0,
            "charge_moyenne": 87.0,
            "coeurs_occupes": 13.04,
        },
        "disque": estimer_disque(config),
        "heures_gpu": estimer(config, 21234.0),
        "heures_gpu_max": estimer(config, 19876.0),
        "heures_cpu": estimer(config, 345.0),
        "jetons_en_10_h_gpu": 21234.0 * 36000,
    }
    texte = tableaux_markdown(
        {"machine": {"disque_libre_go": 44.4, "coeurs_logiques": 16}, "presets": {"tres_grand": ligne}}
    )
    assert "21\u202f234" in texte  # milliers : espace fine insécable
    assert "87\u202f%" in texte
    assert "433,6 M" in texte  # virgule décimale
    assert "**non**" in texte  # 76 Go de pic sur 44,4 Go libres
    assert "19\u202f876" in texte  # le plus grand micro-lot qui tient, à côté du plus rapide
    assert "| 13,0 |" in texte  # cœurs occupés (13,04) : une décimale, virgule française
    assert "milliards" in texte
    assert not re.search(r" [%:;!?]", texte)  # jamais d'espace ordinaire devant ces signes
    assert not re.search(r"\d,\d{3}\b", texte)  # pas de virgule de milliers à l'anglaise


@pytest.mark.gpu
def test_mesurer_presets_balaie_les_micro_lots_sur_la_carte(monkeypatch):
    monkeypatch.setitem(PRESETS, "minuscule", MODELE_MINUSCULE)
    monkeypatch.setattr("forge.mesure.charge_au_repos", lambda *a, **k: 3.0)
    monkeypatch.setattr("forge.mesure.etat_gpu", lambda *a, **k: lire_etat_gpu("1, 1500, 16300"))
    resultats = mesurer_presets(["minuscule"], pas=2, cpu_secondes=2, gpu_accumulation=2)
    ligne = resultats["presets"]["minuscule"]
    # Un modèle minuscule tient avec le plus grand micro-lot essayé (256) ; on mesure 1, 2, 4… 256.
    assert ligne["gpu_max"]["micro_lot"] == 256
    assert sorted(ligne["gpu_balayage"]) == [1, 2, 4, 8, 16, 32, 64, 128, 256]
    # `gpu` est le résultat du micro-lot le plus rapide ; les durées en partent.
    assert ligne["gpu"]["jetons_par_seconde"] == max(r["jetons_par_seconde"] for r in ligne["gpu_balayage"].values())
    assert ligne["heures_gpu"] == pytest.approx(estimer(MODELE_MINUSCULE, ligne["gpu"]["jetons_par_seconde"]))
    assert ligne["heures_gpu_max"] == pytest.approx(estimer(MODELE_MINUSCULE, ligne["gpu_max"]["jetons_par_seconde"]))
    assert ligne["jetons_en_10_h_gpu"] == pytest.approx(ligne["gpu"]["jetons_par_seconde"] * 36000)
    # La limite posée pour la recherche (mémoire libre moins 1 Go) est levée à la fin : on peut de
    # nouveau prendre presque toute la mémoire libre d'un coup (elle serait refusée sous la limite).
    libre = torch.cuda.mem_get_info()[0]
    gros = torch.empty(libre - 512 * 1024**2, dtype=torch.uint8, device="cuda")
    assert gros.numel() > 0
    del gros
    torch.cuda.empty_cache()
