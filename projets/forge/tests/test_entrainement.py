"""Tests de l'entraînement de « ton IA » : planning, chargeur, sauvegardes, pause et reprise.

Tout tourne sur le processeur, avec un modèle minuscule (vocabulaire 128, dim 32, 2 couches,
contexte 16) et un petit corpus de jetons répétitifs écrit par le test, sauf le test marqué
`gpu`. Le corpus a la forme de celui de `forge encoder` : `train/` et `val/`, `index.json` et
`.complet`. Le chargeur coupe ses trois fragments en 51 morceaux de 17 jetons, mélangés à
chaque époque : les tests de reprise traversent un changement d'époque.
"""

import errno
import json
import math
import os
import shutil
import signal
from collections import Counter
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

try:
    import torch
except ImportError as erreur:
    raise ImportError(
        "PyTorch n'est pas installé. Lance les tests avec `uv run --extra gpu pytest -q` "
        "(carte NVIDIA) ou `uv run --extra cpu pytest -q` (sans carte graphique)."
    ) from erreur

from forge.__main__ import main
from forge.chemins import PlaceInsuffisante
from forge.entrainement import (
    ChargeurJetons,
    ConfigEntrainement,
    charger_derniere,
    entrainer,
    lire_config,
    sauvegarder,
    taux,
)
from forge.entrainement import boucle
from forge.modele import ConfigModele, nombre_parametres
from forge.tokenizer.apprentissage import DonneesManquantes

RACINE_DU_PROJET = Path(__file__).resolve().parents[1]

MODELE_TEST = ConfigModele(taille_vocabulaire=128, dim=32, couches=2, tetes=2, longueur_contexte=16)
FRAGMENTS_TRAIN = 3
JETONS_PAR_FRAGMENT = 300


