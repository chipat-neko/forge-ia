"""Valeurs de référence pour le jumeau TypeScript.

Le site refait le même calcul en TypeScript. Ce fichier produit
`tests/attendus.json` : les fusions apprises, puis le découpage de plusieurs
textes avec plusieurs nombres de fusions. Le jumeau TypeScript doit retrouver
exactement les mêmes valeurs.

Pour régénérer le fichier (dans projets/1.3-tokenizer) :

    uv run python -m tokenizer_pedagogique.attendus
"""

import json
from pathlib import Path

from tokenizer_pedagogique.bpe import TokenizerPedagogique, charger_corpus

TEXTES_DE_REFERENCE: list[str] = [
    "Le forgeron frappe le métal sur l'enclume.",
    "Les forgerons découpent le texte en jetons.",
    "les forgerons",
    "reforgeronnes",
    "Salut 🙂",
    "Le forgeron  frappe, 2026 !\nFin",
    "",
    "forgé, reforgé : forgeronne",
]

# Nombres de fusions essayés pour chaque texte (165 = toutes les fusions du corpus).
KS_DE_REFERENCE = [0, 1, 10, 30, 60, 100, 165]

CHEMIN_ATTENDUS = Path(__file__).resolve().parent.parent / "tests" / "attendus.json"


def calculer_attendus() -> dict:
    """Calcule les valeurs de référence (listes et nombres, prêts pour le JSON)."""
    tokenizer = TokenizerPedagogique(charger_corpus())
    return {
        "fusions": [[f.a, f.b, f.compte] for f in tokenizer.fusions],
        "cas": [
            {
                "texte": texte,
                "k": k,
                "jetons": [[j.texte, j.id, j.mot] for j in tokenizer.decouper(texte, k)],
            }
            for texte in TEXTES_DE_REFERENCE
            for k in KS_DE_REFERENCE
        ],
    }


def en_json(attendus: dict) -> str:
    """Écrit les attendus en JSON, une fusion ou un cas par ligne (lisible dans git)."""

    def ligne(valeur) -> str:
        return json.dumps(valeur, ensure_ascii=False)

    fusions = ",\n".join("  " + ligne(f) for f in attendus["fusions"])
    cas = ",\n".join("  " + ligne(c) for c in attendus["cas"])
    return '{\n "fusions": [\n' + fusions + '\n ],\n "cas": [\n' + cas + "\n ]\n}\n"


def ecrire_attendus() -> None:
    """Écrit tests/attendus.json (UTF-8, fins de ligne LF)."""
    with open(CHEMIN_ATTENDUS, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(en_json(calculer_attendus()))


if __name__ == "__main__":
    ecrire_attendus()
    print(f"Écrit : {CHEMIN_ATTENDUS}")
