"""Tirer au sort, selon des probabilités.

Pour deviner la suite d'un texte sans tourner en rond, une IA ne prend pas
toujours le mot le plus probable : elle tire au sort, selon les probabilités.
Ici, les mots qui suivent « le » dans un petit texte, avec leurs comptes,
deviennent des probabilités, puis des tirages.

Le hasard d'un ordinateur est un calcul : une graine, puis une suite de nombres
qui en découle. Le même calcul donne la même suite partout, en Python comme dans
le navigateur : le site refait ces tirages en TypeScript
(site/src/lib/partie-0/maths.ts), avec le Hasard du mini-modèle, et trouve les
mêmes comptes.
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


# Ce qui suit « le » dans un petit texte, avec le nombre de fois.
EXEMPLE_COMPTES = {"fer": 6, "métal": 3, "feu": 1}
# La graine de départ de la figure des tirages et du pari.
GRAINE_TIRAGE = 1234


def probabilites(comptes: dict[str, int]) -> list[float]:
    """Chaque compte divisé par le total : {fer: 6, métal: 3, feu: 1} donne [0.6, 0.3, 0.1]."""
    total = sum(comptes.values())  # des entiers : la somme est exacte
    return [c / total for c in comptes.values()]


# region: tirer
def tirer(probas: list[float], u: float) -> int:
    """L'issue tirée par u, un nombre de [0, 1[.

    Les probabilités sont posées bout à bout de 0 à 1 :
    u tombe dans l'une d'elles. Avec [0.6, 0.3, 0.1],
    u = 0.75 tombe dans la deuxième, l'issue 1.
    """
    cumul = 0.0
    for i, p in enumerate(probas):
        cumul += p
        if u < cumul:
            return i
    # Les arrondis peuvent laisser le cumul un peu sous 1 :
    # un u au-delà prend la dernière issue.
    return len(probas) - 1


def tirages(
    probas: list[float],
    n: int,
    graine: int,
) -> list[int]:
    """n tirages au sort : combien de fois chaque issue
    est sortie."""
    hasard = Hasard(graine)
    comptes = [0] * len(probas)
    for _ in range(n):
        comptes[tirer(probas, hasard.uniforme())] += 1
    return comptes
# fin: tirer
