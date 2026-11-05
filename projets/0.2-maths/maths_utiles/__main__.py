"""Un exemple de chaque idée du chapitre 0.2, en ligne de commande.

Exemple (dans projets/0.2-maths) :

    uv run python -m maths_utiles --taux 0.1 --pas 10 --tirages 1000

Le programme affiche le produit scalaire et le cosinus de (3, 1) et (1, 2),
une matrice fois un vecteur, les pas d'une descente de la pente au taux
demandé, puis des tirages au sort parmi les mots qui suivent « le ».
"""

import argparse
import math
import sys
from typing import NoReturn

from maths_utiles.derivees import descendre, erreur, pas_pour_atteindre, pente
from maths_utiles.tirage import ENTIER_SUR_MAX, EXEMPLE_COMPTES, GRAINE_TIRAGE, probabilites, tirages
from maths_utiles.vecteurs import cosinus, matrice_fois_vecteur, produit_scalaire

FINE = "\u202f"  # l'espace fine insécable de la typographie française
# Au-delà de cette distance au fond (x = 3), la descente a explosé : on s'arrête.
DISTANCE_MAX = 1000.0
# Le seuil d'erreur de la figure : l'erreur la plus basse vaut 1.
SEUIL = 1.01


def nombre(x: float, decimales: int | None = None) -> str:
    """x à la française, avec une espace fine entre les milliers et une virgule.

    nombre(1234.5, 2) donne « 1 234,50 ». Sans nombre de décimales, juste ce qu'il
    faut, 6 au plus : nombre(0.1) donne « 0,1 », et nombre(5.0) donne « 5 ».
    """
    texte = f"{x:,.{6 if decimales is None else decimales}f}"  # « 1,234.50 », à l'anglaise
    if decimales is None:
        texte = texte.rstrip("0").rstrip(".")
    texte = texte.replace(",", FINE).replace(".", ",")
    # Un nombre arrondi à zéro ne garde pas de signe : « 0,000 », jamais « -0,000 ».
    if texte.startswith("-") and texte.strip("-0,") == "":
        texte = texte[1:]
    return texte


def arreter(message: str) -> NoReturn:
    """Affiche le message sur la sortie d'erreur et arrête le programme (code 1)."""
    print(message, file=sys.stderr)
    raise SystemExit(1)


def montrer_vecteurs() -> None:
    a, b = [3, 1], [1, 2]
    print(f"Deux vecteurs{FINE}: a = (3, 1) et b = (1, 2).")
    print(f"  a · b = 3 × 1 + 1 × 2 = {nombre(produit_scalaire(a, b))}")
    print(f"  cosinus de l’angle entre a et b{FINE}: {nombre(cosinus(a, b), 3)}")
    m, v = [[1, 2, 3], [0, 1, 0]], [1, 1, 1]
    resultat = ", ".join(nombre(x) for x in matrice_fois_vecteur(m, v))
    print(f"Une matrice fois un vecteur{FINE}: [[1, 2, 3], [0, 1, 0]] × [1, 1, 1] = [{resultat}]")


def montrer_descente(taux: float, nb_pas: int) -> None:
    print(f"La descente de l’erreur (x − 3)² + 1, depuis x = 0, au taux {nombre(taux)}{FINE}:")
    for n, x in enumerate(descendre(0.0, taux, nb_pas)):
        if abs(x - 3.0) > DISTANCE_MAX:
            print(f"  x est parti à plus de {nombre(DISTANCE_MAX)} du fond{FINE}: ce taux fait exploser la descente.")
            return
        print(f"  pas {n}{FINE}: x = {nombre(x, 3)}, erreur = {nombre(erreur(x), 3)}, pente = {nombre(pente(x), 3)}")
    n = pas_pour_atteindre(0.0, taux, SEUIL)
    if n is None:
        print(f"  En 100 pas, l’erreur ne passe jamais sous {nombre(SEUIL)}.")
    else:
        print(f"  L’erreur passe sous {nombre(SEUIL)} au pas {n}.")


def montrer_tirages(n: int, graine: int) -> None:
    probas = probabilites(EXEMPLE_COMPTES)
    comptes = tirages(probas, n, graine)
    print(f"{nombre(n)} tirages au sort après «{FINE}le{FINE}» (graine {nombre(graine)}){FINE}:")
    largeur = max(len(mot) for mot in EXEMPLE_COMPTES)
    for mot, p, c in zip(EXEMPLE_COMPTES, probas, comptes):
        print(f"  {mot:<{largeur}}  {nombre(100 * p)}{FINE}% attendu, {nombre(c)} tirés ({nombre(100 * c / n, 1)}{FINE}%)")


def principal(arguments: list[str] | None = None) -> None:
    lecteur = argparse.ArgumentParser(
        prog="python -m maths_utiles",
        description="Montre les maths utiles du chapitre 0.2 : vecteurs, matrice, descente et tirages.",
    )
    lecteur.add_argument("--taux", type=float, default=0.1, help="le taux de la descente (0.1 par défaut)")
    lecteur.add_argument("--pas", type=int, default=10, help="le nombre de pas de la descente (10 par défaut)")
    lecteur.add_argument("--tirages", type=int, default=1000, help="le nombre de tirages au sort (1000 par défaut)")
    lecteur.add_argument("--graine", type=int, default=GRAINE_TIRAGE, help=f"la graine du hasard ({GRAINE_TIRAGE} par défaut)")
    options = lecteur.parse_args(arguments)
    # La console Windows n'est pas toujours en UTF-8 : sans cela, « · » ou l'espace fine
    # feraient planter l'affichage, celui des messages d'erreur compris.
    for flux in (sys.stdout, sys.stderr):
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8")
    if not (math.isfinite(options.taux) and options.taux > 0):
        arreter(f"Le taux doit être un nombre positif (reçu {options.taux}){FINE}: relance avec --taux 0.1, par exemple.")
    if not 0 <= options.pas <= 1000:
        arreter(f"Le nombre de pas va de 0 à {nombre(1000)} (reçu {options.pas}){FINE}: relance avec --pas 10, par exemple.")
    if not 1 <= options.tirages <= 1_000_000:
        arreter(
            f"Le nombre de tirages va de 1 à {nombre(1_000_000)} (reçu {options.tirages}){FINE}: "
            "relance avec --tirages 1000, par exemple."
        )
    if not 0 <= options.graine <= ENTIER_SUR_MAX:
        arreter(f"La graine va de 0 à {nombre(ENTIER_SUR_MAX)} (reçu {options.graine}){FINE}: relance avec --graine 1234, par exemple.")

    montrer_vecteurs()
    print()
    montrer_descente(options.taux, options.pas)
    print()
    montrer_tirages(options.tirages, options.graine)


if __name__ == "__main__":
    principal()
