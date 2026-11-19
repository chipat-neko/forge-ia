"""Tests de la DPO (plan 7, tâche 14) : la formule, la référence précalculée, le pas, la validation,
la pause et la reprise.

Tout tourne sur le processeur, en float32, avec le modèle minuscule de `test_sft` (vocabulaire 128,
dim 32, 2 couches, contexte 16), sauf le test marqué `gpu`. Le jeu `dpo` est écrit par le test, comme
`forge preferences` l'écrit : pour chaque paire, la rangée de la réponse choisie puis celle de la
rejetée, chacune « invite `1 q… 2`, réponse, `3` », perte sur la réponse et son `3`. La choisie est
`q + 50`, la rejetée `q + 20` suivie d'un `99` : elles n'ont pas la même longueur.
"""

import dataclasses
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
import torch.nn.functional as F

from test_entrainement import lire_journal
from test_sft import (
    BOURRAGE,
    CPU,
    ETIQUETTE,
    MODELE_SFT,
    TOK,
    FauxChargeur,
    ecrire_jeu_sft,
    gradients,
    lot_de_bourrage,
    publier,
)

from forge.affinage import dpo
from forge.affinage.dpo import logps_des_rangees, perte_dpo
from forge.affinage.empaquetage import Rangee
from forge.affinage.jeu import IGNORE, ChargeurAffinage, LotAffinage, ecrire_jeu
from forge.entrainement import ConfigEntrainement, charger_derniere, entrainer, lire_config
from forge.entrainement import boucle
from forge.entrainement.boucle import ReglagesDPO
from forge.entrainement.methodes import PAIRES_DE_VALIDATION, mesures_dpo_validation, pas_dpo
from forge.exporter import empreinte_sha256
from forge.modele import Transformer
from forge.publication import charger_publication, nom_des_poids

FINE = "\u202f"  # l'espace fine insécable des sorties à l'écran
MESURES = ("logps_choisie", "logps_rejetee", "recompense_choisie", "recompense_rejetee", "marge", "exactitude")


def t(x: float) -> torch.Tensor:
    """Un tenseur float64 d'un seul élément."""
    return torch.tensor([x], dtype=torch.float64)


def sigmoide(z: float) -> float:
    return 1 / (1 + math.exp(-z))


# --- Le jeu dpo et la configuration ------------------------------------------------------


def rangee(invite: list[int], reponse: list[int]) -> Rangee:
    """L'invite, la réponse et son `3`, puis du bourrage jusqu'à 17 positions ; perte sur la réponse et le `3`."""
    ids = [*invite, *reponse, 3]
    reste = 17 - len(ids)
    return Rangee(
        ids=ids + [BOURRAGE] * reste,
        appris=[False] * len(invite) + [True] * (len(reponse) + 1) + [False] * reste,
        documents=[0] * len(ids) + [-1] * reste,
    )


def paires(nombre: int, graine: int) -> list[Rangee]:
    """`nombre` paires : la choisie `q + 50`, puis la rejetée `q + 20, 99`."""
    hasard = np.random.default_rng(graine)
    rangees = []
    for _ in range(nombre):
        question = hasard.integers(10, 60, size=int(hasard.integers(2, 5))).tolist()
        invite = [1, *question, 2]
        rangees.append(rangee(invite, [j + 50 for j in question]))
        rangees.append(rangee(invite, [*(j + 20 for j in question), 99]))
    return rangees


def ecrire_jeu_dpo(dossier: Path, val: int = 6) -> Path:
    """Un jeu `dpo` de 24 paires d'entraînement et `val` de validation (rien si c'est déjà fait)."""
    if (dossier / ".complet").exists():
        return dossier
    sources = {"essai": {"exemples": 2 * (24 + val), "licence": "CC0", "lien": "https://example.org"}}
    ecrire_jeu(dossier, paires(24, graine=1), paires(val, graine=2), "dpo", {"ecartes": 0, "sources": sources}, TOK)
    return dossier


def cfg_dpo(dossier: Path, **changements) -> ConfigEntrainement:
    """Une DPO minuscule : 4 paires par pas (2 micro-lots de 2 paires, rangées de 16), 20 pas en tout.

    Le jeu et la version de départ sont rangés à côté de `dossier`, dans `commun/` : deux
    entraînements du même `tmp_path` lisent les mêmes (et la même référence).
    """
    commun = dossier.parent / "commun"
    valeurs = dict(
        methode="dpo",
        depart=str(publier(commun / ETIQUETTE)),
        preset=MODELE_SFT,
        donnees=str(ecrire_jeu_dpo(commun / "jeu-dpo")),
        jetons_total=128 * 20,
        taille_lot_jetons=128,
        micro_lot=4,
        taux_max=1e-2,
        echauffement=2,
        poids_decroissance=0.0,
        evaluation_tous_pas=5,
        appareil="cpu",
        compiler="non",
        sortie=str(dossier),
    )
    valeurs.update(changements)
    return ConfigEntrainement(**valeurs)


