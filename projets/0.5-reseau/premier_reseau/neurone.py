"""Un neurone à seuil, et les portes logiques ET, OU et OU exclusif.

Le neurone reçoit deux entrées, x1 et x2, qui valent 0 ou 1. Il fait la somme
pondérée w1 × x1 + w2 × x2 + b, et répond 1 si elle dépasse 0, 0 sinon.
Ses trois réglages, les poids w1 et w2 et le biais b, sont cherchés ici sur
une grille de −2 à 2, par pas de 0,5 : 9 × 9 × 9 = 729 réglages.

Avec le bon réglage, il imite les portes ET et OU sur les 4 points. Pour le
OU exclusif, aucun réglage ne classe les 4 points : il en classe 3 au mieux.

Le site refait ce calcul en TypeScript (site/src/lib/partie-0/neurone.ts),
avec les mêmes opérations dans le même ordre : sur ces entrées, tout est
exact, et les deux donnent les mêmes réponses au bit près.
"""

# region: neurone
# Les 4 points (x1, x2), et la réponse attendue de chaque porte, dans le même ordre.
POINTS = [(0, 0), (0, 1), (1, 0), (1, 1)]
PORTES = {
    "et": [0, 0, 0, 1],  # 1 seulement si les deux entrées valent 1
    "ou": [0, 1, 1, 1],  # 1 si au moins une entrée vaut 1
    "ou_exclusif": [0, 1, 1, 0],  # 1 si une seule des deux entrées vaut 1
}
# Les valeurs essayées pour w1, w2 et b : de −2 à 2, par pas de 0,5.
GRILLE = [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0]


def sortie_seuil(poids: tuple[float, float], biais: float, x: tuple[int, int]) -> int:
    """La réponse du neurone : 1 si la somme pondérée dépasse 0, 0 sinon."""
    return 1 if poids[0] * x[0] + poids[1] * x[1] + biais > 0 else 0


def bien_classes(poids: tuple[float, float], biais: float, porte: str) -> int:
    """Le nombre de points, sur 4, où le neurone donne la réponse de la porte."""
    compte = 0
    for x, attendu in zip(POINTS, PORTES[porte]):
        if sortie_seuil(poids, biais, x) == attendu:
            compte += 1
    return compte


def meilleur_reglage(porte: str) -> tuple[int, tuple[float, float], float]:
    """Le meilleur compte de la grille, et le premier réglage (w1, w2), b qui l'atteint."""
    meilleur = (-1, (0.0, 0.0), 0.0)
    for w1 in GRILLE:
        for w2 in GRILLE:
            for b in GRILLE:
                compte = bien_classes((w1, w2), b, porte)
                if compte > meilleur[0]:  # strictement : on garde le premier réglage trouvé
                    meilleur = (compte, (w1, w2), b)
    return meilleur
# fin: neurone
