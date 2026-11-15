"""La ligne de commande du projet : `python -m transformer_pas_a_pas compter` et `comparer`.

Sans PyTorch (la commande lancée sans `--extra cpu`), le script le dit en français, avec la commande
à lancer, sans trace Python, comme ceux des projets 0.4, 0.5, 1.5 et 1.6 (revue finale du plan 5, m4).
"""

import os
import pathlib
import subprocess
import sys

import pytest

from transformer_pas_a_pas.__main__ import main

PROJET = pathlib.Path(__file__).resolve().parents[1]


def test_compter_donne_les_familles_et_le_total_de_forge(capsys):
    assert main(["compter", "--preset", "mini"]) == 0
    sortie = capsys.readouterr().out
    assert "Les paramètres du preset «\u202fmini\u202f» de forge" in sortie
    assert "égal au nombre de paramètres de forge\u202f: oui" in sortie


@pytest.mark.parametrize("commande", [["compter", "--preset", "tres_grand"], ["comparer"]])
def test_pytorch_absent_sans_trace(commande):
    # Le lecteur qui lance `uv run python -m transformer_pas_a_pas compter` sans extra : PyTorch manque.
    # Le paquet et son __main__ s'importent quand même, et le script dit quoi faire, avec le code 2.
    script = (
        "import runpy, sys\n"
        "sys.modules['torch'] = None\n"
        f"sys.argv = ['transformer_pas_a_pas', *{commande!r}]\n"
        "runpy.run_module('transformer_pas_a_pas', run_name='__main__')\n"
    )
    resultat = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        cwd=PROJET,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        timeout=60,
    )
    assert resultat.returncode == 2
    assert "Traceback" not in resultat.stderr + resultat.stdout
    assert "Un module manque" in resultat.stderr
    assert "`uv run --extra cpu python -m transformer_pas_a_pas …`" in resultat.stderr
    assert "--extra gpu" in resultat.stderr
