"""Le noyau de calcul : valeurs exactes, précision, hasard, sommes, motifs et empreintes.

La parité avec le TypeScript est vérifiée par les attendus partagés
(tests/attendus-calcul.json, voir test_attendus.py et calcul.test.ts). Ici, on
vérifie que les calculs sont justes : la libm n'est qu'un témoin de précision.
"""

import math

import pytest

from mini_modele.calcul import (
    INV_LN2,
    LN2_BAS,
    LN2_HAUT,
    PI,
    SQRT_DEMI,
    Hasard,
    cos,
    depuis_hex,
    deux_puissance,
    empreinte,
    empreinte_texte,
    exp,
    log,
    maximum,
    produit_scalaire,
    racine,
    somme,
    vers_hex,
)


def test_constantes():
    assert vers_hex(LN2_HAUT) == "3fe62e42fee00000"
    assert vers_hex(LN2_BAS) == "3dea39ef35793c76"
    assert vers_hex(INV_LN2) == "3ff71547652b82fe"
    assert vers_hex(SQRT_DEMI) == "3fe6a09e667f3bcd"
    assert vers_hex(PI) == "400921fb54442d18"


def test_valeurs_exactes():
    assert exp(0.0) == 1.0 and log(1.0) == 0.0 and cos(0.0) == 1.0 and cos(PI) == -1.0
    assert exp(-746.0) == 0.0 and exp(710.0) == math.inf and log(0.0) == -math.inf
    assert math.isnan(log(-1.0)) and math.isnan(exp(math.nan))
    with pytest.raises(ValueError, match="de 0 à π"):
        cos(4.0)


def test_cas_limites():
    assert exp(-0.0) == 1.0 and exp(-math.inf) == 0.0 and exp(math.inf) == math.inf
    assert log(-0.0) == -math.inf and log(math.inf) == math.inf and math.isnan(log(math.nan))
    assert math.isnan(log(-math.inf))
    # Les résultats sous-normaux passent par deux multiplications exactes, puis un seul arrondi.
    assert 0.0 < exp(-745.0) < 1e-323
    assert exp(709.7) < math.inf


def test_cos_seulement_de_0_a_pi():
    assert cos(-0.0) == 1.0
    for x in (-1e-300, -0.5, PI + 1e-15, 4.0, math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError, match="de 0 à π"):
            cos(x)


def test_proche_de_la_libm():  # précision, pas parité : la libm n'est qu'un témoin
    h = Hasard(7)
    for _ in range(10_000):
        x = (h.uniforme() - 0.5) * 1400
        assert abs(exp(x) - math.exp(x)) <= 1e-15 * math.exp(x) + 1e-320
        y = h.uniforme() * 1e6 + 1e-9
        assert abs(log(y) - math.log(y)) <= 1e-15 * max(1.0, abs(math.log(y)))
        t = h.uniforme() * PI
        assert abs(cos(t) - math.cos(t)) <= 1e-15


def test_log_des_sous_normaux():
    for y in (5e-324, 1e-320, 1e-310, 2.2250738585072014e-308):
        assert abs(log(y) - math.log(y)) <= 1e-15 * abs(math.log(y))


def test_hasard():
    h = Hasard(1234)
    tirages = [h.uniforme() for _ in range(10_000)]
    assert all(0.0 <= u < 1.0 for u in tirages)
    g = Hasard(5)
    gs = [g.gaussienne(1.0) for _ in range(10_000)]
    moyenne = somme(gs) / len(gs)
    assert abs(moyenne) < 0.05 and abs(somme([v * v for v in gs]) / len(gs) - 1.0) < 0.05
    liste = list(range(20))
    Hasard(1).melanger(liste)
    assert sorted(liste) == list(range(20)) and liste != list(range(20))


def test_hasard_entiers():
    h = Hasard(9)
    tirages = [h.entier(10) for _ in range(1_000)]
    assert set(tirages) == set(range(10))
    assert all(isinstance(t, int) for t in tirages)
    h = Hasard(3)
    assert all(0 <= h.suivant32() < 2**32 for _ in range(1_000))


def test_hasard_graine():
    # La graine est ramenée à 32 bits, comme « >>> 0 » en TypeScript.
    assert Hasard(-1).suivant32() == Hasard(0xFFFFFFFF).suivant32()
    assert Hasard(2**32 + 5).suivant32() == Hasard(5).suivant32()
    # Deux tirages d'une même graine sont identiques ; deux graines différentes, non.
    assert [Hasard(42).suivant32() for _ in range(3)] == [Hasard(42).suivant32()] * 3
    assert Hasard(42).suivant32() != Hasard(43).suivant32()
    # Les mêmes graines qu'en TypeScript : un entier sûr de JavaScript, de −(2^53 − 1) à 2^53 − 1.
    assert Hasard(2**53 - 1).suivant32() == Hasard(0xFFFFFFFF).suivant32()
    assert Hasard(-(2**53 - 1)).suivant32() == Hasard(1).suivant32()
    # 7.0 et 7 sont le même nombre en JavaScript : ils donnent la même suite ici aussi.
    assert Hasard(7.0).suivant32() == Hasard(7).suivant32()
    for mauvaise in (1.5, math.nan, math.inf, -math.inf, True, False, "7"):
        with pytest.raises(TypeError, match="entier"):
            Hasard(mauvaise)
    for trop_grande in (2**53, -(2**53), 2**64, float(2**53)):
        with pytest.raises(ValueError, match="entiers sûrs"):
            Hasard(trop_grande)


