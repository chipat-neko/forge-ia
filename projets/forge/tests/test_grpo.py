"""Tests du mini-GRPO (plan 7, tâche 16) : les avantages, le pas, le contrôle de départ, la validation, la pause et
la reprise.

Tout tourne sur le processeur, sauf le test marqué `gpu`. Le modèle a le vocabulaire du tokenizer de ton IA (les
invites sont de vrais énoncés encodés) mais il est minuscule (dim 16, une couche, contexte 128) et tiré au hasard :
il n'écrit jamais une réponse juste. Les tests qui ont besoin d'un signal remplacent donc la récompense par la parité
du premier jeton écrit (`recompense_par_parite`) ; le contrôle de départ d'un modèle sans récompense, lui, garde la
vraie. Les problèmes sont écrits par `forge problemes`, comme pour ton IA 1.9 (graines du RL, difficultés 1 et 2).
"""

import dataclasses
import json
import math
import re
import signal
import subprocess
import sys
from pathlib import Path

import pytest
import torch
import torch.nn.functional as F
from torch import tensor

from test_entrainement import lire_journal
from test_sft import CPU, TOK, gradients, publier

from forge.__main__ import construire_parseur, main
from forge.affinage.jeu import IGNORE
from forge.conversation.format import Reponse
from forge.entrainement import METHODES, ConfigEntrainement, charger_derniere, entrainer, lire_config
from forge.entrainement import boucle
from forge.entrainement.boucle import ReglagesGRPO
from forge.erreurs import DonneesManquantes
from forge.hasard import Hasard
from forge.modele import ConfigModele, Transformer
from forge.publication import charger_publication
from forge.raisonnement import grpo
from forge.raisonnement.grpo import ChargeurInvites, Tirage, avantages, rangees
from forge.raisonnement.problemes import (
    GRAINES_RL,
    GRAINES_VALIDATION_RL,
    PRENOMS_ENTRAINEMENT,
    PRENOMS_VALIDATION_RL,
    generer_problemes,
)

FINE = "\u202f"  # l'espace fine insécable des sorties à l'écran
MODELE_GRPO = ConfigModele(taille_vocabulaire=TOK.taille_vocabulaire, dim=16, couches=1, tetes=2, longueur_contexte=128)
ARRET = TOK.id_special("<|fin_tour|>")
BOURRAGE = TOK.id_special("<|bourrage|>")
ETIQUETTE = "ton-ia-essai-grpo"
MESURES = ("recompense_moyenne", "groupes_sans_signal", "longueur_moyenne", "secondes_generation", "secondes_apprentissage")

# Un GRPO minuscule : 6 pas de 2 problèmes × 4 réponses de 6 jetons au plus, générées 4 par 4 ; un contrôle de
# 3 problèmes × 2 tirages ; une validation sur 4 problèmes.
REGLAGES = dict(
    pas=6,
    invites_par_pas=2,
    reponses_par_invite=4,
    jetons_max_reponse=6,
    lot_de_generation=4,
    controle_invites=3,
    controle_reponses=2,
    evaluation_invites=4,
)


# --- Les données, la configuration et la récompense ---------------------------------------------


def ecrire_problemes(dossier: Path, nombre: int = 40, graine: int = GRAINES_RL, difficultes: str = "1,2") -> Path:
    """Des problèmes écrits par `forge problemes`, comme ceux de ton IA 1.9 (rien si c'est déjà fait)."""
    if not (dossier / ".complet").exists():
        arguments = ["problemes", "--sortie", str(dossier), "--nombre", str(nombre), "--graine-depart", str(graine)]
        assert main([*arguments, "--difficultes", difficultes]) == 0
    return dossier


def cfg_grpo(dossier: Path, grpo_: dict | None = None, **changements) -> ConfigEntrainement:
    """Le GRPO minuscule de `REGLAGES` ; la version de départ et les problèmes sont rangés dans `commun/`."""
    commun = dossier.parent / "commun"
    valeurs = dict(
        methode="grpo",
        depart=str(publier(commun / ETIQUETTE, MODELE_GRPO, etiquette=ETIQUETTE)),
        preset=MODELE_GRPO,
        donnees=str(ecrire_problemes(commun / "rl")),
        micro_lot=3,
        taux_max=1e-2,
        echauffement=1,
        poids_decroissance=0.0,
        evaluation_tous_pas=3,
        appareil="cpu",
        compiler="non",
        sortie=str(dossier),
        grpo={**REGLAGES, **(grpo_ or {})},
    )
    valeurs.update(changements)
    return ConfigEntrainement(**valeurs)


def ecrire_toml(config: ConfigEntrainement, fichier: Path) -> Path:
    """La configuration `config` (celle de `cfg_grpo`) en TOML, comme `forge entrainer --config` la lit."""
    m = config.modele
    lignes = [
        'methode = "grpo"',
        f"depart = '{config.depart}'",
        f"donnees = '{config.donnees}'",
        f"sortie = '{config.sortie}'",
        f"micro_lot = {config.micro_lot}",
        f"taux_max = {config.taux_max}",
        f"echauffement = {config.echauffement}",
        f"poids_decroissance = {config.poids_decroissance}",
        f"evaluation_tous_pas = {config.evaluation_tous_pas}",
        'appareil = "cpu"',
        'compiler = "non"',
        "[preset]",
        f"taille_vocabulaire = {m.taille_vocabulaire}",
        f"dim = {m.dim}",
        f"couches = {m.couches}",
        f"tetes = {m.tetes}",
        f"longueur_contexte = {m.longueur_contexte}",
        "[grpo]",
        *(f"{nom} = {valeur}" for nom, valeur in dataclasses.asdict(config.grpo).items()),
        "",
    ]
    fichier.write_text("\n".join(lignes), encoding="utf-8")
    return fichier


