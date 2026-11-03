"""Tests de l'évaluation de « ton IA » : perte, perplexité, bits par octet, QCM, échantillons, rapport.

Aucun test n'ouvre le réseau : les questions de FrenchBench sont remplacées par quelques lignes
écrites ici, avec les vraies colonnes des deux jeux (relevées le 03/11/2026 sur Hugging Face).
Tout tourne sur le processeur, avec un modèle minuscule (vocabulaire de 322 jetons : 256 octets,
2 places libres pour des fusions et 64 jetons spéciaux ; aucune fusion, donc un jeton par octet),
sauf le test marqué `gpu`.

Deux sortes de modèles : un faux modèle (`MODELE_QUI_PREFERE`), dont on connaît exactement les
scores, pour vérifier la mécanique des QCM ; et un vrai `Transformer` minuscule, entraîné
quelques pas par la vraie boucle d'entraînement, pour lire une vraie sauvegarde.
"""

import gzip
import json
import math
import os
import re
import subprocess
import sys
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
from torch import nn

from forge.__main__ import main
from forge.donnees.jetons import _empreinte_du_tokenizer, encoder_corpus
from forge.entrainement import ChargeurJetons, ConfigEntrainement, entrainer
from forge.evaluation import (
    INVITES,
    QCM,
    bits_par_octet,
    charger_frenchbench,
    echantillons,
    evaluer,
    evaluer_qcm,
    perplexite,
    perte_validation,
)
from forge.evaluation.perte import lire_octets_par_jeton
from forge.evaluation.qcm import scores_qcm
from forge.modele import ConfigModele, Transformer
from forge.tokenizer import TokenizerOctets, entrainer_tokenizer

RACINE_DU_PROJET = Path(__file__).resolve().parents[1]
ESPACE_FINE = " "

TEXTE_DE_TEST = (Path(__file__).parent / "donnees" / "corpus_test.txt").read_text(encoding="utf-8")
PARAGRAPHES = [p.strip() for p in TEXTE_DE_TEST.split("\n\n") if p.strip()]

# 256 octets + 2 places libres + 64 jetons spéciaux, aucune fusion : un jeton par octet.
VOCABULAIRE = 322
TOK_TEST = TokenizerOctets([], VOCABULAIRE, "test")
FIN_DE_TEXTE = TOK_TEST.id_special("<|fin_texte|>")
MODELE_TEST = ConfigModele(taille_vocabulaire=VOCABULAIRE, dim=32, couches=2, tetes=2, longueur_contexte=16)


# --------------------------------------------------------------------------------------
# Des modèles et des données de test
# --------------------------------------------------------------------------------------


class ModeleFactice(nn.Module):
    """Un faux modèle : `scores(ids)` donne les logits `[lot, positions, vocabulaire]`."""

    def __init__(self, scores, vocabulaire: int = VOCABULAIRE, contexte: int = 64) -> None:
        super().__init__()
        self.config = ConfigModele(
            taille_vocabulaire=vocabulaire, dim=2, couches=1, tetes=1, longueur_contexte=contexte
        )
        self._ancre = nn.Parameter(torch.zeros(1))  # pour que le modèle ait un appareil
        self._scores = scores

    def forward(self, ids, cibles=None):
        return self._scores(ids), None


def MODELE_QUI_PREFERE(texte: str, contexte: int = 64, tokenizer: TokenizerOctets = TOK_TEST) -> ModeleFactice:  # noqa: N802
    """Un faux modèle dont les logits favorisent les jetons de `texte`, dans l'ordre.

    À chaque position, il cherche jusqu'où les derniers jetons déjà vus recopient le début de
    `texte` (encodé par `tokenizer` : des octets, avec le tokenizer d'octets purs), et donne un
    grand score (+10) au jeton suivant de `texte` ; les autres jetons valent 0. Pour le texte
    « abc » : après « a » il favorise « b », après « ab » il favorise « c ». Une réponse qui
    recopie `texte` est donc bien plus vraisemblable qu'une autre.

    Un jeton favorisé a pour log-probabilité `10 - ln(e^10 + V - 1)` (V : taille du vocabulaire),
    tout autre `-ln(e^10 + V - 1)` : de quoi calculer à la main la note exacte d'une réponse.
    """
    jetons = tokenizer.encoder(texte)

    def scores(ids: torch.Tensor) -> torch.Tensor:
        logits = torch.zeros(*ids.shape, tokenizer.taille_vocabulaire)
        for b, ligne in enumerate(ids.tolist()):
            for t in range(len(ligne)):
                recopies = max(
                    k for k in range(min(len(jetons), t + 1) + 1) if ligne[t + 1 - k : t + 1] == jetons[:k]
                )
                if recopies < len(jetons):
                    logits[b, t, jetons[recopies]] = 10.0
        return logits

    return ModeleFactice(scores, vocabulaire=tokenizer.taille_vocabulaire, contexte=contexte)


def log_normalisation(vocabulaire: int = VOCABULAIRE) -> float:
    """`ln(e^10 + V - 1)` : ce qu'on retranche aux logits du faux modèle pour avoir des log-probabilités."""
    return math.log(math.exp(10) + vocabulaire - 1)


def ecrire_donnees_test(dossier: Path) -> None:
    """Un dossier de jetons comme celui de `forge encoder` : train/, val/, index.json, .complet.

    Les jetons sont ceux de vrais paragraphes français ; les trois derniers vont dans `val/`.
    """
    parties = {"train": PARAGRAPHES[:-3], "val": PARAGRAPHES[-3:]}
    fichiers, octets, sans_fin = {}, 0, 0
    for partie, textes in parties.items():
        jetons = []
        for texte in textes:
            ids = TOK_TEST.encoder(texte)
            jetons += [*ids, FIN_DE_TEXTE]
            octets += len(texte.encode("utf-8"))
            sans_fin += len(ids)
        (dossier / partie).mkdir(parents=True, exist_ok=True)
        np.array(jetons, dtype="<u2").tofile(dossier / partie / "fragment-00000.bin")
        fichiers[f"{partie}/fragment-00000.bin"] = len(jetons)
    index = {
        "version": 1,
        "tokenizer": {
            "nom": TOK_TEST.nom,
            "taille_vocabulaire": TOK_TEST.taille_vocabulaire,
            "empreinte": _empreinte_du_tokenizer(TOK_TEST),
        },
        "octets": octets,
        "jetons_sans_fin": sans_fin,
        "fichiers": fichiers,
    }
    (dossier / "index.json").write_text(json.dumps(index), encoding="utf-8")
    (dossier / ".complet").write_text(json.dumps({"octets_par_jeton": octets / sans_fin}), encoding="utf-8")


