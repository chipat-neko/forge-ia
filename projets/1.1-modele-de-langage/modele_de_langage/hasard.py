"""Le hasard reproductible du site, copié du projet 0.2.

La classe `Hasard` ci-dessous est une copie exacte de celle de
projets/0.2-maths/maths_utiles/tirage.py (elle-même reprise du mini-modèle) :
un test (tests/test_hasard.py) compare les deux textes caractère pour caractère.
Le site la refait en TypeScript (site/src/lib/mini-modele/calcul.ts) et trouve
la même suite : c'est ce qui permet de rejouer ici une génération de texte
et de retrouver les mêmes caractères dans la page.
"""

# region: hasard
# Le plus grand entier sûr de JavaScript, 2^53 − 1 (Number.MAX_SAFE_INTEGER).
ENTIER_SUR_MAX = 9007199254740991


class Hasard:
    """Le hasard reproductible : SplitMix32, copié du mini-modèle.

    Une même graine donne la même suite en Python et en TypeScript, sur toutes
    les machines. Seules trois méthodes sont reprises de
    projets/mini-modele/mini_modele/calcul.py, telles quelles : un test vérifie
    que la copie reste identique.
    """

    def __init__(self, graine: int) -> None:
        entier = isinstance(graine, int) or (isinstance(graine, float) and graine.is_integer())
        if isinstance(graine, bool) or not entier:
            raise TypeError(
                f"La graine du hasard doit être un entier (reçu {graine!r}). Donne un entier de 0 à 2^32 − 1."
            )
        if not -ENTIER_SUR_MAX <= graine <= ENTIER_SUR_MAX:
            raise ValueError(
                f"La graine du hasard dépasse les entiers sûrs de JavaScript (reçu {graine!r}). "
                "Donne un entier de 0 à 2^32 − 1."
            )
        self.etat = int(graine) & 0xFFFFFFFF

    def suivant32(self) -> int:
        """Le prochain entier sur 32 bits, de 0 à 2^32 − 1."""
        self.etat = (self.etat + 0x9E3779B9) & 0xFFFFFFFF
        z = self.etat
        z = ((z ^ (z >> 16)) * 0x21F0AAAD) & 0xFFFFFFFF
        z = ((z ^ (z >> 15)) * 0x735A2D97) & 0xFFFFFFFF
        return z ^ (z >> 15)

    def uniforme(self) -> float:
        """Un flottant de [0, 1[ : suivant32 divisé par 2^32 (une division exacte)."""
        return self.suivant32() / 4294967296.0
# fin: hasard
