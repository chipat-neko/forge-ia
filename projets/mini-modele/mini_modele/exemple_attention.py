"""L'exemple de l'animation de l'attention : « Le forgeron chauffe le fer puis il le tord ».

Seuls les vecteurs des mots et les matrices sont écrits à la main, dans
donnees/exemple-attention.json : chaque mot porte 8 traits (des 0 et des 1),
et chacune des 2 têtes a trois matrices de 8 lignes et 4 colonnes, d'entiers
de −5 à 5. Tout le reste est calculé ici, par les fonctions du mini-modèle
(attention.py) : les requêtes, les clés et les valeurs, les scores, le
masque, les poids et les sorties.

Le fichier porte aussi sa légende (« legende », facultative) : ce que
l'animation du site dit de ces vecteurs, sous la figure. Elle appartient à
l'exemple : un autre exemple dit d'où viennent ses propres nombres.

Les conventions sont celles du mini-modèle :

- un vecteur est une ligne, et sa projection vaut x · W :
  y[j] = x[0] × W[0][j] + x[1] × W[1][j] + …, par i croissant ;
- les lignes sont les requêtes : la requête i pose la question, et le score
  de la clé j vaut requête · clé (scores_attention), multiplié par l'échelle
  1 / √(taille de la tête) dans scores_echelles ;
- le masque causal : la requête i ne voit que les mots 0 à i. Les cases
  masquées (j > i) n'ont pas de score (None), et leur poids vaut 0,0.

Le jumeau TypeScript est site/src/lib/mini-modele/exemple-attention.ts : il
suit ce fichier ligne à ligne. Ce fichier est vérifié par tests/test_sources.py.
"""

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from mini_modele.attention import melanger_valeurs, scores_attention, softmax
from mini_modele.calcul import produit_scalaire, racine

FICHIER_EXEMPLE = Path(__file__).resolve().parent.parent / "donnees" / "exemple-attention.json"
CLES_EXEMPLE = ("phrase", "jetons", "traits", "x", "tetes")
MATRICES_TETE = ("wq", "wk", "wv")

Matrice = Sequence[Sequence[float]]


@dataclass(frozen=True)
class DetailTete:
    """Tout ce qu'une tête calcule sur la phrase, pour l'animation (n mots).

    - requetes, cles, valeurs : une ligne par mot (n × 4) ;
    - scores (requête · clé) et scores_echelles (fois l'échelle) : n × n, None quand j > i ;
    - poids : n × n, le softmax des scores_echelles visibles, et 0,0 quand j > i ;
    - sorties : une ligne par mot (n × 4), les valeurs mélangées selon les poids.
    """

    requetes: list[list[float]]
    cles: list[list[float]]
    valeurs: list[list[float]]
    scores: list[list[float | None]]
    scores_echelles: list[list[float | None]]
    poids: list[list[float]]
    sorties: list[list[float]]


def est_nombre_fini(v: object) -> bool:
    """Un nombre (pas un booléen), ni infini ni NaN."""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def verifier_matrice(m: object, nom: str, lignes: int | None) -> int:
    """m est une liste de lignes non vide, de même longueur, de nombres finis. Renvoie sa largeur.

    Si lignes est donné, m doit avoir exactement ce nombre de lignes (une par trait).
    """
    if not isinstance(m, (list, tuple)) or len(m) == 0:
        raise ValueError(f"{nom} doit être une liste de lignes non vide.")
    if lignes is not None and len(m) != lignes:
        raise ValueError(f"{nom} doit avoir {lignes} lignes, une par trait (reçu {len(m)}).")
    largeur = -1
    for i in range(len(m)):
        ligne = m[i]
        if not isinstance(ligne, (list, tuple)) or len(ligne) == 0:
            raise ValueError(f"{nom}, ligne {i} : il faut une liste de nombres non vide.")
        if largeur < 0:
            largeur = len(ligne)
        if len(ligne) != largeur:
            raise ValueError(
                f"{nom} : la ligne {i} n'a pas la longueur de la ligne 0 ({len(ligne)} au lieu de {largeur}). "
                "Donne des lignes de même longueur."
            )
        for v in ligne:
            if not est_nombre_fini(v):
                raise ValueError(f"{nom}, ligne {i} : « {v!r} » n'est pas un nombre fini.")
    return largeur


