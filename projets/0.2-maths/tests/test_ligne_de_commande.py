"""La ligne de commande : un exemple de chaque idée, et des messages qui disent quoi faire."""

import pytest

from maths_utiles.__main__ import nombre, principal


def sortie(capsys) -> str:
    """Ce que le programme a écrit, avec des espaces ordinaires à la place des espaces fines."""
    return capsys.readouterr().out.replace("\u202f", " ")


def test_nombre_a_la_francaise():
    assert nombre(1234.5, 1).replace("\u202f", " ") == "1 234,5"
    assert nombre(5.0) == "5" and nombre(-3.0718, 3) == "-3,072"
    # Un résultat arrondi à zéro ne garde pas de signe.
    assert nombre(-0.0, 3) == "0,000" and nombre(-0.0001, 3) == "0,000"
    assert nombre(-10.0, 3) == "-10,000"


def test_par_defaut(capsys):
    principal([])
    texte = sortie(capsys)
    assert "a · b = 3 × 1 + 1 × 2 = 5" in texte
    assert "[[1, 2, 3], [0, 1, 0]] × [1, 1, 1] = [6, 1]" in texte
    assert "pas 3 : x = 1,464, erreur = 3,359, pente = -3,072" in texte
    assert "L’erreur passe sous 1,01 au pas 16." in texte
    assert "1 000 tirages au sort après « le » (graine 1 234) :" in texte
    assert "fer    60 % attendu, 609 tirés (60,9 %)" in texte


def test_descente_qui_explose(capsys):
    principal(["--taux", "1.2", "--pas", "30"])
    texte = sortie(capsys)
    assert "x est parti à plus de 1 000 du fond : ce taux fait exploser la descente." in texte
    assert "nan" not in texte.lower() and "inf" not in texte.lower()


def test_descente_qui_oscille(capsys):
    principal(["--taux", "1", "--pas", "2"])
    texte = sortie(capsys)
    assert "pas 1 : x = 6,000" in texte
    assert "En 100 pas, l’erreur ne passe jamais sous 1,01." in texte


def test_tirages_et_graine(capsys):
    principal(["--tirages", "100000", "--graine", "1235"])
    texte = sortie(capsys)
    assert "100 000 tirages au sort après « le » (graine 1 235) :" in texte
    assert "fer    60 % attendu, 59 975 tirés (60,0 %)" in texte


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["--taux", "0"], "Le taux doit être un nombre positif (reçu 0.0) : relance avec --taux 0.1"),
        (["--taux", "nan"], "Le taux doit être un nombre positif"),
        (["--pas", "-1"], "Le nombre de pas va de 0 à 1 000 (reçu -1)"),
        (["--tirages", "0"], "Le nombre de tirages va de 1 à 1 000 000 (reçu 0)"),
        (["--graine", "-5"], "La graine va de 0 à 9 007 199 254 740 991 (reçu -5)"),
    ],
)
def test_reglages_refuses(capsys, arguments, message):
    with pytest.raises(SystemExit) as fin:
        principal(arguments)
    assert fin.value.code == 1
    assert message in capsys.readouterr().err.replace("\u202f", " ")
