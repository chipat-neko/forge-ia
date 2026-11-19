"""La perte DPO à la main égale celle de forge à 10⁻¹² près, et ne déborde pas."""

import math

import pytest
import torch

from forge.affinage.dpo import perte_dpo
from forge.entrainement.boucle import ReglagesDPO

from alignement_pas_a_pas.attendus import BETAS, ECARTS_DE_LA_CHOISIE, ECARTS_DE_LA_REJETEE
from alignement_pas_a_pas.perte_dpo import (
    derivee_a_la_main,
    moins_log_sigmoide,
    perte_dpo_a_la_main,
    sigmoide,
    terme_sft_a_la_main,
)


def t(x: float) -> torch.Tensor:
    """Un tenseur float64 d'un seul élément : une paire."""
    return torch.tensor([x], dtype=torch.float64)


# region: test-dpo
def test_la_perte_a_la_main_egale_celle_de_forge_a_1e_12_pres():
    ecarts = 0
    for beta in BETAS:
        for pc in (-30.0, -24.0, -20.0):  # les log-probabilités de la politique, sous la référence ou au-dessus
            for pr in (-34.0, -30.0, -26.0):
                qc, qr = -25.0, -30.0
                reglages = ReglagesDPO(beta=beta, poids_sft=0.0)  # sans le terme SFT : la DPO seule
                de_forge, _ = perte_dpo(t(pc), t(pr), t(qc), t(qr), t(7), t(9), reglages)
                a_la_main = perte_dpo_a_la_main(pc, pr, qc, qr, beta)
                assert abs(a_la_main - de_forge.item()) <= 1e-12, (beta, pc, pr)
                ecarts += 1
    assert ecarts == 27
# fin: test-dpo


def test_le_terme_sft_est_la_perte_par_jeton_de_la_choisie():
    pc, pr, qc, qr, lc, lr, beta, poids = -31.5, -44.0, -30.0, -41.0, 12, 15, 0.1, 0.7
    total, _ = perte_dpo(t(pc), t(pr), t(qc), t(qr), t(lc), t(lr), ReglagesDPO(beta=beta, poids_sft=poids))
    a_la_main = perte_dpo_a_la_main(pc, pr, qc, qr, beta) + poids * terme_sft_a_la_main(pc, lc)
    assert abs(total.item() - a_la_main) <= 1e-12
    assert terme_sft_a_la_main(-31.5, 12) == pytest.approx(2.625)  # 31,5 nats sur 12 jetons


def test_sans_ecart_de_gain_la_perte_vaut_ln_2():
    # La politique est la référence : z = 0, σ(0) = 1/2, la perte est ln 2 quel que soit β.
    for beta in BETAS:
        assert perte_dpo_a_la_main(-10.0, -12.0, -10.0, -12.0, beta) == pytest.approx(math.log(2), abs=1e-15)


def test_la_perte_baisse_quand_la_choisie_monte_ou_que_la_rejetee_descend():
    base = perte_dpo_a_la_main(-10.0, -12.0, -10.0, -12.0, 0.1)
    assert perte_dpo_a_la_main(-5.0, -12.0, -10.0, -12.0, 0.1) < base  # la choisie gagne 5
    assert perte_dpo_a_la_main(-10.0, -17.0, -10.0, -12.0, 0.1) < base  # la rejetée perd 5, autant
    assert perte_dpo_a_la_main(-5.0, -12.0, -10.0, -12.0, 0.1) == pytest.approx(perte_dpo_a_la_main(-10.0, -17.0, -10.0, -12.0, 0.1), abs=1e-15)
    assert perte_dpo_a_la_main(-15.0, -12.0, -10.0, -12.0, 0.1) > base  # la choisie perd : la perte monte


def test_la_perte_ne_deborde_pas_aux_extremes():
    # z = -800 : e^800 déborde ; la perte vaut alors -z, à e^z près.
    assert perte_dpo_a_la_main(-4000.0, 4000.0, 0.0, 0.0, 0.1) == pytest.approx(800.0, abs=1e-12)
    assert perte_dpo_a_la_main(4000.0, -4000.0, 0.0, 0.0, 0.1) == 0.0
    assert moins_log_sigmoide(-1e6) == 1e6 and moins_log_sigmoide(1e6) == 0.0
    assert sigmoide(-800.0) == 0.0 and sigmoide(800.0) == 1.0


def test_moins_log_sigmoide_est_log_de_1_plus_exp_moins_z():
    for z in (-30.0, -3.0, -0.5, 0.0, 0.5, 3.0, 30.0):
        assert moins_log_sigmoide(z) == pytest.approx(math.log1p(math.exp(-z)), rel=1e-14, abs=1e-15)
        assert moins_log_sigmoide(z) - moins_log_sigmoide(-z) == pytest.approx(-z, abs=1e-12)  # -ln σ(z) + ln σ(-z) = -z


def test_la_derivee_est_celle_de_la_perte_selon_la_choisie():
    for beta in BETAS:
        for ec in ECARTS_DE_LA_CHOISIE:
            for er in ECARTS_DE_LA_REJETEE:
                h = 1e-6
                numerique = (
                    perte_dpo_a_la_main(ec + h, er, 0.0, 0.0, beta) - perte_dpo_a_la_main(ec - h, er, 0.0, 0.0, beta)
                ) / (2 * h)
                assert derivee_a_la_main(beta, ec, er) == pytest.approx(numerique, abs=1e-7)
                assert derivee_a_la_main(beta, ec, er) < 0  # monter la choisie fait toujours baisser la perte


def test_la_derivee_est_celle_de_pytorch():
    pc = torch.tensor([-12.0], dtype=torch.float64, requires_grad=True)
    perte, _ = perte_dpo(pc, t(-20.0), t(-10.0), t(-18.0), t(7), t(9), ReglagesDPO(beta=0.3, poids_sft=0.0))
    perte.backward()
    assert derivee_a_la_main(0.3, -12.0 - -10.0, -20.0 - -18.0) == pytest.approx(pc.grad.item(), abs=1e-12)


def test_au_dela_de_20_le_softplus_de_pytorch_rend_z_tel_quel():
    # F.softplus(x) rend x quand x > 20 (seuil de PyTorch) : l'écart avec la formule exacte, e^(-x), est alors
    # de l'ordre de 1e-9. C'est pourquoi la grille des attendus et le test de 10⁻¹² restent sous |z| = 20.
    z = -20.5
    de_forge, _ = perte_dpo(t(0.0), t(205.0), t(0.0), t(0.0), t(7), t(9), ReglagesDPO(beta=0.1, poids_sft=0.0))
    exacte = perte_dpo_a_la_main(0.0, 205.0, 0.0, 0.0, 0.1)
    assert de_forge.item() == pytest.approx(-z, abs=1e-12)
    assert 1e-12 < abs(exacte - de_forge.item()) < 1e-8