def cfg_sans_fichiers(**changements) -> ConfigEntrainement:
    """Une configuration de DPO qui ne lit rien sur le disque (pour `pas_dpo` et les réglages)."""
    valeurs = dict(
        methode="dpo",
        depart="inutile",
        preset=MODELE_SFT,
        donnees="inutile",
        jetons_total=64,
        taille_lot_jetons=64,
        micro_lot=2,
        taux_max=1e-2,
        echauffement=0,
        ecretage=1e9,
        evaluation_tous_pas=1,
        appareil="cpu",
        compiler="non",
        sortie="inutile",
    )
    valeurs.update(changements)
    return ConfigEntrainement(**valeurs)


def compter_les_calculs(monkeypatch) -> list[str]:
    """Les parties dont la référence est calculée (et pas relue), dans l'ordre des appels."""
    vraie = dpo.calculer_reference
    parties = []

    def calculer_reference(modele, dossier, partie, taille_lot, appareil, avancer=None):
        parties.append(partie)
        return vraie(modele, dossier, partie, taille_lot, appareil, avancer)

    monkeypatch.setattr(dpo, "calculer_reference", calculer_reference)
    return parties


def lignes_de_pas(dossier: Path) -> list[dict]:
    return [ligne for ligne in lire_journal(dossier) if "perte" in ligne and "evenement" not in ligne]


def marge_sur_l_entrainement(modele: torch.nn.Module, jeu: Path) -> float:
    """La marge moyenne de `modele` sur toutes les paires d'entraînement, d'après `reference.bin`."""
    chargeur = ChargeurAffinage(jeu, "train", 48, graine=0)  # les 24 paires en un lot
    lot = chargeur.lot()
    with torch.no_grad():
        logps, appris = logps_des_rangees(modele, lot, CPU)
        _, mesures = perte_dpo(
            logps[0::2], logps[1::2], lot.reference[0::2], lot.reference[1::2], appris[0::2], appris[1::2], ReglagesDPO()
        )
    return mesures["marge"].item()


def modele_de(etat: dict) -> Transformer:
    modele = Transformer(MODELE_SFT)
    modele.load_state_dict(etat["modele"])
    return modele


# --------------------------------------------------------------------------------------
# Les tests du plan
# --------------------------------------------------------------------------------------


def test_formule_a_la_main():
    perte, m = perte_dpo(t(-10.0), t(-12.0), t(-11.0), t(-11.0), t(5.0), t(6.0), ReglagesDPO(beta=0.1, poids_sft=0.0))
    z = 0.1 * ((-10 + 11) - (-12 + 11))
    assert perte.item() == pytest.approx(-math.log(1 / (1 + math.exp(-z))), abs=1e-12)


def test_au_depart_la_perte_vaut_ln2_plus_sft(tmp_path):
    # La formule : politique = référence, donc z = 0, -log σ(0) = ln 2, plus la NLL par jeton de la choisie.
    perte, m = perte_dpo(t(-10.0), t(-12.0), t(-10.0), t(-12.0), t(5.0), t(6.0), ReglagesDPO())
    assert perte.item() == pytest.approx(math.log(2) + 10 / 5, abs=1e-12)
    assert m["marge"].item() == 0 and m["exactitude"].item() == 0
    # De bout en bout : le premier pas part de la version de départ, qui est aussi la référence.
    entrainer(cfg_dpo(tmp_path / "dpo"), arreter_apres=1)
    (premier,) = lignes_de_pas(tmp_path / "dpo")
    assert premier["logps_choisie"] < 0
    assert premier["perte"] == pytest.approx(math.log(2) - premier["logps_choisie"], abs=1e-4)
    assert abs(premier["marge"]) < 1e-4 and abs(premier["recompense_choisie"]) < 1e-4
    entrainer(cfg_dpo(tmp_path / "sans-sft", dpo={"poids_sft": 0.0}), arreter_apres=1)
    (premier,) = lignes_de_pas(tmp_path / "sans-sft")
    assert premier["perte"] == pytest.approx(math.log(2), abs=1e-4)


def test_normalisation_par_la_longueur():
    # Les gains sont égaux (+1 et +1) : sans normalisation z = 0 ; avec, la choisie (5 jetons) gagne
    # moins par jeton que la rejetée (2 jetons), z < 0.
    arguments = (t(-10.0), t(-12.0), t(-11.0), t(-13.0), t(5.0), t(2.0))
    perte, m = perte_dpo(*arguments, ReglagesDPO(beta=0.1, poids_sft=0.0))
    assert perte.item() == pytest.approx(math.log(2), abs=1e-12)
    perte, m = perte_dpo(*arguments, ReglagesDPO(beta=0.1, normaliser_longueur=True, poids_sft=0.0))
    z = 0.1 * ((-10 + 11) / 5 - (-12 + 13) / 2)
    assert perte.item() == pytest.approx(-math.log(sigmoide(z)), abs=1e-12)
    assert m["exactitude"].item() == 0  # z < 0
    # Les récompenses, elles, ne sont pas normalisées : β (pc − qc).
    assert m["recompense_choisie"].item() == pytest.approx(0.1) and m["recompense_rejetee"].item() == pytest.approx(0.1)
    # Le terme SFT est déjà par jeton : il ne change pas avec la normalisation.
    avec_sft, _ = perte_dpo(*arguments, ReglagesDPO(beta=0.1, normaliser_longueur=True, poids_sft=2.0))
    assert avec_sft.item() == pytest.approx(-math.log(sigmoide(z)) + 2.0 * 10 / 5, abs=1e-12)


