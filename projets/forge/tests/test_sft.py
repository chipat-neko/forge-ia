"""Tests de l'affinage supervisé (SFT, plan 7, tâche 6) : départ d'une version publiée, perte au
niveau du jeton, pause et reprise, sauvegardes et export.

Tout tourne sur le processeur avec un modèle minuscule (vocabulaire 128, dim 32, 2 couches,
contexte 16), sauf le test marqué `gpu`. Le jeu d'affinage est écrit par le test, comme
`forge preparer` l'écrira : des « conversations » `1 question 2 réponse 3` dont seule la réponse
(et son `3`) est apprise, empaquetées en rangées de 17 jetons. La version de départ est un petit
modèle exporté par `forge exporter`, comme une Release.
"""

import copy
import dataclasses
import json
import math
import shutil
import signal
import warnings
from pathlib import Path

import numpy as np
import pytest
import torch
import torch.nn.functional as F

from test_entrainement import config_test, lire_journal

from forge.__main__ import main
from forge.affinage.empaquetage import Rangee, empaqueter
from forge.affinage.jeu import IGNORE, LotAffinage, ecrire_jeu
from forge.conversation.format import ExempleMasque
from forge.donnees.jetons import empreinte_du_tokenizer
from forge.entrainement import METHODES, ConfigEntrainement, charger_derniere, entrainer
from forge.entrainement import boucle
from forge.entrainement.methodes import pas_sft, perte_sft_validation
from forge.entrainement.sauvegarde import VERSION_DE_LA_SAUVEGARDE, sauvegarder
from forge.exporter import TokenizerNonVerifie, empreinte_sha256, exporter
from forge.fichiers import ecrire_atomique
from forge.modele import ConfigModele, Transformer
from forge.publication import charger_publication, nom_des_poids
from forge.tokenizer import TokenizerOctets

TOKENIZER = Path(__file__).resolve().parents[1] / "forge" / "ressources" / "tokenizer-ton-ia-v1.json"
TOK = TokenizerOctets.charger(TOKENIZER)
EMPREINTE = empreinte_du_tokenizer(TOK)  # SHA-1 des fusions, celle d'index.json et des sauvegardes

MODELE_SFT = ConfigModele(taille_vocabulaire=128, dim=32, couches=2, tetes=2, longueur_contexte=16)
BOURRAGE = 0
ETIQUETTE = "ton-ia-essai"
CPU = torch.device("cpu")


# --- Les données et la version de départ ------------------------------------------------


def exemples(nombre: int, graine: int) -> list[ExempleMasque]:
    """`1 q… 2 r… 3`, avec r = q + 50 : la réponse et le `3` final sont appris, la question non."""
    hasard = np.random.default_rng(graine)
    liste = []
    for _ in range(nombre):
        question = hasard.integers(10, 60, size=int(hasard.integers(2, 5))).tolist()
        reponse = [jeton + 50 for jeton in question]
        ids = [1, *question, 2, *reponse, 3]
        appris = [False] * (len(question) + 2) + [True] * (len(reponse) + 1)
        liste.append(ExempleMasque(ids=ids, appris=appris))
    return liste


def ecrire_jeu_sft(dossier: Path, en_plus: list[Rangee] = ()) -> Path:
    """Un jeu `sft` de rangées de 17 jetons (rien si c'est déjà fait) ; `en_plus` s'ajoute à `train`."""
    if (dossier / ".complet").exists():
        return dossier
    train, ecartes = empaqueter(exemples(48, graine=1), longueur=16, bourrage=BOURRAGE)
    val, _ = empaqueter(exemples(10, graine=2), longueur=16, bourrage=BOURRAGE)
    sources = {"essai": {"exemples": 58, "licence": "CC0", "lien": "https://example.org"}}
    ecrire_jeu(dossier, [*train, *en_plus], val, "sft", {"ecartes": ecartes, "sources": sources}, TOK)
    return dossier