def ecrire_corpus(dossier: Path) -> None:
    """Écrit un petit dossier de jetons, comme `forge encoder` (rien si c'est déjà fait).

    Chaque fragment répète une suite de 60 jetons tirée au hasard (graine fixe) : le modèle
    peut l'apprendre en quelques pas, et chaque fragment est différent des autres, donc
    l'ordre des fragments compte.
    """
    if (dossier / ".complet").exists():
        return
    hasard = np.random.default_rng(7)
    fichiers = {}
    for partie, nombre in (("train", FRAGMENTS_TRAIN), ("val", 1)):
        (dossier / partie).mkdir(parents=True, exist_ok=True)
        for k in range(nombre):
            motif = hasard.integers(0, 120, size=60)
            jetons = np.tile(motif, JETONS_PAR_FRAGMENT // 60).astype("<u2")
            nom = f"{partie}/fragment-{k:05d}.bin"
            jetons.tofile(dossier / nom)
            fichiers[nom] = len(jetons)
    (dossier / "index.json").write_text(json.dumps({"version": 1, "fichiers": fichiers}), encoding="utf-8")
    (dossier / ".complet").write_text("{}", encoding="utf-8")


def config_test(dossier: Path, **changements) -> ConfigEntrainement:
    """Une configuration minuscule : 64 jetons par pas (2 lots de 2 × 16), 40 pas en tout."""
    ecrire_corpus(dossier / "jetons")
    valeurs = dict(
        preset=MODELE_TEST,
        donnees=str(dossier / "jetons"),
        jetons_total=64 * 40,
        taille_lot_jetons=64,
        micro_lot=2,
        taux_max=1e-2,
        echauffement=5,
        evaluation_tous_pas=5,
        appareil="cpu",
        compiler="non",
        sortie=str(dossier),
    )
    valeurs.update(changements)
    return ConfigEntrainement(**valeurs)


def lire_journal(dossier: Path) -> list[dict]:
    lignes = (dossier / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(ligne) for ligne in lignes if ligne.strip()]


# --------------------------------------------------------------------------------------
# Les tests du plan
# --------------------------------------------------------------------------------------


def test_reprise_exacte(tmp_path):
    a = entrainer(config_test(tmp_path / "a"), arreter_apres=20)["pertes"]
    entrainer(config_test(tmp_path / "b"), arreter_apres=10)
    b = entrainer(config_test(tmp_path / "b"), reprendre=True, arreter_apres=20)["pertes"]
    assert len(a) == 20 and len(b) == 10
    assert a[10:20] == b  # au bit près sur le processeur


def test_sauvegarde_coupee(tmp_path):
    entrainer(config_test(tmp_path), arreter_apres=10)
    (tmp_path / "sauvegardes" / "etape-0000020.pt.tmp").write_bytes(b"\x00" * 100)  # écriture interrompue
    assert charger_derniere(tmp_path / "sauvegardes")["pas"] == 10


def test_disque_plein_avant_sauvegarde(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "forge.entrainement.sauvegarde.verifier_place",
        lambda *a, **k: (_ for _ in ()).throw(PlaceInsuffisante("Il manque 1 Go sur D:")),
    )
    with pytest.raises(PlaceInsuffisante):
        sauvegarder(tmp_path, {"pas": 1}, "etape-0000001.pt")
    assert not list(tmp_path.iterdir())


def test_memoire_gpu_message(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        "forge.entrainement.boucle._pas_d_optimisation",
        lambda *a, **k: (_ for _ in ()).throw(torch.cuda.OutOfMemoryError("CUDA out of memory")),
    )
    with pytest.raises(SystemExit) as sortie:
        entrainer(config_test(tmp_path), arreter_apres=1)
    assert sortie.value.code == 2
    erreur = capsys.readouterr().err
    assert "Réduis micro_lot" in erreur
    assert "ferme les jeux ou logiciels 3D ouverts, puis relance avec --reprendre." in erreur


def test_planning():
    assert taux(0, 1000, 1e-3, 100) == 0 and taux(100, 1000, 1e-3, 100) == pytest.approx(1e-3)
    assert taux(1000, 1000, 1e-3, 100) == pytest.approx(1e-4)


@pytest.mark.gpu
def test_entrainement_gpu_court(tmp_path):
    r = entrainer(config_test(tmp_path, appareil="cuda"), arreter_apres=30)
    assert r["pertes"][-1] < r["pertes"][0]


# --------------------------------------------------------------------------------------
# Planning du taux d'apprentissage
# --------------------------------------------------------------------------------------


def test_planning_forme():
    # Montée linéaire : la moitié de l'échauffement donne la moitié du taux maximal.
    assert taux(50, 1000, 1e-3, 100) == pytest.approx(5e-4)
    # Au milieu de la descente, le cosinus est à mi-chemin entre le maximum et le minimum.
    assert taux(550, 1000, 1e-3, 100) == pytest.approx((1e-3 + 1e-4) / 2)
    # Après la fin prévue, le taux reste au minimum.
    assert taux(1500, 1000, 1e-3, 100) == pytest.approx(1e-4)
    assert taux(1000, 1000, 1e-3, 100, ratio_min=0.0) == pytest.approx(0.0, abs=1e-12)
    valeurs = [taux(p, 1000, 1e-3, 100) for p in range(1001)]
    assert all(x < y for x, y in zip(valeurs[:100], valeurs[1:101]))  # monte
    assert all(x >= y for x, y in zip(valeurs[100:], valeurs[101:]))  # puis descend


def test_planning_sans_echauffement():
    assert taux(0, 10, 1e-3, 0) == pytest.approx(1e-3)


# --------------------------------------------------------------------------------------
# Chargeur de jetons
# --------------------------------------------------------------------------------------


def ecrire_deux_sources(dossier: Path) -> None:
    """Deux fichiers de « sources » différentes : 2 400 jetons de 0 à 49, 1 600 jetons de 100 à 149."""
    hasard = np.random.default_rng(3)
    (dossier / "train").mkdir(parents=True)
    fichiers = {}
    for k, (bas, nombre) in enumerate(((0, 2400), (100, 1600))):
        nom = f"train/fragment-{k:05d}.bin"
        hasard.integers(bas, bas + 50, size=nombre).astype("<u2").tofile(dossier / nom)
        fichiers[nom] = nombre
    (dossier / "index.json").write_text(json.dumps({"version": 1, "fichiers": fichiers}), encoding="utf-8")
    (dossier / ".complet").write_text("{}", encoding="utf-8")


def tous_les_morceaux(dossier: Path, longueur: int = 16) -> Counter:
    """Les morceaux attendus : chaque fichier coupé en morceaux de `longueur + 1` jetons, bout à bout."""
    attendus = Counter()
    for fichier in sorted(dossier.glob("*.bin")):
        jetons = np.fromfile(fichier, dtype="<u2").tolist()
        for debut in range(0, len(jetons) - longueur, longueur + 1):
            attendus[tuple(jetons[debut : debut + longueur + 1])] += 1
    return attendus


def morceaux_du_lot(x, y) -> list[tuple]:
    """Les morceaux lus dans un lot : chaque ligne de x, plus le dernier jeton de y."""
    return [tuple(ligne + [fin]) for ligne, fin in zip(x.tolist(), y[:, -1].tolist())]


def test_chargeur_lots_decales_d_un_jeton(tmp_path):
    ecrire_corpus(tmp_path)
    attendus = tous_les_morceaux(tmp_path / "train")
    chargeur = ChargeurJetons(tmp_path / "train", longueur=16, taille_lot=8, graine=1)
    x, y = chargeur.lot()
    assert x.shape == (8, 16) and y.shape == (8, 16) and x.dtype == torch.int64
    # La cible de chaque position est le jeton suivant…
    assert torch.equal(x[:, 1:], y[:, :-1])
    # … et chaque ligne est un des morceaux de 17 jetons coupés bout à bout dans UN fichier.
    assert all(morceau in attendus for morceau in morceaux_du_lot(x, y))


def test_chaque_morceau_lu_une_fois_par_epoque(tmp_path):
    ecrire_corpus(tmp_path)
    attendus = tous_les_morceaux(tmp_path / "train")  # 3 fichiers de 300 jetons : 3 × 17 morceaux
    chargeur = ChargeurJetons(tmp_path / "train", longueur=16, taille_lot=3, graine=2)
    assert chargeur.morceaux == sum(attendus.values()) == 51
    ordres = []
    for epoque in range(2):
        lus = [m for _ in range(17) for m in morceaux_du_lot(*chargeur.lot())]
        assert Counter(lus) == attendus  # chaque morceau exactement une fois
        assert chargeur.etat()["epoque"] == epoque
        ordres.append(lus)
    assert ordres[0] != ordres[1]  # un nouvel ordre à chaque époque


def test_chaque_lot_melange_les_sources(tmp_path):
    ecrire_deux_sources(tmp_path)  # 2 400 jetons : 141 morceaux de 17 ; 1 600 jetons : 94 morceaux
    chargeur = ChargeurJetons(tmp_path / "train", longueur=16, taille_lot=5, graine=0)

    def sources(x):
        return ["a" if ligne[0] < 100 else "b" for ligne in x.tolist()]

    premiers = ChargeurJetons(tmp_path / "train", longueur=16, taille_lot=8, graine=0)
    for _ in range(5):
        assert set(sources(premiers.lot()[0])) == {"a", "b"}
    # Sur une époque entière (235 morceaux = 47 lots de 5), chaque source est lue en proportion
    # exacte de ses morceaux.
    lus = [s for _ in range(47) for s in sources(chargeur.lot()[0])]
    assert (lus.count("a"), lus.count("b")) == (141, 94)


def test_chargeur_meme_jetons_quelle_que_soit_la_taille_du_lot(tmp_path):
    """Un lot de 4 lignes, ou deux lots de 2 : les mêmes morceaux, dans le même ordre (époques comprises)."""
    ecrire_corpus(tmp_path)
    gros = ChargeurJetons(tmp_path / "train", longueur=16, taille_lot=4, graine=5)
    petit = ChargeurJetons(tmp_path / "train", longueur=16, taille_lot=2, graine=5)
    for _ in range(20):  # 80 morceaux : on passe la fin de la première époque (51)
        attendu = gros.lot()[0]
        assert torch.equal(torch.cat([petit.lot()[0], petit.lot()[0]]), attendu)


def test_chargeur_reprend_au_meme_endroit(tmp_path):
    ecrire_corpus(tmp_path)
    premier = ChargeurJetons(tmp_path / "train", longueur=16, taille_lot=2, graine=3)
    for _ in range(11):
        premier.lot()
    etat = premier.etat()
    json.dumps(etat)  # l'état tient en nombres simples
    suite = [premier.lot() for _ in range(25)]

    second = ChargeurJetons(tmp_path / "train", longueur=16, taille_lot=2, graine=3)
    second.restaurer(etat)
    for (x1, y1), (x2, y2) in zip(suite, (second.lot() for _ in range(25))):
        assert torch.equal(x1, x2) and torch.equal(y1, y2)


def test_chargeur_refuse_un_encodage_inacheve(tmp_path):
    ecrire_corpus(tmp_path)
    (tmp_path / ".complet").unlink()
    with pytest.raises(DonneesManquantes, match="encod"):
        ChargeurJetons(tmp_path / "train", longueur=16, taille_lot=2, graine=0)


def test_chargeur_refuse_l_etat_d_autres_donnees(tmp_path):
    ecrire_corpus(tmp_path / "un")
    ecrire_deux_sources(tmp_path / "autre")
    etat = ChargeurJetons(tmp_path / "un" / "train", longueur=16, taille_lot=2, graine=0).etat()
    autre = ChargeurJetons(tmp_path / "autre" / "train", longueur=16, taille_lot=2, graine=0)
    with pytest.raises(ValueError, match="ne sont plus ceux de la sauvegarde"):
        autre.restaurer(etat)
    # Même nombre de fichiers et de jetons, mais d'autres morceaux : refusé aussi.
    etat["morceaux"] += 1
    with pytest.raises(ValueError, match="morceaux"):
        ChargeurJetons(tmp_path / "un" / "train", longueur=16, taille_lot=2, graine=0).restaurer(etat)


# --------------------------------------------------------------------------------------
# Sauvegardes
# --------------------------------------------------------------------------------------


def test_on_garde_les_deux_dernieres_et_la_meilleure(tmp_path):
    sauvegarder(tmp_path, {"pas": 0}, "meilleur.pt")
    for pas in (1, 2, 3, 4):
        sauvegarder(tmp_path, {"pas": pas}, f"etape-{pas:07d}.pt")
    assert sorted(f.name for f in tmp_path.iterdir()) == ["etape-0000003.pt", "etape-0000004.pt", "meilleur.pt"]
    assert charger_derniere(tmp_path)["pas"] == 4


def test_sauvegarde_illisible_ignoree(tmp_path, capsys):
    sauvegarder(tmp_path, {"pas": 1}, "etape-0000001.pt")
    (tmp_path / "etape-0000002.pt").write_bytes(b"PK\x03\x04 coupure de courant")
    assert charger_derniere(tmp_path)["pas"] == 1
    assert "etape-0000002.pt" in capsys.readouterr().err


def test_aucune_sauvegarde(tmp_path):
    assert charger_derniere(tmp_path) is None
    assert charger_derniere(tmp_path / "absent") is None


def save_comme_torch_sur_disque_plein(etat, fichier, *a, **k):
    """Ce que fait le vrai `torch.save` quand le disque se remplit : une RuntimeError, l'OSError en contexte."""
    fichier.write(b"PK\x03\x04 debut")
    try:
        raise OSError(errno.ENOSPC, "No space left on device")
    except OSError:
        raise RuntimeError("[enforce fail at inline_container.cc:671] . unexpected pos 704 vs 598")


def test_disque_plein_pendant_l_ecriture(tmp_path, monkeypatch):
    monkeypatch.setattr("forge.entrainement.sauvegarde.torch.save", save_comme_torch_sur_disque_plein)
    with pytest.raises(PlaceInsuffisante, match="--reprendre"):
        sauvegarder(tmp_path, {"pas": 1}, "etape-0000001.pt")
    assert not list(tmp_path.iterdir())


def test_disque_plein_sans_cause_dans_l_erreur(tmp_path, monkeypatch):
    """Une erreur qui ne dit rien du disque, mais il ne reste plus de place : c'est le disque."""

    def save_qui_echoue(etat, fichier, *a, **k):
        fichier.write(b"PK\x03\x04 debut")
        raise RuntimeError("PytorchStreamWriter failed writing file data/0: file write failed")

    plein = shutil.disk_usage(tmp_path)._replace(free=4096)
    monkeypatch.setattr("forge.entrainement.sauvegarde.verifier_place", lambda *a, **k: None)
    monkeypatch.setattr("forge.entrainement.sauvegarde.torch.save", save_qui_echoue)
    monkeypatch.setattr("forge.entrainement.sauvegarde.shutil.disk_usage", lambda chemin: plein)
    with pytest.raises(PlaceInsuffisante, match="Il manque"):
        sauvegarder(tmp_path, {"pas": 1}, "etape-0000001.pt")
    assert not list(tmp_path.iterdir())


def test_autre_erreur_d_ecriture_non_deguisee(tmp_path, monkeypatch):
    def save_qui_echoue(etat, fichier, *a, **k):
        raise TypeError("objet impossible à enregistrer")

    monkeypatch.setattr("forge.entrainement.sauvegarde.torch.save", save_qui_echoue)
    with pytest.raises(TypeError):
        sauvegarder(tmp_path, {"pas": 1}, "etape-0000001.pt")
    assert not list(tmp_path.iterdir())


class FichierQuiRemplitLeDisque:
    """Un fichier texte sur un disque qui se remplit après `lignes` lignes ; `close` réécrit son tampon."""

    def __init__(self, lignes: int) -> None:
        self.restantes = lignes
        self.en_attente = False

    def write(self, texte):
        if self.restantes == 0:
            self.en_attente = True
            raise OSError(errno.ENOSPC, "No space left on device")
        self.restantes -= 1

    def flush(self):
        pass

    def close(self):
        if self.en_attente:
            raise OSError(errno.ENOSPC, "No space left on device")


def test_disque_plein_en_ecrivant_le_journal(tmp_path):
    journal = boucle._Journal(tmp_path / "journal.jsonl")
    journal._fichier.close()
    journal._fichier = FichierQuiRemplitLeDisque(lignes=0)
    with pytest.raises(PlaceInsuffisante, match="--reprendre"):
        journal.ecrire({"pas": 1})
    journal.fermer()  # ne relance pas l'erreur du disque plein


def test_disque_plein_pendant_l_entrainement(tmp_path, monkeypatch):
    class JournalSurDisquePlein(boucle._Journal):
        def __init__(self, chemin):
            super().__init__(chemin)
            self._fichier.close()
            self._fichier = FichierQuiRemplitLeDisque(lignes=4)

    monkeypatch.setattr(boucle, "_Journal", JournalSurDisquePlein)
    with pytest.raises(PlaceInsuffisante, match="--reprendre"):
        entrainer(config_test(tmp_path), arreter_apres=10)


def test_remplacement_reessaye_si_windows_refuse(tmp_path, monkeypatch):
    """Antivirus ou Explorateur : os.replace échoue deux fois, puis réussit."""
    vrai_replace = os.replace
    refus = []

    def replace_bloque_deux_fois(source, cible):
        if len(refus) < 2:
            refus.append(cible)
            raise PermissionError(13, "Accès refusé")
        vrai_replace(source, cible)

    monkeypatch.setattr("forge.entrainement.sauvegarde.os.replace", replace_bloque_deux_fois)
    monkeypatch.setattr("forge.entrainement.sauvegarde.time.sleep", lambda secondes: None)
    chemin = sauvegarder(tmp_path, {"pas": 1}, "etape-0000001.pt")
    assert len(refus) == 2 and charger_derniere(tmp_path)["pas"] == 1
    assert sorted(f.name for f in tmp_path.iterdir()) == [chemin.name]


def test_effacer_une_ancienne_etape_n_est_jamais_fatal(tmp_path, monkeypatch):
    for pas in (1, 2):
        sauvegarder(tmp_path, {"pas": pas}, f"etape-{pas:07d}.pt")
    vrai_unlink = Path.unlink

    def unlink_bloque(chemin, *a, **k):
        if chemin.name == "etape-0000001.pt":
            raise PermissionError(13, "Accès refusé")
        vrai_unlink(chemin, *a, **k)

    monkeypatch.setattr(Path, "unlink", unlink_bloque)
    notes = []
    sauvegarder(tmp_path, {"pas": 3}, "etape-0000003.pt", noter=notes.append)
    assert charger_derniere(tmp_path)["pas"] == 3
    assert len(notes) == 1 and "etape-0000001.pt" in notes[0]


# --------------------------------------------------------------------------------------
# Boucle : journal, pause, reprise, compilation, configuration
# --------------------------------------------------------------------------------------


def test_journal_et_meilleure_sauvegarde(tmp_path):
    r = entrainer(config_test(tmp_path), arreter_apres=10)
    lignes = [ligne for ligne in lire_journal(tmp_path) if "perte" in ligne]
    assert [ligne["pas"] for ligne in lignes] == list(range(1, 11))
    for ligne in lignes:
        assert {"pas", "jetons_vus", "perte", "taux", "jetons_par_seconde", "secondes"} <= ligne.keys()
    assert lignes[-1]["jetons_vus"] == 640
    assert [ligne["pas"] for ligne in lignes if "perte_val" in ligne] == [5, 10]
    assert [ligne["perte"] for ligne in lignes] == pytest.approx(r["pertes"])
    sauvegardes = tmp_path / "sauvegardes"
    assert sorted(f.name for f in sauvegardes.iterdir()) == ["etape-0000010.pt", "meilleur.pt"]
    etat = charger_derniere(sauvegardes)
    assert {"modele", "optimiseur", "chargeur", "hasard", "config", "config_modele"} <= etat.keys()
    assert ConfigModele(**etat["config_modele"]) == MODELE_TEST
    meilleur = torch.load(sauvegardes / "meilleur.pt", weights_only=True)
    assert meilleur["pas"] in (5, 10) and meilleur["perte_val"] == etat["meilleure_perte_val"]


def test_pause_par_ctrl_c(tmp_path, monkeypatch, capsys):
    reference = entrainer(config_test(tmp_path / "ref"), arreter_apres=8)["pertes"]

    vrai_pas = boucle._pas_d_optimisation
    faits = []

    def pas_puis_ctrl_c(*a, **k):
        perte = vrai_pas(*a, **k)
        faits.append(perte)
        if len(faits) == 3:
            signal.raise_signal(signal.SIGINT)  # comme Ctrl+C au milieu du pas 3
        return perte

    monkeypatch.setattr(boucle, "_pas_d_optimisation", pas_puis_ctrl_c)
    config = config_test(tmp_path / "pause", fichier="configs/essai.toml")
    r = entrainer(config, arreter_apres=8)
    assert r["en_pause"] and r["pas"] == 3 and len(r["pertes"]) == 3
    sortie = capsys.readouterr().out
    assert (
        "Entraînement mis en pause au pas 3. Pour reprendre : "
        "python -m forge entrainer --config configs/essai.toml --reprendre"
    ) in sortie
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler
    assert charger_derniere(tmp_path / "pause" / "sauvegardes")["pas"] == 3

    monkeypatch.setattr(boucle, "_pas_d_optimisation", vrai_pas)
    suite = entrainer(config, reprendre=True, arreter_apres=8)["pertes"]
    assert reference[3:8] == suite  # au bit près sur le processeur


def test_reprise_coupe_le_journal(tmp_path):
    entrainer(config_test(tmp_path), arreter_apres=10)
    with open(tmp_path / "journal.jsonl", "a", encoding="utf-8") as journal:
        # Deux pas faits après la dernière sauvegarde, puis une ligne coupée par une panne.
        journal.write(json.dumps({"pas": 11, "perte": 9.0}) + "\n")
        journal.write(json.dumps({"pas": 12, "perte": 9.0}) + "\n")
        journal.write('{"pas": 13, "per')
    entrainer(config_test(tmp_path), reprendre=True, arreter_apres=12)
    pas = [ligne["pas"] for ligne in lire_journal(tmp_path) if "perte" in ligne]
    assert pas == list(range(1, 13))


def test_refuse_de_repartir_de_zero_sur_un_entrainement(tmp_path):
    entrainer(config_test(tmp_path), arreter_apres=2)
    with pytest.raises(FileExistsError, match="--reprendre"):
        entrainer(config_test(tmp_path), arreter_apres=4)


def test_reprendre_sans_sauvegarde_part_du_debut(tmp_path, capsys):
    r = entrainer(config_test(tmp_path), reprendre=True, arreter_apres=3)
    assert r["pas"] == 3 and len(r["pertes"]) == 3
    assert "Aucune sauvegarde" in capsys.readouterr().out


def test_reprise_avec_un_micro_lot_plus_petit(tmp_path):
    """Après un manque de mémoire, on réduit micro_lot : les mêmes jetons, en plus de morceaux."""
    a = entrainer(config_test(tmp_path / "a"), arreter_apres=12)["pertes"]
    entrainer(config_test(tmp_path / "b"), arreter_apres=6)
    b = entrainer(config_test(tmp_path / "b", micro_lot=1), reprendre=True, arreter_apres=12)["pertes"]
    assert a[6:12] == pytest.approx(b, abs=1e-4)


def test_micro_lot_qui_ne_divise_pas_le_lot(tmp_path):
    with pytest.raises(ValueError, match="micro_lot"):
        entrainer(config_test(tmp_path, micro_lot=3), arreter_apres=1)


def test_reprise_refusee_si_le_modele_change(tmp_path):
    entrainer(config_test(tmp_path), arreter_apres=2)
    autre = replace(MODELE_TEST, dim=64)
    with pytest.raises(ValueError, match="modèle"):
        entrainer(config_test(tmp_path, preset=autre), reprendre=True, arreter_apres=4)


def test_reprise_refusee_si_un_reglage_du_calcul_change(tmp_path):
    entrainer(config_test(tmp_path), arreter_apres=2)
    changee = config_test(tmp_path, betas=(0.5, 0.6), poids_decroissance=0.0, taille_lot_jetons=128)
    with pytest.raises(ValueError, match="La configuration a changé") as erreur:
        entrainer(changee, reprendre=True, arreter_apres=4)
    for reglage in ("betas", "poids_decroissance", "taille_lot_jetons"):
        assert reglage in str(erreur.value)
    for reglage, valeur in (("ecretage", 0.5), ("graine", 7), ("echauffement", 9), ("jetons_total", 64 * 30)):
        with pytest.raises(ValueError, match=reglage):
            entrainer(config_test(tmp_path, **{reglage: valeur}), reprendre=True, arreter_apres=4)
    with pytest.raises(ValueError, match="taux_max"):  # le taux ne peut que baisser
        entrainer(config_test(tmp_path, taux_max=2e-2), reprendre=True, arreter_apres=4)


def test_reprise_avec_les_reglages_libres(tmp_path, monkeypatch):
    entrainer(config_test(tmp_path), arreter_apres=2)
    # compiler = "auto" : on évite le vrai essai de torch.compile, lent sur le processeur.
    monkeypatch.setattr(torch, "compile", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("pas ici")))
    libre = config_test(tmp_path, micro_lot=1, compiler="auto", sauvegarde_minutes=5, evaluation_tous_pas=3)
    assert entrainer(libre, reprendre=True, arreter_apres=4)["pas"] == 4


