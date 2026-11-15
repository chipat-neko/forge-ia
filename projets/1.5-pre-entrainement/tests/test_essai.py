"""L'essai de pause et de reprise : les données minuscules, la configuration, et la reprise exacte.

Tout tourne sur le processeur, sauf le test marqué `gpu` (sauté sans carte graphique). Les essais
écrivent dans le dossier temporaire du test, jamais dans les données de « ton IA ».
"""

import json
import pathlib
import re
import time

import numpy as np
import pytest
from forge.entrainement import ChargeurJetons
from forge.tokenizer import TokenizerOctets

from pre_entrainement import essai
from pre_entrainement.essai import config_essai, essai_pause_reprise, preparer_essai, texte_du_site

TOKENIZER = essai.TOKENIZER
TEXTE = "Le forgeron frappe le fer rouge sur l'enclume. " * 120 + "Puis il le plonge dans l'eau. " * 60


def test_preparer_essai_ecrit_le_format_de_forge(tmp_path):
    dossier = preparer_essai(tmp_path, TEXTE)
    assert dossier == tmp_path / "jetons"
    assert sorted(p.name for p in dossier.iterdir()) == [".complet", "index.json", "train", "val"]
    index = json.loads((dossier / "index.json").read_text(encoding="utf-8"))
    assert index["version"] == 1
    assert sorted(index["fichiers"]) == ["train/fragment-00000.bin", "val/fragment-00000.bin"]
    # Les fichiers sont en uint16 petit-boutiste, et l'index dit combien de jetons ils ont.
    train = np.fromfile(dossier / "train" / "fragment-00000.bin", dtype="<u2")
    val = np.fromfile(dossier / "val" / "fragment-00000.bin", dtype="<u2")
    assert len(train) == index["fichiers"]["train/fragment-00000.bin"]
    assert len(val) == index["fichiers"]["val/fragment-00000.bin"]
    # Le texte, encodé par le tokenizer figé, suivi de <|fin_texte|> ; 90 % à l'entraînement.
    tokenizer = TokenizerOctets.charger(TOKENIZER)
    jetons = tokenizer.encoder(TEXTE) + [tokenizer.id_special("<|fin_texte|>")]
    assert list(train) + list(val) == jetons
    assert len(train) == int(0.9 * len(jetons))
    assert val[-1] == tokenizer.id_special("<|fin_texte|>")


def test_le_chargeur_de_forge_lit_le_dossier(tmp_path):
    dossier = preparer_essai(tmp_path, TEXTE)
    entrainement = ChargeurJetons(dossier / "train", 64, 4, 0)
    validation = ChargeurJetons(dossier / "val", 64, 4, 0)
    assert entrainement.morceaux > 0 and validation.morceaux > 0
    x, y = entrainement.lot()
    assert tuple(x.shape) == (4, 64) and tuple(y.shape) == (4, 64)


def test_le_texte_du_site_donne_de_quoi_entrainer(tmp_path):
    # Le texte réel : assez de morceaux de 65 jetons pour 60 pas de 16 lignes, et pour valider.
    dossier = preparer_essai(tmp_path, texte_du_site())
    assert ChargeurJetons(dossier / "train", 64, 16, 0).morceaux >= 16
    assert ChargeurJetons(dossier / "val", 64, 16, 0).morceaux >= 1


def test_preparer_essai_refuse_un_texte_trop_court(tmp_path):
    with pytest.raises(ValueError, match="trop court"):
        preparer_essai(tmp_path, "Bonjour.")


def test_config_essai(tmp_path):
    c = config_essai("cpu", tmp_path)
    assert (c.modele.dim, c.modele.couches, c.modele.tetes, c.modele.longueur_contexte) == (64, 2, 4, 64)
    assert c.modele.taille_vocabulaire == 32768
    assert (c.taille_lot_jetons, c.micro_lot, c.taux_max, c.echauffement) == (1024, 16, 1e-3, 6)
    assert (c.evaluation_tous_pas, c.compiler, c.appareil) == (20, "non", "cpu")
    assert c.pas_total == 60 and c.accumulation == 1
    # Les chemins sont sous la racine donnée : l'essai n'écrit rien ailleurs.
    assert pathlib.Path(c.donnees) == tmp_path / "jetons"
    assert c.dossier_sortie.parent == tmp_path
    assert config_essai("cuda", tmp_path, pas=30).pas_total == 30
    assert config_essai("cuda", tmp_path).appareil == "cuda"


# region: test-reprise
def test_reprise_exacte_sur_le_processeur(tmp_path):
    r = essai_pause_reprise("cpu", tmp_path)
    assert r["ecart"] == 0.0
    # De plus : la moitié de l'entraînement est refaite, pas à pas, avec les mêmes pertes.
    assert r["pas_de_la_pause"] == 30 and r["pertes_identiques"]
# fin: test-reprise