def publier(dossier: Path, config: ConfigModele = MODELE_SFT, graine: int = 0, etiquette: str = ETIQUETTE) -> Path:
    """Exporte un modèle tiré de `graine`, comme une version publiée (rien si c'est déjà fait)."""
    if dossier.is_dir():
        return dossier
    torch.manual_seed(graine)
    etat = {
        "version": VERSION_DE_LA_SAUVEGARDE,
        "pas": 0,
        "modele": Transformer(config).state_dict(),
        "config": {},
        "config_modele": dataclasses.asdict(config),
        "empreinte_du_tokenizer": EMPREINTE,
    }
    sauvegarde = sauvegarder(dossier.parent / f"{dossier.name}-sauvegarde", etat, "meilleur.pt")
    exporter(sauvegarde, dossier, nom_des_poids(etiquette))
    return dossier


def cfg_sft(dossier: Path, **changements) -> ConfigEntrainement:
    """Un SFT minuscule : 64 positions par pas (2 micro-lots de 2 rangées de 16), 20 pas en tout.

    Le jeu et la version de départ sont rangés à côté de `dossier`, dans `commun/` : deux
    entraînements du même `tmp_path` lisent les mêmes.
    """
    commun = dossier.parent / "commun"
    valeurs = dict(
        methode="sft",
        depart=str(publier(commun / ETIQUETTE)),
        preset=MODELE_SFT,
        donnees=str(ecrire_jeu_sft(commun / "jeu")),
        jetons_total=64 * 20,
        taille_lot_jetons=64,
        micro_lot=2,
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


# --- Des lots faits à la main, pour `pas_sft` ---------------------------------------------


class FauxChargeur:
    """Rend les lots donnés, dans l'ordre."""

    def __init__(self, lots: list[LotAffinage]) -> None:
        self._lots = list(lots)

    def lot(self) -> LotAffinage:
        return self._lots.pop(0)


def cfg_pas(accumulation: int = 2) -> ConfigEntrainement:
    """`accumulation` micro-lots d'une rangée de 16 par pas ; pas d'écrêtage (on compare les gradients)."""
    return ConfigEntrainement(
        methode="sft",
        depart="inutile",
        preset=MODELE_SFT,
        donnees="inutile",
        jetons_total=16 * accumulation,
        taille_lot_jetons=16 * accumulation,
        micro_lot=1,
        taux_max=1e-2,
        echauffement=0,
        ecretage=1e9,
        evaluation_tous_pas=1,
        appareil="cpu",
        compiler="non",
        sortie="inutile",
    )


def lot_avec(appris: list[int], graine: int, documents: list[int] | None = None) -> LotAffinage:
    """Une rangée de 16 jetons tirés au hasard, dont seules les positions `appris` ont une cible."""
    hasard = torch.Generator().manual_seed(graine)
    ids = torch.randint(4, 120, (1, 17), generator=hasard)
    cibles = torch.full((1, 16), IGNORE)
    cibles[0, appris] = ids[0, 1:][appris]
    docs = torch.zeros((1, 16), dtype=torch.long) if documents is None else torch.tensor([documents])
    return LotAffinage(ids=ids[:, :-1].clone(), cibles=cibles, documents=docs)


def lot_de_bourrage() -> LotAffinage:
    return LotAffinage(
        ids=torch.full((1, 16), BOURRAGE),
        cibles=torch.full((1, 16), IGNORE),
        documents=torch.full((1, 16), -1),
    )


def faire_un_pas(lots: list[LotAffinage], graine: int = 0) -> tuple[dict, Transformer]:
    """`pas_sft` à taux nul sur un modèle tiré de `graine` : rend le résultat et le modèle (ses gradients)."""
    torch.manual_seed(graine)
    modele = Transformer(MODELE_SFT)
    config = cfg_pas(len(lots))
    optimiseur = boucle.creer_optimiseur(modele, config, CPU)
    return pas_sft(modele, optimiseur, FauxChargeur(lots), config, 0.0, CPU, {}, numero=1), modele


def pertes_des_jetons(modele: Transformer, lot: LotAffinage) -> torch.Tensor:
    """La perte de chaque jeton appris du lot, calculée sans `pas_sft`."""
    logits, _ = modele(lot.ids, documents=lot.documents)
    pertes = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), lot.cibles.reshape(-1), reduction="none")
    return pertes[lot.cibles.reshape(-1) != IGNORE]


def gradients(modele: torch.nn.Module) -> dict[str, torch.Tensor]:
    return {nom: p.grad.clone() for nom, p in modele.named_parameters() if p.grad is not None}