@pytest.fixture
def recompense_par_parite(monkeypatch):
    """La récompense vaut 1 quand le premier jeton écrit est pair : un modèle tiré au hasard a alors un signal."""

    def recompense(reponse: Reponse, probleme) -> float:
        return 1.0 if reponse.ids and reponse.ids[0] % 2 == 0 else 0.0

    monkeypatch.setattr(grpo, "recompense", recompense)


def lignes_de_pas(dossier: Path) -> list[dict]:
    return [ligne for ligne in lire_journal(dossier) if "perte" in ligne and "evenement" not in ligne]


def lire_controle(dossier: Path) -> dict:
    return json.loads((dossier / "controle.json").read_text(encoding="utf-8"))


def tirage_de(recompenses: list[list[float]], graine: int = 0, apres_l_arret: list[int] = ()) -> Tirage:
    """Un tirage fait à la main : des problèmes du RL, des réponses de 1 à 4 jetons tirés au hasard puis `<|fin_tour|>`.

    `apres_l_arret` est ajouté après le `<|fin_tour|>` de chaque réponse (ce que la génération ne rend jamais).
    """
    problemes = generer_problemes(len(recompenses), GRAINES_RL)
    hasard = torch.Generator().manual_seed(graine)
    sorties = []
    for _ in range(len(recompenses) * len(recompenses[0])):
        n = int(torch.randint(1, 5, (1,), generator=hasard))
        sorties.append([*torch.randint(300, 30_000, (n,), generator=hasard).tolist(), ARRET, *apres_l_arret])
    return Tirage(
        invites=[grpo.invite_du_probleme(TOK, p) for p in problemes],
        sorties=sorties,
        recompenses=tensor(recompenses),
        arret=ARRET,
        bourrage=BOURRAGE,
    )


def modele_neuf(graine: int = 0) -> Transformer:
    torch.manual_seed(graine)
    return Transformer(MODELE_GRPO)


# --------------------------------------------------------------------------------------
# Les tests du plan
# --------------------------------------------------------------------------------------


def test_avantages():
    assert avantages(tensor([[1., 0., 0., 1.], [0., 0., 0., 0.]])).tolist() == [[.5, -.5, -.5, .5], [0., 0., 0., 0.]]


def test_groupe_sans_signal_sans_gradient():
    """Des récompenses toutes égales dans chaque groupe : avantages nuls, perte nulle, aucun gradient."""
    modele = modele_neuf()
    tirage = tirage_de([[1., 1., 1.], [0., 0., 0.]])
    perte = grpo.apprendre(modele, tirage, avantages(tirage.recompenses), 2, CPU)
    assert perte.item() == 0
    assert all(p.grad is None or not p.grad.any() for p in modele.parameters())

    # À côté d'un groupe qui a un signal, un groupe sans signal n'ajoute rien : le gradient est celui de la formule,
    # −Σ A · log π(jeton) sur les jetons générés des seules réponses du premier groupe, divisée par TOUS les jetons
    # générés du pas (ceux du second groupe comptent dans le diviseur).
    melange = tirage_de([[1., 0., 0.], [1., 1., 1.]], graine=1)
    a = avantages(melange.recompenses)
    modele = modele_neuf()
    perte = grpo.apprendre(modele, melange, a, 2, CPU)
    temoin = modele_neuf()
    total = sum(len(s) for s in melange.sorties)  # chaque réponse finit à son <|fin_tour|>
    attendue = torch.zeros(())
    for k in range(3):
        rangee = melange.invites[0] + melange.sorties[k]
        logits, _ = temoin(tensor([rangee[:-1]]))
        log_probas = F.log_softmax(logits[0].float(), dim=-1)
        debut = len(melange.invites[0])
        logp = sum(log_probas[j - 1, rangee[j]] for j in range(debut, len(rangee)))
        attendue = attendue - a[0, k] * logp / total
    attendue.backward()
    assert perte.item() == pytest.approx(attendue.item(), rel=1e-5, abs=1e-8)
    attendus = gradients(temoin)
    for nom, gradient in gradients(modele).items():
        torch.testing.assert_close(gradient, attendus[nom], rtol=1e-4, atol=1e-7)


