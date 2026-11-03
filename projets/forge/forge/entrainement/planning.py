"""Le planning du taux d'apprentissage : une montée linéaire, puis une descente en cosinus.

Le taux d'apprentissage dit de combien on bouge les poids à chaque pas. Au tout début, les
poids sont tirés au hasard et les gradients sont désordonnés : de grands pas déstabiliseraient
le modèle. On monte donc doucement, en ligne droite, de 0 jusqu'à `taux_max` pendant les
`echauffement` premiers pas. Ensuite, on redescend lentement en suivant une demi-vague de
cosinus, jusqu'à `ratio_min × taux_max` au dernier pas : en fin d'entraînement, de petits pas
affinent ce qui est appris sans le défaire.

Le taux ne dépend que du numéro du pas : après une pause, le planning repart au bon endroit
sans rien sauvegarder de plus que ce numéro.
"""

import math


def taux(pas: int, pas_total: int, taux_max: float, echauffement: int, ratio_min: float = 0.1) -> float:
    """Taux d'apprentissage du pas numéro `pas` (le premier pas exécuté porte le numéro 1).

    - de 0 à `echauffement` : montée linéaire, de 0 à `taux_max` ;
    - de `echauffement` à `pas_total` : descente en cosinus, de `taux_max` à
      `ratio_min × taux_max` ;
    - après `pas_total` : `ratio_min × taux_max`, sans bouger.

    Exemple, avec 1 000 pas dont 100 d'échauffement et `taux_max = 1e-3` : le pas 50 a
    5e-4, le pas 100 a 1e-3, le pas 550 (au milieu de la descente) a 5,5e-4 et le pas 1 000
    a 1e-4.
    """
    taux_min = ratio_min * taux_max
    if pas < echauffement:
        return taux_max * pas / echauffement
    if pas >= pas_total:
        return taux_min
    avancement = (pas - echauffement) / max(1, pas_total - echauffement)  # de 0 à 1
    return taux_min + (taux_max - taux_min) * 0.5 * (1 + math.cos(math.pi * avancement))
