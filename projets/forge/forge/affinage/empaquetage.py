"""Empaquetage BFD (« best-fit decreasing ») des exemples en rangées de `longueur + 1` jetons.

Plusieurs conversations courtes partagent une rangée : le masque par document du transformer
(`forge.modele.transformer.masque_des_documents`) les empêche de se voir. Un exemple n'est
jamais coupé : s'il est plus long qu'une rangée, ou s'il n'a aucun jeton appris (il ne
donnerait aucune perte), il est écarté, et compté.
"""

import heapq
from collections.abc import Sequence
from dataclasses import dataclass

from forge.conversation.format import ExempleMasque


@dataclass(frozen=True)
class Rangee:
    """Une rangée de `longueur + 1` positions.

    - `ids` : les jetons, puis du bourrage ;
    - `appris` : `True` là où le jeton est une cible apprise (jamais pour le bourrage) ;
    - `documents` : le numéro de l'exemple de chaque position, de 0 à n - 1 dans la rangée,
      et -1 pour le bourrage.
    """

    ids: list[int]
    appris: list[bool]
    documents: list[int]


def empaqueter(
    exemples: Sequence[ExempleMasque], longueur: int, bourrage: int
) -> tuple[list[Rangee], int]:
    """Range les exemples en rangées de `longueur + 1` jetons ; rend aussi le nombre d'écartés.

    Les exemples sont pris par longueur décroissante (à égalité, dans leur ordre d'origine).
    Chacun va dans la rangée où il laisse le moins de place libre ; s'il ne tient dans aucune,
    il ouvre une nouvelle rangée. Le reste de chaque rangée est du bourrage (`bourrage`,
    `appris=False`, document -1).
    """
    if longueur < 1:
        raise ValueError(f"La longueur d'une rangée doit valoir au moins 1, pas {longueur}.")
    capacite = longueur + 1
    gardes: list[tuple[int, ExempleMasque]] = []
    ecartes = 0
    for rang, exemple in enumerate(exemples):
        if len(exemple.ids) != len(exemple.appris):
            raise ValueError(
                f"L'exemple {rang} a {len(exemple.ids)} jetons mais {len(exemple.appris)} valeurs "
                "de masque : refais son encodage avec `encoder_conversation`."
            )
        if len(exemple.ids) > capacite or not any(exemple.appris):
            ecartes += 1
        else:
            gardes.append((rang, exemple))
    gardes.sort(key=lambda g: (-len(g[1].ids), g[0]))

    contenus: list[list[ExempleMasque]] = []
    libre: list[int] = []
    # Un tas de numéros de rangée par place libre : la plus petite place qui convient, puis la
    # première rangée ouverte. La capacité est petite (2 049) : balayer les places suffit.
    par_place: list[list[int]] = [[] for _ in range(capacite + 1)]
    for _, exemple in gardes:
        taille = len(exemple.ids)
        place = next((p for p in range(taille, capacite + 1) if par_place[p]), None)
        if place is None:
            numero = len(contenus)
            contenus.append([])
            libre.append(capacite)
        else:
            numero = heapq.heappop(par_place[place])
        contenus[numero].append(exemple)
        libre[numero] -= taille
        heapq.heappush(par_place[libre[numero]], numero)

    return [_rangee(contenu, capacite, bourrage) for contenu in contenus], ecartes


def _rangee(exemples: list[ExempleMasque], capacite: int, bourrage: int) -> Rangee:
    ids: list[int] = []
    appris: list[bool] = []
    documents: list[int] = []
    for numero, exemple in enumerate(exemples):
        ids += exemple.ids
        appris += exemple.appris
        documents += [numero] * len(exemple.ids)
    reste = capacite - len(ids)
    return Rangee(ids + [bourrage] * reste, appris + [False] * reste, documents + [-1] * reste)