def test_grpo_reprise_exacte(tmp_path, monkeypatch, recompense_par_parite):
    """6 pas d'une traite, ou une pause (Ctrl+C) au pas 3 puis la reprise : les mêmes pas, au bit près."""
    reference = entrainer(cfg_grpo(tmp_path / "ref"))
    assert len(reference["pertes"]) == 6 and any(p != 0 for p in reference["pertes"])
    methode = METHODES["grpo"]
    faits = []

    def pas_puis_ctrl_c(*arguments, **options):
        resultat = methode.pas(*arguments, **options)
        faits.append(resultat)
        if len(faits) == 3:
            signal.raise_signal(signal.SIGINT)  # comme Ctrl+C au milieu du pas 3
        return resultat

    monkeypatch.setitem(METHODES, "grpo", dataclasses.replace(methode, pas=pas_puis_ctrl_c))
    config = cfg_grpo(tmp_path / "pause", fichier="configs/grpo-essai.toml")
    r = entrainer(config)
    assert r["en_pause"] and r["pas"] == 3
    monkeypatch.setitem(METHODES, "grpo", methode)
    suite = entrainer(config, reprendre=True)
    assert suite["pas"] == 6 and reference["pertes"][3:] == suite["pertes"]  # au bit près sur le processeur
    poids_a = charger_derniere(tmp_path / "ref" / "sauvegardes")["modele"]
    poids_b = charger_derniere(tmp_path / "pause" / "sauvegardes")["modele"]
    assert all(torch.equal(poids_a[nom], poids_b[nom]) for nom in poids_a)
    # Le journal repris a les mêmes tirages et la même validation que celui d'une traite.
    for cle in ("recompense_moyenne", "groupes_sans_signal", "longueur_moyenne", "reussite_val"):
        assert [l.get(cle) for l in lignes_de_pas(tmp_path / "ref")] == [l.get(cle) for l in lignes_de_pas(tmp_path / "pause")]
    # La reprise ne refait pas le contrôle de départ.
    assert [l["evenement"] for l in lire_journal(tmp_path / "pause") if l.get("evenement") == "controle"] == ["controle"]


def test_recompense_nulle(tmp_path, capsys):
    """Aucune réponse juste au contrôle : code 6, la ligne de journal, controle.json, et aucune sauvegarde."""
    config = cfg_grpo(tmp_path / "grpo")
    with pytest.raises(SystemExit) as sortie:
        entrainer(config)
    assert sortie.value.code == boucle.CODE_RECOMPENSE_NULLE == 6
    erreur = capsys.readouterr().err
    assert f"Aucune des 6 réponses n'est juste{FINE}: le RL n'aurait aucun signal. Rien n'est lancé." in erreur
    assert str(tmp_path / "grpo" / "controle.json") in erreur
    controle = lire_controle(tmp_path / "grpo")
    assert {"invites": 3, "reponses": 6, "justes": 0, "taux": 0.0, "lance": False}.items() <= controle.items()
    assert controle["depart"] == ETIQUETTE
    assert lire_journal(tmp_path / "grpo") == [{"evenement": "recompense_nulle", "controle": controle, "pas": 0}]
    assert not (tmp_path / "grpo" / "sauvegardes").exists()


def test_recompense_nulle_en_ligne_de_commande(tmp_path, capsys):
    """`forge entrainer` sort avec le code 6, sans trace d'erreur Python."""
    fichier = ecrire_toml(cfg_grpo(tmp_path / "grpo"), tmp_path / "grpo.toml")
    with pytest.raises(SystemExit) as sortie:
        main(["entrainer", "--config", str(fichier)])
    assert sortie.value.code == 6
    erreur = capsys.readouterr().err
    assert "Rien n'est lancé." in erreur and "Traceback" not in erreur


def test_controle_seul(tmp_path, recompense_par_parite, capsys):
    """`--arreter-apres 0` : le contrôle de départ seul, écrit dans controle.json ; aucun pas, aucune sauvegarde."""
    fichier = ecrire_toml(cfg_grpo(tmp_path / "grpo"), tmp_path / "grpo.toml")
    assert main(["entrainer", "--config", str(fichier), "--arreter-apres", "0"]) == 0
    controle = lire_controle(tmp_path / "grpo")
    assert {"invites", "reponses", "justes", "taux", "lance"} <= controle.keys()  # ce que lit le projet 1.9
    assert controle["invites"] == 3 and controle["reponses"] == 6 and controle["lance"] is True
    assert 0 < controle["justes"] <= 6 and controle["taux"] == controle["justes"] / 6
    lignes = lire_journal(tmp_path / "grpo")
    assert [l.get("evenement") for l in lignes] == ["debut", "controle"]
    assert lignes[1]["controle"] == controle
    assert not lignes_de_pas(tmp_path / "grpo")
    assert not (tmp_path / "grpo" / "sauvegardes").exists()
    sortie = capsys.readouterr().out
    assert f"Contrôle de départ{FINE}: {controle['justes']} réponses justes sur 6" in sortie
    assert f"Arrêt demandé (--arreter-apres 0){FINE}: aucun pas fait, rien n'est sauvegardé." in sortie