def test_reprise_jetons_total_augmente_et_taux_max_baisse(tmp_path):
    entrainer(config_test(tmp_path), arreter_apres=2)
    plus_long = config_test(tmp_path, jetons_total=64 * 80, taux_max=5e-3)
    r = entrainer(plus_long, reprendre=True, arreter_apres=4)
    assert r["pas_total"] == 80
    messages = [l["message"] for l in lire_journal(tmp_path) if l.get("evenement") == "configuration"]
    assert any("jetons_total" in m for m in messages) and any("taux_max" in m for m in messages)
    # La sauvegarde suivante enregistre la nouvelle configuration.
    assert charger_derniere(tmp_path / "sauvegardes")["config"]["jetons_total"] == 64 * 80


def test_perte_infinie_arrete_sans_sauvegarder(tmp_path, monkeypatch, capsys):
    vrai_pas = boucle._pas_d_optimisation
    appels = []

    def pas_qui_diverge(modele, *a, **k):
        appels.append(1)
        if len(appels) == 3:
            with torch.no_grad():
                modele.plongement.weight.fill_(math.nan)  # comme une divergence
        return vrai_pas(modele, *a, **k)

    monkeypatch.setattr(boucle, "_pas_d_optimisation", pas_qui_diverge)
    with pytest.raises(SystemExit) as sortie:
        # Sauvegarde à chaque pas : les pas 1 et 2 sont sauvegardés, le pas 3 ne doit pas l'être.
        entrainer(config_test(tmp_path, sauvegarde_minutes=1e-9), arreter_apres=10)
    assert sortie.value.code == 3
    assert (
        "La perte est devenue infinie au pas 3 : l'entraînement s'arrête sans sauvegarder ; "
        "reprends depuis la dernière sauvegarde avec un taux_max plus petit."
    ) in capsys.readouterr().err
    assert charger_derniere(tmp_path / "sauvegardes")["pas"] == 2


