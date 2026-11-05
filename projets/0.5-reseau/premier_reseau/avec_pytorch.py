"""Le même réseau 2-2-1, dans PyTorch : mêmes poids de départ, mêmes calculs, en float64.

`construire` recopie les poids d'un Reseau dans un modèle PyTorch. Autograd,
le calcul automatique des dérivées de PyTorch, doit alors retrouver les
gradients calculés à la main (a_la_main.py), à 10⁻¹² près : seuls les
arrondis des derniers chiffres diffèrent. `entrainer_pytorch` fait la même
descente avec l'optimiseur SGD de PyTorch, sur le processeur ou sur la carte
graphique, et la chronomètre.
"""

import time
from dataclasses import dataclass

import torch
from torch import nn

from premier_reseau.a_la_main import Gradients, Reseau
from premier_reseau.appareil import choisir_appareil


# region: modele
def construire(r: Reseau) -> nn.Sequential:
    """Le réseau 2-2-1 dans PyTorch, en float64, avec les poids de r."""
    modele = nn.Sequential(
        nn.Linear(2, 2, dtype=torch.float64),  # la couche cachée : 2 entrées, 2 neurones
        nn.Sigmoid(),
        nn.Linear(2, 1, dtype=torch.float64),  # la sortie : 2 entrées, 1 neurone
        nn.Sigmoid(),
    )
    with torch.no_grad():  # recopier des poids n'est pas un calcul à dériver
        modele[0].weight.copy_(torch.tensor(r.w1, dtype=torch.float64))  # forme (2, 2), comme w1[j][i]
        modele[0].bias.copy_(torch.tensor(r.b1, dtype=torch.float64))
        modele[2].weight.copy_(torch.tensor([r.w2], dtype=torch.float64))  # forme (1, 2)
        modele[2].bias.copy_(torch.tensor([r.b2], dtype=torch.float64))
    return modele
# fin: modele


def en_tenseurs(
    donnees: list[tuple[tuple[int, int], int]], appareil: torch.device | str = "cpu"
) -> tuple[torch.Tensor, torch.Tensor]:
    """Les points, de forme (4, 2), et leurs réponses, de forme (4, 1), en float64 sur l'appareil."""
    x = torch.tensor([point for point, _ in donnees], dtype=torch.float64, device=appareil)
    y = torch.tensor([[reponse] for _, reponse in donnees], dtype=torch.float64, device=appareil)
    return x, y


def reseau_de(modele: nn.Sequential) -> Reseau:
    """Les poids du modèle, recopiés dans un Reseau (sur le processeur)."""
    return Reseau(
        w1=modele[0].weight.detach().cpu().tolist(),
        b1=modele[0].bias.detach().cpu().tolist(),
        w2=modele[2].weight.detach().cpu()[0].tolist(),
        b2=modele[2].bias.detach().cpu().item(),
    )


# region: autograd
def gradients_pytorch(modele: nn.Sequential, donnees: list[tuple[tuple[int, int], int]]) -> Gradients:
    """Les dérivées de la perte moyenne par rapport aux 9 poids, calculées par autograd."""
    x, y = en_tenseurs(donnees, modele[0].weight.device)
    modele.zero_grad()  # efface les dérivées d'un calcul précédent
    perte = nn.BCELoss()(modele(x), y)  # l'erreur de 0.2, en moyenne sur les 4 points
    perte.backward()  # autograd remonte le calcul et range chaque dérivée dans .grad
    return Gradients(
        w1=modele[0].weight.grad.cpu().tolist(),
        b1=modele[0].bias.grad.cpu().tolist(),
        w2=modele[2].weight.grad.cpu()[0].tolist(),
        b2=modele[2].bias.grad.cpu().item(),
    )
# fin: autograd


@dataclass
class HistoriqueTorch:
    pertes: list[float]  # la perte moyenne avant le premier pas, puis après chaque pas
    reseau: Reseau  # les poids après le dernier pas
    millisecondes: float  # la durée des nb_pas pas


def attendre(appareil: torch.device) -> None:
    """Sur la carte, les calculs partent en file d'attente : on attend qu'ils soient finis."""
    if appareil.type == "cuda":
        torch.cuda.synchronize()


# region: entrainer-pytorch
def entrainer_pytorch(
    modele: nn.Sequential, donnees: list[tuple[tuple[int, int], int]], taux: float, nb_pas: int, appareil: str
) -> HistoriqueTorch:
    """La descente de a_la_main.entrainer, faite par PyTorch sur l'appareil, et chronométrée."""
    ou = choisir_appareil(appareil)
    modele.to(ou)  # les poids vont dans la mémoire de l'appareil
    x, y = en_tenseurs(donnees, ou)
    erreur = nn.BCELoss()
    optimiseur = torch.optim.SGD(modele.parameters(), lr=taux)  # chaque pas : poids −= taux × dérivée
    pertes = []
    attendre(ou)
    debut = time.perf_counter()
    for _ in range(nb_pas):
        optimiseur.zero_grad()
        perte = erreur(modele(x), y)
        pertes.append(perte.detach())  # gardée sur l'appareil : la lire ici ferait attendre la carte
        perte.backward()
        optimiseur.step()
    with torch.no_grad():
        pertes.append(erreur(modele(x), y))  # la perte après le dernier pas
    attendre(ou)  # sur la carte, les calculs ne sont finis qu'ici
    millisecondes = (time.perf_counter() - debut) * 1000
    return HistoriqueTorch(torch.stack(pertes).cpu().tolist(), reseau_de(modele), millisecondes)
# fin: entrainer-pytorch


def en_liste(poids: Reseau | Gradients) -> list[float]:
    """Les 9 nombres d'un réseau ou de ses gradients, à plat : w1, b1, w2, puis b2."""
    return [*poids.w1[0], *poids.w1[1], *poids.b1, *poids.w2, poids.b2]


def plus_grand_ecart(a: Reseau | Gradients, b: Reseau | Gradients) -> float:
    """Le plus grand écart entre deux séries de 9 nombres, nombre par nombre."""
    return max(abs(x - y) for x, y in zip(en_liste(a), en_liste(b), strict=True))