@pytest.fixture(scope="module")
def donnees_test(tmp_path_factory) -> Path:
    dossier = tmp_path_factory.mktemp("jetons")
    ecrire_donnees_test(dossier)
    return dossier


@pytest.fixture(scope="module")
def tok_fusions() -> TokenizerOctets:
    """Un petit tokenizer AVEC fusions (150), appris sur le texte de test : des jetons de plusieurs octets."""
    return entrainer_tokenizer(PARAGRAPHES, taille_vocabulaire=256 + 150 + 64)


@pytest.fixture(scope="module")
def tok_fichier_test(tmp_path_factory) -> Path:
    chemin = tmp_path_factory.mktemp("tokenizer") / "tokenizer-test.json"
    TOK_TEST.enregistrer(chemin)
    return chemin


@pytest.fixture(scope="module")
def sauvegardes_minuscules(tmp_path_factory, donnees_test) -> Path:
    """Le dossier `sauvegardes/` d'un vrai entraînement de 4 pas (`etape-0000004.pt`, `meilleur.pt`)."""
    sortie = tmp_path_factory.mktemp("entrainement")
    config = ConfigEntrainement(
        preset=MODELE_TEST,
        donnees=str(donnees_test),
        jetons_total=32 * 6,
        taille_lot_jetons=32,
        micro_lot=2,
        taux_max=1e-2,
        echauffement=2,
        evaluation_tous_pas=2,
        appareil="cpu",
        compiler="non",
        sortie=str(sortie),
    )
    entrainer(config, arreter_apres=4)
    return sortie / "sauvegardes"


@pytest.fixture
def sauvegarde_minuscule(sauvegardes_minuscules) -> Path:
    return sauvegardes_minuscules / "meilleur.pt"


# --------------------------------------------------------------------------------------
# Les tests du plan
# --------------------------------------------------------------------------------------


def test_bits_par_octet():
    assert bits_par_octet(math.log(2) * 3, 3.0) == pytest.approx(1.0)


def test_qcm_choisit_la_vraisemblance():
    q = [QCM("Le ciel est", [" bleu.", " xqzv."], 0)]
    r = evaluer_qcm(MODELE_QUI_PREFERE(" bleu."), TOK_TEST, q)
    assert r["exactitude"] == 1.0 and r["hasard"] == 0.5 and r["n"] == 1


def test_rapport(tmp_path, sauvegarde_minuscule, donnees_test, tok_fichier_test):
    r = evaluer(sauvegarde_minuscule, donnees_test, tok_fichier_test, tmp_path, n_qcm=0, appareil="cpu")
    assert {"perte_val", "perplexite", "bits_par_octet", "echantillons"} <= r.keys()
    assert "Perplexité" in (tmp_path / "rapport.md").read_text(encoding="utf-8")


# --------------------------------------------------------------------------------------
# Perte, perplexité, bits par octet
# --------------------------------------------------------------------------------------


def test_bits_par_octet_refuse_un_nombre_d_octets_nul():
    with pytest.raises(ValueError, match="octets par jeton"):
        bits_par_octet(2.0, 0.0)


def test_perplexite():
    assert perplexite(math.log(7)) == pytest.approx(7.0)
    assert perplexite(0.0) == 1.0
    assert perplexite(10_000.0) == math.inf  # pas de plantage quand la perte explose


def test_octets_par_jeton_de_l_index(tmp_path):
    ecrire_donnees_test(tmp_path)
    assert lire_octets_par_jeton(tmp_path) == pytest.approx(1.0)  # un octet par jeton
    # Sans les totaux dans l'index, on retombe sur le nombre gardé dans `.complet`.
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    del index["octets"], index["jetons_sans_fin"]
    (tmp_path / "index.json").write_text(json.dumps(index), encoding="utf-8")
    (tmp_path / ".complet").write_text(json.dumps({"octets_par_jeton": 3.5}), encoding="utf-8")
    assert lire_octets_par_jeton(tmp_path) == 3.5
    # Ni l'un ni l'autre : message qui dit quoi faire.
    (tmp_path / ".complet").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="python -m forge encoder"):
        lire_octets_par_jeton(tmp_path)


def test_octets_par_jeton_lit_la_sortie_de_l_encodeur(tmp_path):
    """Le même nombre que le résumé de `forge encoder`, lu dans ce qu'il a écrit."""
    source = tmp_path / "textes" / "web_fr"
    source.mkdir(parents=True)
    with gzip.GzipFile(source / "fragment-00000.jsonl.gz", mode="wb", mtime=0) as fichier:
        for i in range(20):
            texte = f"document {i}\n\n{PARAGRAPHES[i % len(PARAGRAPHES)]}"
            fichier.write((json.dumps({"texte": texte}, ensure_ascii=False) + "\n").encode("utf-8"))
    (source / ".complet").write_text("{}", encoding="utf-8")
    resume = encoder_corpus([source], TOK_TEST, tmp_path / "jetons", processus=1)
    assert lire_octets_par_jeton(tmp_path / "jetons") == pytest.approx(resume["octets_par_jeton"])
    assert resume["octets_par_jeton"] == pytest.approx(1.0)


def test_perte_validation_d_un_modele_neuf_vaut_ln_du_vocabulaire(donnees_test):
    torch.manual_seed(0)
    modele = Transformer(MODELE_TEST)
    chargeur = ChargeurJetons(donnees_test / "val", longueur=16, taille_lot=4, graine=1)
    # Poids tirés très petits : tous les jetons ont presque la même probabilité.
    assert perte_validation(modele, chargeur, n_lots=3) == pytest.approx(math.log(VOCABULAIRE), abs=0.05)


def test_perte_validation_est_fixe_et_ne_depend_pas_du_lot(donnees_test):
    torch.manual_seed(0)
    modele = Transformer(MODELE_TEST)
    valeurs = []
    for taille_lot, n_lots in ((2, 6), (3, 4), (4, 3)):  # toujours 12 morceaux
        chargeur = ChargeurJetons(donnees_test / "val", longueur=16, taille_lot=taille_lot, graine=1234)
        chargeur.lot()  # le chargeur a déjà avancé : la mesure repart quand même du début
        chargeur.lot()
        valeurs.append(perte_validation(modele, chargeur, n_lots))
    assert valeurs[0] == pytest.approx(valeurs[1], rel=1e-6) == pytest.approx(valeurs[2], rel=1e-6)
    # Appelée deux fois, elle donne le même nombre.
    assert perte_validation(modele, chargeur, 3) == valeurs[2]