def remplacer_le_sft(monkeypatch, **fonctions):
    """Le temps du test, la méthode « sft » du registre a ces fonctions-là à la place des siennes."""
    monkeypatch.setitem(METHODES, "sft", dataclasses.replace(METHODES["sft"], **fonctions))


# --------------------------------------------------------------------------------------
# Les tests du plan
# --------------------------------------------------------------------------------------


def test_sft_reprise_exacte(tmp_path):
    a = entrainer(cfg_sft(tmp_path / "a"), arreter_apres=12)["pertes"]
    entrainer(cfg_sft(tmp_path / "b"), arreter_apres=6)
    b = entrainer(cfg_sft(tmp_path / "b"), reprendre=True, arreter_apres=12)["pertes"]
    assert len(a) == 12 and len(b) == 6
    assert a[6:12] == b  # au bit près sur le processeur


def test_sft_pause_par_ctrl_c(tmp_path, monkeypatch, capsys):
    """Point à surveiller 3 : Ctrl+C au milieu d'un SFT, puis la reprise, donnent les pertes d'une traite."""
    reference = entrainer(cfg_sft(tmp_path / "ref"), arreter_apres=8)["pertes"]
    sft = METHODES["sft"]
    faits = []

    def pas_puis_ctrl_c(*a, **k):
        resultat = sft.pas(*a, **k)
        faits.append(resultat)
        if len(faits) == 3:
            signal.raise_signal(signal.SIGINT)  # comme Ctrl+C au milieu du pas 3
        return resultat

    monkeypatch.setitem(METHODES, "sft", dataclasses.replace(sft, pas=pas_puis_ctrl_c))
    config = cfg_sft(tmp_path / "pause", fichier="configs/sft-essai.toml")
    r = entrainer(config, arreter_apres=8)
    assert r["en_pause"] and r["pas"] == 3
    assert "python -m forge entrainer --config configs/sft-essai.toml --reprendre" in capsys.readouterr().out
    monkeypatch.setitem(METHODES, "sft", sft)
    suite = entrainer(config, reprendre=True, arreter_apres=8)["pertes"]
    assert reference[3:8] == suite  # au bit près sur le processeur


def test_perte_au_niveau_du_jeton():
    """Un micro-lot à 1 jeton appris, un autre à 9 : la perte du pas est la moyenne sur les 10 jetons."""
    lots = [lot_avec([5], graine=1), lot_avec([1, 2, 3, 6, 8, 9, 11, 13, 15], graine=2)]
    resultat, modele = faire_un_pas(lots)
    torch.manual_seed(0)
    reference = Transformer(MODELE_SFT)
    une, neuf = (pertes_des_jetons(reference, lot) for lot in lots)
    attendue = (une.sum() + neuf.sum()) / 10
    assert resultat["jetons_appris"] == 10
    assert resultat["perte"] == pytest.approx(attendue.item(), rel=1e-6)
    moyenne_des_moyennes = (une.mean() + neuf.mean()).item() / 2
    assert resultat["perte"] != pytest.approx(moyenne_des_moyennes, rel=1e-3)  # le choix 5 du plan
    attendue.backward()
    attendus = gradients(reference)
    for nom, gradient in gradients(modele).items():
        torch.testing.assert_close(gradient, attendus[nom], msg=nom)


def test_cible_non_apprise_sans_effet():
    """Changer un jeton dont la cible vaut -100, dans un document sans jeton appris : ni la perte ni les
    gradients ne bougent. Que ce document vienne après celui qui apprend (la causalité le cache) ou
    avant (seul le masque par document le cache)."""
    documents = [0] * 8 + [1] * 8
    for appris, position in (([2, 4, 6], 12), ([10, 12, 14], 3)):
        lot = lot_avec(appris, graine=3, documents=documents)
        change = copy.deepcopy(lot)
        change.ids[0, position] = (lot.ids[0, position] + 7) % 120
        a, modele_a = faire_un_pas([lot])
        b, modele_b = faire_un_pas([change])
        assert a["perte"] == b["perte"], position
        grads_b = gradients(modele_b)
        for nom, gradient in gradients(modele_a).items():
            assert torch.equal(gradient, grads_b[nom]), (position, nom)
    # Le test n'est pas vide : sans le masque par document (un seul document), le même changement
    # avant les jetons appris change la perte ; et dans le document qui apprend aussi.
    seul = lot_avec([10, 12, 14], graine=3)
    change = copy.deepcopy(seul)
    change.ids[0, 3] = (seul.ids[0, 3] + 7) % 120
    assert faire_un_pas([change])[0]["perte"] != faire_un_pas([seul])[0]["perte"]
    lot = lot_avec([2, 4, 6], graine=3, documents=documents)
    autre = copy.deepcopy(lot)
    autre.ids[0, 1] = (lot.ids[0, 1] + 7) % 120
    assert faire_un_pas([autre])[0]["perte"] != faire_un_pas([lot])[0]["perte"]


