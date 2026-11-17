"""Tests du registre des méthodes d'entraînement (plan 7, tâche 6) et des réglages qui vont avec.

Le pré-entraînement passe désormais par le registre (`forge.entrainement.methodes`) : ces tests
vérifient qu'il n'a pas bougé (mêmes pertes qu'avant la tâche, ancienne sauvegarde reprise), et
que la configuration connaît `methode`, `depart` et `longueur`. Tout tourne sur le processeur,
avec le modèle minuscule de `test_entrainement`.
"""

import argparse
import dataclasses

import pytest
import torch

from test_entrainement import RACINE_DU_PROJET, config_test, ecrire_config_toml

from forge.__main__ import construire_parseur, main
from forge.entrainement import (
    METHODES,
    ConfigEntrainement,
    Methode,
    charger_derniere,
    enregistrer_methode,
    entrainer,
)
from forge.entrainement import boucle
from forge.entrainement.sauvegarde import nom_etape

# Les pertes des 12 premiers pas de `config_test`, relevées avec le code d'AVANT la tâche 6 (le
# pré-entraînement ne passait pas encore par le registre). Le pré-entraînement ne doit pas changer.
PERTES_D_AVANT = [
    4.880496978759766,
    4.832585334777832,
    4.800534248352051,
    4.6804962158203125,
    4.715790748596191,
    4.576905727386475,
    4.431995391845703,
    4.506043434143066,
    4.411639213562012,
    4.283843994140625,
    4.124358177185059,
    4.214241027832031,
]
MEILLEURE_PERTE_VAL_D_AVANT = 4.875699996948242

# Ce que la tâche 6 ajoute aux sauvegardes : une ancienne sauvegarde ne l'a pas.
NOUVEAUX_REGLAGES = ("methode", "depart", "longueur", "dpo", "grpo")
NOUVELLES_CLES = ("methode", "depart_version", "depart_empreinte")


def test_le_registre_a_le_pre_entrainement_et_le_sft():
    assert {"pre_entrainement", "sft"} <= METHODES.keys()
    for nom, methode in METHODES.items():
        assert isinstance(methode, Methode) and methode.nom == nom
    assert not METHODES["pre_entrainement"].plus_grand_est_meilleur
    assert not METHODES["sft"].plus_grand_est_meilleur


def test_enregistrer_une_methode(monkeypatch):
    registre = dict(METHODES)  # le registre du test : le vrai est rendu tel quel après
    monkeypatch.setattr("forge.entrainement.methodes.METHODES", registre)
    base = METHODES["pre_entrainement"]
    essai = dataclasses.replace(base, nom="essai")
    enregistrer_methode(essai)
    assert registre["essai"] is essai and "essai" not in METHODES
    with pytest.raises(ValueError, match="déjà"):
        enregistrer_methode(essai)
    with pytest.raises(ValueError, match="déjà"):
        enregistrer_methode(base)


def test_le_pre_entrainement_n_a_pas_bouge(tmp_path):
    r = entrainer(config_test(tmp_path), arreter_apres=12)
    assert r["pertes"] == pytest.approx(PERTES_D_AVANT, rel=1e-6, abs=1e-6)
    assert r["meilleure_perte_val"] == pytest.approx(MEILLEURE_PERTE_VAL_D_AVANT, rel=1e-6, abs=1e-6)
    etat = charger_derniere(tmp_path / "sauvegardes")
    assert etat["methode"] == "pre_entrainement" and etat["config"]["methode"] == "pre_entrainement"
    assert etat["depart_version"] is None and etat["depart_empreinte"] is None


def test_une_ancienne_sauvegarde_de_pre_entrainement_se_reprend(tmp_path):
    """Une sauvegarde d'avant la tâche 6 (sans `methode` ni `depart`) se relit et se reprend comme avant."""
    a = entrainer(config_test(tmp_path / "a"), arreter_apres=8)["pertes"]
    entrainer(config_test(tmp_path / "b"), arreter_apres=4)
    chemin = tmp_path / "b" / "sauvegardes" / nom_etape(4)
    etat = torch.load(chemin, weights_only=True)
    for cle in NOUVELLES_CLES:
        del etat[cle]
    for reglage in NOUVEAUX_REGLAGES:
        del etat["config"][reglage]
    torch.save(etat, chemin)
    b = entrainer(config_test(tmp_path / "b"), reprendre=True, arreter_apres=8)["pertes"]
    assert a[4:8] == b  # au bit près sur le processeur


def test_methode_inconnue(tmp_path):
    with pytest.raises(ValueError, match="pre_entrainement") as erreur:
        config_test(tmp_path, methode="rlhf")
    assert "rlhf" in str(erreur.value) and "sft" in str(erreur.value)


