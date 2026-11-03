"""Tests de l'entraînement de « ton IA » : planning, chargeur, sauvegardes, pause et reprise.

Tout tourne sur le processeur, avec un modèle minuscule (vocabulaire 128, dim 32, 2 couches,
contexte 16) et un petit corpus de jetons répétitifs écrit par le test, sauf le test marqué
`gpu`. Le corpus a la forme de celui de `forge encoder` : `train/` et `val/`, `index.json` et
`.complet`. Le chargeur coupe ses trois fragments en 51 morceaux de 17 jetons, mélangés à
chaque époque : les tests de reprise traversent un changement d'époque.
"""

import errno
import json
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
from forge.modele import ConfigModele
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
    assert a[10:20] == pytest.approx(b, abs=1e-6)


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


def test_disque_plein_pendant_l_ecriture(tmp_path, monkeypatch):
    def save_qui_remplit_le_disque(etat, fichier, *a, **k):
        fichier.write(b"debut")
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr("forge.entrainement.sauvegarde.torch.save", save_qui_remplit_le_disque)
    with pytest.raises(PlaceInsuffisante, match="--reprendre"):
        sauvegarder(tmp_path, {"pas": 1}, "etape-0000001.pt")
    assert not list(tmp_path.iterdir())


def test_disque_plein_en_ecrivant_le_journal(tmp_path):
    class FichierPlein:
        def write(self, texte):
            raise OSError(errno.ENOSPC, "No space left on device")

        def close(self):
            pass

    journal = boucle._Journal(tmp_path / "journal.jsonl")
    journal._fichier.close()
    journal._fichier = FichierPlein()
    with pytest.raises(PlaceInsuffisante, match="--reprendre"):
        journal.ecrire({"pas": 1})


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
    assert reference[3:8] == pytest.approx(suite, abs=1e-6)


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