def test_part_de_la_version_publiee(tmp_path, monkeypatch):
    """Au pas 0, quand l'optimiseur est créé, les poids sont ceux de `charger_publication`."""
    vus = []
    vrai = boucle.creer_optimiseur

    def creer_en_regardant(modele, *a, **k):
        vus.append({nom: t.detach().clone() for nom, t in modele.state_dict().items()})
        return vrai(modele, *a, **k)

    monkeypatch.setattr(boucle, "creer_optimiseur", creer_en_regardant)
    config = cfg_sft(tmp_path / "sft")
    entrainer(config, arreter_apres=1)
    publies = charger_publication(Path(config.depart)).modele.state_dict()
    assert len(vus) == 1 and vus[0].keys() == publies.keys()
    for nom, tenseur in publies.items():
        assert torch.equal(vus[0][nom], tenseur), nom


def test_depart_d_autres_dimensions(tmp_path):
    autre = publier(tmp_path / "autre", dataclasses.replace(MODELE_SFT, dim=64), etiquette="ton-ia-large")
    with pytest.raises(ValueError, match="autres dimensions") as erreur:
        entrainer(cfg_sft(tmp_path / "sft", depart=str(autre)), arreter_apres=1)
    assert "ton-ia-large" in str(erreur.value) and "dim 64" in str(erreur.value)
    assert not (tmp_path / "sft" / "sauvegardes").exists()


def test_rangee_toute_de_bourrage(tmp_path):
    """Point à surveiller 2 : une rangée sans aucun jeton appris ne donne ni NaN ni arrêt « perte infinie »."""
    # Un micro-lot entier de bourrage, à côté d'un micro-lot normal : la perte est celle du second.
    normal = lot_avec([3, 7, 9], graine=4)
    resultat, modele = faire_un_pas([lot_de_bourrage(), normal])
    torch.manual_seed(0)
    attendue = pertes_des_jetons(Transformer(MODELE_SFT), normal).mean()
    assert resultat["jetons_appris"] == 3 and resultat["perte"] == pytest.approx(attendue.item(), rel=1e-6)
    assert all(torch.isfinite(g).all() for g in gradients(modele).values())
    # De bout en bout : une rangée de bourrage dans le jeu, lue pendant l'entraînement.
    bourrage = Rangee(ids=[BOURRAGE] * 17, appris=[False] * 17, documents=[-1] * 17)
    jeu = ecrire_jeu_sft(tmp_path / "jeu-bourrage", en_plus=[bourrage])
    r = entrainer(cfg_sft(tmp_path / "sft", donnees=str(jeu), micro_lot=1), arreter_apres=10)
    assert r["pas"] == 10 and all(math.isfinite(p) for p in r["pertes"])


def test_pas_sans_jeton_appris():
    with pytest.raises(ValueError, match="forge preparer"):
        faire_un_pas([lot_de_bourrage(), lot_de_bourrage()])


def test_longueur_differente_de_l_index(tmp_path):
    with pytest.raises(ValueError, match="longueur") as erreur:
        entrainer(cfg_sft(tmp_path / "sft", longueur=8, taille_lot_jetons=32), arreter_apres=1)
    assert "8" in str(erreur.value) and "16" in str(erreur.value)


# --------------------------------------------------------------------------------------
# La validation
# --------------------------------------------------------------------------------------


