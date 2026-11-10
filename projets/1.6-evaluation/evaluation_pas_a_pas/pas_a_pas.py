"""Les mesures de l'évaluation refaites à la main, une région par étape du chapitre 1.6.

Chaque fonction refait ce que forge calcule (`forge.evaluation`), avec le moins d'outils possible,
pour qu'on voie d'où vient chaque nombre. Les tests les comparent à forge.

- `perte` : la perte d'un lot, `-ln` de la probabilité donnée au vrai jeton suivant, en moyenne ;
- `perplexite` : `exp(perte)` ;
- `bits` : la perte ramenée à un octet de texte ;
- `qcm` : la log-vraisemblance de chaque choix d'une question à choix multiples, sans que le modèle
  écrive un mot, puis sa version divisée par les octets du choix ;
- `marge` : la marge de la mesure, celle du hasard, et le verdict.

Le verdict est celui du rapport de forge (`forge.evaluation.rapport.verdict`) : l'exactitude
NORMALISÉE comparée au hasard, avec la marge du HASARD.
"""

import math
from typing import Literal

import torch
from forge.evaluation.qcm import JETON_DE_DEBUT, QCM
from torch import Tensor


# region: perte
def perte_a_la_main(logits: Tensor, cibles: Tensor) -> float:
    """La perte d'un lot : la moyenne de `-ln(probabilité du vrai jeton suivant)`, sans `F.cross_entropy`.

    `logits` a la forme `[..., V]` (un score par jeton possible, à chaque position) et `cibles` la même
    forme sans le dernier axe (le vrai jeton suivant). La probabilité d'un jeton est son score mis
    à l'exponentielle, divisé par la somme de tous les scores mis à l'exponentielle (softmax). On
    retire d'abord le plus grand score à tous : la probabilité ne change pas, et `exp` ne déborde jamais.
    """
    plus_grand = logits.max(dim=-1, keepdim=True).values
    decales = logits - plus_grand
    log_somme = decales.exp().sum(dim=-1).log()  # ln de la somme des exponentielles
    choisis = decales.gather(-1, cibles[..., None]).squeeze(-1)  # le score du vrai jeton
    return float((log_somme - choisis).mean())  # -ln(proba) = ln(somme) - score
# fin: perte


# region: perplexite
def perplexite_a_la_main(perte: float) -> float:
    """`exp(perte)` : entre combien de jetons également probables le modèle hésite."""
    return math.exp(perte)
# fin: perplexite


# region: bits
def bits_par_octet_a_la_main(perte: float, octets_par_jeton: float) -> float:
    """La perte (en nats par jeton) ramenée à des bits par octet de texte : `perte / ln 2 / octets_par_jeton`."""
    return perte / math.log(2) / octets_par_jeton
# fin: bits


# region: qcm
@torch.no_grad()
def scores_a_la_main(modele, tokenizer, qcm: QCM) -> list[float]:
    """La log-vraisemblance (en nats) de chaque choix d'une question, une séquence à la fois.

    Pour un choix, le modèle lit `<|fin_texte|>`, la question, puis le choix, d'un seul coup. La
    position `t` donne un score à chaque jeton possible pour la position `t + 1` : la
    log-vraisemblance du choix est la somme, sur ses jetons, de `ln(probabilité du jeton sachant ce
    qui précède)`. Le modèle n'écrit rien : il juge seulement un texte déjà écrit. Rend les mêmes
    nombres que `forge.evaluation.qcm.scores_qcm` (à 10⁻⁵ près en relatif\u202f: forge arrondit les scores en
    float32 avant sa softmax, et lit plusieurs séquences d'un coup).
    """
    longueur = modele.config.longueur_contexte
    appareil = next(modele.parameters()).device
    debut = tokenizer.id_special(JETON_DE_DEBUT)
    contexte = tokenizer.encoder(qcm.contexte)
    scores = []
    for choix in qcm.choix:
        reponse = tokenizer.encoder(choix)
        ids = ([debut, *contexte, *reponse])[-longueur:]
        premiere = max(len(ids) - len(reponse), 1)  # la première position du choix
        logits, _ = modele(torch.tensor([ids], device=appareil))
        decales = logits[0] - logits[0].max(dim=-1, keepdim=True).values
        log_probas = decales - decales.exp().sum(dim=-1, keepdim=True).log()  # ln(softmax)
        total = 0.0
        for position in range(premiere, len(ids)):
            total += float(log_probas[position - 1, ids[position]])  # la position d'avant prédit ce jeton
        scores.append(total)
    return scores


def octets_du_choix(choix: str) -> int:
    """Le nombre d'octets UTF-8 d'un choix, espace initiale comprise (le texte qui suit la question)."""
    return len(choix.encode("utf-8"))


def scores_par_octet(qcm: QCM, scores: list[float]) -> list[float]:
    """Chaque log-vraisemblance divisée par les octets de son choix : des nats par octet.

    Un choix long a plus de jetons à deviner, donc une log-vraisemblance plus basse : sans cette
    division, les réponses courtes gagneraient. C'est « l'exactitude normalisée » du rapport.
    """
    return [score / octets_du_choix(choix) for score, choix in zip(scores, qcm.choix)]


def choix_prefere(scores: list[float]) -> int:
    """L'indice du plus grand score ; à égalité parfaite, le premier choix gagne (comme forge)."""
    return max(range(len(scores)), key=scores.__getitem__)
# fin: qcm


# region: marge
Verdict = Literal["au-dessus", "pas-different", "en-dessous"]

# 1,96 : l'intervalle à 95 % d'une loi normale va de −1,96 à +1,96 écarts-types.
Z_95 = 1.96


def marge_95(exactitude: float, n: int) -> float:
    """La demi-largeur de l'intervalle à 95 % d'une exactitude mesurée sur `n` questions (marge de Wald).

    C'est la formule de forge (`forge.evaluation.qcm._marge_95`) : `1,96 × √(p (1 − p) / n)`. Elle
    s'annule quand l'exactitude vaut 0 ou 1, même sur 5 questions : pour juger un écart au hasard,
    on utilise la marge du hasard.
    """
    return Z_95 * math.sqrt(exactitude * (1 - exactitude) / n)


def marge_hasard(n: int, choix: int = 4) -> float:
    """La demi-largeur de l'intervalle à 95 % d'un tirage au sort sur `n` questions de `choix` choix chacune.

    Chaque question est juste avec la probabilité `p = 1 / choix`, de variance `p (1 − p)` ; ces
    variances s'additionnent d'une question à l'autre. Elle ne dépend que des questions, jamais
    du résultat. Pour des questions qui n'ont pas toutes le même nombre de choix, forge additionne
    leurs variances une à une (`forge.evaluation.qcm._marge_hasard`).
    """
    p = 1 / choix
    return Z_95 * math.sqrt(n * (p * (1 - p))) / n


def verdict(exactitude: float, hasard: float, marge: float) -> Verdict:
    """Où est l'exactitude (normalisée) par rapport au hasard : « au-dessus », « en dessous » ou « pas-different ».

    C'est la règle de `forge.evaluation.rapport.verdict`. `marge` est la marge du HASARD
    (`marge_hasard`), pas celle de la mesure : la marge de la mesure s'annule à 0 ou 100 % de bonnes
    réponses, et affirmerait « en dessous du hasard » sur 0 bonne réponse sur 5, ce qui arrive une
    fois sur quatre au hasard avec 4 choix.
    """
    ecart = exactitude - hasard
    if ecart > marge:
        return "au-dessus"
    if ecart < -marge:
        return "en-dessous"
    return "pas-different"
# fin: marge