def test_perte_validation_laisse_le_modele_et_le_chargeur_comme_avant(donnees_test):
    modele = Transformer(MODELE_TEST)
    chargeur = ChargeurJetons(donnees_test / "val", longueur=16, taille_lot=2, graine=5)
    chargeur.lot()
    avant = chargeur.etat()
    modele.train()
    perte_validation(modele, chargeur, 2)
    assert modele.training and all(m.training for m in modele.modules())
    modele.eval()
    perte_validation(modele, chargeur, 2)
    assert not modele.training and not any(m.training for m in modele.modules())
    assert chargeur.etat() == avant


def test_perte_validation_ne_relit_pas_deux_fois_un_morceau(donnees_test):
    """Demander plus de lots qu'il n'y a de morceaux s'arrête au dernier morceau."""
    torch.manual_seed(0)
    modele = Transformer(MODELE_TEST)
    chargeur = ChargeurJetons(donnees_test / "val", longueur=16, taille_lot=1, graine=1)
    assert perte_validation(modele, chargeur, 10_000) == pytest.approx(
        perte_validation(modele, chargeur, chargeur.morceaux), rel=1e-6
    )


# --------------------------------------------------------------------------------------
# Les QCM
# --------------------------------------------------------------------------------------

QUESTION_CIEL = "Le ciel est"


def test_qcm_compte_les_bonnes_et_les_mauvaises_reponses():
    qcms = [
        QCM(QUESTION_CIEL, [" bleu.", " xqzv."], 0),
        QCM(QUESTION_CIEL, [" bleu.", " xqzv."], 1),  # le modèle se trompe : la bonne est l'autre
    ]
    r = evaluer_qcm(MODELE_QUI_PREFERE(" bleu."), TOK_TEST, qcms)
    assert r["exactitude"] == 0.5 and r["exactitude_normalisee"] == 0.5 and r["n"] == 2


def test_qcm_normalise_par_octets():
    """La réponse longue perd en total (plus d'octets à deviner) mais gagne par octet."""
    court, long_ = " bx", " bleu blxu"
    qcm = QCM(QUESTION_CIEL, [court, long_], 1)
    modele = MODELE_QUI_PREFERE(" bleu bleu bleu")
    total_court, total_long = scores_qcm(modele, TOK_TEST, [qcm])[0]
    # Les conditions du test : le total préfère la courte, la moyenne par octet la longue.
    assert total_court > total_long
    assert total_court / len(court.encode()) < total_long / len(long_.encode())
    r = evaluer_qcm(modele, TOK_TEST, [qcm])
    assert r["exactitude"] == 0.0 and r["exactitude_normalisee"] == 1.0


def test_qcm_note_exactement_les_jetons_du_choix():
    """Valeurs exactes : la bonne réponse a 6 jetons favorisés ; l'autre, 1 favorisé et 5 ratés.

    Après « est », le faux modèle favorise l'espace (premier jeton de « bleu. » comme de
    « xqzv. ») ; ensuite « x » n'est pas le « b » attendu, et ainsi de suite.
    """
    ln = log_normalisation()
    bonne, autre = scores_qcm(MODELE_QUI_PREFERE(" bleu."), TOK_TEST, [QCM(QUESTION_CIEL, [" bleu.", " xqzv."], 0)])[0]
    assert bonne == pytest.approx(6 * (10 - ln), abs=1e-3)
    assert autre == pytest.approx((10 - ln) + 5 * (-ln), abs=1e-3)


def test_qcm_donne_au_modele_le_debut_le_contexte_puis_le_choix():
    """La séquence passée au modèle : `<|fin_texte|>`, jetons du contexte, jetons du choix."""
    vues = []
    oracle = MODELE_QUI_PREFERE(" bleu.")

    def scores(ids):
        vues.extend(ids.tolist())
        return oracle._scores(ids)

    scores_qcm(ModeleFactice(scores), TOK_TEST, [QCM(QUESTION_CIEL, [" bleu.", " xqzv."], 0)])
    contexte = TOK_TEST.encoder(QUESTION_CIEL)
    attendues = [[FIN_DE_TEXTE, *contexte, *TOK_TEST.encoder(choix)] for choix in (" bleu.", " xqzv.")]
    assert sorted(vues) == sorted(attendues)


def test_encoder_le_contexte_puis_le_choix_donne_les_memes_jetons_que_le_tout(tok_fusions, monkeypatch):
    """Le choix commence par son espace : la frontière tombe entre deux pré-mots, même avec des fusions."""
    qcms = [QCM(QUESTION_CIEL, [" bleu.", " xqzv.", " le souffle du soufflet", " 5 grammes", " (a) l'enclume"], 0)]
    faux_jeu(monkeypatch, [LIGNE_HELLASWAG_ACTIVITYNET, LIGNE_HELLASWAG_WIKIHOW, LIGNE_HELLASWAG_MARQUEURS_TRADUITS])
    qcms += charger_frenchbench("hellaswag")
    faux_jeu(monkeypatch, [LIGNE_ARC, {**LIGNE_ARC, "question": "Combien font 2 + 3 ?", "choices": ["5", "10"]}])
    qcms += charger_frenchbench("arc")
    assert len(qcms) == 6
    assert len(tok_fusions.encoder(" le souffle du soufflet")) < len(" le souffle du soufflet".encode())  # des fusions servent
    for qcm in qcms:
        for choix in qcm.choix:
            ensemble = tok_fusions.encoder(qcm.contexte + choix)
            assert tok_fusions.encoder(qcm.contexte) + tok_fusions.encoder(choix) == ensemble, (qcm.contexte, choix)


def test_qcm_note_exactement_les_jetons_du_choix_avec_des_fusions(tok_fusions):
    """Avec des jetons de plusieurs octets : la note compte un terme par JETON du choix, ni plus ni moins."""
    choix = " le souffle du soufflet"
    jetons = tok_fusions.encoder(choix)
    assert 2 < len(jetons) < len(choix.encode())
    modele = MODELE_QUI_PREFERE(choix, tokenizer=tok_fusions)
    note, autre = scores_qcm(modele, tok_fusions, [QCM(QUESTION_CIEL, [choix, " la forge et l'enclume"], 0)])[0]
    ln = log_normalisation(tok_fusions.taille_vocabulaire)
    assert note == pytest.approx(len(jetons) * (10 - ln), abs=1e-3)
    assert autre < note