def test_la_marge_grandit(tmp_path):
    config = cfg_dpo(tmp_path / "dpo")
    entrainer(config, arreter_apres=20)
    jeu = Path(config.donnees)
    initiale = marge_sur_l_entrainement(charger_publication(Path(config.depart)).modele, jeu)
    finale = marge_sur_l_entrainement(modele_de(charger_derniere(tmp_path / "dpo" / "sauvegardes")), jeu)
    assert abs(initiale) < 1e-4  # la version de départ est la référence
    assert finale > initiale


def test_dpo_reprise_exacte(tmp_path):
    a = entrainer(cfg_dpo(tmp_path / "a"), arreter_apres=12)["pertes"]
    entrainer(cfg_dpo(tmp_path / "b"), arreter_apres=6)
    b = entrainer(cfg_dpo(tmp_path / "b"), reprendre=True, arreter_apres=12)["pertes"]
    assert len(a) == 12 and len(b) == 6
    assert a[6:12] == b  # au bit près sur le processeur
    poids_a = charger_derniere(tmp_path / "a" / "sauvegardes")["modele"]
    poids_b = charger_derniere(tmp_path / "b" / "sauvegardes")["modele"]
    assert poids_a.keys() == poids_b.keys()
    assert all(torch.equal(poids_a[nom], poids_b[nom]) for nom in poids_a)
    # Le journal repris a les mêmes mesures que celui d'une traite.
    assert [l["marge"] for l in lignes_de_pas(tmp_path / "a")] == [l["marge"] for l in lignes_de_pas(tmp_path / "b")]


def test_reference_recalculee_si_le_depart_change(tmp_path, monkeypatch):
    calculs = compter_les_calculs(monkeypatch)
    config = cfg_dpo(tmp_path / "a")
    entrainer(config, arreter_apres=1)
    train = Path(config.donnees) / "train"
    assert calculs == ["train", "val"]
    avant = (train / "reference.bin").read_bytes()
    assert json.loads((train / "reference.json").read_text(encoding="utf-8"))["version"] == ETIQUETTE

    # Le même nom de version, d'autres poids : l'empreinte change, la référence est recalculée.
    memes_nom = publier(tmp_path / "autres-poids" / ETIQUETTE, graine=1)
    entrainer(cfg_dpo(tmp_path / "b", depart=str(memes_nom)), arreter_apres=1)
    assert calculs == ["train", "val"] * 2
    assert (train / "reference.bin").read_bytes() != avant
    description = json.loads((train / "reference.json").read_text(encoding="utf-8"))
    assert description["version"] == ETIQUETTE
    assert description["empreinte_des_poids"] == empreinte_sha256(memes_nom / nom_des_poids(ETIQUETTE))
    (ligne,) = [l for l in lire_journal(tmp_path / "b") if l.get("evenement") == "reference"]
    assert "calculée" in ligne["message"] and ETIQUETTE in ligne["message"] and ligne["pas"] == 0

    # Une autre version.
    autre = publier(tmp_path / "autre", graine=1, etiquette="ton-ia-autre")
    entrainer(cfg_dpo(tmp_path / "c", depart=str(autre)), arreter_apres=1)
    assert calculs == ["train", "val"] * 3
    assert json.loads((train / "reference.json").read_text(encoding="utf-8"))["version"] == "ton-ia-autre"

    # Une référence sans sa description (un calcul interrompu entre les deux écritures) est refaite.
    (train / "reference.json").unlink()
    entrainer(cfg_dpo(tmp_path / "d", depart=str(autre)), arreter_apres=1)
    assert calculs == ["train", "val"] * 3 + ["train"]


def test_reference_relue_si_le_depart_est_le_meme(tmp_path, monkeypatch):
    calculs = compter_les_calculs(monkeypatch)
    entrainer(cfg_dpo(tmp_path / "a"), arreter_apres=2)
    assert calculs == ["train", "val"]
    entrainer(cfg_dpo(tmp_path / "a"), reprendre=True, arreter_apres=4)  # une reprise
    entrainer(cfg_dpo(tmp_path / "b"), arreter_apres=1)  # un autre entraînement, même départ
    copie = tmp_path / "ailleurs"  # la même version, rangée ailleurs
    shutil.copytree(tmp_path / "commun" / ETIQUETTE, copie)
    entrainer(cfg_dpo(tmp_path / "c", depart=str(copie)), arreter_apres=1)
    assert calculs == ["train", "val"]  # aucun recalcul
    for sortie in ("b", "c"):
        (ligne,) = [l for l in lire_journal(tmp_path / sortie) if l.get("evenement") == "reference"]
        assert "relue" in ligne["message"]


