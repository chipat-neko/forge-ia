"""Les vecteurs : produit scalaire, norme, cosinus, somme, et une matrice fois un vecteur."""

import math

import pytest

from maths_utiles.vecteurs import cosinus, matrice_fois_vecteur, norme, produit_scalaire, somme


def test_produit_scalaire():
    assert produit_scalaire([2, 1], [-1, 2]) == 0 and produit_scalaire([3, 1], [1, 2]) == 5
    assert produit_scalaire([], []) == 0.0
    # Une somme de produits, toujours un flottant : 0.0 au départ, puis + x × y.
    assert isinstance(produit_scalaire([1, 2], [3, 4]), float)
    assert produit_scalaire([0.5, -1.5], [2, 2]) == -2.0


def test_produit_scalaire_refuse_deux_tailles_differentes():
    # Un message en français, le même que le site (la section messages des attendus le vérifie),
    # au lieu de l'erreur anglaise de zip ou d'oublier la fin du plus long.
    with pytest.raises(ValueError) as erreur:
        produit_scalaire([1, 2, 3], [1, 2])
    assert str(erreur.value) == "Les deux vecteurs n’ont pas la même taille (3 et 2 nombres)\u202f: il en faut autant."
    with pytest.raises(ValueError, match="0 et 1 nombres"):
        produit_scalaire([], [4])


def test_norme_et_cosinus():
    assert norme([3, 4]) == 5.0 and cosinus([1, 0], [0, 0]) is None
    assert cosinus([0, 0], [1, 0]) is None and cosinus([0, 0], [0, 0]) is None
    assert norme([0, 0]) == 0.0
    assert cosinus([2, 1], [-1, 2]) == 0.0
    # √10 × √10 n'est pas tout à fait 10 en flottant : le cosinus de deux vecteurs
    # opposés vaut -0,9999999999999998, pas -1. Le site trouve le même nombre.
    assert cosinus([3, 1], [-3, -1]) == -0.9999999999999998
    assert math.isclose(cosinus([3, 1], [-3, -1]), -1.0)
    assert math.isclose(cosinus([3, 1], [1, 2]), 1 / math.sqrt(2))
    # Le même calcul que le site : produit scalaire ÷ (norme de a × norme de b), dans cet ordre.
    assert cosinus([3, 1], [1, 2]) == 5.0 / (math.sqrt(10.0) * math.sqrt(5.0))


def test_somme():
    assert somme([3, 1], [1, 2]) == [4, 3]
    assert somme([], []) == []
    with pytest.raises(ValueError) as erreur:
        somme([1], [1, 2])
    assert str(erreur.value) == "Les deux vecteurs n’ont pas la même taille (1 et 2 nombres)\u202f: il en faut autant."


def test_matrice_fois_vecteur():
    assert matrice_fois_vecteur([[1, 2, 3], [0, 1, 0]], [1, 1, 1]) == [6, 1]
    assert matrice_fois_vecteur([[0, -1], [1, 0]], [3, 1]) == [-1, 3]
    assert matrice_fois_vecteur([], [1, 2]) == []


def test_matrice_fois_vecteur_tailles_qui_ne_vont_pas():
    with pytest.raises(ValueError, match="autant"):
        matrice_fois_vecteur([[1, 2, 3, 4]], [1, 2, 3])
    with pytest.raises(ValueError) as erreur:
        matrice_fois_vecteur([[1, 2, 3, 4]], [1, 2, 3])
    assert str(erreur.value) == "La matrice a 4 colonnes et le vecteur 3 nombres\u202f: il en faut autant."
    # Au singulier quand il n'y en a qu'un.
    with pytest.raises(ValueError) as erreur:
        matrice_fois_vecteur([[1], [2]], [1, 2])
    assert str(erreur.value) == "La matrice a 1 colonne et le vecteur 2 nombres\u202f: il en faut autant."
