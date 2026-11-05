"""Les exemples du chapitre 0.4 : créer un tenseur, le lire, calculer avec.

Chaque fonction rend ce qu'elle a fabriqué, pour que les tests vérifient les
valeurs que le chapitre commente. Tout se passe sur le processeur : ces
tenseurs sont minuscules.
"""

import torch


# region: creer
def exemple_creer() -> dict[str, torch.Tensor]:
    """Des tenseurs de 0 à 3 dimensions."""
    nombre = torch.tensor(3.5)  # un nombre seul : forme ()
    vecteur = torch.tensor([1.0, 2.0, 3.0, 4.0])  # une liste de nombres : forme (4,)
    matrice = torch.arange(6.0).reshape(2, 3)  # 0 à 5, rangés en 2 lignes de 3 : forme (2, 3)
    lot = torch.zeros(2, 3, 4)  # deux matrices de 3 × 4 zéros : forme (2, 3, 4)
    entiers = torch.tensor([1, 2, 3])  # sans virgule, ce sont des entiers : type int64
    return {"nombre": nombre, "vecteur": vecteur, "matrice": matrice, "lot": lot, "entiers": entiers}
# fin: creer


# region: lire
def exemple_lire() -> dict:
    """Ce qu'on lit d'un tenseur : sa forme, son type, son appareil, et ses nombres."""
    m = torch.arange(6.0).reshape(2, 3)  # [[0, 1, 2], [3, 4, 5]]
    return {
        "forme": tuple(m.shape),  # (2, 3) : 2 lignes, 3 colonnes
        "dimensions": m.dim(),  # 2
        "nombres": m.numel(),  # 2 × 3 = 6
        "type": str(m.dtype),  # torch.float32 : des nombres à virgule de 32 bits
        "appareil": str(m.device),  # cpu : le processeur
        "case": m[1, 2].item(),  # ligne 1, colonne 2 (on compte depuis 0) : 5.0
        "ligne": m[1].tolist(),  # toute la ligne 1
        "colonne": m[:, 0].tolist(),  # toute la colonne 0
    }
# fin: lire


# region: calculer
def exemple_calculer() -> dict:
    """Calculer avec deux matrices 2 × 2 : case par case, ou en produit matriciel."""
    a = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
    b = torch.tensor([[10.0, 20.0], [30.0, 40.0]])
    return {
        "somme": (a + b).tolist(),  # case par case
        "produit_case_par_case": (a * b).tolist(),
        "produit_matriciel": (a @ b).tolist(),  # chaque ligne de a avec chaque colonne de b
        "total": a.sum().item(),  # la somme de tous les nombres
        "moyenne_par_colonne": a.mean(dim=0).tolist(),  # dim=0 : on fait la moyenne en descendant
        "diffusion": (a + torch.tensor([100.0, 200.0])).tolist(),  # (2, 2) + (2,) : le vecteur sur chaque ligne
    }
# fin: calculer