def test_reprise_apres_invalidation_de_la_reference(tmp_path, monkeypatch):
    """Une reprise dont la référence a été invalidée la recalcule avec le modèle de départ, pas avec la politique."""
    calculs = compter_les_calculs(monkeypatch)
    config = cfg_dpo(tmp_path / "a")
    entrainer(config, arreter_apres=3)
    train = Path(config.donnees) / "train"
    avant = (train / "reference.bin").read_bytes()
    (train / "reference.json").unlink()
    r = entrainer(cfg_dpo(tmp_path / "a"), reprendre=True, arreter_apres=5)
    assert r["pas"] == 5
    assert calculs == ["train", "val", "train"]
    assert (train / "reference.bin").read_bytes() == avant  # à l'octet près : les poids de départ, pas ceux du pas 3


def test_reference_tronquee_recalculee(tmp_path, monkeypatch):
    """Un `reference.bin` qui n'a pas une valeur par rangée est recalculé, même si sa description est juste."""
    calculs = compter_les_calculs(monkeypatch)
    config = cfg_dpo(tmp_path / "a")
    entrainer(config, arreter_apres=1)
    train = Path(config.donnees) / "train"
    avant = (train / "reference.bin").read_bytes()
    (train / "reference.bin").write_bytes(avant[:-8])
    entrainer(cfg_dpo(tmp_path / "b"), arreter_apres=1)
    assert calculs == ["train", "val", "train"]
    assert (train / "reference.bin").read_bytes() == avant


def test_l_avancement_du_calcul_de_la_reference(tmp_path, monkeypatch, capsys):
    """Une ligne d'avancement au plus toutes les 30 s (aucune pour un calcul plus court), puis la durée."""
    config = cfg_dpo(tmp_path / "a")
    entrainer(config, arreter_apres=1)
    sortie = capsys.readouterr().out
    assert "rangées sur" not in sortie  # le calcul a duré moins de 30 s
    assert f"Référence de la DPO{FINE}: 60 rangées en " in sortie
    for fichier in Path(config.donnees).rglob("reference.*"):
        fichier.unlink()
    monkeypatch.setattr(dpo, "SECONDES_ENTRE_PROGRES", 0)  # une ligne après chaque paquet
    entrainer(cfg_dpo(tmp_path / "b"), arreter_apres=1)
    lignes = [l for l in capsys.readouterr().out.splitlines() if "rangées sur 60" in l]
    # 48 + 12 rangées par paquets de 4 : 15 paquets, une ligne après chacun sauf le dernier.
    assert len(lignes) == 14
    assert lignes[0].startswith(f"Référence de la DPO{FINE}: 4 rangées sur 60 (6,7{FINE}%) · ")
    assert all("rangées/s · reste ≈ " in l for l in lignes)
    (ligne,) = [l for l in lire_journal(tmp_path / "b") if l.get("evenement") == "reference"]
    assert " en " in ligne["message"]  # la durée du calcul, pour la mesurer sur la carte


def ecrire_toml(config: ConfigEntrainement, fichier: Path) -> Path:
    """La configuration `config` (celle de `cfg_dpo`) en TOML, comme `forge entrainer --config` la lit."""
    m = config.modele
    lignes = [
        'methode = "dpo"',
        f"depart = '{config.depart}'",
        f"donnees = '{config.donnees}'",
        f"sortie = '{config.sortie}'",
        f"jetons_total = {config.jetons_total}",
        f"taille_lot_jetons = {config.taille_lot_jetons}",
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
        "",
    ]
    fichier.write_text("\n".join(lignes), encoding="utf-8")
    return fichier