def test_perte_de_validation_par_jeton_appris(tmp_path):
    """La moyenne par jeton appris sur les n premières rangées, quelle que soit la taille des paquets."""
    from forge.affinage.jeu import ChargeurAffinage

    jeu = ecrire_jeu_sft(tmp_path / "jeu")
    torch.manual_seed(0)
    modele = Transformer(MODELE_SFT)
    valeurs = []
    for taille in (1, 2, 3):
        chargeur = ChargeurAffinage(jeu, "val", taille, graine=5)
        valeurs.append(perte_sft_validation(modele, chargeur, chargeur.etat(), 3, CPU))
    seul = ChargeurAffinage(jeu, "val", 3, graine=5).lot()
    with torch.no_grad():
        attendue = pertes_des_jetons(modele, seul).mean().item()
    assert valeurs == pytest.approx([attendue] * 3, rel=1e-5)


def test_le_journal_du_sft(tmp_path):
    r = entrainer(cfg_sft(tmp_path / "sft"), arreter_apres=10)
    lignes = [json.loads(l) for l in (tmp_path / "sft" / "journal.jsonl").read_text(encoding="utf-8").splitlines()]
    pas = [l for l in lignes if "perte" in l]
    assert [l["pas"] for l in pas] == list(range(1, 11))
    assert all(isinstance(l["jetons_appris"], int) and l["jetons_appris"] > 0 for l in pas)
    assert [l["pas"] for l in pas if "perte_val" in l] == [5, 10]
    assert (tmp_path / "sft" / "sauvegardes" / "meilleur.pt").is_file()
    assert r["meilleure_perte_val"] == min(l["perte_val"] for l in pas if "perte_val" in l)


# --------------------------------------------------------------------------------------
# Les sauvegardes, la reprise et l'export
# --------------------------------------------------------------------------------------


def test_la_sauvegarde_retient_la_methode_et_le_depart(tmp_path):
    config = cfg_sft(tmp_path / "sft")
    entrainer(config, arreter_apres=5)
    poids = Path(config.depart) / nom_des_poids(ETIQUETTE)
    for etat in (charger_derniere(tmp_path / "sft" / "sauvegardes"), torch.load(tmp_path / "sft" / "sauvegardes" / "meilleur.pt", weights_only=True)):
        assert etat["methode"] == "sft" and etat["config"]["methode"] == "sft"
        assert etat["depart_version"] == ETIQUETTE
        assert etat["depart_empreinte"] == empreinte_sha256(poids)
        assert etat["empreinte_du_tokenizer"] == EMPREINTE  # le SHA-1 du tokenizer de la version de départ


def test_l_empreinte_vient_du_depart_meme_sans_bloc_tokenizer(tmp_path):
    """L'index des problèmes du GRPO n'a pas de bloc `tokenizer` : la sauvegarde d'un affinage a quand même l'empreinte."""
    donnees = tmp_path / "problemes"
    donnees.mkdir()
    (donnees / "index.json").write_text(json.dumps({"version": 1}), encoding="utf-8")
    config = cfg_sft(tmp_path / "sft", donnees=str(donnees))
    depart = boucle.VersionDeDepart(version="ton-ia-x", empreinte_des_poids="a" * 64, empreinte_du_tokenizer=EMPREINTE)
    etat = boucle._etat_du_modele(config, Transformer(MODELE_SFT), 3, depart)
    assert etat["empreinte_du_tokenizer"] == EMPREINTE
    assert (etat["methode"], etat["depart_version"], etat["depart_empreinte"]) == ("sft", "ton-ia-x", "a" * 64)
    with pytest.raises(ValueError, match="départ"):
        boucle._etat_du_modele(config, Transformer(MODELE_SFT), 3)


def test_forge_exporter_accepte_un_sft_sans_avertissement(tmp_path, capsys):
    config = cfg_sft(tmp_path / "sft")
    entrainer(config, arreter_apres=3)
    capsys.readouterr()
    with warnings.catch_warnings():
        warnings.simplefilter("error", TokenizerNonVerifie)
        code = main(
            [
                "exporter",
                "--sauvegarde",
                str(tmp_path / "sft" / "sauvegardes"),
                "--sortie",
                str(tmp_path / "ton-ia-sft"),
                "--poids",
                "ton-ia-sft.safetensors",
            ]
        )
    erreur = capsys.readouterr().err
    assert code == 0 and "Attention" not in erreur and "Erreur" not in erreur
    assert charger_publication(tmp_path / "ton-ia-sft").version == "ton-ia-sft"


