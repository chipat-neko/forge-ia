"""Les mesures refaites à la main égalent celles de forge.

La perte à la main est comparée à `F.cross_entropy` en float64 (10⁻¹² près), les scores d'un QCM à
`forge.evaluation.qcm.scores_qcm`, la marge à `_marge_95` de forge, et le verdict à celui du rapport.
La sauvegarde chargée par le projet rend la même perte que le modèle d'origine.
"""

import math
import random

import pytest
import torch
import torch.nn.functional as F
from forge.evaluation.perte import bits_par_octet, perplexite
from forge.evaluation.qcm import QCM, _marge_95, _marge_hasard, scores_qcm
from forge.evaluation.rapport import verdict as verdict_de_forge
from modele_factice import petit_modele, sauvegarder, tokenizer

from evaluation_pas_a_pas.pas_a_pas import (
    bits_par_octet_a_la_main,
    choix_prefere,
    marge_95,
    marge_hasard,
    octets_du_choix,
    perplexite_a_la_main,
    perte_a_la_main,
    scores_a_la_main,
    scores_par_octet,
    verdict,
)
from evaluation_pas_a_pas.sauvegarde import charger_sauvegarde

QUESTIONS = [
    QCM("Question : Quelle est la capitale de la France ?\nRéponse :", [" Paris.", " Lyon, une grande ville.", " Rome."], 0),
    QCM("Le chat dort sur le", [" canapé.", " toit de la maison voisine.", " lune.", " é"], 1),
]


def test_perte_a_la_main():
    graine = torch.Generator().manual_seed(0)
    logits = torch.randn(5, 7, dtype=torch.float64, generator=graine)
    cibles = torch.tensor([0, 3, 6, 1, 2])
    assert abs(perte_a_la_main(logits, cibles) - F.cross_entropy(logits, cibles).item()) <= 1e-12


def test_perte_a_la_main_sur_un_lot_de_textes():
    graine = torch.Generator().manual_seed(1)
    logits = torch.randn(3, 4, 11, dtype=torch.float64, generator=graine)
    cibles = torch.randint(0, 11, (3, 4), generator=graine)
    attendu = F.cross_entropy(logits.reshape(-1, 11), cibles.reshape(-1)).item()
    assert abs(perte_a_la_main(logits, cibles) - attendu) <= 1e-12


def test_perte_a_la_main_ne_deborde_pas():
    # Des scores énormes : exp(1000) déborderait sans le décalage par le plus grand score.
    logits = torch.tensor([[1000.0, 0.0, -1000.0]], dtype=torch.float64)
    assert perte_a_la_main(logits, torch.tensor([0])) == pytest.approx(0.0, abs=1e-12)
    assert perte_a_la_main(logits, torch.tensor([1])) == pytest.approx(1000.0, abs=1e-9)


def test_un_modele_au_hasard_a_la_perte_de_ln_v():
    logits = torch.zeros(4, 32768, dtype=torch.float64)
    assert perte_a_la_main(logits, torch.tensor([1, 2, 3, 4])) == pytest.approx(math.log(32768), abs=1e-12)


def test_perplexite_et_bits_egalent_ceux_de_forge():
    for perte in (0.5, 3.428356409072876, 10.39720770839918):
        assert perplexite_a_la_main(perte) == perplexite(perte)
        assert bits_par_octet_a_la_main(perte, 4.365476958627542) == bits_par_octet(perte, 4.365476958627542)


def test_scores_a_la_main_egaux_a_forge():
    modele, tok = petit_modele().double(), tokenizer()
    for qcm in QUESTIONS:
        a_la_main = scores_a_la_main(modele, tok, qcm)
        de_forge = scores_qcm(modele, tok, [qcm])[0]
        assert len(a_la_main) == len(qcm.choix)
        # forge arrondit les scores en float32 avant sa softmax : l'écart relatif reste sous 10⁻⁵.
        assert a_la_main == pytest.approx(de_forge, rel=1e-5)


def test_scores_a_la_main_gardent_la_fin_d_un_contexte_trop_long():
    modele, tok = petit_modele().double(), tokenizer()
    long = QCM("mot " * 200 + "fin", [" un.", " deux."], 0)  # bien plus de 64 jetons
    assert scores_a_la_main(modele, tok, long) == pytest.approx(scores_qcm(modele, tok, [long])[0], rel=1e-5)


def test_scores_par_octet_et_choix_prefere():
    qcm = QUESTIONS[0]
    scores = [-3.0, -9.0, -6.0]
    par_octet = scores_par_octet(qcm, scores)
    assert par_octet == [-3.0 / octets_du_choix(" Paris."), -9.0 / octets_du_choix(" Lyon, une grande ville."), -6.0 / octets_du_choix(" Rome.")]
    assert octets_du_choix(" é") == 3  # espace + « é » sur deux octets
    # Le choix long perd en log-vraisemblance brute, mais pas forcément par octet.
    assert choix_prefere([-5.0, -4.0, -4.0]) == 1  # à égalité, le premier gagne
    assert choix_prefere([-1.0, -2.0]) == 0


