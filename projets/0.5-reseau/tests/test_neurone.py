"""Le neurone à seuil : il imite ET et OU, et pas le OU exclusif."""

import itertools

from premier_reseau.neurone import GRILLE, POINTS, PORTES, bien_classes, meilleur_reglage, sortie_seuil


def test_meilleurs_reglages():
    assert meilleur_reglage("et")[0] == 4 and meilleur_reglage("ou")[0] == 4
    assert meilleur_reglage("ou_exclusif")[0] == 3


def test_sortie_seuil():
    assert sortie_seuil((1.0, 1.0), -1.5, (1, 1)) == 1 and sortie_seuil((1.0, 1.0), -1.5, (1, 0)) == 0
    # Une somme nulle ne dépasse pas 0 : le neurone répond 0.
    assert sortie_seuil((1.0, 1.0), -1.0, (1, 0)) == 0


def test_les_points_les_portes_et_la_grille():
    assert POINTS == [(0, 0), (0, 1), (1, 0), (1, 1)]
    assert PORTES == {"et": [0, 0, 0, 1], "ou": [0, 1, 1, 1], "ou_exclusif": [0, 1, 1, 0]}
    # De −2 à 2, par pas de 0,5 : 9 valeurs, toutes exactes en binaire.
    assert len(GRILLE) == 9 and GRILLE[0] == -2.0 and GRILLE[-1] == 2.0
    assert all(b - a == 0.5 for a, b in zip(GRILLE, GRILLE[1:]))


def test_l_exemple_de_la_porte_et():
    # Le réglage de départ de l'atelier du chapitre : w = (1, 1) et b = 0 classent 2 points sur 4,
    # puis b = −1,5 les classe tous.
    assert bien_classes((1.0, 1.0), 0.0, "et") == 2
    assert bien_classes((1.0, 1.0), -1.5, "et") == 4


def test_poids_nuls():
    # Tous les réglages à 0 : la somme vaut 0 partout, le neurone répond toujours 0.
    assert [sortie_seuil((0.0, 0.0), 0.0, x) for x in POINTS] == [0, 0, 0, 0]
    assert bien_classes((0.0, 0.0), 0.0, "et") == 3 and bien_classes((0.0, 0.0), 0.0, "ou_exclusif") == 2


def test_le_premier_meilleur_reglage_de_la_grille():
    # meilleur_reglage parcourt w1, puis w2, puis b, dans l'ordre de la grille, et garde le
    # premier réglage qui atteint le meilleur compte.
    reglages = [((w1, w2), b) for w1 in GRILLE for w2 in GRILLE for b in GRILLE]
    assert len(reglages) == 729
    for porte in PORTES:
        comptes = [bien_classes(poids, b, porte) for poids, b in reglages]
        compte, poids, biais = meilleur_reglage(porte)
        assert compte == max(comptes)
        assert (poids, biais) == reglages[comptes.index(compte)]
        assert bien_classes(poids, biais, porte) == compte


def test_le_ou_exclusif_est_impossible_meme_sur_une_grille_plus_fine():
    # Ce n'est pas la grille qui manque de finesse : il faudrait b ≤ 0, w2 + b > 0, w1 + b > 0
    # et w1 + w2 + b ≤ 0. Les deux du milieu donnent w1 + w2 + 2b > 0, donc w1 + w2 + b > −b ≥ 0.
    fine = [k / 4 for k in range(-20, 21)]  # de −5 à 5, par pas de 0,25
    meilleur = max(bien_classes((w1, w2), b, "ou_exclusif") for w1, w2, b in itertools.product(fine, repeat=3))
    assert meilleur == 3
