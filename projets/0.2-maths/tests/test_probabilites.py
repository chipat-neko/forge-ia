"""Des scores aux probabilités (softmax), et l'erreur d'une prédiction (−ln p)."""

import math

import pytest

from maths_utiles.probabilites import erreur_de_prediction, softmax


def test_softmax():
    assert softmax([0.0, 0.0]) == [0.5, 0.5]
    p = softmax([2.0, 1.0, 0.1])
    assert math.isclose(math.fsum(p), 1.0) and p[0] > p[1] > p[2]
    # Soustraire le plus grand score ne change rien au résultat, et évite qu'exp déborde.
    assert softmax([1000.0, 1000.0]) == [0.5, 0.5]
    assert math.isclose(softmax([1001.0, 1000.0])[0], 1 / (1 + math.exp(-1)))


def test_softmax_temperature():
    froide, tiede, chaude = (softmax([2.0, 1.0, 0.1], t) for t in (0.5, 1.0, 2.0))
    # Plus la température est basse, plus le plus grand score l'emporte.
    assert froide[0] > tiede[0] > chaude[0]
    assert softmax([2.0, 1.0, 0.1]) == tiede
    with pytest.raises(ValueError, match="température"):
        softmax([1.0, 2.0], 0.0)


def test_erreur_de_prediction():
    assert abs(erreur_de_prediction(1 / 40) - math.log(40)) < 1e-12
    assert erreur_de_prediction(1.0) == 0.0
    assert math.isclose(erreur_de_prediction(0.5), math.log(2))
    # Moins le modèle donne de chances à la bonne réponse, plus l'erreur est grande.
    assert erreur_de_prediction(0.1) > erreur_de_prediction(0.5) > erreur_de_prediction(1.0)
    for p in (0.0, -0.5, 1.5):
        with pytest.raises(ValueError, match="probabilité"):
            erreur_de_prediction(p)