def test_ctrl_c_pendant_le_calcul_de_la_reference(tmp_path, monkeypatch, capsys):
    """Ctrl+C pendant le calcul de la référence : une pause propre, rien d'écrit, et la reprise refait tout."""
    from forge.__main__ import main

    fichier = ecrire_toml(cfg_dpo(tmp_path / "dpo"), tmp_path / "dpo.toml")
    config = lire_config(fichier)
    vraie = dpo.logps_des_rangees
    appels = []

    def logps_puis_ctrl_c(*arguments, **options):
        appels.append(1)
        if len(appels) == 2:
            raise KeyboardInterrupt  # comme Ctrl+C pendant le deuxième paquet de rangées
        return vraie(*arguments, **options)

    monkeypatch.setattr(dpo, "logps_des_rangees", logps_puis_ctrl_c)
    capsys.readouterr()
    assert main(["entrainer", "--config", str(fichier), "--arreter-apres", "3"]) == 0
    sortie = capsys.readouterr()
    assert sortie.err == ""  # ni trace d'erreur, ni « Erreur »
    assert (
        f"Pause pendant le calcul de la référence{FINE}: rien n'est sauvegardé, la référence sera recalculée à la "
        f"reprise. Pour reprendre{FINE}: python -m forge entrainer --config {fichier} --reprendre" in sortie.out
    )
    jeu = Path(config.donnees)
    assert not list(jeu.rglob("reference.*")) and not list(jeu.rglob("*.tmp"))  # aucun fichier partiel
    assert not (tmp_path / "dpo" / "sauvegardes").exists()
    derniere = lire_journal(tmp_path / "dpo")[-1]
    assert derniere["evenement"] == "pause" and derniere["pas"] == 0 and "référence" in derniere["message"]

    monkeypatch.setattr(dpo, "logps_des_rangees", vraie)
    suite = entrainer(config, reprendre=True, arreter_apres=3)
    assert (jeu / "train" / "reference.bin").is_file() and (jeu / "val" / "reference.bin").is_file()
    assert suite["pertes"] == entrainer(cfg_dpo(tmp_path / "temoin"), arreter_apres=3)["pertes"]


# --------------------------------------------------------------------------------------
# La formule, les log-probabilités et le pas
# --------------------------------------------------------------------------------------


def test_les_mesures_a_la_main():
    pc, pr = torch.tensor([-10.0, -20.0], dtype=torch.float64), torch.tensor([-12.0, -16.0], dtype=torch.float64)
    qc, qr = torch.tensor([-11.0, -21.0], dtype=torch.float64), torch.tensor([-11.0, -17.0], dtype=torch.float64)
    lc, lr = torch.tensor([5, 10]), torch.tensor([6, 9])
    perte, m = perte_dpo(pc, pr, qc, qr, lc, lr, ReglagesDPO(beta=0.5, poids_sft=0.25))
    z = [0.5 * ((-10 + 11) - (-12 + 11)), 0.5 * ((-20 + 21) - (-16 + 17))]  # 1 et 0
    attendue = sum(-math.log(sigmoide(v)) for v in z) / 2 + 0.25 * (10 / 5 + 20 / 10) / 2
    assert perte.item() == pytest.approx(attendue, abs=1e-12)
    assert m["logps_choisie"].item() == pytest.approx((-10 / 5 - 20 / 10) / 2)
    assert m["logps_rejetee"].item() == pytest.approx((-12 / 6 - 16 / 9) / 2)
    assert m["recompense_choisie"].item() == pytest.approx(0.5)
    assert m["recompense_rejetee"].item() == pytest.approx(0.0)
    assert m["marge"].item() == pytest.approx(0.5)
    assert m["exactitude"].item() == 0.5  # z = 1 compte, z = 0 non
    assert set(m) == set(MESURES) and all(not v.requires_grad for v in m.values())


def test_logps_des_rangees():
    """Par rangée : la somme des log-probabilités des jetons appris, en float32, et leur nombre."""
    hasard = torch.Generator().manual_seed(3)
    ids = torch.randint(4, 120, (3, 17), generator=hasard)
    cibles = torch.full((3, 16), IGNORE)
    cibles[0, [4, 5, 6]] = ids[0, 5:8]
    cibles[1, [2, 9]] = ids[1, [3, 10]]
    documents = torch.zeros((3, 16), dtype=torch.long)
    documents[2] = -1  # la troisième rangée n'est que du bourrage : aucun jeton appris
    lot = LotAffinage(ids=ids[:, :-1].clone(), cibles=cibles, documents=documents)
    torch.manual_seed(0)
    modele = Transformer(MODELE_SFT)
    logps, appris = logps_des_rangees(modele, lot, CPU)
    assert logps.dtype == torch.float32 and appris.tolist() == [3, 2, 0]
    with torch.no_grad():
        logits, _ = modele(lot.ids, documents=lot.documents)
        log_probas = F.log_softmax(logits.float(), dim=-1)
    attendues = [
        sum(log_probas[r, p, cibles[r, p]].item() for p in range(16) if cibles[r, p] != IGNORE) for r in range(3)
    ]
    assert logps.tolist() == pytest.approx(attendues, rel=1e-5)
    assert logps[2].item() == 0


def lot_de_paires(graine: int, reference: list[float]) -> LotAffinage:
    """Deux rangées (une paire) tirées au hasard, avec leur référence."""
    hasard = torch.Generator().manual_seed(graine)
    ids = torch.randint(4, 120, (2, 17), generator=hasard)
    cibles = torch.full((2, 16), IGNORE)
    cibles[0, 6:10] = ids[0, 7:11]
    cibles[1, 6:13] = ids[1, 7:14]
    return LotAffinage(
        ids=ids[:, :-1].clone(),
        cibles=cibles,
        documents=torch.zeros((2, 16), dtype=torch.long),
        reference=torch.tensor(reference, dtype=torch.float64),
    )