def test_validation_ne_depend_pas_du_micro_lot(tmp_path):
    ecrire_corpus(tmp_path)
    torch.manual_seed(0)
    modele = boucle.Transformer(MODELE_TEST)
    valeurs = []
    for micro_lot in (2, 3, 4):
        chargeur = ChargeurJetons(tmp_path / "val", longueur=16, taille_lot=micro_lot, graine=1234)
        valeurs.append(boucle._perte_validation(modele, chargeur, chargeur.etat(), 12, torch.device("cpu")))
    assert valeurs[0] == pytest.approx(valeurs[1], rel=1e-6) == pytest.approx(valeurs[2], rel=1e-6)


def test_accumulation_moyenne_les_gradients(tmp_path):
    """Un pas en 2 micro-lots de 2 lignes, ou en 1 micro-lot de 4 : les mêmes gradients."""
    ecrire_corpus(tmp_path)
    gradients = []
    for micro_lot, accumulation in ((2, 2), (4, 1)):
        torch.manual_seed(0)
        modele = boucle.Transformer(MODELE_TEST)
        optimiseur = torch.optim.AdamW(modele.parameters(), lr=0.0)
        chargeur = ChargeurJetons(tmp_path / "train", longueur=16, taille_lot=micro_lot, graine=8)
        boucle._pas_d_optimisation(modele, optimiseur, chargeur, accumulation, 0.0, 1e9, torch.device("cpu"))
        gradients.append([p.grad.clone() for p in modele.parameters()])
    for deux_fois_deux, une_fois_quatre in zip(*gradients):
        assert torch.allclose(deux_fois_deux, une_fois_quatre, atol=1e-6, rtol=1e-5)