def test_marge_95_est_la_formule_de_forge():
    for exactitude in (0.0, 0.1, 0.2721139430284857, 0.5, 1.0):
        for n in (5, 100, 1169, 9338):
            assert marge_95(exactitude, n) == _marge_95(exactitude, n)
    assert marge_95(0.0, 5) == 0.0 and marge_95(1.0, 5) == 0.0  # la marge de la mesure s'annule aux extrêmes


def test_marge_hasard_est_celle_de_forge():
    for n in (5, 100, 1169, 9338):
        for choix in (3, 4, 5):
            qcms = [QCM("c", [" x"] * choix, 0)] * n
            assert marge_hasard(n, choix) == pytest.approx(_marge_hasard(qcms), rel=1e-12)
    assert marge_hasard(5, 4) > 0  # elle ne s'annule pas


def test_verdict_est_celui_de_forge():
    traduction = {"au-dessus du hasard": "au-dessus", "en dessous du hasard": "en-dessous", "pas différent du hasard": "pas-different"}
    hasard = random.Random(0)
    for _ in range(300):
        choix = hasard.choice((3, 4, 5))
        n = hasard.choice((5, 100, 1169))
        exactitude = hasard.randrange(n + 1) / n
        mesures = {"exactitude_normalisee": exactitude, "hasard": 1 / choix, "marge_hasard": marge_hasard(n, choix)}
        assert verdict(exactitude, 1 / choix, marge_hasard(n, choix)) == traduction[verdict_de_forge(mesures)]


def test_verdict_de_mini():
    # Les deux tests de « mini » (docs/mesures/ton-ia-mini.md) : HellaSwag au-dessus du hasard, ARC pas différent.
    assert verdict(0.27211394302848574, 0.25, 0.008782734869282344) == "au-dessus"
    assert verdict(0.23609923011120615, 0.2501568291987454, 0.024825917545327553) == "pas-different"
    assert verdict(0.0, 0.25, marge_hasard(5, 4)) == "pas-different"  # 0 juste sur 5 : un quart du temps, au hasard
    assert verdict(0.1, 0.25, marge_hasard(1169, 4)) == "en-dessous"


def test_sauvegarde_chargee_rend_la_meme_perte_que_forge(tmp_path):
    modele = petit_modele(3)
    chemin = sauvegarder(modele, tmp_path / "sauvegardes" / "etape-0000007.pt")
    charge, config = charger_sauvegarde(chemin)
    assert config == modele.config and not charge.training
    graine = torch.Generator().manual_seed(0)
    x = torch.randint(0, config.taille_vocabulaire, (2, 16), generator=graine)
    y = torch.randint(0, config.taille_vocabulaire, (2, 16), generator=graine)
    with torch.no_grad():
        _, perte_de_forge = modele(x, y)
        logits, perte_chargee = charge(x, y)
    assert perte_chargee.item() == perte_de_forge.item()
    assert abs(perte_a_la_main(logits.double(), y) - perte_de_forge.item()) <= 1e-6


def test_sauvegarde_d_un_dossier_prend_la_derniere_etape(tmp_path):
    sauvegarder(petit_modele(1), tmp_path / "etape-0000005.pt", pas=5)
    sauvegarder(petit_modele(2), tmp_path / "etape-0000009.pt", pas=9)
    charge, _ = charger_sauvegarde(tmp_path)
    assert torch.equal(charge.plongement.weight, petit_modele(2).plongement.weight)


def test_sauvegardes_inutilisables(tmp_path):
    with pytest.raises(FileNotFoundError, match="Sauvegarde introuvable"):
        charger_sauvegarde(tmp_path / "rien.pt")
    with pytest.raises(FileNotFoundError, match="Aucune sauvegarde"):
        charger_sauvegarde(tmp_path)
    faux = tmp_path / "faux.pt"
    faux.write_bytes(b"pas une sauvegarde")
    with pytest.raises(ValueError, match="ne se lit pas comme une sauvegarde"):
        charger_sauvegarde(faux)
    sans_config = tmp_path / "sans-config.pt"
    torch.save({"modele": {}}, sans_config)
    with pytest.raises(ValueError, match="n'est pas une sauvegarde de la forge"):
        charger_sauvegarde(sans_config)
    ancienne = tmp_path / "ancienne.pt"
    torch.save({"version": 0, "modele": {}, "config_modele": {}}, ancienne)
    with pytest.raises(ValueError, match="version 0"):
        charger_sauvegarde(ancienne)
