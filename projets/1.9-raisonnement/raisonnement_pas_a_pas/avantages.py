"""L'avantage d'une réponse dans son groupe, et la chance qu'un groupe n'apprenne rien.

Le GRPO (chapitre 1.9) fait écrire plusieurs réponses à chaque problème : un **groupe**. Chaque réponse reçoit une
récompense, 1 si elle est juste et 0 sinon. Son **avantage** est sa récompense moins la moyenne de son groupe : positif
pour une réponse meilleure que ses sœurs, négatif pour une pire, nul pour toutes si elles ont la même récompense. Un
groupe aux avantages nuls n'apprend rien : la perte du GRPO est une somme d'avantages fois des log-probabilités.

`avantages_a_la_main` refait `forge.raisonnement.grpo.avantages` en nombres Python (un test les compare à 10⁻¹² près,
sur des tenseurs en float64). `sans_signal(p, n)` est la chance qu'un groupe de `n` réponses soit sans signal quand
chacune est juste avec la chance `p` : toutes justes, `pⁿ`, ou toutes fausses, `(1 − p)ⁿ`.

Le site refait ces deux fonctions à l'identique en TypeScript (`site/src/lib/partie-1/avantages.ts`) : la moyenne et
les puissances se calculent par des boucles, dans le même ordre, pour que les deux langages tombent sur les mêmes
flottants.
"""


# region: avantages
def avantages_a_la_main(recompenses: list[list[float]]) -> list[list[float]]:
    """Pour chaque groupe (une liste de récompenses), la récompense de chaque réponse moins la moyenne du groupe.

    La moyenne est la somme des récompenses (une boucle, de gauche à droite) divisée par leur nombre : sans division
    par l'écart-type, comme dans `forge.raisonnement.grpo.avantages`. Un groupe vide est refusé.
    """
    resultat = []
    for groupe in recompenses:
        if len(groupe) == 0:
            raise ValueError("Un groupe sans aucune réponse n'a pas de moyenne : donne au moins une récompense par groupe.")
        somme = 0.0
        for r in groupe:
            somme += r
        moyenne = somme / len(groupe)
        resultat.append([r - moyenne for r in groupe])
    return resultat


def sans_signal(p: float, n: int) -> float:
    """La chance qu'un groupe de `n` réponses soit sans signal : pⁿ + (1 − p)ⁿ, p étant la chance d'une réponse juste.

    Les deux puissances sont deux produits en boucle (`n` multiplications chacun), pas `**` : le site fait les mêmes
    multiplications, dans le même ordre. `p` est entre 0 et 1, `n` est un entier d'au moins 1.
    """
    if not 0 <= p <= 1:
        raise ValueError(f"p vaut {p!r} : c'est une chance, elle est entre 0 et 1.")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError(f"n vaut {n!r} : un groupe a au moins une réponse (un nombre entier).")
    q = 1 - p
    toutes_justes = 1.0
    toutes_fausses = 1.0
    for _ in range(n):
        toutes_justes *= p
        toutes_fausses *= q
    return toutes_justes + toutes_fausses
# fin: avantages
