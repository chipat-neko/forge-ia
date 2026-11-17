r"""La langue d'un texte : une règle simple, fondée sur des mots outils.

Pas de bibliothèque de détection : la règle tient en quelques lignes, déterministe, et le site la refait
à l'identique en TypeScript (plan 8). Elle ne dit pas quelle langue est écrite, seulement si le texte est
du français, en comptant les mots outils de deux listes écrites plus bas :

1. `mots` découpe le texte en suites de lettres (toute catégorie Unicode qui commence par « L »), en
   minuscules ; tout le reste (chiffres, ponctuation, apostrophes droite et courbe, espaces) coupe ;
2. `f` compte les mots de la liste française, `a` ceux de la liste anglaise ;
3. `langue` rend « indetermine » s'il y a moins de 3 mots outils en tout (texte vide, chiffres, code, mot
   seul), « fr » si `f >= 2 * a`, sinon « autre ».

Ni `\w` ni `\b` : Python et JavaScript ne s'y accordent pas (Unicode contre ASCII). Les tests de
caractères sont explicites, pour que le plan 8 les traduise un à un.
"""

import unicodedata
from typing import Literal

# Les deux listes n'ont aucun mot commun (un test le vérifie) : les mots qui existent dans les deux langues
# (« a », « on », « as », « me », « or », « son », « but », « an », « plus », « par »...) en sont absents.
# Les lettres seules nées d'une apostrophe (« l », « d », « s », « t »...) n'y sont pas non plus.
MOTS_FRANCAIS = frozenset(
    """
    le la les un une des du de et est en que qui dans pour pas sur au aux avec il elle ils elles nous vous
    je tu ce cette ces ses sa mais ou où se ne ni y à été sont ont était être avoir fait puis dont comme
    très aussi tout tous leur leurs lui cela ça mon ton notre votre mes tes cet quand sans sous entre
    chez vers donc car si
    """.split()
)

MOTS_ANGLAIS = frozenset(
    """
    the and of to is are was were be been in it that this with for his her they their have has had not at
    by from which you your we he she there would will can if then than when what who how do does did so
    its also just about into my our them these those been being
    """.split()
)


def mots(texte: str) -> list[str]:
    """Les suites de lettres du texte, en minuscules (`str.lower()`) ; le reste coupe, apostrophes comprises."""
    resultat: list[str] = []
    courant: list[str] = []
    for c in texte:
        if unicodedata.category(c)[0] == "L":
            courant.append(c)
        elif courant:
            resultat.append("".join(courant).lower())
            courant = []
    if courant:
        resultat.append("".join(courant).lower())
    return resultat


def langue(texte: str) -> Literal["fr", "autre", "indetermine"]:
    """« fr » si le texte est français, « autre » sinon, « indetermine » s'il a moins de 3 mots outils."""
    f = 0
    a = 0
    for mot in mots(texte):
        if mot in MOTS_FRANCAIS:
            f += 1
        elif mot in MOTS_ANGLAIS:
            a += 1
    if f + a < 3:
        return "indetermine"
    if f >= 2 * a:
        return "fr"
    return "autre"