def test_le_pas_est_la_moyenne_sur_les_paires():
    """Deux micro-lots d'une paire : la perte et les gradients du pas sont ceux de la moyenne sur les deux paires."""
    lots = [lot_de_paires(1, [-20.0, -40.0]), lot_de_paires(2, [-25.0, -30.0])]
    config = cfg_sans_fichiers(dpo={"beta": 0.5})
    torch.manual_seed(0)
    modele = Transformer(MODELE_SFT)
    optimiseur = boucle.creer_optimiseur(modele, config, CPU)
    resultat = pas_dpo(modele, optimiseur, FauxChargeur(lots), config, 0.0, CPU, {}, numero=1)
    assert set(resultat) == {"perte", *MESURES} and all(isinstance(v, float) for v in resultat.values())

    torch.manual_seed(0)
    temoin = Transformer(MODELE_SFT)
    tout = LotAffinage(
        ids=torch.cat([l.ids for l in lots]),
        cibles=torch.cat([l.cibles for l in lots]),
        documents=torch.cat([l.documents for l in lots]),
        reference=torch.cat([l.reference for l in lots]),
    )
    logps, appris = logps_des_rangees(temoin, tout, CPU)
    q = tout.reference
    perte, mesures = perte_dpo(logps[0::2], logps[1::2], q[0::2], q[1::2], appris[0::2], appris[1::2], config.dpo)
    perte.backward()
    assert resultat["perte"] == pytest.approx(perte.item(), rel=1e-6)
    for nom in MESURES:
        assert resultat[nom] == pytest.approx(mesures[nom].item(), rel=1e-6, abs=1e-9)
    attendus = gradients(temoin)
    for nom, gradient in gradients(modele).items():
        torch.testing.assert_close(gradient, attendus[nom], rtol=1e-5, atol=1e-7)


def test_une_paire_sans_jeton_appris_est_refusee():
    bourrage = lot_de_bourrage()
    paire = lot_de_paires(1, [-20.0, -40.0])
    abimee = LotAffinage(
        ids=torch.cat([paire.ids[:1], bourrage.ids]),
        cibles=torch.cat([paire.cibles[:1], bourrage.cibles]),
        documents=torch.cat([paire.documents[:1], bourrage.documents]),
        reference=paire.reference,
    )
    config = cfg_sans_fichiers()
    torch.manual_seed(0)
    modele = Transformer(MODELE_SFT)
    optimiseur = boucle.creer_optimiseur(modele, config, CPU)
    with pytest.raises(ValueError, match="forge preferences"):
        pas_dpo(modele, optimiseur, FauxChargeur([abimee, paire]), config, 0.0, CPU, {}, numero=1)


# --------------------------------------------------------------------------------------
# La référence sur le disque
# --------------------------------------------------------------------------------------


def test_la_reference_du_jeu(tmp_path):
    """`reference.bin` : float64, une valeur par rangée, dans l'ordre du fichier ; `reference.json` la décrit."""
    config = cfg_dpo(tmp_path / "dpo")
    entrainer(config, arreter_apres=1)
    jeu = Path(config.donnees)
    depart = charger_publication(Path(config.depart)).modele
    for partie, rangees in (("train", 48), ("val", 12)):
        valeurs = np.fromfile(jeu / partie / "reference.bin", dtype="<f8")
        assert valeurs.shape == (rangees,)
        chargeur = ChargeurAffinage(jeu, partie, 2, graine=0)
        with torch.no_grad():
            attendues, _ = logps_des_rangees(depart, chargeur.lot_des_rangees(0, rangees), CPU)
        assert valeurs.tolist() == pytest.approx(attendues.tolist(), rel=1e-5)
        description = json.loads((jeu / partie / "reference.json").read_text(encoding="utf-8"))
        poids = Path(config.depart) / nom_des_poids(ETIQUETTE)
        assert description["version"] == ETIQUETTE and description["empreinte_des_poids"] == empreinte_sha256(poids)
        assert description["rangees"] == rangees
    assert not list(jeu.rglob("*.tmp"))


def test_lot_des_rangees_dans_l_ordre_du_fichier(tmp_path):
    jeu = ecrire_jeu_dpo(tmp_path / "jeu")
    chargeur = ChargeurAffinage(jeu, "train", 4, graine=7)
    etat = chargeur.etat()
    lot = chargeur.lot_des_rangees(2, 6)
    attendues = paires(24, graine=1)[2:6]
    assert lot.ids.tolist() == [r.ids[:-1] for r in attendues]
    assert chargeur.etat() == etat  # la position du chargeur n'a pas bougé
    for r, ligne in zip(attendues, lot.cibles.tolist()):
        assert ligne == [r.ids[p + 1] if r.appris[p + 1] else IGNORE for p in range(16)]


def test_un_jeu_sft_est_refuse_sans_rien_y_ecrire(tmp_path):
    jeu = ecrire_jeu_sft(tmp_path / "jeu-sft")
    with pytest.raises(ValueError, match="sft") as erreur:
        entrainer(cfg_dpo(tmp_path / "dpo", donnees=str(jeu)), arreter_apres=1)
    assert "dpo" in str(erreur.value)
    assert not list(jeu.rglob("reference.*"))