def test_exporter_ne_cherche_sous_jetons_que_pour_le_pre_entrainement(tmp_path, monkeypatch):
    """Le repli par l'`index.json` de `jetons/` ne vaut que pour une sauvegarde de pré-entraînement."""
    monkeypatch.setenv("FORGE_DONNEES", str(tmp_path))
    (tmp_path / "jetons" / "jeu-x").mkdir(parents=True)
    index = {"version": 1, "tokenizer": {"nom": "autre", "taille_vocabulaire": 128, "empreinte": "f" * 40}}
    (tmp_path / "jetons" / "jeu-x" / "index.json").write_text(json.dumps(index), encoding="utf-8")
    torch.manual_seed(0)
    base = {
        "version": VERSION_DE_LA_SAUVEGARDE,
        "pas": 3,
        "modele": Transformer(MODELE_SFT).state_dict(),
        "config_modele": dataclasses.asdict(MODELE_SFT),
    }
    # Un affinage sans empreinte (une sauvegarde abîmée) : jetons/ n'est pas lu, l'export avertit.
    affinage = sauvegarder(tmp_path / "a", {**base, "methode": "grpo", "config": {"methode": "grpo", "donnees": "jeu-x"}}, "meilleur.pt")
    with pytest.warns(TokenizerNonVerifie, match="pas pu être vérifié"):
        exporter(affinage, tmp_path / "sortie-a")
    # Le pré-entraînement, nouveau ou ancien (sans `methode`), est vérifié par l'index de jetons/ : refusé.
    for nom, config in (("b", {"methode": "pre_entrainement", "donnees": "jeu-x"}), ("c", {"donnees": "jeu-x"})):
        sauvegarde = sauvegarder(tmp_path / nom, {**base, "config": config}, "meilleur.pt")
        with pytest.raises(ValueError, match="autre tokenizer"):
            exporter(sauvegarde, tmp_path / f"sortie-{nom}")


def test_reprise_refusee_si_la_version_de_depart_change(tmp_path):
    entrainer(cfg_sft(tmp_path / "sft"), arreter_apres=2)
    autre = publier(tmp_path / "autre", graine=1, etiquette="ton-ia-autre")
    with pytest.raises(ValueError, match="version de départ") as erreur:
        entrainer(cfg_sft(tmp_path / "sft", depart=str(autre)), reprendre=True, arreter_apres=4)
    assert ETIQUETTE in str(erreur.value) and "ton-ia-autre" in str(erreur.value)
    # La même version, rangée ailleurs : le chemin est un réglage libre, la reprise a lieu.
    copie = tmp_path / "ailleurs"
    shutil.copytree(tmp_path / "commun" / ETIQUETTE, copie)
    assert entrainer(cfg_sft(tmp_path / "sft", depart=str(copie)), reprendre=True, arreter_apres=4)["pas"] == 4


def test_reprise_refusee_si_la_methode_change(tmp_path):
    entrainer(cfg_sft(tmp_path / "sft"), arreter_apres=2)
    pre = config_test(tmp_path / "pre", preset=MODELE_SFT, sortie=str(tmp_path / "sft"))
    with pytest.raises(ValueError, match="methode"):
        entrainer(pre, reprendre=True, arreter_apres=4)


def test_jeu_d_un_autre_tokenizer_refuse(tmp_path):
    jeu = tmp_path / "jeu-autre"
    shutil.copytree(ecrire_jeu_sft(tmp_path / "commun" / "jeu"), jeu)
    index = json.loads((jeu / "index.json").read_text(encoding="utf-8"))
    index["tokenizer"]["empreinte"] = "0" * 40
    (jeu / "index.json").write_text(json.dumps(index), encoding="utf-8")
    with pytest.raises(ValueError, match="tokenizer") as erreur:
        entrainer(cfg_sft(tmp_path / "sft", donnees=str(jeu)), arreter_apres=1)
    assert "0" * 40 in str(erreur.value) and EMPREINTE in str(erreur.value)