def test_jetons_apres_l_arret_hors_perte():
    """Seuls les jetons générés jusqu'au premier <|fin_tour|> compris comptent ; l'invite et ce qui suit, non."""
    ids, cibles = rangees([[1, 2, 3], [4, 5]], [[10, 11, ARRET, 12, 13], [20]], ARRET, BOURRAGE)
    assert ids.tolist() == [[1, 2, 3, 10, 11], [4, 5, BOURRAGE, BOURRAGE, BOURRAGE]]
    assert cibles.tolist() == [[IGNORE, IGNORE, 10, 11, ARRET], [IGNORE, 20, IGNORE, IGNORE, IGNORE]]
    assert grpo.longueur_generee([10, 11, ARRET, 12, 13], ARRET) == 3 and grpo.longueur_generee([20], ARRET) == 1

    # De bout en bout : ce qui suit l'arrêt ne change ni la perte, ni ses gradients, ni le diviseur.
    sans, avec = tirage_de([[1., 0.]]), tirage_de([[1., 0.]], apres_l_arret=[777, 888, 999])
    modele_a, modele_b = modele_neuf(), modele_neuf()
    perte_a = grpo.apprendre(modele_a, sans, avantages(sans.recompenses), 2, CPU)
    perte_b = grpo.apprendre(modele_b, avec, avantages(avec.recompenses), 2, CPU)
    assert perte_a.item() == perte_b.item() != 0
    attendus = gradients(modele_a)
    for nom, gradient in gradients(modele_b).items():
        assert torch.equal(gradient, attendus[nom])


def test_grpo_refuse_jetons_total():
    valeurs = dict(
        methode="grpo", depart="ton-ia-1.9-traces", preset=MODELE_GRPO, donnees="rl-1.9", micro_lot=1,
        taux_max=1e-6, echauffement=0, evaluation_tous_pas=1, sortie="essai", grpo={"pas": 10},
    )
    assert ConfigEntrainement(**valeurs).pas_total == 10
    for reglage in ("jetons_total", "taille_lot_jetons"):
        with pytest.raises(ValueError, match=r"nombre de pas vient de \[grpo\] pas") as erreur:
            ConfigEntrainement(**valeurs, **{reglage: 4096})
        assert reglage in str(erreur.value)


# --------------------------------------------------------------------------------------
# Le pas : tirages, graines, journal
# --------------------------------------------------------------------------------------


def test_la_recompense_est_la_justesse():
    p = generer_problemes(1, GRAINES_RL)[0]
    juste = Reponse(texte=f"La réponse est {p.reponse}.", pensee="\n".join(p.etapes), ids=[1, 2], terminee=True)
    assert grpo.recompense(juste, p) == 1.0
    assert grpo.recompense(dataclasses.replace(juste, terminee=False), p) == 0.0  # coupée : jamais juste
    assert grpo.recompense(dataclasses.replace(juste, texte=f"La réponse est {p.reponse + 1}."), p) == 0.0
    # Seul le texte compte, pas la pensée.
    assert grpo.recompense(Reponse(texte="Je ne sais pas.", pensee=str(p.reponse), ids=[1], terminee=True), p) == 0.0


def test_la_graine_et_les_invites_de_chaque_pas(tmp_path, monkeypatch, recompense_par_parite):
    """Pas n : `generer_lot` des invites répétées, graine (graine × 1 000 003 + n) mod 2³², arrêt <|fin_tour|>."""
    assert grpo.graine_du_pas(1234, 7) == 1234 * 1_000_003 + 7
    assert grpo.graine_du_pas(2**32 - 1, 5) == ((2**32 - 1) * 1_000_003 + 5) % 2**32
    vraie = grpo.generer_lot
    appels = []

    def espion(modele, invites, n_nouveaux, temperature, top_k, graine, arret, lot):
        appels.append(dict(invites=invites, n=n_nouveaux, temperature=temperature, top_k=top_k, graine=graine, arret=arret, lot=lot))
        return vraie(modele, invites, n_nouveaux, temperature, top_k, graine, arret, lot)

    monkeypatch.setattr(grpo, "generer_lot", espion)
    config = cfg_grpo(tmp_path / "grpo", evaluation_tous_pas=100, grpo_={"pas": 2})
    entrainer(config)
    # Le contrôle : 3 problèmes × 2 tirages, par paquets de 2 problèmes (4 réponses, lot_de_generation), chacun
    # avec sa graine, tirée de la graine du « pas 0 ».
    hasard = Hasard(grpo.graine_du_pas(config.graine, 0))
    assert [a["graine"] for a in appels[:2]] == [hasard.suivant32(), hasard.suivant32()]
    assert [len(a["invites"]) for a in appels[:2]] == [4, 2]
    controle, pas, validation = appels[:2], appels[2:4], appels[4:]
    assert [a["graine"] for a in pas] == [grpo.graine_du_pas(config.graine, 1), grpo.graine_du_pas(config.graine, 2)]
    for appel in controle + pas:
        assert (appel["n"], appel["temperature"], appel["top_k"], appel["arret"], appel["lot"]) == (6, 1.0, 50, ARRET, 4)
    for appel in pas:
        invites = appel["invites"]
        assert len(invites) == 8 and invites[0] == invites[3] != invites[4] == invites[7]  # chaque invite 4 fois, à la suite
    # La validation (au dernier pas) : glouton, une réponse par problème.
    (val,) = validation
    assert val["temperature"] == 0 and len(val["invites"]) == 4 and val["n"] == 6