def test_sommes_et_hex():
    assert somme([0.1, 0.2, 0.3]) == (0.1 + 0.2) + 0.3
    assert depuis_hex(vers_hex(-0.0)) == 0.0 and vers_hex(-0.0) == "8000000000000000"
    assert vers_hex(PI) == "400921fb54442d18"
    assert somme([]) == 0.0
    # Pas de sommation compensée : 1e16 + 1 + 1 reste 1e16 quand on additionne dans l'ordre.
    assert somme([1e16, 1.0, 1.0]) == 1e16


def test_hex():
    assert vers_hex(1.0) == "3ff0000000000000" and vers_hex(5e-324) == "0000000000000001"
    assert vers_hex(math.inf) == "7ff0000000000000" and vers_hex(-math.inf) == "fff0000000000000"
    for x in (0.0, 1.0, -2.5, 0.1, 5e-324, 1.7976931348623157e308, -math.inf):
        assert vers_hex(depuis_hex(vers_hex(x))) == vers_hex(x)
    # Tous les NaN s'écrivent de la même façon : leur motif varie selon la machine.
    assert vers_hex(math.nan) == "7ff8000000000000"
    assert vers_hex(depuis_hex("fff8000000000001")) == "7ff8000000000000"
    for mauvais in ("3FF0000000000000", "3ff000000000000", "3ff00000000000000", "3ff000000000000g", ""):
        with pytest.raises(ValueError, match="16 chiffres"):
            depuis_hex(mauvais)


def test_produit_scalaire_et_maximum():
    assert produit_scalaire([1.0, 2.0, 3.0], [4.0, 5.0, 6.0]) == 32.0
    assert produit_scalaire([], []) == 0.0
    with pytest.raises(ValueError, match="même longueur"):
        produit_scalaire([1.0], [1.0, 2.0])
    assert maximum([1.0, 3.0, 2.0]) == 3.0
    assert maximum([-5.0]) == -5.0
    # Une boucle « if v > m » garde la première valeur en cas d'égalité, même -0 face à 0.
    assert math.copysign(1.0, maximum([-0.0, 0.0])) == -1.0
    assert math.copysign(1.0, maximum([0.0, -0.0])) == 1.0
    with pytest.raises(ValueError, match="vide"):
        maximum([])


def test_racine():
    assert racine(2.0) == math.sqrt(2.0) and racine(0.0) == 0.0 and racine(math.inf) == math.inf
    assert vers_hex(racine(-0.0)) == "8000000000000000"
    assert math.isnan(racine(math.nan))
    with pytest.raises(ValueError, match="négatif"):
        racine(-1.0)


def test_deux_puissance():
    assert deux_puissance(0) == 1.0 and deux_puissance(-1074) == 5e-324
    assert deux_puissance(1023) == 8.98846567431158e307 and deux_puissance(-1022) == 2.2250738585072014e-308
    for k in (1024, -1075):
        with pytest.raises(ValueError, match="de -1074 à 1023"):
            deux_puissance(k)


def fnv1a_de_reference(octets: bytes) -> str:
    """FNV-1a 32 bits écrit à part, pour vérifier celui du paquet."""
    h = 0x811C9DC5
    for o in octets:
        h = ((h ^ o) * 0x01000193) % 2**32
    return f"{h:08x}"


def test_empreintes():
    # Valeurs publiées de FNV-1a 32 bits.
    assert empreinte_texte("") == "811c9dc5" and empreinte([]) == "811c9dc5"
    assert empreinte_texte("a") == "e40c292c" and empreinte_texte("foobar") == "bf9cf968"
    assert empreinte_texte("é") == fnv1a_de_reference("é".encode("utf-8"))
    # Chaque flottant compte pour ses 8 octets, gros-boutistes, dans l'ordre de la liste.
    assert empreinte([1.0, -0.0]) == fnv1a_de_reference(bytes.fromhex("3ff0000000000000" + "8000000000000000"))
    assert empreinte([1.0, -0.0]) != empreinte([-0.0, 1.0])
    assert empreinte([math.nan]) == empreinte([depuis_hex("fff8000000000000")])