def test_fin_d_entrainement(tmp_path):
    r = entrainer(config_test(tmp_path, jetons_total=64 * 6))
    assert r["termine"] and r["pas"] == 6 and len(r["pertes"]) == 6
    assert charger_derniere(tmp_path / "sauvegardes")["pas"] == 6
    encore = entrainer(config_test(tmp_path, jetons_total=64 * 6), reprendre=True)
    assert encore["termine"] and encore["pertes"] == []


def test_compilation_auto_repli_silencieux(tmp_path, monkeypatch, capsys):
    attendu = entrainer(config_test(tmp_path / "non"), arreter_apres=4)["pertes"]

    def compile_qui_echoue(modele, *a, **k):
        def appel(*a, **k):
            raise RuntimeError("Cannot find a working triton installation")

        return appel

    monkeypatch.setattr(torch, "compile", compile_qui_echoue)
    capsys.readouterr()
    r = entrainer(config_test(tmp_path / "auto", compiler="auto"), arreter_apres=4)
    assert r["pertes"] == pytest.approx(attendu, abs=1e-6)
    assert "triton" not in capsys.readouterr().err  # pas de trace à l'écran
    messages = [ligne for ligne in lire_journal(tmp_path / "auto") if ligne.get("evenement") == "compilation"]
    assert len(messages) == 1 and "mode immédiat" in messages[0]["message"]


