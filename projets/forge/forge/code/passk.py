"""pass@k : la chance qu'au moins une de k réponses tirées passe les tests, estimée sans biais."""


def pass_a_k(n: int, c: int, k: int) -> float:
    """L'estimateur sans biais de pass@k, pour un problème : `n` réponses tirées, dont `c` justes.

    C'est celui de l'article Codex (Chen et al., « Evaluating Large Language Models Trained on Code »,
    arXiv 2107.03374), section 2.1 « Functional Correctness » : on tire n ≥ k réponses par problème, on compte
    les c qui passent les tests, et

        pass@k = 1 − C(n − c, k) / C(n, k)

    (la moyenne sur les problèmes donne le score). C(n − c, k) / C(n, k) est la chance que k réponses prises
    parmi les n soient toutes fausses. Calculer ces coefficients binomiaux tels quels donne de très grands nombres
    (C(200, 100) dépasse 10^58) : on prend la forme stable de la figure 3 de l'article,

        1 − Π_{i = n − c + 1}^{n} (1 − k / i)

    calculée en boucle, dans cet ordre, et 1 dès que n − c < k (il y a moins de k réponses fausses : tout tirage
    de k en contient une juste).

    `ValueError` si `k` sort de [1, n] ou si `c` sort de [0, n].
    """
    if not 0 <= c <= n:
        raise ValueError(
            f"c = {c} sort de [0, n = {n}] : c compte les réponses justes parmi les n tirées. "
            "Vérifie le comptage des réponses qui passent les tests."
        )
    if not 1 <= k <= n:
        raise ValueError(
            f"k = {k} sort de [1, n = {n}] : pass@k demande au moins k réponses tirées par problème. "
            "Tire plus de réponses, ou prends un k plus petit."
        )
    if n - c < k:
        return 1.0
    produit = 1.0
    for i in range(n - c + 1, n + 1):
        produit *= 1.0 - k / i
    return 1.0 - produit