def verifier_exemple(exemple: object) -> None:
    """L'exemple a ses cinq clés, une ligne de x par jeton, une case par trait, et des têtes complètes."""
    if not isinstance(exemple, dict):
        raise ValueError("L'exemple doit être un objet JSON avec phrase, jetons, traits, x et tetes.")
    for cle in CLES_EXEMPLE:
        if cle not in exemple:
            raise ValueError(f"Exemple d'attention : il manque « {cle} » (il faut phrase, jetons, traits, x et tetes).")
    phrase, jetons, traits, x = exemple["phrase"], exemple["jetons"], exemple["traits"], exemple["x"]
    if (
        not isinstance(phrase, str)
        or not isinstance(jetons, (list, tuple))
        or not isinstance(traits, (list, tuple))
        or len(jetons) == 0
        or len(traits) == 0
        or not all(isinstance(t, str) for t in list(jetons) + list(traits))
    ):
        raise ValueError(
            "Exemple d'attention : la phrase, les jetons et les traits sont des textes (au moins un jeton et un trait)."
        )
    if "legende" in exemple and not isinstance(exemple["legende"], str):
        raise ValueError("Exemple d'attention : la légende, si elle est donnée, est un texte.")
    largeur = verifier_matrice(x, "x", None)
    if len(x) != len(jetons):
        raise ValueError(f"Exemple d'attention : il faut une ligne de x par jeton ({len(jetons)} jetons, {len(x)} lignes).")
    if largeur != len(traits):
        raise ValueError(
            f"Exemple d'attention : chaque ligne de x a une case par trait ({len(traits)} traits, {largeur} cases)."
        )
    tetes = exemple["tetes"]
    if not isinstance(tetes, (list, tuple)) or len(tetes) == 0:
        raise ValueError("Exemple d'attention : il faut au moins une tête dans tetes.")
    for tete in tetes:
        if not isinstance(tete, dict) or not isinstance(tete.get("nom"), str) or not isinstance(tete.get("description"), str):
            raise ValueError("Exemple d'attention : le nom et la description de chaque tête sont des textes.")
        for m in MATRICES_TETE:
            if m not in tete:
                raise ValueError(f"Exemple d'attention : il manque « {m} » dans la tête « {tete['nom']} ».")
            verifier_matrice(tete[m], f"tête « {tete['nom']} », {m}", largeur)


def charger_exemple(chemin: str | Path | None = None) -> dict:
    """L'exemple du fichier (par défaut donnees/exemple-attention.json), vérifié. Chaque appel relit le fichier."""
    octets = Path(FICHIER_EXEMPLE if chemin is None else chemin).read_bytes()
    exemple = json.loads(octets.decode("utf-8"))
    verifier_exemple(exemple)
    return exemple


def en_flottants(m: Matrice) -> list[list[float]]:
    """Une copie de la matrice, en flottants : les mêmes nombres que ceux du TypeScript."""
    return [[float(v) for v in ligne] for ligne in m]


def projeter(x: Sequence[float], w: Matrice) -> list[float]:
    """x · W : y[j] = x[0] × W[0][j] + x[1] × W[1][j] + …, par i croissant (comme produit dans modele.py)."""
    y = []
    for j in range(len(w[0])):
        colonne = [w[i][j] for i in range(len(w))]
        y.append(produit_scalaire(x, colonne))
    return y


def detailler_tete(x: Matrice, wq: Matrice, wk: Matrice, wv: Matrice) -> DetailTete:
    """Le calcul d'une tête sur toute la phrase, mot par mot, avec les fonctions du mini-modèle."""
    traits = verifier_matrice(x, "x", None)
    taille = verifier_matrice(wq, "wq", traits)
    if verifier_matrice(wk, "wk", traits) != taille:
        raise ValueError(
            f"wq et wk doivent avoir autant de colonnes ({taille} et {len(wk[0])}) : le score est requête · clé."
        )
    verifier_matrice(wv, "wv", traits)
    xf, wqf, wkf, wvf = en_flottants(x), en_flottants(wq), en_flottants(wk), en_flottants(wv)
    requetes = [projeter(ligne, wqf) for ligne in xf]
    cles = [projeter(ligne, wkf) for ligne in xf]
    valeurs = [projeter(ligne, wvf) for ligne in xf]
    echelle = 1.0 / racine(float(taille))  # 1 / √4 = 0,5 pour des têtes de 4
    n = len(xf)
    scores = []
    scores_echelles = []
    poids = []
    sorties = []
    for i in range(n):
        visibles = cles[: i + 1]  # le masque causal : les mots 0 à i
        masques = n - i - 1
        bruts = scores_attention(requetes[i], visibles, 1.0)
        echelles = scores_attention(requetes[i], visibles, echelle)
        p = softmax(echelles)
        scores.append(bruts + [None] * masques)
        scores_echelles.append(echelles + [None] * masques)
        poids.append(p + [0.0] * masques)
        sorties.append(melanger_valeurs(p, valeurs[: i + 1]))
    return DetailTete(requetes, cles, valeurs, scores, scores_echelles, poids, sorties)


def detailler_exemple(exemple: dict) -> list[DetailTete]:
    """Le détail de chaque tête de l'exemple, dans l'ordre des têtes."""
    verifier_exemple(exemple)
    return [detailler_tete(exemple["x"], t["wq"], t["wk"], t["wv"]) for t in exemple["tetes"]]
