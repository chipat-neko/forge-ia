"""Le mélange des sources et la mise à part des documents de validation.

`MELANGE_PAR_DEFAUT` est la seule définition des parts de chaque source : le
téléchargement et l'apprentissage du tokenizer la lisent ici (l'encodage la lira aussi).
"""

import math

# Part de chaque source : 75 % de web français, 10 % de Wikipédia française, 15 % de code
# Python sous licence permissive. L'ordre est celui de lecture et d'affichage.
MELANGE_PAR_DEFAUT: dict[str, float] = {"web_fr": 0.75, "wikipedia_fr": 0.10, "code_python": 0.15}


def repartir(octets_total: int, melange: dict[str, float] = MELANGE_PAR_DEFAUT) -> dict[str, int]:
    """Partage `octets_total` entre les sources, selon les parts de `melange`.

    La somme des parts rendues vaut exactement `octets_total` : chaque part est arrondie
    vers le bas, puis les octets qui restent vont aux sources dont la part avait la plus
    grosse partie décimale.
    """
    if octets_total < 0:
        raise ValueError(f"Le volume à répartir ne peut pas être négatif : {octets_total}.")
    if any(part < 0 for part in melange.values()):
        raise ValueError(f"Une part du mélange est négative : {melange}. Les parts doivent être positives.")
    if not math.isclose(sum(melange.values()), 1.0, abs_tol=1e-9):
        raise ValueError(f"Les parts du mélange doivent faire 1 en tout, elles font {sum(melange.values())}.")
    exactes = {nom: octets_total * part for nom, part in melange.items()}
    parts = {nom: math.floor(valeur) for nom, valeur in exactes.items()}
    reste = octets_total - sum(parts.values())
    # Les octets restants vont, un par un, aux plus grosses parties décimales.
    for nom in sorted(exactes, key=lambda n: exactes[n] - parts[n], reverse=True)[:reste]:
        parts[nom] += 1
    return parts


def est_validation(empreinte: str, part: float = 0.005) -> bool:
    """Dit si un document, d'après son empreinte, va dans la validation (0,5 % par défaut).

    On lit les 8 premiers chiffres hexadécimaux de l'empreinte comme un entier, entre 0 et
    2³² − 1, et on le compare à `part` × 2³². Le choix ne dépend que du texte : le même
    document tombe toujours du même côté, quel que soit l'ordre ou le moment du calcul.
    """
    return int(empreinte[:8], 16) < part * 2**32