def test_qcm_hasard_est_la_moyenne_des_inverses():
    qcms = [
        QCM(QUESTION_CIEL, [" a", " b", " c"], 0),
        QCM(QUESTION_CIEL, [" a", " b", " c", " d"], 0),
    ]
    r = evaluer_qcm(MODELE_QUI_PREFERE(" a"), TOK_TEST, qcms)
    assert r["hasard"] == pytest.approx((1 / 3 + 1 / 4) / 2)
    assert r["n"] == 2


def test_qcm_donne_une_marge_d_erreur():
    """Avec peu de questions, on ne peut pas conclure : la marge à 95 % le dit."""
    qcms = [QCM(QUESTION_CIEL, [" bleu.", " xqzv."], 0)] * 100
    r = evaluer_qcm(MODELE_QUI_PREFERE(" bleu."), TOK_TEST, qcms)
    assert r["marge_95"] == 0.0  # tout juste : aucune dispersion
    qcms = [QCM(QUESTION_CIEL, [" bleu.", " xqzv."], 0)] * 60 + [QCM(QUESTION_CIEL, [" bleu.", " xqzv."], 1)] * 40
    r = evaluer_qcm(MODELE_QUI_PREFERE(" bleu."), TOK_TEST, qcms)
    assert r["exactitude"] == pytest.approx(0.6)
    assert r["marge_95"] == pytest.approx(1.96 * math.sqrt(0.6 * 0.4 / 100))


def test_qcm_marge_du_hasard():
    """La marge à 95 % d'un résultat QUI SERAIT dû au hasard : elle ne s'annule jamais, même à 0 bonne réponse."""
    qcms = [QCM(QUESTION_CIEL, [" bleu.", " a", " b", " c"], 3)] * 5  # 0 bonne réponse sur 5, 4 choix
    r = evaluer_qcm(MODELE_QUI_PREFERE(" bleu."), TOK_TEST, qcms)
    assert r["exactitude"] == 0.0 and r["marge_95"] == 0.0  # la marge de Wald, elle, s'annule à 0
    assert r["marge_hasard"] == pytest.approx(1.96 * math.sqrt(0.25 * 0.75 / 5))
    # Questions à 2 et à 4 choix : la variance d'un tirage au sort est la somme de celles des questions.
    melange = [QCM(QUESTION_CIEL, [" bleu.", " a"], 0)] * 3 + [QCM(QUESTION_CIEL, [" bleu.", " a", " b", " c"], 0)]
    r = evaluer_qcm(MODELE_QUI_PREFERE(" bleu."), TOK_TEST, melange)
    variance = 3 * 0.5 * 0.5 + 0.25 * 0.75
    assert r["marge_hasard"] == pytest.approx(1.96 * math.sqrt(variance) / 4)


def mesures_a_quatre_choix(n_justes: int, n: int) -> dict:
    """`n` questions à 4 choix dont `n_justes` sont bien notées par le faux modèle (les autres, jamais)."""
    juste = QCM(QUESTION_CIEL, [" bleu.", " a", " b", " c"], 0)
    fausse = QCM(QUESTION_CIEL, [" bleu.", " a", " b", " c"], 3)
    return evaluer_qcm(MODELE_QUI_PREFERE(" bleu."), TOK_TEST, [juste] * n_justes + [fausse] * (n - n_justes))


def test_verdict_est_prudent_avec_peu_de_questions():
    from forge.evaluation.rapport import verdict

    # 0 sur 5 et 0 sur 10 (hasard : 25 %) : un tel score arrive souvent par hasard, on ne conclut rien.
    assert verdict(mesures_a_quatre_choix(0, 5)) == "pas différent du hasard"
    assert verdict(mesures_a_quatre_choix(0, 10)) == "pas différent du hasard"
    assert verdict(mesures_a_quatre_choix(25, 100)) == "pas différent du hasard"
    # Une seule question juste (hasard : 25 %) ne prouve rien non plus, dans l'autre sens.
    assert verdict(mesures_a_quatre_choix(1, 1)) == "pas différent du hasard"
    # Beaucoup de questions : l'écart se voit, dans les deux sens.
    assert verdict(mesures_a_quatre_choix(40, 50)) == "au-dessus du hasard"
    assert verdict(mesures_a_quatre_choix(0, 100)) == "en dessous du hasard"


def test_qcm_contexte_plus_long_que_le_modele():
    """Le début du contexte est oublié ; la réponse, elle, est toujours jugée en entier."""
    long = "Il était une fois un village au bord d'une rivière. " * 6 + QUESTION_CIEL
    modele = MODELE_QUI_PREFERE(" bleu.", contexte=8)
    r = evaluer_qcm(modele, TOK_TEST, [QCM(long, [" bleu.", " xqzv."], 0)])
    assert r["exactitude"] == 1.0
    # Une réponse plus longue que le modèle : pas d'erreur, des scores finis.
    reponse = " bleu bleu bleu bleu bleu bleu"
    scores = scores_qcm(modele, TOK_TEST, [QCM(QUESTION_CIEL, [reponse, " x"], 0)])[0]
    assert all(math.isfinite(s) for s in scores)


def test_qcm_les_lots_donnent_les_memes_scores_qu_un_a_un():
    """Le remplissage des lots et leur découpage ne changent aucun score."""
    torch.manual_seed(0)
    modele = Transformer(MODELE_TEST)
    qcms = []
    for i in range(12):
        texte = PARAGRAPHES[i % len(PARAGRAPHES)]
        contexte = texte[: 5 + i * 9]  # des contextes de longueurs très différentes
        reponses = [texte[40 + 3 * k : 40 + 3 * k + 4 + 5 * k] or " a" for k in range(3)]
        qcms.append(QCM(contexte, reponses, i % 3))
    ensemble = scores_qcm(modele, TOK_TEST, qcms, jetons_par_lot=40)  # 2 séquences par lot au plus
    seul_a_seul = [scores_qcm(modele, TOK_TEST, [q])[0] for q in qcms]
    assert np.allclose(np.array(ensemble), np.array(seul_a_seul), atol=1e-4)
    # Et l'exactitude est celle de la moyenne des questions.
    r = evaluer_qcm(modele, TOK_TEST, qcms)
    attendu = sum(int(np.argmax(s) == q.bonne) for s, q in zip(seul_a_seul, qcms)) / len(qcms)
    assert r["exactitude"] == pytest.approx(attendu)


def test_qcm_refuse_les_questions_mal_formees():
    modele = MODELE_QUI_PREFERE(" a")
    with pytest.raises(ValueError, match="Aucune question"):
        evaluer_qcm(modele, TOK_TEST, [])
    with pytest.raises(ValueError, match="bonne réponse"):
        evaluer_qcm(modele, TOK_TEST, [QCM("Q", [" a", " b"], 2)])
    with pytest.raises(ValueError, match="au moins deux"):
        evaluer_qcm(modele, TOK_TEST, [QCM("Q", [" a"], 0)])
    with pytest.raises(ValueError, match="vide"):
        evaluer_qcm(modele, TOK_TEST, [QCM("Q", [" a", ""], 0)])