# --------------------------------------------------------------------------------------
# Le journal et la validation
# --------------------------------------------------------------------------------------


def test_le_journal_de_la_dpo(tmp_path):
    r = entrainer(cfg_dpo(tmp_path / "dpo"), arreter_apres=10)
    pas = lignes_de_pas(tmp_path / "dpo")
    assert [l["pas"] for l in pas] == list(range(1, 11))
    for ligne in pas:
        assert all(isinstance(ligne[nom], float) and math.isfinite(ligne[nom]) for nom in MESURES)
        assert ligne["marge"] == pytest.approx(ligne["recompense_choisie"] - ligne["recompense_rejetee"])
        assert 0 <= ligne["exactitude"] <= 1
    validations = [l for l in pas if "perte_val" in l]
    assert [l["pas"] for l in validations] == [5, 10]
    assert all(0 <= l["exactitude_val"] <= 1 for l in validations)
    assert r["meilleure_perte_val"] == min(l["perte_val"] for l in validations)
    assert (tmp_path / "dpo" / "sauvegardes" / "meilleur.pt").is_file()
    (ligne,) = [l for l in lire_journal(tmp_path / "dpo") if l.get("evenement") == "reference"]
    assert "calculée" in ligne["message"]


def test_la_validation_lit_les_premieres_paires(tmp_path):
    """La perte et l'exactitude des n premières paires de validation, quelle que soit la taille des paquets."""
    assert PAIRES_DE_VALIDATION == 256
    config = cfg_dpo(tmp_path / "dpo")
    entrainer(config, arreter_apres=1)  # calcule la référence
    jeu = Path(config.donnees)
    modele = charger_publication(Path(config.depart)).modele
    torch.manual_seed(5)
    with torch.no_grad():  # une politique qui n'est plus la référence
        for p in modele.parameters():
            p.add_(0.05 * torch.randn_like(p))
    valeurs = []
    for taille in (2, 4, 6):
        chargeur = ChargeurAffinage(jeu, "val", taille, graine=5)
        valeurs.append(mesures_dpo_validation(modele, chargeur, chargeur.etat(), 3, CPU, ReglagesDPO()))
    lot = ChargeurAffinage(jeu, "val", 6, graine=5).lot()  # les 3 premières paires, d'un coup
    with torch.no_grad():
        logps, appris = logps_des_rangees(modele, lot, CPU)
        q = lot.reference
        perte, mesures = perte_dpo(logps[0::2], logps[1::2], q[0::2], q[1::2], appris[0::2], appris[1::2], ReglagesDPO())
    for valeur in valeurs:
        assert set(valeur) == {"perte_val", "exactitude_val"}
        assert valeur["perte_val"] == pytest.approx(perte.item(), rel=1e-5)
        assert valeur["exactitude_val"] == mesures["exactitude"].item()


def test_la_validation_s_arrete_aux_paires_du_jeu(tmp_path):
    """Moins de 256 paires de validation : on les lit toutes, une seule fois."""
    config = cfg_dpo(tmp_path / "dpo", jetons_total=128 * 5)
    entrainer(config, arreter_apres=5)
    jeu = Path(config.donnees)
    modele = modele_de(charger_derniere(tmp_path / "dpo" / "sauvegardes"))
    chargeur = ChargeurAffinage(jeu, "val", 4, graine=config.graine)
    attendu = mesures_dpo_validation(modele, chargeur, chargeur.etat(), 6, CPU, ReglagesDPO())
    (ligne,) = [l for l in lignes_de_pas(tmp_path / "dpo") if "perte_val" in l]
    assert ligne["perte_val"] == pytest.approx(attendu["perte_val"], rel=1e-6)


def test_un_jeu_dpo_sans_validation(tmp_path):
    jeu = tmp_path / "jeu-sans-val"
    ecrire_jeu(jeu, paires(24, graine=1), [], "dpo", {}, TOK)
    r = entrainer(cfg_dpo(tmp_path / "dpo", donnees=str(jeu)), arreter_apres=5)
    assert r["pas"] == 5 and r["meilleure_perte_val"] is None
    assert not (jeu / "val" / "reference.bin").exists()
    (ligne,) = [l for l in lire_journal(tmp_path / "dpo") if l.get("evenement") == "validation"]
    assert "aucune rangée de validation" in ligne["message"]


# --------------------------------------------------------------------------------------
# Les réglages [dpo]
# --------------------------------------------------------------------------------------