def test_le_journal_du_grpo(tmp_path, recompense_par_parite):
    r = entrainer(cfg_grpo(tmp_path / "grpo"))
    pas = lignes_de_pas(tmp_path / "grpo")
    assert [l["pas"] for l in pas] == list(range(1, 7))
    for ligne in pas:
        assert all(isinstance(ligne[nom], float) and math.isfinite(ligne[nom]) for nom in MESURES)
        assert 0 <= ligne["recompense_moyenne"] <= 1 and ligne["groupes_sans_signal"] in (0.0, 0.5, 1.0)
        assert 1 <= ligne["longueur_moyenne"] <= 6
        assert "jetons_vus" not in ligne and "jetons_par_seconde" not in ligne  # les pas n'ont pas tous les mêmes jetons
    validations = [l for l in pas if "reussite_val" in l]
    assert [l["pas"] for l in validations] == [3, 6] and all(0 <= l["reussite_val"] <= 1 for l in validations)
    assert r["meilleure_perte_val"] == max(l["reussite_val"] for l in validations)  # la plus HAUTE réussite
    meilleur = torch.load(tmp_path / "grpo" / "sauvegardes" / "meilleur.pt", weights_only=True)
    assert meilleur["reussite_val"] == r["meilleure_perte_val"] and meilleur["methode"] == "grpo"
    assert charger_derniere(tmp_path / "grpo" / "sauvegardes")["jetons_vus"] is None


def test_un_pas_sans_aucun_signal_ne_bouge_pas_les_poids(tmp_path, monkeypatch):
    """Récompenses toutes égales : le pas est écrit au journal (groupes_sans_signal = 1), les poids ne bougent pas."""
    monkeypatch.setattr(grpo, "recompense", lambda reponse, probleme: 1.0)
    entrainer(cfg_grpo(tmp_path / "grpo", evaluation_tous_pas=100, grpo_={"pas": 2}))
    lignes = lignes_de_pas(tmp_path / "grpo")
    assert len(lignes) == 2
    for ligne in lignes:
        assert ligne["groupes_sans_signal"] == 1.0 and ligne["perte"] == 0.0 and ligne["recompense_moyenne"] == 1.0
    depart = charger_publication(tmp_path / "commun" / ETIQUETTE).modele.state_dict()
    apres = charger_derniere(tmp_path / "grpo" / "sauvegardes")["modele"]
    assert all(torch.equal(apres[nom], depart[nom]) for nom in depart)


def test_reprise_exacte_a_travers_des_pas_sans_signal(tmp_path, monkeypatch, recompense_par_parite):
    """Les pas 1 et 4 sans aucun signal (aucune mise à jour) : trois sessions, pas 1 | 2 à 4 | 5 et 6, donnent au bit
    près les pertes, les poids et l'état d'AdamW d'une traite, dont le compteur ne compte que les vraies mises à jour."""
    vraie = grpo.tirer
    sans_signal = {grpo.graine_du_pas(1234, 1), grpo.graine_du_pas(1234, 4)}

    def tirer(modele, tok, problemes, n_reponses, graine, reglages, **options):
        tirage = vraie(modele, tok, problemes, n_reponses, graine, reglages, **options)
        if graine in sans_signal:  # toutes les réponses du pas ont la même récompense
            return dataclasses.replace(tirage, recompenses=torch.ones_like(tirage.recompenses))
        return tirage

    monkeypatch.setattr(grpo, "tirer", tirer)
    traite = entrainer(cfg_grpo(tmp_path / "traite"))["pertes"]
    assert traite[0] == traite[3] == 0.0 and all(traite[k] != 0 for k in (1, 2, 4, 5))
    config = cfg_grpo(tmp_path / "sessions")
    assert config.graine == 1234
    sessions = entrainer(config, arreter_apres=1)["pertes"]
    sessions += entrainer(config, reprendre=True, arreter_apres=4)["pertes"]
    sessions += entrainer(config, reprendre=True)["pertes"]
    assert sessions == traite
    a = charger_derniere(tmp_path / "traite" / "sauvegardes")
    b = charger_derniere(tmp_path / "sessions" / "sauvegardes")
    assert all(torch.equal(a["modele"][nom], b["modele"][nom]) for nom in a["modele"])
    etats_a, etats_b = a["optimiseur"]["state"], b["optimiseur"]["state"]
    assert etats_a.keys() == etats_b.keys()
    for numero, etat in etats_a.items():
        assert all(torch.equal(etat[cle], etats_b[numero][cle]) for cle in etat)
        assert etat["step"].item() == 4  # 6 pas de la boucle, dont 2 sans mise à jour
    assert [l["groupes_sans_signal"] for l in lignes_de_pas(tmp_path / "sessions")] == [
        l["groupes_sans_signal"] for l in lignes_de_pas(tmp_path / "traite")
    ]


# --------------------------------------------------------------------------------------
# Le contrôle de départ
# --------------------------------------------------------------------------------------