# --- FrenchBench : les colonnes des deux jeux, relevées sur Hugging Face -----------------

# manu/french_bench_hellaswag, split « validation » (deux lignes du jeu, raccourcies).
LIGNE_HELLASWAG_WIKIHOW = {
    "ind": 9492,
    "activity_label": "Personal Care and Style",
    "ctx_a": (
        "[header] Comment obtenir une jolie coiffure d'été [title] Préparez vos cheveux dans la douche. "
        "[title] Séchez les cheveux jusqu'à ce qu'ils soient secs."
    ),
    "ctx_b": "",
    "ctx": "(non utilisé)",
    "endings": [
        "[title] Ensuite, brossez les nœuds. [title] Séparez vos cheveux en deux parties.",
        "[title] Gonflez vos cheveux avec un peigne à dents larges.",
        "[title] Voici un shampooing sec. [step] Il contient une tasse.",
        "[title] Portez une coiffure finie. [step] Vous pouvez la porter détachée",
    ],
    "source_id": "wikihow~15665",
    "split": "val",
    "split_type": "zeroshot",
    "label": "0",
}
# La traduction automatique a traduit les marqueurs de WikiHow dans plus de 600 cas du jeu.
LIGNE_HELLASWAG_MARQUEURS_TRADUITS = {
    "ind": 1,
    "activity_label": "Youth",
    "ctx_a": "[en-tête] Comment gagner de l'argent à l'école [titre] Vendez des choses. [titre] Élaborez un plan",
    "ctx_b": "",
    "ctx": "(non utilisé)",
    "endings": [
        "[étape] Faites des affiches. [sous-étapes] Utilisez des couleurs vives.",
        "[entête] Ceci n'est pas un plan [Sous-étape] ni une idée.",
        "[titre] Un résumé [citation needed] est utile.",
        "[étape]  Dernier choix  [substeps ] fini. [sousteps] Fin.",
    ],
    "source_id": "wikihow~1",
    "split": "val",
    "split_type": "zeroshot",
    "label": "2",
}
LIGNE_HELLASWAG_ACTIVITYNET = {
    "ind": 23536,
    "activity_label": "Running a marathon",
    "ctx_a": "Une femme en costume rouge parle derrière un bureau.",
    "ctx_b": "un homme",
    "ctx": "Une femme en costume rouge parle derrière un bureau. un homme",
    "endings": [
        "prend des balles sur un rack mural.",
        "passe l'aspirateur sur une chaise en plastique noir.",
        "aspire de l'eau dans un petit évier blanc.",
        "se tient debout en tenant son pied derrière son dos.",
    ],
    "source_id": "activitynet~v_eyfUkLbsixg",
    "split": "val",
    "split_type": "zeroshot",
    "label": "3",
}
# manu/french_bench_arc_challenge, split « test » : `choices` est une simple liste de textes.
LIGNE_ARC = {
    "id": "ARC-Challenge/test/Mercury_SC_415719",
    "question": "Anna tient un glaçon. Pourquoi le glaçon fond-il dans sa main ?",
    "choices": [
        "La chaleur se déplace de sa main vers le glaçon.",
        "Le froid se déplace de sa main vers le glaçon.",
        "La chaleur se déplace du glaçon vers sa main.",
        "Le froid se déplace du glaçon vers sa main.",
    ],
    "answerKey": "A",
}


def faux_jeu(monkeypatch, lignes: list[dict]) -> list[tuple[str, str]]:
    """Remplace le téléchargement par `lignes` ; renvoie la liste des (jeu, split) demandés."""
    demandes = []

    def lignes_du_jeu(jeu: str, split: str):
        demandes.append((jeu, split))
        return iter(lignes)

    monkeypatch.setattr("forge.evaluation.qcm._lignes_du_jeu", lignes_du_jeu)
    return demandes


def test_frenchbench_hellaswag(monkeypatch):
    demandes = faux_jeu(monkeypatch, [LIGNE_HELLASWAG_ACTIVITYNET, LIGNE_HELLASWAG_WIKIHOW])
    qcms = charger_frenchbench("hellaswag")
    assert demandes == [("manu/french_bench_hellaswag", "validation")]
    assert qcms[0] == QCM(
        # La fin du contexte reçoit une majuscule, comme dans HellaSwag ; l'étiquette d'activité
        # (en anglais dans ce jeu) n'est pas utilisée.
        "Une femme en costume rouge parle derrière un bureau. Un homme",
        [
            " prend des balles sur un rack mural.",
            " passe l'aspirateur sur une chaise en plastique noir.",
            " aspire de l'eau dans un petit évier blanc.",
            " se tient debout en tenant son pied derrière son dos.",
        ],
        3,  # `label` est le texte « 3 » : on en fait l'indice
    )
    # Les marqueurs [header], [title], [step] disparaissent : chacun devient une fin de phrase.
    assert qcms[1].contexte == (
        "Comment obtenir une jolie coiffure d'été. Préparez vos cheveux dans la douche. "
        "Séchez les cheveux jusqu'à ce qu'ils soient secs."
    )
    assert qcms[1].choix[0] == " Ensuite, brossez les nœuds. Séparez vos cheveux en deux parties."
    assert qcms[1].choix[2] == " Voici un shampooing sec. Il contient une tasse."
    assert qcms[1].choix[3] == " Portez une coiffure finie. Vous pouvez la porter détachée"
    assert qcms[1].bonne == 0
    assert "[" not in "".join(qcms[1].choix) + qcms[1].contexte


def test_frenchbench_hellaswag_marqueurs_traduits(monkeypatch):
    faux_jeu(monkeypatch, [LIGNE_HELLASWAG_MARQUEURS_TRADUITS])
    (qcm,) = charger_frenchbench("hellaswag")
    assert qcm.contexte == "Comment gagner de l'argent à l'école. Vendez des choses. Élaborez un plan"
    assert qcm.choix == [
        " Faites des affiches. Utilisez des couleurs vives.",
        " Ceci n'est pas un plan. ni une idée.",
        " Un résumé [citation needed] est utile.",  # un vrai crochet du texte : on n'y touche pas
        " Dernier choix. fini. Fin.",
    ]
    assert qcm.bonne == 2


