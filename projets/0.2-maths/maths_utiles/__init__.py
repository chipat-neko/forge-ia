"""Les maths utiles du chapitre 0.2 : vecteurs, pente, descente, tirages et probabilités."""

from maths_utiles.derivees import (
    TAUX_DESCENTE,
    descendre,
    erreur,
    exemple_chaine,
    pas_pour_atteindre,
    pente,
    pente_approchee,
)
from maths_utiles.probabilites import erreur_de_prediction, softmax
from maths_utiles.tirage import EXEMPLE_COMPTES, GRAINE_TIRAGE, Hasard, probabilites, tirages, tirer
from maths_utiles.vecteurs import cosinus, matrice_fois_vecteur, norme, produit_scalaire, somme

__all__ = [
    "EXEMPLE_COMPTES",
    "GRAINE_TIRAGE",
    "Hasard",
    "TAUX_DESCENTE",
    "cosinus",
    "descendre",
    "erreur",
    "erreur_de_prediction",
    "exemple_chaine",
    "matrice_fois_vecteur",
    "norme",
    "pas_pour_atteindre",
    "pente",
    "pente_approchee",
    "probabilites",
    "produit_scalaire",
    "softmax",
    "somme",
    "tirages",
    "tirer",
]
