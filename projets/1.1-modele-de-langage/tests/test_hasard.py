"""Le Hasard de ce projet est une copie exacte de celui du projet 0.2 (la région `hasard`, avec ENTIER_SUR_MAX)."""

import pathlib

import pytest

from modele_de_langage.hasard import Hasard

RACINE = pathlib.Path(__file__).resolve().parents[3]
ORIGINAL = RACINE / "projets" / "0.2-maths" / "maths_utiles" / "tirage.py"
COPIE = RACINE / "projets" / "1.1-modele-de-langage" / "modele_de_langage" / "hasard.py"


def region_hasard(source: str) -> str:
    """Le texte de la région `hasard` : de « # region: hasard » à « # fin: hasard », constante comprise."""
    debut = source.index("# region: hasard")
    fin = source.index("# fin: hasard", debut) + len("# fin: hasard")
    return source[debut:fin]


def test_la_copie_est_identique_a_l_original():
    if not ORIGINAL.exists():
        pytest.skip("Le projet 0.2 n'est pas là : rien à comparer.")
    assert region_hasard(COPIE.read_text(encoding="utf-8")) == region_hasard(ORIGINAL.read_text(encoding="utf-8"))


def test_la_suite_est_reproductible():
    h = Hasard(1234)
    premiers = [h.suivant32() for _ in range(3)]
    assert all(0 <= x < 2**32 for x in premiers)
    assert Hasard(1234).uniforme() == premiers[0] / 4294967296.0
    assert Hasard(0).suivant32() != Hasard(1).suivant32()