def test_frenchbench_arc(monkeypatch):
    sans_lettre = {"id": "ARC-Challenge/test/NYSEDREGENTS_X", "question": "Combien ?", "choices": ["a", "b", "c"], "answerKey": "2"}
    cinq = {"id": "ARC-Challenge/test/Y", "question": "Laquelle ?", "choices": list("vwxyz"), "answerKey": "E"}
    demandes = faux_jeu(monkeypatch, [LIGNE_ARC, sans_lettre, cinq])
    qcms = charger_frenchbench("arc")
    assert demandes == [("manu/french_bench_arc_challenge", "test")]
    assert qcms[0] == QCM(
        "Question : Anna tient un glaçon. Pourquoi le glaçon fond-il dans sa main ?\nRéponse :",
        [" " + texte for texte in LIGNE_ARC["choices"]],
        0,  # la lettre « A »
    )
    assert qcms[1].bonne == 1 and len(qcms[1].choix) == 3  # un chiffre « 2 » compte à partir de 1
    assert qcms[2].bonne == 4 and len(qcms[2].choix) == 5  # « E », cinquième choix


def test_frenchbench_n_max_et_erreurs(monkeypatch):
    faux_jeu(monkeypatch, [LIGNE_ARC] * 10)
    assert len(charger_frenchbench("arc", 3)) == 3
    faux_jeu(monkeypatch, [LIGNE_ARC] * 10)
    assert len(charger_frenchbench("arc", None)) == 10
    with pytest.raises(ValueError, match="hellaswag.*arc"):
        charger_frenchbench("mmlu")
    faux_jeu(monkeypatch, [{**LIGNE_ARC, "answerKey": "Z"}])
    with pytest.raises(ValueError, match="Mercury_SC_415719"):
        charger_frenchbench("arc")


# --------------------------------------------------------------------------------------
# Les échantillons
# --------------------------------------------------------------------------------------


def test_les_invites():
    assert len(INVITES) == 10
    assert not any(invite.startswith("def ") for invite in INVITES[:8])  # 8 débuts de phrase
    assert all(invite.startswith("def ") for invite in INVITES[8:])  # puis 2 débuts de fonction Python
    # Jamais une espace à la fin : le pré-découpage la lirait autrement que dans le corpus d'entraînement.
    assert not any(invite.endswith(" ") for invite in INVITES)


def test_echantillons_sont_fixes_par_la_graine():
    torch.manual_seed(0)
    modele = Transformer(MODELE_TEST)
    a = echantillons(modele, TOK_TEST, graine=3, n_nouveaux=12)
    assert a == echantillons(modele, TOK_TEST, graine=3, n_nouveaux=12)
    assert echantillons(modele, TOK_TEST, graine=4, n_nouveaux=12) != a
    assert [e["invite"] for e in a] == INVITES
    assert all(isinstance(e["suite"], str) and e["n_jetons"] <= 12 for e in a)
    assert len({e["graine"] for e in a}) == len(a)  # chaque invite a sa graine, notée
    assert modele.training  # un modèle neuf est en mode entraînement : il y revient


def test_echantillons_s_arretent_a_la_fin_de_texte():
    def scores(ids):
        logits = torch.zeros(*ids.shape, VOCABULAIRE)
        logits[..., FIN_DE_TEXTE] = 50.0  # le modèle ne veut écrire que « fin de texte »
        return logits

    resultats = echantillons(ModeleFactice(scores), TOK_TEST, n_nouveaux=30)
    assert all(e["suite"] == "" and e["n_jetons"] == 0 and e["s_arrete"] for e in resultats)


def test_echantillons_ne_plantent_pas_sur_un_identifiant_libre():
    """L'identifiant 256 n'est ni un octet ni une fusion (aucune n'a été apprise) : il s'écrit « � »."""

    def scores(ids):
        logits = torch.zeros(*ids.shape, VOCABULAIRE)
        logits[..., 256] = 50.0
        return logits

    resultats = echantillons(ModeleFactice(scores), TOK_TEST, n_nouveaux=5)
    assert all(e["suite"] == "�" * 5 and e["n_jetons"] == 5 and not e["s_arrete"] for e in resultats)


# --------------------------------------------------------------------------------------
# Le rapport
# --------------------------------------------------------------------------------------


def lire_rapport(dossier: Path) -> tuple[dict, str]:
    rapport = json.loads((dossier / "rapport.json").read_text(encoding="utf-8"))
    return rapport, (dossier / "rapport.md").read_text(encoding="utf-8")


def verifier_typographie(md: str) -> None:
    """Espace fine insécable avant « : », « ; », « ! », « ? », « % » et dans les guillemets, jamais une
    espace ordinaire (hors des blocs de code, où le modèle écrit ce qu'il veut)."""
    texte = re.sub(r"(`{3,}).*?\1", "", md, flags=re.DOTALL)
    for signe in (":", ";", "!", "?", "»", "%"):
        if f" {signe}" in texte:
            debut = texte.index(f" {signe}")
            raise AssertionError(f"espace ordinaire avant {signe!r} : {texte[max(0, debut - 50) : debut + 10]!r}")
    assert "« " not in texte


def test_rapport_ecrit_json_et_markdown_en_francais(tmp_path, sauvegarde_minuscule, donnees_test, tok_fichier_test):
    r = evaluer(sauvegarde_minuscule, donnees_test, tok_fichier_test, tmp_path / "sortie", n_qcm=0, appareil="cpu")
    ecrit, md = lire_rapport(tmp_path / "sortie")
    assert ecrit == json.loads(json.dumps(r))  # le JSON est ce que `evaluer` renvoie
    # Les chiffres sont cohérents entre eux : un octet par jeton avec ce tokenizer.
    assert r["octets_par_jeton"] == pytest.approx(1.0)
    assert r["perplexite"] == pytest.approx(math.exp(r["perte_val"]))
    assert r["bits_par_octet"] == pytest.approx(r["perte_val"] / math.log(2))
    assert r["perte_hasard"] == pytest.approx(math.log(VOCABULAIRE))
    assert r["perte_val"] < r["perte_hasard"]  # 4 pas ont déjà appris quelque chose
    assert r["pas"] == 4 and r["qcm"] == {}
    assert len(r["echantillons"]) == 10 and r["morceaux_val"] > 0 and r["modele"]["dim"] == 32
    # Le Markdown est en français, avec les chiffres à la française…
    assert md.startswith(f"# Évaluation de «{ESPACE_FINE}ton IA{ESPACE_FINE}»")
    for libelle in ("Perte de validation", "Perplexité", "Bits par octet", "## Échantillons"):
        assert libelle in md
    assert f"{r['perte_val']:.3f}".replace(".", ",") in md
    assert "non évalués" in md  # n_qcm = 0 : on le dit
    # … et la typographie française : espace fine insécable avant « : », « ; », « ! », « ? » et
    # dans les guillemets, jamais une espace ordinaire (hors des textes écrits par le modèle).
    assert f"Sauvegarde{ESPACE_FINE}:" in md
    verifier_typographie(md)
    # Les bits par octet sont une estimation, et le rapport le dit.
    assert "Bits par octet (estimation)" in md and "octets par jeton du corpus entier" in md
    assert "la perte compte aussi les fins de texte" in md
    for invite in INVITES:
        assert invite.strip() in md


