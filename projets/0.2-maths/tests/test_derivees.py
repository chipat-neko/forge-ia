"""La pente : l'erreur selon un poids, sa pente exacte et approchée, la descente et la règle de la chaîne."""

from maths_utiles.derivees import (
    TAUX_DESCENTE,
    descendre,
    erreur,
    exemple_chaine,
    pas_pour_atteindre,
    pente,
    pente_approchee,
)


def test_erreur_et_pente():
    assert erreur(3.0) == 1.0 and erreur(0.0) == 10.0 and erreur(5.0) == 5.0
    assert pente(3.0) == 0.0 and pente(0.0) == -6.0 and pente(4.5) == 3.0


def test_pente_approchee():
    assert abs(pente_approchee(erreur, 0.0) - pente(0.0)) < 1e-6
    # Une différence centrée : (f(x + h) − f(x − h)) ÷ 2h, exacte sur une parabole, aux arrondis près.
    for x in (-2.0, 0.5, 3.0, 7.0):
        assert abs(pente_approchee(erreur, x) - pente(x)) < 1e-6
    assert pente_approchee(lambda x: 4.0 * x, 2.0, h=0.5) == 4.0


def test_descendre():
    assert descendre(0.0, 0.5, 1) == [0.0, 3.0]
    assert descendre(0.0, 0.1, 0) == [0.0]
    positions = descendre(0.0, 0.1, 30)
    assert len(positions) == 31 and positions[0] == 0.0
    # Au taux 0,1, chaque pas réduit la distance au fond (x = 3) : elle est multipliée par 0,8.
    distances = [abs(x - 3.0) for x in positions]
    assert all(d2 < d1 for d1, d2 in zip(distances, distances[1:]))
    # Au taux 1, la descente saute d'un bord à l'autre : 0, 6, 0, 6…
    assert descendre(0.0, 1.0, 4) == [0.0, 6.0, 0.0, 6.0, 0.0]


def test_pas_pour_atteindre():
    assert pas_pour_atteindre(0.0, 0.1, 1.01) == 16
    assert pas_pour_atteindre(0.0, 0.5, 1.01) == 1
    assert pas_pour_atteindre(0.0, 1.0, 1.01) is None  # oscille entre 0 et 6
    # Déjà au fond : zéro pas.
    assert pas_pour_atteindre(3.0, 0.1, 1.01) == 0
    # Au taux 1,2, la descente s'éloigne du fond à chaque pas.
    assert pas_pour_atteindre(0.0, 1.2, 1.01) is None
    # max_pas borne la recherche.
    assert pas_pour_atteindre(0.0, 0.1, 1.01, max_pas=15) is None
    assert pas_pour_atteindre(0.0, 0.1, 1.01, max_pas=16) == 16


def test_taux_de_la_figure():
    assert TAUX_DESCENTE == [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0, 1.05, 1.2]


def test_exemple_chaine():
    c = exemple_chaine()
    assert c["exacte"] == 12.0 and abs(c["approchee"] - 12.0) < 1e-5
    assert c["x"] == 1.0 and c["h"] == 9.0
    assert list(c) == ["x", "h", "exacte", "approchee"]
