"""Compter les paramètres d'un transformer de forge, famille par famille."""

from forge.modele.config import ConfigModele, largeur_cachee


def repartition(config: ConfigModele) -> dict[str, int]:
    """Les paramètres par famille : `plongement`, `attention`, `mlp` et `normes`.

    La somme vaut `forge.modele.config.nombre_parametres(config)`. Le plongement d'entrée et la
    matrice de sortie sont la même : elle n'est comptée qu'une fois. RoPE n'a aucun paramètre.
    """
    dim = config.dim
    return {
        "plongement": config.taille_vocabulaire * dim,
        "attention": config.couches * 4 * dim * dim,  # q, k, v et la sortie
        "mlp": config.couches * 3 * dim * largeur_cachee(dim),  # porte, haute, basse
        "normes": config.couches * 2 * dim + dim,  # deux par bloc, plus la finale
    }