def test_les_reglages_dpo_de_la_configuration(tmp_path):
    assert cfg_sans_fichiers().dpo == ReglagesDPO(beta=0.1, normaliser_longueur=False, poids_sft=1.0)
    config = cfg_sans_fichiers(dpo={"beta": 0.5, "normaliser_longueur": True})
    assert config.dpo == ReglagesDPO(beta=0.5, normaliser_longueur=True, poids_sft=1.0)
    assert dataclasses.replace(config, micro_lot=2).dpo == config.dpo
    assert cfg_sans_fichiers(dpo=ReglagesDPO(poids_sft=0.0)).dpo.poids_sft == 0.0
    assert cfg_sans_fichiers(dpo={"beta": 1}).dpo.beta == 1.0
    with pytest.raises(ValueError, match="beta, normaliser_longueur, poids_sft"):
        cfg_sans_fichiers(dpo={"bta": 0.1})
    for mauvais in ({"beta": 0}, {"beta": -0.1}, {"beta": True}, {"poids_sft": -1.0}, {"normaliser_longueur": "oui"}):
        with pytest.raises(ValueError, match=next(iter(mauvais))):
            cfg_sans_fichiers(dpo=mauvais)
    with pytest.raises(ValueError, match="pair"):
        cfg_sans_fichiers(micro_lot=3, taille_lot_jetons=48, jetons_total=48)
    # Le pré-entraînement et le SFT n'ont pas de réglages [dpo].
    assert cfg_sans_fichiers(methode="sft").dpo is None


def test_la_table_dpo_du_toml(tmp_path):
    fichier = tmp_path / "dpo.toml"
    fichier.write_text(
        "\n".join(
            [
                'methode = "dpo"',
                'depart = "ton-ia-1.7"',
                'preset = "mini"',
                'donnees = "preferences-1.8"',
                "jetons_total = 4096",
                "taille_lot_jetons = 4096",
                "longueur = 512",
                "micro_lot = 8",
                "taux_max = 1e-6",
                "echauffement = 0",
                "evaluation_tous_pas = 10",
                'sortie = "ton-ia-1.8"',
                "",
                "[dpo]",
                "beta = 0.2",
                "poids_sft = 0.5",
                "",
            ]
        ),
        encoding="utf-8",
    )
    assert lire_config(fichier).dpo == ReglagesDPO(beta=0.2, normaliser_longueur=False, poids_sft=0.5)


def test_l_exemple_du_readme_se_lit_tel_quel(tmp_path):
    """L'exemple TOML de la DPO du README est une configuration complète, aux rangées du jeu `preferences-1.8`."""
    from forge.preferences.construction import RECETTES_PREFERENCES

    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    debut = readme.index('```toml\nmethode = "dpo"') + len("```toml\n")
    fichier = tmp_path / "dpo.toml"
    fichier.write_text(readme[debut : readme.index("```", debut)], encoding="utf-8")
    config = lire_config(fichier)
    assert config.methode == "dpo" and config.dpo == ReglagesDPO()
    assert config.longueur == RECETTES_PREFERENCES[config.donnees].longueur
    assert config.pas_total == 100 and config.taille_lot_jetons // config.longueur // 2 == 32  # 32 paires par pas


def test_reprise_refusee_si_les_reglages_dpo_changent(tmp_path):
    entrainer(cfg_dpo(tmp_path / "dpo"), arreter_apres=1)
    with pytest.raises(ValueError, match="dpo"):
        entrainer(cfg_dpo(tmp_path / "dpo", dpo={"beta": 0.5}), reprendre=True, arreter_apres=2)
    # Écrire les valeurs par défaut, ou ne rien écrire, c'est pareil.
    r = entrainer(cfg_dpo(tmp_path / "dpo", dpo={"beta": 0.1, "poids_sft": 1.0}), reprendre=True, arreter_apres=2)
    assert r["pas"] == 2


@pytest.mark.gpu
def test_dpo_gpu_court(tmp_path):
    config = cfg_dpo(tmp_path / "dpo", appareil="cuda")
    r = entrainer(config, arreter_apres=20)
    assert len(r["pertes"]) == 20 and all(math.isfinite(p) for p in r["pertes"])
    pas = lignes_de_pas(tmp_path / "dpo")
    assert abs(pas[0]["marge"]) < 5e-2  # bf16 : la politique et la référence diffèrent à peine
    jeu = Path(config.donnees)
    finale = marge_sur_l_entrainement(modele_de(charger_derniere(tmp_path / "dpo" / "sauvegardes")), jeu)
    assert finale > marge_sur_l_entrainement(charger_publication(Path(config.depart)).modele, jeu)


def test_dpo_s_importe_en_premier():
    """« import forge.affinage.dpo » seul, dans un interpréteur neuf : pas d'import circulaire.

    dpo.py importe forge.evaluation, qui importe forge.entrainement, donc methodes.py, qui se sert de
    dpo.py : methodes.py importe le module, pas ses noms, pour que cet ordre-là marche aussi.
    """
    # Un délai, pour qu'un import bloqué ne bloque pas toute la suite ; pas 2 s : PyTorch seul en prend environ 5.
    resultat = subprocess.run(
        [sys.executable, "-c", "import forge.affinage.dpo"], capture_output=True, text=True, timeout=120
    )
    assert resultat.returncode == 0, resultat.stderr
