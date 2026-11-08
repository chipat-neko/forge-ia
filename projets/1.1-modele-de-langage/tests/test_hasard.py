"""Le Hasard de ce projet est une copie exacte de celui du projet 0.2."""

import pathlib

import pytest

from modele_de_langage.hasard import Hasard

RACINE = pathlib.Path(__file__).resolve().parents[3]
ORIGINAL = RACINE / "projets" / "0.2-maths" / "maths_utiles" / "tirage.py"
COPIE = RACINE / "projets" / "1.1-modele-de-langage" / "modele_de_langage" / "hasard.py"


def classe_hasard(source: str) -> str:
    """Le texte de la classe Hasard : de « class Hasard: » à « # fin: hasard » (ou à la fin du fichier)."""
    debut = source.index("class Hasard:")
    marque = source.find("# fin: hasard", debut)
    fin = len(source) if marque == -1 else marque
    return source[debut:fin].rstrip() + "\n"


def test_la_copie_est_identique_a_l_original():
    if not ORIGINAL.exists():
        pytest.skip("Le projet 0.2 n'est pas là : rien à comparer.")
    assert classe_hasard(COPIE.read_text(encoding="utf-8")) == classe_hasard(ORIGINAL.read_text(encoding="utf-8"))


def test_la_suite_est_reproductible():
    h = Hasard(1234)
    premiers = [h.suivant32() for _ in range(3)]
    assert all(0 <= x < 2**32 for x in premiers)
    assert Hasard(1234).uniforme() == premiers[0] / 4294967296.0
    assert Hasard(0).suivant32() != Hasard(1).suivant32()
