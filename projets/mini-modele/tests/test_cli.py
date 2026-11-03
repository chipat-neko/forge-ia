"""La ligne de commande : python -m mini_modele entrainer.

Elle affiche l'erreur du lot tous les 50 pas et au dernier pas
(« pas 50 : erreur 2,734 »), puis l'erreur de validation et des prénoms
inventés. Un taux trop grand l'arrête avec un message qui dit quoi faire.
"""

import os
import pathlib
import re
import subprocess
import sys

import pytest

from mini_modele.__main__ import formater_erreur, main

PROJET = pathlib.Path(__file__).resolve().parent.parent
LIGNE_DE_PAS = re.compile(r"^pas (\d+) : erreur (\d+,\d{3})$", re.MULTILINE)


def prenoms_affiches(sortie: str) -> list[str]:
    """Les prénoms de la ligne « Prénoms inventés : a, b (existe déjà), … », sans la mention."""
    ligne = next(l for l in sortie.splitlines() if l.startswith("Prénoms inventés : "))
    return [p.removesuffix(" (existe déjà)") for p in ligne.removeprefix("Prénoms inventés : ").split(", ")]


def test_cli(capsys):
    main(["entrainer", "--pas", "2"])
    assert "pas 2" in capsys.readouterr().out


def test_cli_affiche_tous_les_50_pas_et_le_dernier(capsys):
    assert main(["entrainer", "--preset", "avant-gout", "--pas", "51"]) == 0
    sortie = capsys.readouterr().out
    assert [int(m.group(1)) for m in LIGNE_DE_PAS.finditer(sortie)] == [50, 51]
    assert "préréglage avant-gout, 51 pas, taux maximal 0,01" in sortie
    assert re.search(r"^Erreur de validation au départ : \d,\d{3}", sortie, re.MULTILINE)
    assert re.search(r"^Erreur de validation au pas 51 : \d,\d{3}", sortie, re.MULTILINE)
    prenoms = prenoms_affiches(sortie)
    assert len(prenoms) == 8 and all(prenoms)


def test_cli_accepte_la_virgule_et_le_point(capsys):
    assert main(["entrainer", "--pas", "1", "--taux", "0,03"]) == 0
    assert "taux maximal 0,03" in capsys.readouterr().out
    assert main(["entrainer", "--pas", "1", "--taux", "0.003"]) == 0
    assert "taux maximal 0,003" in capsys.readouterr().out


def test_cli_taux_trop_grand(capsys):
    assert main(["entrainer", "--pas", "20", "--taux", "1000"]) == 1
    sortie = capsys.readouterr().out
    assert re.search(r"L'erreur a explosé au pas \d+ : ce taux est trop grand\. Recommence avec un taux plus petit", sortie)
    assert "Prénoms inventés" not in sortie


@pytest.mark.parametrize(
    "arguments",
    [
        ["entrainer", "--taux", "0"],
        ["entrainer", "--taux", "abc"],
        ["entrainer", "--pas", "0"],
        ["entrainer", "--pas", "2.5"],
        ["entrainer", "--preset", "inconnu"],
        [],
    ],
)
def test_cli_refuse_un_mauvais_reglage(arguments, capsys):
    with pytest.raises(SystemExit) as fin:
        main(arguments)
    assert fin.value.code == 2
    assert capsys.readouterr().err


def test_formater_erreur():
    assert formater_erreur(2.7344) == "2,734"
    assert formater_erreur(3.0) == "3,000"
    assert formater_erreur(12.3456) == "12,346"


def test_le_module_se_lance():
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    fini = subprocess.run(
        [sys.executable, "-m", "mini_modele", "entrainer", "--pas", "1"],
        capture_output=True,
        cwd=PROJET,
        env=env,
        timeout=120,
    )
    sortie = fini.stdout.decode("utf-8")
    assert fini.returncode == 0, fini.stderr.decode("utf-8")
    assert LIGNE_DE_PAS.search(sortie.replace("\r\n", "\n"))