def test_jeu_d_une_autre_sorte_refuse(tmp_path):
    jeu = tmp_path / "jeu-dpo"
    rangees, _ = empaqueter(exemples(8, graine=3), longueur=16, bourrage=BOURRAGE)
    ecrire_jeu(jeu, rangees[:2], rangees[2:4], "dpo", {}, TOK)
    with pytest.raises(ValueError, match="dpo"):
        entrainer(cfg_sft(tmp_path / "sft", donnees=str(jeu)), arreter_apres=1)


# --------------------------------------------------------------------------------------
# Le contrat du registre : l'ordre des appels et ce que reçoivent `preparer` et `pas`
# --------------------------------------------------------------------------------------


def test_preparer_passe_avant_les_chargeurs(tmp_path, monkeypatch):
    """Un `reference.bin` que `preparer` écrit, en remplaçant un ancien, est celui que lit le premier lot.

    Les chargeurs n'ouvrent leurs fichiers qu'après `preparer` : sous Windows, un fichier ouvert
    (projeté en mémoire) ne se remplace pas.
    """
    jeu = tmp_path / "jeu-reference"
    shutil.copytree(ecrire_jeu_sft(tmp_path / "commun" / "jeu"), jeu)
    rangees = json.loads((jeu / "index.json").read_text(encoding="utf-8"))["rangees"]["train"]
    np.zeros(rangees, dtype="<f8").tofile(jeu / "train" / "reference.bin")  # une référence périmée
    sft = METHODES["sft"]
    contextes, references = [], []

    def preparer(config, modele, appareil, noter, *, depart, reprise):
        nouvelle = (1000.0 + np.arange(rangees)).astype("<f8")
        ecrire_atomique(config.dossier_donnees / "train" / "reference.bin", lambda f: f.write(nouvelle.tobytes()))
        return {"reference": "écrite"}

    def creer_chargeurs(config, contexte, noter):
        contextes.append(contexte)
        return sft.creer_chargeurs(config, contexte, noter)

    def pas(modele, optimiseur, chargeur, config, taux_du_pas, appareil, contexte, *, numero):
        references.append(chargeur.lot().reference)
        return {"perte": 1.0}

    remplacer_le_sft(monkeypatch, preparer=preparer, creer_chargeurs=creer_chargeurs, pas=pas)
    entrainer(cfg_sft(tmp_path / "sft", donnees=str(jeu)), arreter_apres=1)
    assert contextes == [{"reference": "écrite"}]
    assert references[0] is not None and len(references[0]) == 2 and bool((references[0] >= 1000).all())


def test_pas_recoit_son_numero(tmp_path, monkeypatch):
    """Le numéro du pas suit l'entraînement, reprise comprise (le GRPO en tire sa graine)."""
    sft = METHODES["sft"]
    numeros = []

    def pas(*arguments, numero, **reste):
        numeros.append(numero)
        return sft.pas(*arguments, numero=numero, **reste)

    remplacer_le_sft(monkeypatch, pas=pas)
    entrainer(cfg_sft(tmp_path / "sft"), arreter_apres=3)
    entrainer(cfg_sft(tmp_path / "sft"), reprendre=True, arreter_apres=5)
    assert numeros == [1, 2, 3, 4, 5]


def espionner_preparer(monkeypatch, nom: str = "sft") -> list[dict]:
    """Ce que reçoit `preparer` de la méthode `nom`, à chaque appel ; elle se prépare ensuite comme d'habitude."""
    vraie = METHODES[nom]
    vus = []

    def preparer(config, modele, appareil, noter, *, depart, reprise):
        vus.append({"depart": depart, "reprise": reprise, "plongement": modele.plongement.weight.detach().clone()})
        return vraie.preparer(config, modele, appareil, noter, depart=depart, reprise=reprise)

    monkeypatch.setitem(METHODES, nom, dataclasses.replace(vraie, preparer=preparer))
    return vus


