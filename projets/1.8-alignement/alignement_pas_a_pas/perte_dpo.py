"""La perte DPO, refaite à la main, en nombres ordinaires.

Pour une paire (réponse choisie, réponse rejetée), la DPO a besoin de quatre log-probabilités, chacune la somme
des log-probabilités des jetons de la réponse :

- `pc` et `pr` : celles de la **politique**, le modèle qu'on entraîne, pour la choisie et la rejetée ;
- `qc` et `qr` : celles de la **référence**, la version de départ, qui ne bouge pas.

Le gain d'une réponse est l'écart entre la politique et la référence. La perte pousse le gain de la choisie
au-dessus de celui de la rejetée :

    z = β ((pc − qc) − (pr − qr))
    perte = −ln σ(z) = ln(1 + e^(−z))

`forge.affinage.dpo.perte_dpo` calcule la même chose sur des tenseurs, et y ajoute le terme SFT. Ce module les
refait en nombres Python (des float64), et un test les compare à 10⁻¹² près.
"""

import math


# region: perte-dpo
def sigmoide(x: float) -> float:
    """σ(x) = 1 / (1 + e^(−x)), sans dépassement : e^(−x) n'est calculé que pour un exposant négatif ou nul."""
    if x >= 0:
        return 1 / (1 + math.exp(-x))
    e = math.exp(x)
    return e / (1 + e)


def moins_log_sigmoide(z: float) -> float:
    """−ln σ(z) = ln(1 + e^(−z)), écrit pour rester exact quand z est très grand ou très négatif.

    Pour z négatif, −z est positif et e^(−z) est énorme : on sort −z de la somme, ln(1 + e^(−z)) = −z + ln(1 + e^z).
    """
    return max(-z, 0.0) + math.log1p(math.exp(-abs(z)))


def perte_dpo_a_la_main(pc: float, pr: float, qc: float, qr: float, beta: float) -> float:
    """La perte DPO d'une paire : −ln σ(β ((pc − qc) − (pr − qr))).

    Sans le terme SFT (voir `terme_sft_a_la_main`). β dit la force de la préférence : plus il est grand, plus
    un petit écart de gain suffit à rendre la perte petite.
    """
    gain_choisie = pc - qc
    gain_rejetee = pr - qr
    z = beta * (gain_choisie - gain_rejetee)
    return moins_log_sigmoide(z)


def terme_sft_a_la_main(pc: float, lc: int) -> float:
    """Le terme SFT d'une paire : la perte par jeton de la réponse choisie, −pc / lc (lc : ses jetons appris).

    La DPO seule peut écarter les deux réponses en les rendant toutes deux moins probables ; ce terme retient la
    choisie. La perte totale de forge est `perte_dpo + poids_sft × terme_sft`.
    """
    return -pc / lc


def derivee_a_la_main(beta: float, ecart_choisie: float, ecart_rejetee: float) -> float:
    """La dérivée de la perte DPO selon l'écart de la choisie (pc − qc) : −β σ(−z).

    Elle est négative : monter la choisie fait baisser la perte. Selon l'écart de la rejetée, la dérivée est
    l'opposée (+β σ(−z)) : baisser la rejetée fait baisser la perte aussi, d'autant plus que z est petit.
    """
    z = beta * (ecart_choisie - ecart_rejetee)
    return -beta * sigmoide(-z)
# fin: perte-dpo
