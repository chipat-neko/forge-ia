"""Les règles de forme de PyTorch, en Python pur : la diffusion et le produit matriciel.

Une forme est un tuple d'entiers : (2, 3) pour une matrice de 2 lignes et 3
colonnes, (4,) pour un vecteur de 4 nombres, () pour un nombre seul. Les deux
fonctions disent quelle forme aura le résultat, sans rien calculer, ou None
quand PyTorch refuserait l'opération. Les tests les comparent à PyTorch
lui-même (`torch.broadcast_shapes` et `torch.matmul`), et le site en a un
jumeau exact, site/src/lib/partie-0/formes.ts.

Ce fichier n'importe rien : les règles ne dépendent pas de PyTorch.
"""


# region: diffusion
def forme_diffusee(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, ...] | None:
    """La forme de a + b selon la règle de la diffusion, ou None si les formes ne vont pas ensemble."""
    a, b = tuple(a), tuple(b)
    # On aligne les deux formes par la droite : une dimension qui manque à gauche compte pour 1.
    n = max(len(a), len(b))
    a = (1,) * (n - len(a)) + a
    b = (1,) * (n - len(b)) + b
    resultat = []
    for x, y in zip(a, b):
        if x == y or y == 1:
            resultat.append(x)  # égales, ou b s'étire pour suivre a
        elif x == 1:
            resultat.append(y)  # a s'étire pour suivre b
        else:
            return None  # deux tailles différentes, et aucune ne vaut 1
    return tuple(resultat)
# fin: diffusion


# region: produit
def forme_produit(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, ...] | None:
    """La forme de a @ b (torch.matmul), ou None si les formes ne vont pas ensemble."""
    a, b = tuple(a), tuple(b)
    if len(a) == 0 or len(b) == 0:
        return None  # un nombre seul n'a pas de produit matriciel
    # Un vecteur à gauche devient une ligne (1, n) ; à droite, une colonne (n, 1).
    gauche = (1,) + a if len(a) == 1 else a
    droite = b + (1,) if len(b) == 1 else b
    # (…, n, m) @ (…, m, p) : la dernière dimension de gauche est l'avant-dernière de droite.
    if gauche[-1] != droite[-2]:
        return None
    # Les autres dimensions, celles du lot, se diffusent comme pour a + b.
    lot = forme_diffusee(gauche[:-2], droite[:-2])
    if lot is None:
        return None
    forme = lot + (gauche[-2], droite[-1])
    # On retire le 1 ajouté à un vecteur.
    if len(a) == 1:
        forme = forme[:-2] + forme[-1:]
    if len(b) == 1:
        forme = forme[:-1]
    return forme
# fin: produit