def test_ctrl_c_pendant_le_controle(tmp_path, monkeypatch, capsys, recompense_par_parite):
    """Ctrl+C pendant le contrôle : une pause propre (code 0), aucun controle.json (ni l'ancien), rien de sauvegardé."""
    fichier = ecrire_toml(cfg_grpo(tmp_path / "grpo"), tmp_path / "grpo.toml")
    (tmp_path / "grpo").mkdir()
    (tmp_path / "grpo" / "controle.json").write_text('{"vieux": true}', encoding="utf-8")  # celui d'un ancien essai
    vraie = grpo.generer_lot
    appels = []

    def generer_puis_ctrl_c(*arguments, **options):
        appels.append(1)
        if len(appels) == 2:
            raise KeyboardInterrupt  # comme Ctrl+C pendant le deuxième paquet du contrôle
        return vraie(*arguments, **options)

    monkeypatch.setattr(grpo, "generer_lot", generer_puis_ctrl_c)
    capsys.readouterr()
    assert main(["entrainer", "--config", str(fichier), "--arreter-apres", "2"]) == 0
    sortie = capsys.readouterr()
    assert sortie.err == ""
    assert (
        f"Pause pendant le contrôle de départ{FINE}: rien n'est sauvegardé, le contrôle sera refait à la reprise. "
        f"Pour reprendre{FINE}: python -m forge entrainer --config {fichier} --reprendre" in sortie.out
    )
    assert not (tmp_path / "grpo" / "controle.json").exists() and not list((tmp_path / "grpo").glob("*.tmp"))
    assert not (tmp_path / "grpo" / "sauvegardes").exists()
    derniere = lire_journal(tmp_path / "grpo")[-1]
    assert derniere["evenement"] == "pause" and derniere["pas"] == 0 and "contrôle" in derniere["message"]

    monkeypatch.setattr(grpo, "generer_lot", vraie)
    suite = entrainer(lire_config(fichier), reprendre=True, arreter_apres=2)
    assert lire_controle(tmp_path / "grpo")["lance"] is True
    assert suite["pertes"] == entrainer(cfg_grpo(tmp_path / "temoin"), arreter_apres=2)["pertes"]


def test_l_avancement_du_controle(tmp_path, monkeypatch, capsys, recompense_par_parite):
    """Une ligne d'avancement au plus toutes les 30 s (aucune pour un contrôle plus court), puis le résultat."""
    entrainer(cfg_grpo(tmp_path / "a"), arreter_apres=0)
    sortie = capsys.readouterr().out
    assert "réponses sur 6" not in sortie
    assert f"Contrôle de départ{FINE}: 3 problèmes × 2 tirages avec {ETIQUETTE}" in sortie
    monkeypatch.setattr(grpo, "SECONDES_ENTRE_PROGRES", 0)  # une ligne après chaque paquet
    entrainer(cfg_grpo(tmp_path / "b"), arreter_apres=0)
    lignes = [l for l in capsys.readouterr().out.splitlines() if "réponses sur 6" in l]
    assert len(lignes) == 1  # deux paquets : une ligne après le premier
    assert lignes[0].startswith(f"Contrôle de départ{FINE}: 4 réponses sur 6 (66,7{FINE}%) · ")
    assert "réponses/s · reste ≈ " in lignes[0]


def test_le_controle_prend_les_premiers_problemes_du_dossier(tmp_path, monkeypatch):
    vus = []
    vraie = grpo.tirer

    def tirer(modele, tok, problemes, n_reponses, graine, reglages, **options):
        vus.extend(p.id for p in problemes)
        return vraie(modele, tok, problemes, n_reponses, graine, reglages, **options)

    monkeypatch.setattr(grpo, "tirer", tirer)
    config = cfg_grpo(tmp_path / "grpo")
    with pytest.raises(SystemExit):
        entrainer(config)
    assert vus == [p.id for p in grpo.lire_problemes(Path(config.donnees))[:3]]


# --------------------------------------------------------------------------------------
# Les problèmes : le chargeur et la validation
# --------------------------------------------------------------------------------------


def test_le_chargeur_d_invites(tmp_path):
    dossier = ecrire_problemes(tmp_path / "rl", nombre=10)
    tous = grpo.lire_problemes(dossier)
    assert [p.id for p in tous] == [p.id for p in generer_problemes(10, GRAINES_RL, difficultes=(1, 2))]
    chargeur = ChargeurInvites(dossier, 4, graine=3)
    epoque = [p.id for _ in range(5) for p in chargeur.lot()]  # 20 problèmes : deux époques
    assert sorted(epoque[:10]) == sorted(p.id for p in tous) == sorted(epoque[10:])
    assert epoque[:10] != epoque[10:]  # mélangées autrement à chaque époque

    a = ChargeurInvites(dossier, 4, graine=3)
    a.lot()
    a.lot()
    a.lot()  # au milieu de la deuxième époque
    b = ChargeurInvites(dossier, 4, graine=3)
    b.restaurer(json.loads(json.dumps(a.etat())))  # l'état passe par une sauvegarde
    assert [[p.id for p in a.lot()] for _ in range(4)] == [[p.id for p in b.lot()] for _ in range(4)]
    with pytest.raises(ValueError, match="graine"):
        ChargeurInvites(dossier, 4, graine=4).restaurer(a.etat())


def test_le_chargeur_refuse_des_problemes_regeneres(tmp_path):
    """Un dossier régénéré avec le même nombre de problèmes, mais d'autres graines : la reprise est refusée."""
    a = ChargeurInvites(ecrire_problemes(tmp_path / "a", nombre=10), 4, graine=0)
    autre = ecrire_problemes(tmp_path / "b", nombre=10, graine=GRAINES_RL + 1000)
    b = ChargeurInvites(autre, 4, graine=0)
    assert len(a.problemes) == len(b.problemes) and a.etat()["empreinte"] != b.etat()["empreinte"]
    with pytest.raises(ValueError, match="n'a plus les problèmes de la sauvegarde") as erreur:
        b.restaurer(a.etat())
    assert "forge problemes" in str(erreur.value) and "sortie" in str(erreur.value)
    b.restaurer(ChargeurInvites(autre, 4, graine=0).etat())  # les mêmes problèmes : accepté


