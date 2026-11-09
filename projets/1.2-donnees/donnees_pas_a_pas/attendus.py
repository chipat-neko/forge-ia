"""Valeurs de référence pour le jumeau TypeScript et pour le chapitre 1.2.

Le site refait le nettoyage en TypeScript (site/src/lib/partie-1/nettoyeur.ts). Ce fichier
produit `tests/attendus.json` : des textes fixés, et ce que le code de forge en tire. Le
jumeau TypeScript doit retrouver exactement les mêmes valeurs, dans Node comme dans Chrome,
Firefox et WebKit.

Le fichier contient, dans l'ordre :

- `blancs_python` : les points de code où `chr(i).isspace()` est vrai. Le jumeau ne peut pas
  s'en remettre à `trimEnd()`, qui ne retire pas les mêmes caractères (il retire U+FEFF,
  que Python ne considère pas comme un blanc) ;
- `textes` : pour chaque texte de référence (les exemples du projet, puis les pièges), le texte
  nettoyé (`null` s'il fait moins de 200 caractères), la longueur du texte normalisé en points
  de code, son empreinte SHA-1 et `validation` (est-il mis de côté ?) ;
- `licences` : des lignes de code, et ce que le filtre de `code_python` en dit ;
- `tris` : pour chaque source, les lignes des exemples et le verdict du tri sur chacune.

Un texte s'écrit dans le fichier de l'une de ces trois façons (`coder`, `decoder`) : en chaîne ;
en liste de points de code quand il contient une moitié de paire de substitution (U+D800 à
U+DFFF), qui ne s'écrit pas en UTF-8 ; ou en `{"repete": motif, "fois": n}` pour un très long
texte d'un seul caractère répété.

Pour régénérer le fichier (dans projets/1.2-donnees) :

    uv run python -m donnees_pas_a_pas.attendus
"""

import json
from pathlib import Path

from forge.donnees.melange import est_validation
from forge.donnees.nettoyage import _normaliser, empreinte, nettoyer
from forge.donnees.sources import SOURCES

from donnees_pas_a_pas.trier import lire_jsonl, trier

CHEMIN_ATTENDUS = Path(__file__).resolve().parent.parent / "tests" / "attendus.json"
EXEMPLES = Path(__file__).resolve().parent.parent / "exemples"

# Les caractères que `str.rstrip()` retire : ceux où `str.isspace()` est vrai.
BLANCS_PYTHON = [i for i in range(0x110000) if chr(i).isspace()]

# Un texte de 200 caractères ou plus, pour que les pièges de la fin du texte se voient.
_BASE = "a" * 210

# Les pièges du nettoyage : un nom, et le texte.
TEXTES_PIEGES: dict[str, str] = {
    "texte vide": "",
    "199 caractères": "a" * 199,
    "200 caractères": "a" * 200,
    "199 caractères et une espace en fin": "a" * 199 + " ",
    "200 caractères et une espace en fin": "a" * 200 + " ",
    "U+3000 en fin": _BASE + "\u3000",
    "U+2028 en fin": _BASE + "\u2028",
    "U+00A0 en fin": _BASE + "\u00a0",
    "U+FEFF en fin": _BASE + "\ufeff",
    "U+FEFF puis une espace en fin": _BASE + "\ufeff ",
    "tous les blancs de Python en fin": _BASE + "".join(chr(i) for i in BLANCS_PYTHON),
    "blancs au milieu et en fin": "a" * 100 + "\u3000\u2028" + "b" * 110 + "\u3000",
    "tous les contrôles, puis du texte": "".join(chr(i) for i in [*range(0, 9), *range(0x0B, 0x20), *range(0x7F, 0xA0)])
    + "a" * 200,
    "un contrôle entre une lettre et son accent": "e\x00\u0301" * 210,
    "la forme NFC, sans la compatibilité": "\u212b\ufb01" * 105,
    "200 emojis": "\U0001f600" * 200,
    "moitiés de paire, loin l'une de l'autre": "\ud83d" + "a" * 210 + "\ude00",
    "moitiés de paire dans l'ordre inverse": "\ude00" + "a" * 100 + "\ud83d" + "b" * 100,
    # Le seul de la liste que est_validation met de côté (l'essai 190 : une chance sur 200 par essai).
    "un texte mis de côté pour la validation": "Ce texte est mis de côté pour la validation : c'est l'essai numéro 190. " * 4,
    "100 000 x": "x" * 100_000,
}