def test_preparer_sait_si_c_est_une_reprise(tmp_path, monkeypatch):
    vus = espionner_preparer(monkeypatch)
    config = cfg_sft(tmp_path / "sft")
    entrainer(config, reprendre=True, arreter_apres=2)  # aucune sauvegarde : c'est un départ neuf
    entrainer(config, reprendre=True, arreter_apres=4)
    assert [v["reprise"] for v in vus] == [False, True]
    # Même en reprenant, la méthode se prépare sur les poids de départ, pas sur ceux de la sauvegarde.
    publies = charger_publication(Path(config.depart)).modele.plongement.weight
    assert torch.equal(vus[0]["plongement"], publies) and torch.equal(vus[1]["plongement"], publies)


def test_preparer_recoit_la_version_de_depart(tmp_path, monkeypatch):
    vus = espionner_preparer(monkeypatch)
    config = cfg_sft(tmp_path / "sft")
    entrainer(config, arreter_apres=1)
    poids = Path(config.depart) / nom_des_poids(ETIQUETTE)
    attendue = boucle.VersionDeDepart(
        version=ETIQUETTE, empreinte_des_poids=empreinte_sha256(poids), empreinte_du_tokenizer=EMPREINTE
    )
    assert vus[0]["depart"] == attendue
    pre = espionner_preparer(monkeypatch, "pre_entrainement")
    entrainer(config_test(tmp_path / "pre"), arreter_apres=1)
    assert pre[0]["depart"] is None and pre[0]["reprise"] is False


def test_les_notes_de_preparer_vont_au_journal(tmp_path, monkeypatch):
    def preparer(config, modele, appareil, noter, *, depart, reprise):
        noter({"evenement": "essai", "message": "préparé"})
        return {}

    remplacer_le_sft(monkeypatch, preparer=preparer)
    entrainer(cfg_sft(tmp_path / "sft"), arreter_apres=1)
    lignes = lire_journal(tmp_path / "sft")
    assert lignes[0]["evenement"] == "debut" and lignes[1] == {"evenement": "essai", "message": "préparé", "pas": 0}


def test_les_notes_d_un_preparer_qui_echoue_vont_au_journal(tmp_path, monkeypatch):
    """Le contrôle de départ du GRPO note son résultat, puis refuse de lancer : la note reste au journal."""

    class Refus(RuntimeError):
        pass

    def preparer(config, modele, appareil, noter, *, depart, reprise):
        noter({"evenement": "controle", "message": "aucune réponse juste"})
        raise Refus("rien n'est lancé")

    remplacer_le_sft(monkeypatch, preparer=preparer)
    with pytest.raises(Refus):
        entrainer(cfg_sft(tmp_path / "sft"), arreter_apres=1)
    assert lire_journal(tmp_path / "sft") == [{"evenement": "controle", "message": "aucune réponse juste", "pas": 0}]
    assert not (tmp_path / "sft" / "sauvegardes").exists()


def test_une_validation_abimee_arrete_le_sft(tmp_path):
    """Un fichier de validation coupé n'est pas une absence de validation : l'entraînement refuse de partir."""
    jeu = tmp_path / "jeu-abime"
    shutil.copytree(ecrire_jeu_sft(tmp_path / "commun" / "jeu"), jeu)
    contenu = (jeu / "val" / "ids.bin").read_bytes()
    (jeu / "val" / "ids.bin").write_bytes(contenu[:-34])
    with pytest.raises(ValueError, match="forge preparer"):
        entrainer(cfg_sft(tmp_path / "sft", donnees=str(jeu)), arreter_apres=1)


def test_un_jeu_sans_validation(tmp_path):
    jeu = tmp_path / "jeu-sans-val"
    train, _ = empaqueter(exemples(48, graine=1), longueur=16, bourrage=BOURRAGE)
    ecrire_jeu(jeu, train, [], "sft", {}, TOK)
    r = entrainer(cfg_sft(tmp_path / "sft", donnees=str(jeu)), arreter_apres=5)
    assert r["pas"] == 5 and r["meilleure_perte_val"] is None
    (ligne,) = [l for l in lire_journal(tmp_path / "sft") if l.get("evenement") == "validation"]
    assert "aucune rangée de validation" in ligne["message"] and ligne["pas"] == 0


@pytest.mark.gpu
def test_sft_gpu_court(tmp_path):
    r = entrainer(cfg_sft(tmp_path / "sft", appareil="cuda"), arreter_apres=20)
    assert len(r["pertes"]) == 20 and r["pertes"][-1] < r["pertes"][0]