def test_les_problemes_ne_sont_lus_qu_une_fois(tmp_path, monkeypatch, recompense_par_parite):
    """Un entraînement neuf lit les premiers problèmes pour le contrôle, puis tous une fois ; une reprise, une fois."""
    vraie = grpo.lire_elements
    lus = []

    def lire_elements(dossier, prefixe):
        lus.append(0)
        for element in vraie(dossier, prefixe):
            lus[-1] += 1
            yield element

    monkeypatch.setattr(grpo, "lire_elements", lire_elements)
    config = cfg_grpo(tmp_path / "grpo")
    entrainer(config, arreter_apres=1)
    assert lus == [3, 40]  # les 3 problèmes du contrôle, puis les 40 du chargeur
    lus.clear()
    entrainer(config, reprendre=True, arreter_apres=2)
    assert lus == [40]


@pytest.mark.parametrize("graine, usage", [(1_000_000, "evaluation"), (GRAINES_VALIDATION_RL, "validation_rl")])
def test_les_problemes_reserves_ne_servent_jamais_au_rl(tmp_path, graine, usage):
    dossier = ecrire_problemes(tmp_path / usage, nombre=10, graine=graine)
    with pytest.raises(ValueError, match=usage):
        ChargeurInvites(dossier, 4, graine=0)
    with pytest.raises(ValueError, match=usage):
        entrainer(cfg_grpo(tmp_path / "grpo", donnees=str(dossier)))
    assert not (tmp_path / "grpo" / "controle.json").exists()


def test_des_problemes_absents(tmp_path):
    with pytest.raises(DonneesManquantes, match="forge problemes"):
        ChargeurInvites(tmp_path / "absents", 4, graine=0)


def test_la_validation_du_rl(tmp_path):
    """`evaluation_invites` problèmes des graines de la validation du RL, aux difficultés du dossier d'entraînement."""
    dossier = ecrire_problemes(tmp_path / "rl", nombre=10, difficultes="1")
    validation = grpo.problemes_de_validation(dossier, 12)
    assert list(validation.problemes) == generer_problemes(12, GRAINES_VALIDATION_RL, difficultes=(1,))
    assert all(p.difficulte == 1 for p in validation.problemes)
    # Ses prénoms ne sont ni ceux de l'entraînement ni ceux de l'évaluation : aucun énoncé en commun (des mots
    # entiers : « Louis », de l'entraînement, est dans « Louise », de la validation).
    mots = [set(re.findall(r"\w+", p.enonce)) for p in validation.problemes]
    assert all(mots_du_probleme & set(PRENOMS_VALIDATION_RL) for mots_du_probleme in mots)
    assert not any(mots_du_probleme & set(PRENOMS_ENTRAINEMENT) for mots_du_probleme in mots)
    assert validation.etat() == {}


# --------------------------------------------------------------------------------------
# Les réglages [grpo], la reprise, la mémoire
# --------------------------------------------------------------------------------------


def test_les_reglages_grpo():
    assert ReglagesGRPO(pas=400) == ReglagesGRPO(
        pas=400, invites_par_pas=16, reponses_par_invite=16, jetons_max_reponse=256, temperature=1.0, top_k=50,
        lot_de_generation=32, controle_invites=200, controle_reponses=8, evaluation_invites=200,
    )
    valeurs = dict(
        methode="grpo", depart="ton-ia-1.9-traces", preset=MODELE_GRPO, donnees="rl-1.9", micro_lot=1,
        taux_max=1e-6, echauffement=0, evaluation_tous_pas=1, sortie="essai",
    )
    with pytest.raises(ValueError, match=r"\[grpo\]"):
        ConfigEntrainement(**valeurs)  # la table est obligatoire : elle donne le nombre de pas
    with pytest.raises(ValueError, match="pas"):
        ConfigEntrainement(**valeurs, grpo={"invites_par_pas": 8})
    with pytest.raises(ValueError, match="pas, invites_par_pas"):
        ConfigEntrainement(**valeurs, grpo={"pas": 10, "invite_par_pas": 8})
    for mauvais in ({"pas": 0}, {"reponses_par_invite": 1}, {"temperature": 0}, {"lot_de_generation": 0},
                    {"jetons_max_reponse": 2.5}, {"top_k": -1}, {"controle_reponses": True}):
        with pytest.raises(ValueError, match=next(iter(mauvais))):
            ConfigEntrainement(**valeurs, grpo={"pas": 10, **mauvais})
    config = ConfigEntrainement(**valeurs, grpo={"pas": 10, "temperature": 1})
    assert config.grpo.temperature == 1.0 and isinstance(config.grpo.temperature, float) and config.pas_total == 10