def test_rapport_avec_qcm(tmp_path, monkeypatch, sauvegarde_minuscule, donnees_test, tok_fichier_test):
    appels = []

    def faux_chargement(nom, n_max=None):
        appels.append((nom, n_max))
        return [QCM(QUESTION_CIEL, [" bleu.", " xqzv.", " rouge."], i % 3) for i in range(30)][:n_max]

    monkeypatch.setattr("forge.evaluation.rapport.charger_frenchbench", faux_chargement)
    r = evaluer(sauvegarde_minuscule, donnees_test, tok_fichier_test, tmp_path, n_qcm=12, appareil="cpu")
    assert appels == [("hellaswag", 12), ("arc", 12)]  # n_qcm limite chaque test
    for nom in ("hellaswag", "arc"):
        assert r["qcm"][nom]["n"] == 12 and r["qcm"][nom]["hasard"] == pytest.approx(1 / 3)
    ecrit, md = lire_rapport(tmp_path)
    assert ecrit["qcm"] == json.loads(json.dumps(r["qcm"]))
    assert "HellaSwag" in md and "ARC-Challenge" in md and "hasard" in md.lower()
    assert f"33,3{ESPACE_FINE}%" in md  # le hasard, à la française
    verifier_typographie(md)
    # La marge du hasard a son unité ; le verdict est prudent (12 questions) ; la mesure n'est pas celle des autres.
    assert re.search(r"± \d+,\d points?", md)
    assert "pas différent du hasard" in md
    assert "pas aux scores publiés" in md and "comparable seulement entre nos modèles et au hasard" in md
    # Quand le nombre de questions est limité, le rapport dit sur combien de questions le test existe.
    assert f"12 premières questions sur 9{ESPACE_FINE}338" in md and f"12 premières questions sur 1{ESPACE_FINE}169" in md
    assert (r["qcm"]["hellaswag"]["total_du_test"], r["qcm"]["arc"]["total_du_test"]) == (9338, 1169)
    # Toutes les questions : `None` est transmis tel quel.
    appels.clear()
    evaluer(sauvegarde_minuscule, donnees_test, tok_fichier_test, tmp_path, n_qcm=None, appareil="cpu")
    assert appels == [("hellaswag", None), ("arc", None)]
    assert "premières questions" not in lire_rapport(tmp_path)[1]  # toutes les questions : rien à préciser


def test_rapport_garde_les_mesures_si_frenchbench_est_injoignable(
    tmp_path, monkeypatch, sauvegarde_minuscule, donnees_test, tok_fichier_test
):
    def reseau_coupe(nom, n_max=None):
        raise ConnectionError("Impossible de joindre huggingface.co")

    monkeypatch.setattr("forge.evaluation.rapport.charger_frenchbench", reseau_coupe)
    r = evaluer(sauvegarde_minuscule, donnees_test, tok_fichier_test, tmp_path, n_qcm=5, appareil="cpu")
    assert "huggingface.co" in r["qcm"]["hellaswag"]["erreur"] and "erreur" in r["qcm"]["arc"]
    assert r["perplexite"] > 1 and len(r["echantillons"]) == 10  # le reste est bien là
    _, md = lire_rapport(tmp_path)
    assert "huggingface.co" in md and "Relance" in md
    assert f"ConnectionError{ESPACE_FINE}: Impossible" in md  # le nom de l'erreur, typographié
    verifier_typographie(md)


def test_rapport_ecrit_null_et_jamais_infinity(
    tmp_path, monkeypatch, sauvegarde_minuscule, donnees_test, tok_fichier_test
):
    """Une perte énorme donne une perplexité infinie : le JSON écrit `null`, un JSON valide partout."""
    monkeypatch.setattr("forge.evaluation.rapport.perte_validation", lambda *arguments, **options: 1000.0)
    r = evaluer(sauvegarde_minuscule, donnees_test, tok_fichier_test, tmp_path, n_qcm=0, appareil="cpu")
    assert r["perplexite"] == math.inf
    texte = (tmp_path / "rapport.json").read_text(encoding="utf-8")
    assert "Infinity" not in texte and "NaN" not in texte

    def refuser(constante):
        raise ValueError(f"constante non JSON : {constante}")

    ecrit = json.loads(texte, parse_constant=refuser)  # un analyseur strict accepte le fichier
    assert ecrit["perplexite"] is None and ecrit["perte_val"] == 1000.0
    assert ecrit["bits_par_octet"] == pytest.approx(1000 / math.log(2))  # fini : écrit tel quel
    md = (tmp_path / "rapport.md").read_text(encoding="utf-8")
    assert "| Perplexité | ∞ |" in md
    verifier_typographie(md)


def test_rapport_lit_une_etape_ou_un_dossier(tmp_path, sauvegardes_minuscules, donnees_test, tok_fichier_test):
    etape = evaluer(sauvegardes_minuscules / "etape-0000004.pt", donnees_test, tok_fichier_test, tmp_path / "a", 0, "cpu")
    dossier = evaluer(sauvegardes_minuscules, donnees_test, tok_fichier_test, tmp_path / "b", 0, "cpu")
    assert etape["pas"] == dossier["pas"] == 4  # un dossier : la dernière étape
    assert etape["perte_val"] == pytest.approx(dossier["perte_val"])


def test_rapport_est_reproductible(tmp_path, sauvegarde_minuscule, donnees_test, tok_fichier_test):
    a = evaluer(sauvegarde_minuscule, donnees_test, tok_fichier_test, tmp_path / "a", 0, "cpu")
    b = evaluer(sauvegarde_minuscule, donnees_test, tok_fichier_test, tmp_path / "b", 0, "cpu")
    for cle in ("perte_val", "perplexite", "bits_par_octet", "echantillons"):
        assert a[cle] == b[cle]