def test_depart_obligatoire_ou_interdit(tmp_path):
    with pytest.raises(ValueError, match="depart"):
        config_test(tmp_path, methode="sft")
    with pytest.raises(ValueError, match="depart"):
        config_test(tmp_path, depart="ton-ia-1.5")  # pré-entraînement : on part de zéro
    assert config_test(tmp_path, methode="sft", depart="ton-ia-1.5").depart == "ton-ia-1.5"


def test_le_dossier_des_donnees_et_du_depart_selon_la_methode(monkeypatch, tmp_path):
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    valeurs = dict(
        preset="mini",
        jetons_total=1024,
        taille_lot_jetons=512,
        micro_lot=1,
        taux_max=1e-3,
        echauffement=0,
        evaluation_tous_pas=1,
        sortie="essai",
        donnees="court",
    )
    pre = ConfigEntrainement(**valeurs)
    assert pre.dossier_donnees == tmp_path / "jetons" / "court" and pre.dossier_depart is None
    sft = ConfigEntrainement(**valeurs, methode="sft", depart="ton-ia-1.5")
    assert sft.dossier_donnees == tmp_path / "affinage" / "court"
    assert sft.dossier_depart == tmp_path / "publications" / "ton-ia-1.5"
    assert ConfigEntrainement(**valeurs, methode="sft", depart=str(tmp_path / "ailleurs")).dossier_depart == tmp_path / "ailleurs"


def test_le_depart_est_un_reglage_libre():
    assert "depart" in boucle.REGLAGES_LIBRES


@pytest.mark.parametrize("reglage", ["jetons_total", "taille_lot_jetons"])
def test_jetons_obligatoires_hors_grpo(tmp_path, reglage):
    with pytest.raises(ValueError, match=reglage):
        config_test(tmp_path, **{reglage: None})


@pytest.mark.parametrize("longueur", [0, 17, 2.5])
def test_longueur_dans_le_contexte(tmp_path, longueur):
    with pytest.raises(ValueError, match="longueur"):
        config_test(tmp_path, longueur=longueur)


def test_longueur_plus_courte_que_le_contexte(tmp_path):
    """`longueur` règle la taille des lignes, et le lot doit en être un multiple."""
    config = config_test(tmp_path, longueur=8, taille_lot_jetons=32)
    assert config.longueur_des_rangees == 8 and config.accumulation == 2
    with pytest.raises(ValueError, match="micro_lot"):
        config_test(tmp_path, longueur=8, taille_lot_jetons=40)
    assert config_test(tmp_path).longueur_des_rangees == 16  # par défaut, le contexte du modèle


@pytest.mark.parametrize("table", ["dpo", "grpo"])
def test_table_d_une_autre_methode_refusee(tmp_path, table):
    with pytest.raises(ValueError, match=table):
        config_test(tmp_path, methode="sft", depart="ton-ia-1.5", **{table: {"beta": 0.1}})


def test_lire_config_connait_les_nouveaux_reglages(tmp_path):
    fichier = ecrire_config_toml(tmp_path)
    texte = fichier.read_text(encoding="utf-8").replace("[preset]", 'methode = "sft"\n[preset]')
    fichier.write_text(texte, encoding="utf-8")
    with pytest.raises(ValueError, match="depart"):
        boucle.lire_config(fichier)


def test_commande_entrainer_arreter_apres(tmp_path, capsys):
    fichier = ecrire_config_toml(tmp_path)  # 6 pas en tout
    assert main(["entrainer", "--config", str(fichier), "--arreter-apres", "2"]) == 0
    assert charger_derniere(tmp_path / "sortie" / "sauvegardes")["pas"] == 2
    assert "Arrêt demandé au pas 2" in capsys.readouterr().out
    assert main(["entrainer", "--config", str(fichier), "--reprendre", "--arreter-apres", "4"]) == 0
    assert charger_derniere(tmp_path / "sortie" / "sauvegardes")["pas"] == 4
    assert main(["entrainer", "--config", str(fichier), "--reprendre"]) == 0
    assert charger_derniere(tmp_path / "sortie" / "sauvegardes")["pas"] == 6


def test_commande_entrainer_arreter_apres_illisible(tmp_path, capsys):
    fichier = ecrire_config_toml(tmp_path)
    with pytest.raises(SystemExit) as sortie:
        main(["entrainer", "--config", str(fichier), "--arreter-apres", "deux"])
    assert sortie.value.code == 2 and "deux" in capsys.readouterr().err


def test_aide_de_entrainer():
    sous_commandes = next(a for a in construire_parseur()._actions if isinstance(a, argparse._SubParsersAction))
    aide = sous_commandes.choices["entrainer"].format_help()
    assert "--arreter-apres" in aide and "--reprendre" in aide


def test_le_readme_explique_l_affinage():
    readme = (RACINE_DU_PROJET / "README.md").read_text(encoding="utf-8")
    debut = readme.index("## Affiner ton IA")
    section = readme[debut : readme.index("\n## ", debut + 1)]
    for mot in ("methode", "depart", "--reprendre", "--arreter-apres", "publications", "affinage"):
        assert mot in section, mot