def test_le_resultat_de_l_essai_et_son_silence(tmp_path, capsys):
    r = essai_pause_reprise("cpu", tmp_path / "essai")
    assert r["appareil"] == "cpu" and r["pas_total"] == 60 and r["secondes"] > 0
    assert r["perte_un_trait"] == r["perte_reprise"]
    assert 0 < r["perte_un_trait"] < 10.4  # sous le hasard, ln 32 768 = 10,397
    assert r["ecart"] == abs(r["perte_un_trait"] - r["perte_reprise"])
    json.dumps(r, allow_nan=False)
    # Tout est écrit sous la racine donnée.
    assert sorted(p.name for p in (tmp_path / "essai").iterdir()) == ["d-un-trait", "en-pause", "jetons"]
    # La boucle de forge affiche sa progression ; l'essai la garde pour lui, la sortie de la
    # commande n'a que les lignes du résumé.
    assert capsys.readouterr().out == ""


def entrainements_simules(monkeypatch, appels: list) -> None:
    """Remplace l'entraînement de forge par un faux, instantané, qui note le dossier de chaque entraînement."""

    def faux_entrainer(config, reprendre=False, arreter_apres=None):
        appels.append(pathlib.Path(config.sortie).name)
        pas = arreter_apres or config.pas_total
        return {"pertes": [7.5] * (pas - (config.pas_total // 2 if reprendre else 0))}

    monkeypatch.setattr(essai, "entrainer", faux_entrainer)


@pytest.mark.parametrize("appareil, echauffee", [("cuda", True), ("cpu", False)])
def test_l_echauffement_de_la_carte_passe_avant_le_chronometre(monkeypatch, tmp_path, appareil, echauffee):
    # Sans carte : les entraînements sont simulés. Sur la carte (et seulement sur elle), l'échauffement
    # passe d'abord, et sa durée (ici 0,3 s) n'entre pas dans les secondes de l'essai.
    appels = []
    entrainements_simules(monkeypatch, appels)

    def faux_echauffement(base, racine):
        appels.append("échauffement")
        time.sleep(0.3)
        return 0.3

    monkeypatch.setattr(essai, "echauffer_la_carte", faux_echauffement)
    r = essai_pause_reprise(appareil, tmp_path)
    attendus = ["d-un-trait", "en-pause", "en-pause"]
    assert appels == (["échauffement", *attendus] if echauffee else attendus)
    assert r["secondes_echauffement"] == (0.3 if echauffee else 0.0)
    assert r["secondes"] < 0.25 and r["ecart"] == 0.0


def test_echauffer_la_carte_fait_deux_pas_dans_son_dossier(monkeypatch, tmp_path):
    import torch

    appels, configs, attentes = [], [], []
    entrainements_simules(monkeypatch, appels)
    vrai_faux = essai.entrainer
    monkeypatch.setattr(essai, "entrainer", lambda config, **options: (configs.append(config), vrai_faux(config, **options))[1])
    monkeypatch.setattr(torch.cuda, "synchronize", lambda *a: attentes.append("synchronisée"))
    base = config_essai("cuda", tmp_path)
    secondes = essai.echauffer_la_carte(base, tmp_path)
    assert appels == ["echauffement"] and attentes == ["synchronisée"] and secondes >= 0
    (config,) = configs
    # Le même modèle, le même appareil, les mêmes lots : seuls le nombre de pas et le dossier changent.
    assert config.pas_total == 2 and config.appareil == "cuda" and config.modele == base.modele
    assert config.taille_lot_jetons == base.taille_lot_jetons and pathlib.Path(config.sortie) == tmp_path / "echauffement"


@pytest.mark.gpu
def test_essai_sur_la_carte(tmp_path):
    # Sur la carte, deux entraînements identiques peuvent différer un peu (la carte additionne dans un
    # ordre qui varie) : on ne demande pas 0, seulement une reprise qui ne s'écarte pas.
    r = essai_pause_reprise("cuda", tmp_path)
    assert r["appareil"] == "cuda"
    assert 0 < r["perte_un_trait"] < 10.4 and 0 < r["perte_reprise"] < 10.4
    assert r["ecart"] < 0.1


def test_regions_de_essai():
    lignes = pathlib.Path(essai.__file__).read_text(encoding="utf-8").splitlines()
    ouvertes = [m.group(1) for ligne in lignes if (m := re.match(r"\s*# region: (\S+)", ligne))]
    fermees = [m.group(1) for ligne in lignes if (m := re.match(r"\s*# fin: (\S+)", ligne))]
    assert ouvertes == ["essai-donnees", "essai-reprise"]
    assert fermees == ouvertes


def test_le_releve_de_l_essai_sur_la_carte():
    projet = pathlib.Path(__file__).resolve().parents[1]
    chemin, texte = projet / "mesures" / "essai-rtx-5070-ti.json", projet / "sorties" / "essai-rtx-5070-ti.txt"
    if not chemin.exists():
        pytest.skip("L'essai sur la carte n'est pas encore relevé (voir le README du projet).")
    releve = json.loads(chemin.read_text(encoding="utf-8"))
    assert releve["appareil"] == "cuda" and releve["pas_total"] == 60 and releve["pas_de_la_pause"] == 30
    assert releve["ecart"] == abs(releve["perte_un_trait"] - releve["perte_reprise"]) and releve["ecart"] < 0.1
    assert releve["secondes_echauffement"] > 0  # l'échauffement de la carte, hors des secondes de l'essai
    lignes = texte.read_text(encoding="utf-8").splitlines()
    assert lignes[0] == f"# relevé le {releve['releve_le']}"
    assert lignes[1].startswith("Pause et reprise exacte, sur la carte graphique, NVIDIA GeForce RTX 5070 Ti")