# Des lignes de code pour le filtre : la colonne `license` est lue sans tenir compte de la casse.
LIGNES_DE_LICENCE: list[dict] = [
    {"language": "Python", "license": "mit"},
    {"language": "Python", "license": "MIT"},
    {"language": "Python", "license": "Apache-2.0"},
    {"language": "Python", "license": "bsd-2-clause"},
    {"language": "Python", "license": "BSD-3-Clause"},
    {"language": "Python", "license": "isc"},
    {"language": "Python", "license": "Unlicense"},
    {"language": "Python", "license": "cc0-1.0"},
    {"language": "Python", "license": "gpl-3.0"},
    {"language": "Python", "license": "mit "},
    {"language": "Python", "license": ""},
    {"language": "Python", "license": None},
    {"language": "Python", "license": 5},
    {"language": "Python"},
    {"language": "python", "license": "mit"},
    {"language": "Java", "license": "mit"},
    {"license": "mit"},
    {},
]


def coder(texte: str) -> str | list[int] | dict:
    """Comment le fichier écrit un texte : chaîne, liste de points de code, ou motif répété."""
    if any(0xD800 <= ord(c) <= 0xDFFF for c in texte):
        return [ord(c) for c in texte]
    if len(texte) > 1000 and texte == texte[0] * len(texte):
        return {"repete": texte[0], "fois": len(texte)}
    return texte


def decoder(valeur):
    """L'inverse de `coder` (une valeur qui n'est ni liste ni motif répété est rendue telle quelle)."""
    if isinstance(valeur, list):
        return "".join(chr(i) for i in valeur)
    if isinstance(valeur, dict) and set(valeur) == {"repete", "fois"}:
        return valeur["repete"] * valeur["fois"]
    return valeur


def vers_json(valeur) -> str:
    """La valeur en JSON, comme dans le fichier : UTF-8, sans NaN, indentée d'une espace."""
    return json.dumps(valeur, ensure_ascii=False, allow_nan=False, indent=1)


def _textes_de_reference() -> list[tuple[str, str]]:
    textes = []
    for fichier, colonne in (("web.jsonl", "text"), ("code.jsonl", "code")):
        for i, ligne in enumerate(lire_jsonl(EXEMPLES / fichier), start=1):
            textes.append((f"{fichier}, ligne {i}", ligne[colonne]))
    return textes + list(TEXTES_PIEGES.items())


def calculer_blancs() -> list[int]:
    return list(BLANCS_PYTHON)


def calculer_textes() -> list[dict]:
    resultats = []
    for nom, texte in _textes_de_reference():
        nettoye = nettoyer(texte)
        digest = empreinte(texte)
        resultats.append(
            {
                "nom": nom,
                "entree": coder(texte),
                "nettoye": None if nettoye is None else coder(nettoye),
                # La longueur du texte normalisé, avant le seuil de 200 : elle dit aussi pourquoi un texte est trop court.
                "longueur": len(_normaliser(texte)),
                "empreinte": digest,
                "validation": est_validation(digest),
            }
        )
    return resultats


def calculer_licences() -> list[dict]:
    garder = SOURCES["code_python"].garder
    return [{"ligne": ligne, "garde": garder(ligne)} for ligne in LIGNES_DE_LICENCE]


def _coder_ligne(ligne: dict) -> dict:
    return {cle: coder(v) if isinstance(v, str) else v for cle, v in ligne.items()}


def calculer_tris() -> list[dict]:
    tris = []
    for nom_source, fichier in (("web_fr", "web.jsonl"), ("code_python", "code.jsonl")):
        lignes = list(lire_jsonl(EXEMPLES / fichier))
        verdicts = trier(lignes, SOURCES[nom_source])
        tris.append(
            {
                "source": nom_source,
                "lignes": [_coder_ligne(ligne) for ligne in lignes],
                "verdicts": [
                    {
                        "garde": v.garde,
                        "raison": v.raison,
                        "texte": v.texte,
                        "empreinte": v.empreinte,
                        "validation": v.validation,
                    }
                    for v in verdicts
                ],
            }
        )
    return tris


def calculer_attendus() -> dict:
    """Calcule toutes les sections, dans l'ordre du fichier."""
    return {
        "blancs_python": calculer_blancs(),
        "textes": calculer_textes(),
        "licences": calculer_licences(),
        "tris": calculer_tris(),
    }


def ecrire() -> None:
    contenu = vers_json(calculer_attendus()) + "\n"
    with open(CHEMIN_ATTENDUS, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(contenu)
    print(f"Écrit : {CHEMIN_ATTENDUS}")


if __name__ == "__main__":
    ecrire()