def test_compilation_oui_qui_echoue(tmp_path, monkeypatch):
    def compile_qui_echoue(modele, *a, **k):
        raise RuntimeError("pas de compilateur")

    monkeypatch.setattr(torch, "compile", compile_qui_echoue)
    with pytest.raises(boucle.CompilationImpossible, match="compiler"):
        entrainer(config_test(tmp_path, compiler="oui"), arreter_apres=1)


def test_config_mini_toml():
    config = lire_config(RACINE_DU_PROJET / "configs" / "mini.toml")
    assert config.preset == "mini" and config.appareil == "cuda"
    assert config.taille_lot_jetons % (config.micro_lot * 512) == 0
    assert config.fichier.endswith("mini.toml")


def test_config_principal_toml():
    # Le choix de l'utilisateur après la mesure de la tâche 10 : la carte, la taille « tres_grand »,
    # 20 jetons par paramètre.
    config = lire_config(RACINE_DU_PROJET / "configs" / "principal.toml")
    assert config.preset == "tres_grand" and config.appareil == "cuda"
    assert config.micro_lot == 1 and config.accumulation == 256
    assert config.taille_lot_jetons == 524_288 and config.pas_total == 16_540
    assert config.taux_max == 4e-4 and config.echauffement == 500
    # 20 jetons par paramètre, arrondis au pas entier au-dessus.
    parametres = nombre_parametres(config.modele)
    assert parametres == 433_573_120
    assert 20 * parametres <= config.jetons_total < 20 * parametres + config.taille_lot_jetons


