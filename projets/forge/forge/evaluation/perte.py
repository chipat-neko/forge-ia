"""La perte de validation, la perplexité et les bits par octet : trois façons de dire « le modèle prédit bien ».

La perte est la moyenne, sur des textes que le modèle n'a jamais appris (`val/`), de
`-ln(probabilité donnée au vrai jeton suivant)`. Elle se mesure en « nats par jeton » (le nat
est l'unité du logarithme népérien). Un modèle qui devine au hasard parmi 32 768 jetons a une
perte de `ln(32768) = 10,4` ; plus elle descend, mieux le modèle prédit.

- la perplexité, `exp(perte)`, dit « le modèle hésite comme s'il choisissait entre autant de
  jetons également probables » ;
- les bits par octet, `perte / ln 2 / octets_par_jeton`, ramènent la perte à un octet de texte
  au lieu d'un jeton. Un jeton ne vaut pas le même nombre d'octets d'un tokenizer à l'autre
  (environ 4,4 octets par jeton ici sur le mélange, voir `docs/mesures/tokenizer-ton-ia-v1.md`,
  1 pour un tokenizer d'octets purs) : seuls les bits par octet se comparent d'un tokenizer à
  l'autre.

La mesure se fait sur des morceaux fixes de `val/` (les mêmes à chaque fois, comme pendant
l'entraînement) : deux évaluations du même modèle donnent le même nombre.

Ce module ne doit pas importer `forge.entrainement` (la boucle d'entraînement importe celui-ci) :
le chargeur de jetons n'y sert qu'aux annotations de type.
"""

import json
import math
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import torch
from torch import nn

if TYPE_CHECKING:
    from forge.entrainement.chargeur import ChargeurJetons


def autocast(appareil: torch.device):
    """bf16 sur la carte graphique ; sur le processeur, on reste en 32 bits.

    Le calcul en `bfloat16` (16 bits au lieu de 32) est bien plus rapide sur la carte et prend
    deux fois moins de mémoire ; les poids, eux, restent en 32 bits.
    """
    return torch.autocast(device_type=appareil.type, dtype=torch.bfloat16, enabled=appareil.type == "cuda")


@contextmanager
def en_evaluation(modele: nn.Module) -> Iterator[None]:
    """Met le modèle en mode évaluation (sans dropout, etc.), puis rend à chaque sous-module le mode qu'il avait."""
    modes = {module: module.training for module in modele.modules()}
    modele.eval()
    try:
        yield
    finally:
        for module, mode in modes.items():
            module.training = mode


@torch.no_grad()
def perte_sur_morceaux(modele: nn.Module, chargeur: "ChargeurJetons", depart: dict, n_morceaux: int, appareil) -> float:
    """Perte moyenne par jeton sur les `n_morceaux` premiers morceaux de validation.

    Le chargeur repart toujours de `depart` : ce sont toujours les mêmes morceaux. On les lit
    par paquets de la taille du chargeur (`micro_lot`), le dernier paquet coupé au besoin :
    le résultat ne dépend pas de la taille des paquets. C'est la mesure de l'entraînement
    (`forge.entrainement.boucle`) et celle de l'évaluation.
    """
    chargeur.restaurer(depart)
    with en_evaluation(modele):
        somme = torch.zeros((), device=appareil)
        restants = n_morceaux
        while restants > 0:
            x, y = chargeur.lot()
            x, y = x[:restants], y[:restants]
            with autocast(appareil):
                _, perte = modele(x.to(appareil), y.to(appareil))
            somme += perte.float() * x.numel()  # la perte est une moyenne par jeton : on la remet en somme
            restants -= x.shape[0]
    return (somme / (n_morceaux * chargeur.longueur)).item()


def perte_validation(modele: nn.Module, chargeur: "ChargeurJetons", n_lots: int) -> float:
    """Perte de validation en nats par jeton, sur les `n_lots` premiers lots du chargeur.

    Un lot est `chargeur.taille_lot` morceaux de `chargeur.longueur` jetons. On lit toujours
    les premiers morceaux de l'époque 0, quelle que soit la position du chargeur : la mesure est
    fixe. On s'arrête au dernier morceau s'il y a moins de `n_lots` lots, sans en relire un.
    Le modèle et le chargeur sont rendus comme avant l'appel.
    """
    if n_lots < 1:
        raise ValueError(f"n_lots vaut {n_lots} : il faut lire au moins un lot.")
    avant = chargeur.etat()
    n_morceaux = min(n_lots * chargeur.taille_lot, chargeur.morceaux)
    try:
        appareil = next(modele.parameters()).device
        return perte_sur_morceaux(modele, chargeur, {**avant, "epoque": 0, "position": 0}, n_morceaux, appareil)
    finally:
        chargeur.restaurer(avant)


def perplexite(perte: float) -> float:
    """`exp(perte)` : entre combien de jetons également probables le modèle hésite."""
    try:
        return math.exp(perte)
    except OverflowError:
        return math.inf  # une perte d'au moins 710 nats : le modèle est complètement perdu


def bits_par_octet(perte: float, octets_par_jeton: float) -> float:
    """Ramène la perte (nats par jeton) à des bits par octet de texte : `perte / ln 2 / octets_par_jeton`."""
    if not octets_par_jeton > 0:
        raise ValueError(
            f"Le nombre d'octets par jeton vaut {octets_par_jeton} : il doit être plus grand que 0. "
            "Il vient de l'encodage des données (`python -m forge encoder`), dans index.json."
        )
    return perte / math.log(2) / octets_par_jeton


def lire_octets_par_jeton(dossier: Path) -> float:
    """Nombre moyen d'octets UTF-8 par jeton du corpus encodé dans `dossier`.

    `forge encoder` écrit, dans `index.json`, le nombre d'octets des textes (`octets`) et de
    leurs jetons sans les `<|fin_texte|>` (`jetons_sans_fin`) ; leur quotient est lu d'abord. À
    défaut, on prend `octets_par_jeton` du marqueur `.complet`, qui contient le même nombre.
    Ce nombre vaut pour tout le corpus (train et val ensemble) : c'est la meilleure mesure
    disponible pour la validation seule.
    """
    dossier = Path(dossier)
    try:
        index = json.loads((dossier / "index.json").read_text(encoding="utf-8"))
        octets, jetons = index["octets"], index["jetons_sans_fin"]
        if octets > 0 and jetons > 0:
            return octets / jetons
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        valeur = json.loads((dossier / ".complet").read_text(encoding="utf-8"))["octets_par_jeton"]
        if isinstance(valeur, int | float) and not isinstance(valeur, bool) and valeur > 0:
            return float(valeur)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    raise ValueError(
        f"Les jetons de {dossier} ne disent pas combien d'octets contient un jeton, nécessaire "
        "pour les bits par octet. Relance l'encodage avec : python -m forge encoder --donnees "
        f"{dossier.name} --tokenizer <chemin> (les fragments déjà encodés sont gardés)."
    )
