"""Les attendus du chapitre 0.3 : chaque situation nommée, ses faits et ses constats.

Le site ne refait pas le diagnostic : il lit ce fichier, `tests/attendus.json`,
pour son tableau des situations et ses paris. Pour le régénérer (dans
projets/0.3-poste) :

    uv run --extra cpu python -m poste.attendus
"""

import json
from dataclasses import asdict
from pathlib import Path

from poste.diagnostic import SITUATIONS, diagnostiquer

CHEMIN_ATTENDUS = Path(__file__).resolve().parent.parent / "tests" / "attendus.json"


def calculer_attendus() -> dict:
    """{"situations": [[nom, {"faits": {…}, "constats": [{niveau, cle, message, a_faire}, …]}], …]}"""
    return {
        "situations": [
            [nom, {"faits": asdict(faits), "constats": [asdict(c) for c in diagnostiquer(faits)]}]
            for nom, faits in SITUATIONS.items()
        ]
    }


def vers_json(valeur) -> str:
    """Le texte JSON du fichier : UTF-8 lisible, sans NaN, indenté d'une espace, fini par un retour à la ligne."""
    return json.dumps(valeur, ensure_ascii=False, allow_nan=False, indent=1) + "\n"


def ecrire_attendus() -> None:
    """Écrit tests/attendus.json (UTF-8, fins de ligne LF)."""
    with open(CHEMIN_ATTENDUS, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(vers_json(calculer_attendus()))


if __name__ == "__main__":
    ecrire_attendus()
    print(f"Écrit\u202f: {CHEMIN_ATTENDUS}")
