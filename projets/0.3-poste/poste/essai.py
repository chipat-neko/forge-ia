"""Un essai de calcul : multiplier deux matrices sur un appareil, et vérifier le résultat.

Le produit se fait en float32, les nombres à virgule de 32 bits que les IA
utilisent, sur l'appareil choisi. On le compare au même produit fait en float64,
deux fois plus précis, sur le processeur : l'écart doit être minuscule. On
mesure aussi la durée d'un produit, en millisecondes.
"""

import math
import time
from dataclasses import dataclass

import torch

from poste.appareil import choisir_appareil

TAILLE_ESSAI = 512  # des matrices 512 × 512
REPETITIONS = 10  # la durée est la moyenne de 10 produits
NOMS = {"cpu": "processeur", "cuda": "carte graphique"}


# region: essai
@dataclass(frozen=True)
class EssaiCalcul:
    appareil: str  # « cpu » ou « cuda »
    ecart_max: float  # le plus grand écart avec le calcul en float64
    millisecondes: float  # la durée d'un produit


def attendre(appareil: torch.device) -> None:
    """Sur la carte, les calculs partent en file d'attente : on attend qu'ils soient finis."""
    if appareil.type == "cuda":
        torch.cuda.synchronize()


def essai_de_calcul(appareil: str, taille: int = TAILLE_ESSAI) -> EssaiCalcul:
    """Multiplie deux matrices taille × taille en float32 sur l'appareil, et compare au float64."""
    ou = choisir_appareil(appareil)
    hasard = torch.Generator().manual_seed(0)  # les mêmes matrices à chaque essai
    a = torch.randn(taille, taille, generator=hasard, dtype=torch.float64) / math.sqrt(taille)
    b = torch.randn(taille, taille, generator=hasard, dtype=torch.float64) / math.sqrt(taille)
    exact = a @ b  # en float64, sur le processeur

    a32 = a.to(device=ou, dtype=torch.float32)
    b32 = b.to(device=ou, dtype=torch.float32)
    produit = a32 @ b32  # un premier produit pour rien : sur la carte, il prépare le calcul
    attendre(ou)
    debut = time.perf_counter()
    for _ in range(REPETITIONS):
        produit = a32 @ b32
    attendre(ou)
    millisecondes = (time.perf_counter() - debut) * 1000 / REPETITIONS

    ecart = (produit.to(device="cpu", dtype=torch.float64) - exact).abs().max().item()
    return EssaiCalcul(ou.type, ecart, millisecondes)


# fin: essai


def en_francais(x: float, chiffres: int = 2) -> str:
    """Un nombre positif à la française, avec `chiffres` chiffres significatifs (au moins les unités) :
    2,1 ; 13 ; 123 ; 0,031 ; 0,0000012 ; 1 234 (avec une espace fine)."""
    if x == 0:
        return "0"
    decimales = max(0, chiffres - 1 - math.floor(math.log10(abs(x))))
    return f"{x:,.{decimales}f}".replace(",", "\u202f").replace(".", ",")


def decrire_essai(essai: EssaiCalcul) -> str:
    """La ligne du rapport pour un essai."""
    return (
        f"{NOMS.get(essai.appareil, essai.appareil)} ({essai.appareil})\u202f: "
        f"{en_francais(essai.millisecondes)} ms par produit, écart maximal {en_francais(essai.ecart_max)}"
    )
