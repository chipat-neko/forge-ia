r"""Lire la réponse d'une sortie de ton IA et la comparer à la bonne réponse.

Deux fonctions, que le site refait à l'identique en TypeScript (plan 8) :

- `extraire_nombre(texte)` rend le **dernier** nombre du texte, en `Fraction` (exacte, sans flottant), ou
  `None` s'il n'y en a aucun ;
- `est_juste(reponse, attendu)` dit si le nombre extrait du **texte** de la réponse est `attendu`, à condition
  que la réponse soit terminée (`reponse.terminee`) : une sortie coupée n'est jamais juste.

Ce qui compte est le texte, jamais la pensée : ton IA écrit sa pensée entre `<|pensee|>` et
`<|fin_pensee|>`, un brouillon où elle peut se tromper, se reprendre ou citer plusieurs nombres. Seule
la réponse qu'elle donne après compte. Un nombre juste resté dans la pensée ne rend donc pas une réponse
juste, et un nombre faux dans la pensée n'en rend pas une fausse.

Les écritures françaises d'un nombre, que `extraire_nombre` lit :

- les milliers séparés par une espace ordinaire, une espace insécable (U+00A0) ou une espace fine
  insécable (U+202F) : « 1 234 567 ». Le séparateur ne compte que suivi d'exactement 3 chiffres et
  d'aucun autre : « 12 345 » vaut 12345, mais « 12 3456 » est « 12 » puis « 3456 », et « 1 2 3 » est trois nombres ;
- la virgule décimale : « 12,5 » vaut 25/2 (une virgule suivie d'une espace ou d'une lettre ne compte pas :
  « 3, puis 4 » donne 3 et 4). Un point entre deux chiffres compte aussi comme virgule décimale : « 3.5 »
  vaut 7/2 (jamais comme séparateur de milliers : « 1.234 » vaut 1,234) ;
- le signe moins, « - » (U+002D) ou « − » (U+2212), à condition qu'une lettre ou un chiffre ne le
  précède pas : « −3 » et « x = -4 » sont négatifs, mais « 5-3 » est 5 puis 3 (la soustraction n'est pas un signe).

Seuls les chiffres ASCII 0 à 9 sont lus (`[0-9]`, jamais `\d`, qui lit en Python tous les chiffres Unicode) : le site
lit la même chose.

Les cas ambigus ont une réponse fixe : plusieurs nombres, « 3 puis 7 » donne 7 (le dernier) ; aucun
nombre, « rien » donne `None`. Comme il n'existe pas de lettres dans la règle, « trois » n'est pas un nombre.
"""

import re
from fractions import Fraction

from forge.conversation.format import Reponse

# Les séparateurs de milliers : espace, espace insécable, espace fine insécable.
_SEPARATEURS = " \u00a0\u202f"
_MOINS = "-−"

# Un nombre : un signe facultatif (jamais collé à un chiffre ou une lettre qui le précède), des chiffres (par
# groupes de trois séparés par une espace, ou d'une traite), une partie décimale facultative après « , » ou « . ».
# Le « (?![0-9]) » de la fin d'un groupe empêche « 12 3456 » de se lire « 12 345 » suivi de « 6 ».
_NOMBRE = re.compile(
    rf"(?<![0-9])(?P<signe>(?<![^\W_])[{_MOINS}])?"
    rf"(?P<entier>[0-9]{{1,3}}(?:[{_SEPARATEURS}][0-9]{{3}})+(?![0-9])|[0-9]+)"
    r"(?:[,.](?P<decimales>[0-9]+))?"
)


def extraire_nombre(texte: str) -> Fraction | None:
    """Le dernier nombre du texte, ou `None` s'il n'y en a pas.

    Voir le haut du module pour les écritures lues : milliers séparés par une espace, une espace
    insécable ou une espace fine, virgule décimale, signe moins `-` ou `−`.
    """
    dernier = None
    for lu in _NOMBRE.finditer(texte):
        dernier = lu
    if dernier is None:
        return None
    chiffres = re.sub(rf"[{_SEPARATEURS}]", "", dernier["entier"])
    valeur = Fraction(int(chiffres))
    decimales = dernier["decimales"]
    if decimales is not None:
        valeur += Fraction(int(decimales), 10 ** len(decimales))
    return -valeur if dernier["signe"] else valeur


def est_juste(reponse: Reponse, attendu: int | str) -> bool:
    """Vrai si la réponse est terminée et si le nombre extrait de son **texte** (après la pensée) égale `attendu`.

    `attendu` est un entier, ou une chaîne lue comme `extraire_nombre` (« 1 234 », « −3 »). La pensée
    est ignorée, même quand elle contient la bonne réponse ou une réponse qui contredit le texte. Une
    réponse coupée (`terminee` faux : la limite de jetons est atteinte, rien ne dit que le dernier nombre est
    complet, « 12 » peut venir de « 123 »), une réponse sans nombre, ou un `attendu` chaîne qui n'est pas un
    nombre, ne sont jamais justes. Un `attendu` d'un autre type (flottant, booléen…) lève `TypeError`.
    """
    if isinstance(attendu, bool) or not isinstance(attendu, (int, str)):
        raise TypeError(
            f"L'attendu doit être un entier ou une chaîne (reçu {attendu!r} de type {type(attendu).__name__}). "
            "Un flottant se compare mal (0,1 n'est pas exact) : écris l'attendu en entier, ou en chaîne comme « 12,5 »."
        )
    if not reponse.terminee:
        return False
    lu = extraire_nombre(reponse.texte)
    if lu is None:
        return False
    voulu = extraire_nombre(attendu) if isinstance(attendu, str) else Fraction(attendu)
    return voulu is not None and lu == voulu