def test_rapport_erreurs_en_francais(tmp_path, sauvegarde_minuscule, donnees_test, tok_fichier_test):
    # Une sauvegarde absente.
    with pytest.raises(FileNotFoundError, match="introuvable"):
        evaluer(tmp_path / "absent.pt", donnees_test, tok_fichier_test, tmp_path / "s", 0, "cpu")
    # Un fichier qui n'est pas une sauvegarde de la forge.
    autre = tmp_path / "autre.pt"
    torch.save({"quelque chose": 1}, autre)
    with pytest.raises(ValueError, match="pas une sauvegarde"):
        evaluer(autre, donnees_test, tok_fichier_test, tmp_path / "s", 0, "cpu")
    # Un autre tokenizer : un vocabulaire d'une autre taille…
    autre_tokenizer = tmp_path / "autre-tokenizer.json"
    TokenizerOctets([], 400, "autre").enregistrer(autre_tokenizer)
    with pytest.raises(ValueError, match="400 jetons.*322"):
        evaluer(sauvegarde_minuscule, donnees_test, autre_tokenizer, tmp_path / "s", 0, "cpu")
    # … ou, à taille égale, des jetons encodés autrement (l'empreinte de l'index ne correspond pas).
    fusionne = TokenizerOctets([(104, 105)], VOCABULAIRE, "fusionne")  # « h » + « i » : une fusion de plus
    fichier = tmp_path / "fusionne.json"
    fusionne.enregistrer(fichier)
    with pytest.raises(ValueError, match="autre tokenizer"):
        evaluer(sauvegarde_minuscule, donnees_test, fichier, tmp_path / "s", 0, "cpu")


@pytest.mark.gpu
def test_rapport_gpu_donne_la_meme_perte_qu_en_bf16(tmp_path, sauvegarde_minuscule, donnees_test, tok_fichier_test):
    cpu = evaluer(sauvegarde_minuscule, donnees_test, tok_fichier_test, tmp_path / "cpu", 0, "cpu")
    gpu = evaluer(sauvegarde_minuscule, donnees_test, tok_fichier_test, tmp_path / "gpu", 0, "cuda")
    assert gpu["appareil"] == "cuda" and cpu["appareil"] == "cpu"
    assert gpu["perte_val"] == pytest.approx(cpu["perte_val"], abs=0.05)  # bf16 : quelques millièmes d'écart


# --------------------------------------------------------------------------------------
# La sous-commande
# --------------------------------------------------------------------------------------


def arguments_evaluer(sauvegarde: Path, donnees: Path, tokenizer: Path, sortie: Path, *plus: str) -> list[str]:
    return [
        "evaluer",
        "--sauvegarde",
        str(sauvegarde),
        "--donnees",
        str(donnees),
        "--tokenizer",
        str(tokenizer),
        "--sortie",
        str(sortie),
        "--appareil",
        "cpu",
        *plus,
    ]


def test_sous_commande_evaluer(tmp_path, sauvegarde_minuscule, donnees_test, tok_fichier_test, capsys):
    assert main(arguments_evaluer(sauvegarde_minuscule, donnees_test, tok_fichier_test, tmp_path, "--qcm", "0")) == 0
    ecran = capsys.readouterr().out
    assert (tmp_path / "rapport.json").is_file() and (tmp_path / "rapport.md").is_file()
    assert "Perplexité" in ecran and str(tmp_path / "rapport.md") in ecran


def test_sous_commande_evaluer_sortie_par_defaut(tmp_path, sauvegarde_minuscule, donnees_test, tok_fichier_test):
    """Sans --sortie : `<entraînement>/evaluation/<nom de la sauvegarde>/`, une sauvegarde ne cache pas l'autre."""
    copie = tmp_path / "entrainement" / "sauvegardes"
    copie.mkdir(parents=True)
    (copie / "meilleur.pt").write_bytes(sauvegarde_minuscule.read_bytes())
    arguments = ["evaluer", "--sauvegarde", str(copie / "meilleur.pt"), "--donnees", str(donnees_test)]
    arguments += ["--tokenizer", str(tok_fichier_test), "--appareil", "cpu", "--qcm", "0"]
    assert main(arguments) == 0
    assert (tmp_path / "entrainement" / "evaluation" / "meilleur" / "rapport.md").is_file()


def test_sous_commande_evaluer_leve_le_mode_hors_ligne(
    tmp_path, monkeypatch, sauvegarde_minuscule, donnees_test, tok_fichier_test, capsys
):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.delenv("HF_DATASETS_OFFLINE", raising=False)
    vus = []

    def faux_chargement(nom, n_max=None):
        vus.append(os.environ["HF_HUB_OFFLINE"])
        return [QCM(QUESTION_CIEL, [" bleu.", " rouge."], 0)]

    monkeypatch.setattr("forge.evaluation.rapport.charger_frenchbench", faux_chargement)
    # Sans QCM, pas de réseau : la variable reste comme l'utilisateur l'a réglée.
    assert main(arguments_evaluer(sauvegarde_minuscule, donnees_test, tok_fichier_test, tmp_path / "a", "--qcm", "0")) == 0
    assert os.environ["HF_HUB_OFFLINE"] == "1" and vus == []
    capsys.readouterr()
    # Avec des QCM, FrenchBench se charge avec le réseau permis, et la commande le dit.
    assert main(arguments_evaluer(sauvegarde_minuscule, donnees_test, tok_fichier_test, tmp_path / "b", "--qcm", "1")) == 0
    assert vus == ["0", "0"]
    assert "HF_HUB_OFFLINE" in capsys.readouterr().out


def test_sous_commande_evaluer_erreurs_en_francais(tmp_path, donnees_test, tok_fichier_test, capsys):
    code = main(arguments_evaluer(tmp_path / "absent.pt", donnees_test, tok_fichier_test, tmp_path / "s", "--qcm", "0"))
    erreur = capsys.readouterr().err
    assert code == 1 and erreur.startswith("Erreur : ") and "absent.pt" in erreur


# --------------------------------------------------------------------------------------
# Les imports
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("premier", ["forge.entrainement", "forge.evaluation", "forge.entrainement.boucle"])
def test_les_deux_paquets_s_importent_dans_n_importe_quel_ordre(premier):
    """`boucle` réutilise `forge.evaluation.perte`, qui ne doit pas rappeler `forge.entrainement`."""
    code = f"import {premier}, forge.entrainement, forge.evaluation; print('ok')"
    resultat = subprocess.run(
        [sys.executable, "-c", code], cwd=RACINE_DU_PROJET, capture_output=True, text=True, encoding="utf-8"
    )
    assert resultat.returncode == 0 and resultat.stdout.strip() == "ok", resultat.stderr