def test_reprise_avec_d_autres_reglages_grpo(tmp_path, recompense_par_parite):
    """En reprenant : `lot_de_generation` peut changer (un manque de mémoire) et `pas` augmenter ; rien d'autre."""
    entrainer(cfg_grpo(tmp_path / "grpo"), arreter_apres=2)
    with pytest.raises(ValueError, match="jetons_max_reponse") as erreur:
        entrainer(cfg_grpo(tmp_path / "grpo", grpo_={"jetons_max_reponse": 5}), reprendre=True)
    assert "lot_de_generation" in str(erreur.value)  # le message dit ce qu'on peut changer
    with pytest.raises(ValueError, match="pas"):
        entrainer(cfg_grpo(tmp_path / "grpo", grpo_={"pas": 5}), reprendre=True)
    r = entrainer(cfg_grpo(tmp_path / "grpo", grpo_={"lot_de_generation": 2, "pas": 8}), reprendre=True, arreter_apres=3)
    assert r["pas"] == 3 and r["pas_total"] == 8
    messages = [l["message"] for l in lire_journal(tmp_path / "grpo") if l.get("evenement") == "configuration"]
    assert any("lot_de_generation" in m for m in messages) and any("pas passe de 6 à 8" in m for m in messages)


def test_manque_de_memoire_pendant_la_generation(tmp_path, monkeypatch, capsys):
    def sans_memoire(*arguments, **options):
        raise torch.cuda.OutOfMemoryError("CUDA out of memory")

    monkeypatch.setattr(grpo, "generer_lot", sans_memoire)
    with pytest.raises(SystemExit) as sortie:
        entrainer(cfg_grpo(tmp_path / "grpo"))
    assert sortie.value.code == 2
    erreur = capsys.readouterr().err
    assert "pendant une génération du GRPO" in erreur and "lot_de_generation = 4" in erreur
    assert "Réduis lot_de_generation dans la table [grpo]" in erreur and "--reprendre" in erreur
    assert "Réduis micro_lot" not in erreur


def test_manque_de_memoire_pendant_l_apprentissage(tmp_path, monkeypatch, capsys, recompense_par_parite):
    def sans_memoire(*arguments, **options):
        raise torch.cuda.OutOfMemoryError("CUDA out of memory")

    monkeypatch.setattr(grpo, "perte_de_politique", sans_memoire)
    with pytest.raises(SystemExit) as sortie:
        entrainer(cfg_grpo(tmp_path / "grpo"))
    assert sortie.value.code == 2
    erreur = capsys.readouterr().err
    assert "Réduis micro_lot" in erreur and "lot_de_generation" not in erreur


# --------------------------------------------------------------------------------------
# L'import, l'aide et le README
# --------------------------------------------------------------------------------------


def test_grpo_s_importe_en_premier():
    """« import forge.raisonnement.grpo » seul, dans un interpréteur neuf : pas d'import circulaire.

    grpo.py importe forge.evaluation, qui importe forge.entrainement, donc methodes.py, qui se sert de grpo.py :
    methodes.py importe le module, pas ses noms (comme pour la DPO).
    """
    # Un délai, pour qu'un import bloqué ne bloque pas toute la suite ; pas 2 s : PyTorch seul en prend environ 5.
    resultat = subprocess.run(
        [sys.executable, "-c", "import forge.raisonnement.grpo"], capture_output=True, text=True, timeout=120
    )
    assert resultat.returncode == 0, resultat.stderr


def test_l_aide_de_entrainer_parle_du_grpo():
    from forge import __main__ as principal

    assert principal.CODE_RECOMPENSE_NULLE == boucle.CODE_RECOMPENSE_NULLE  # recopié pour l'aide, sans PyTorch
    sous_commandes = next(a for a in construire_parseur()._actions if a.__class__.__name__ == "_SubParsersAction")
    aide = " ".join(sous_commandes.choices["entrainer"].format_help().split())
    assert f"code {boucle.CODE_RECOMPENSE_NULLE}" in aide and "aucune réponse juste" in aide
    assert "0 : seulement le contrôle de départ du GRPO" in aide


def test_l_exemple_du_readme_se_lit_tel_quel(tmp_path):
    """L'exemple TOML du GRPO du README est une configuration complète, aux valeurs de nanochat."""
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    debut = readme.index('```toml\nmethode = "grpo"') + len("```toml\n")
    fichier = tmp_path / "grpo.toml"
    fichier.write_text(readme[debut : readme.index("```", debut)], encoding="utf-8")
    config = lire_config(fichier)
    assert config.methode == "grpo" and config.jetons_total is None
    assert dataclasses.replace(config.grpo, pas=1) == ReglagesGRPO(pas=1)  # les valeurs par défaut, écrites
    assert config.pas_total == config.grpo.pas
    assert f"code {boucle.CODE_RECOMPENSE_NULLE}" in readme and "controle.json" in readme


@pytest.mark.gpu
def test_grpo_gpu_court(tmp_path, recompense_par_parite):
    """Sur la carte (bf16) : 6 pas, des pertes finies, et la reprise après le pas 3 continue."""
    r = entrainer(cfg_grpo(tmp_path / "grpo", appareil="cuda"), arreter_apres=3)
    assert r["pas"] == 3 and all(math.isfinite(p) for p in r["pertes"])
    suite = entrainer(cfg_grpo(tmp_path / "grpo", appareil="cuda"), reprendre=True)
    assert suite["pas"] == 6 and all(math.isfinite(p) for p in suite["pertes"])
    assert all(0 <= l["recompense_moyenne"] <= 1 for l in lignes_de_pas(tmp_path / "grpo"))