def test_config_cle_inconnue(tmp_path):
    fichier = tmp_path / "faux.toml"
    fichier.write_text('preset = "mini"\nmicrolot = 4\n', encoding="utf-8")
    with pytest.raises(ValueError, match="microlot"):
        lire_config(fichier)


def test_commande_entrainer(tmp_path, capsys):
    ecrire_corpus(tmp_path / "jetons")
    fichier = tmp_path / "essai.toml"
    fichier.write_text(
        "\n".join(
            [
                f"donnees = '{tmp_path / 'jetons'}'",
                f"sortie = '{tmp_path / 'sortie'}'",
                "jetons_total = 384",
                "taille_lot_jetons = 64",
                "micro_lot = 2",
                "taux_max = 0.01",
                "echauffement = 2",
                "evaluation_tous_pas = 3",
                'appareil = "cpu"',
                'compiler = "non"',
                "[preset]",
                "taille_vocabulaire = 128",
                "dim = 32",
                "couches = 2",
                "tetes = 2",
                "longueur_contexte = 16",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    assert main(["entrainer", "--config", str(fichier)]) == 0
    assert charger_derniere(tmp_path / "sortie" / "sauvegardes")["pas"] == 6
    # Relancer sans --reprendre ne détruit pas l'entraînement fait : message et code 1.
    assert main(["entrainer", "--config", str(fichier)]) == 1
    assert "--reprendre" in capsys.readouterr().err
    assert main(["entrainer", "--config", str(fichier), "--reprendre"]) == 0
