"""Valeurs de référence pour le jumeau TypeScript et pour le chapitre 1.1.

Le site refait ce projet en TypeScript (site/src/lib/partie-1/ngrammes.ts).
Ce fichier produit `tests/attendus.json` : des entrées fixées, et ce que le
Python en tire. Le jumeau TypeScript doit retrouver exactement les mêmes
valeurs, sauf les perplexités : elles passent par exp et log, que le site ne
refait pas (il les lit dans le fichier).

Le fichier contient, dans l'ordre :

- `alphabet` : les caractères du texte entier ;
- `ordres` : pour chaque n de 0 à 6, la perplexité sur le texte d'apprentissage
  et sur celui de validation, la part de contextes jamais vus, et les dix
  caractères les plus probables après chaque contexte de référence ;
- `suites` : le texte écrit, pour chaque n, chaque température et deux graines ;
- `cas_limites` : le texte vide, un seul caractère, un caractère répété, un emoji
  (hors du premier plan d'Unicode), « İ » (dont la minuscule a deux caractères)
  et des contextes que le texte ne contient pas.

Pour régénérer le fichier (dans projets/1.1-modele-de-langage) :

    uv run python -m modele_de_langage.attendus
"""

import json
from pathlib import Path

from modele_de_langage.ngrammes import (
    ORDRE_MAX,
    TEMPERATURES,
    alphabet,
    charger_texte,
    compter,
    compter_par_ordre,
    couper,
    distribution,
    generer,
    part_jamais_vue,
    perplexite,
)

# Les sections qui n'utilisent que des comptes, + − × ÷ et la racine carrée : le même
# résultat au bit près sur toutes les machines, et dans le navigateur.
SECTIONS_EXACTES = ("alphabet", "suites", "cas_limites")
# La section `ordres` mêle des valeurs exactes et des perplexités, qui passent par
# math.exp et math.log : leur dernier chiffre peut changer d'un système à l'autre
# (voir tests/test_attendus.py). Ces deux clés se comparent à 10^-9 près.
SECTIONS_LIBM = ("ordres",)
SORTIES_LIBM = ("perplexite_entrainement", "perplexite_validation")

# Les contextes de référence ont 12 caractères : chaque ordre n en garde les n derniers.
LONGUEUR_CONTEXTE = 12
NB_RANGS = 10
# Les départs des suites : les n premiers caractères du texte de validation.
GRAINES = (0, 1)
LONGUEUR_SUITE = 120
# Un contexte que le texte ne contient pas : tous ses ordres donnent la loi uniforme.
CONTEXTE_ABSENT = "¤" * LONGUEUR_CONTEXTE

CHEMIN_ATTENDUS = Path(__file__).resolve().parent.parent / "tests" / "attendus.json"

# Les cas limites : (nom, texte, n, contexte). Le contexte sert de départ à la suite.
CAS_LIMITES: list[tuple[str, str, int, str]] = [
    ("texte vide", "", 1, ""),
    ("un seul caractère", "a", 1, "a"),
    ("un caractère répété", "aaaa", 2, "aa"),
    ("un emoji hors du premier plan, et un caractère plus grand que ses unités UTF-16", "\U0001f600～a\U0001f600～a\U0001f600", 1, "\U0001f600"),
    ("la majuscule İ", "İiİiİ", 1, "İ"),
    ("un contexte jamais vu", "abab", 2, "bb"),
    ("un contexte trop court", "abab", 2, "a"),
    ("l'ordre zéro", "abracadabra", 0, ""),
]


def vers_json(valeur) -> str:
    """La valeur en JSON, comme dans le fichier : UTF-8, sans NaN, indentée d'une espace.

    Deux flottants égaux mais écrits différemment (-0.0 et 0.0, 6.0 et 6) ne
    donnent pas le même texte : c'est ainsi qu'on compare les sections exactes.
    """
    return json.dumps(valeur, ensure_ascii=False, allow_nan=False, indent=1)


def contextes_de_reference(entrainement: str, validation: str) -> list[str]:
    """Des contextes de 12 caractères : quatre du texte d'apprentissage, le début de la validation, un absent."""
    positions = [len(entrainement) * k // 5 for k in range(1, 5)]
    return [
        *(entrainement[p - LONGUEUR_CONTEXTE : p] for p in positions),
        validation[:LONGUEUR_CONTEXTE],
        CONTEXTE_ABSENT,
    ]


def calculer_alphabet() -> list[str]:
    return alphabet(charger_texte())


def calculer_ordres() -> list[dict]:
    texte = charger_texte()
    entrainement, validation = couper(texte)
    lettres = alphabet(texte)
    contextes = contextes_de_reference(entrainement, validation)
    ordres = []
    for n in range(ORDRE_MAX + 1):
        comptes = compter(entrainement, n)
        absents, total = part_jamais_vue(comptes, validation, n)
        ordres.append(
            {
                "n": n,
                "perplexite_entrainement": perplexite(comptes, lettres, n, entrainement),
                "perplexite_validation": perplexite(comptes, lettres, n, validation),
                "jamais_vus": [absents, total],
                "distributions": [
                    {
                        "contexte": contexte,
                        "rangs": [[c, p] for c, p in distribution(comptes, lettres, contexte, n)[:NB_RANGS]],
                    }
                    for contexte in contextes
                ],
            }
        )
    return ordres


def calculer_suites() -> list[dict]:
    texte = charger_texte()
    entrainement, validation = couper(texte)
    lettres = alphabet(texte)
    suites = []
    for n in range(1, ORDRE_MAX + 1):
        comptes = compter_par_ordre(entrainement, n)
        depart = validation[:n]
        for temperature in TEMPERATURES:
            for graine in GRAINES:
                suites.append(
                    {
                        "n": n,
                        "temperature": temperature,
                        "graine": graine,
                        "depart": depart,
                        "longueur": LONGUEUR_SUITE,
                        "suite": generer(comptes, lettres, n, depart, LONGUEUR_SUITE, temperature, graine),
                    }
                )
    return suites


def calculer_cas_limites() -> list[dict]:
    cas = []
    for nom, texte, n, contexte in CAS_LIMITES:
        entrainement, validation = couper(texte)
        lettres = alphabet(texte)
        comptes = compter(texte, n)
        try:
            rangs = [[c, p] for c, p in distribution(comptes, lettres, contexte, n)]
            erreur = None
        except ValueError as e:
            rangs, erreur = None, str(e)
        try:
            suite = generer(compter_par_ordre(texte, n), lettres, n, contexte, 8, 1, 0)
            erreur_suite = None
        except ValueError as e:
            suite, erreur_suite = None, str(e)
        cas.append(
            {
                "nom": nom,
                "texte": texte,
                "n": n,
                "contexte": contexte,
                "alphabet": lettres,
                "coupe": [entrainement, validation],
                "comptes": [[ctx, [[c, k] for c, k in suivants.items()]] for ctx, suivants in comptes.items()],
                "distribution": rangs,
                "erreur": erreur,
                "suite": suite,
                "erreur_suite": erreur_suite,
            }
        )
    return cas


def calculer_attendus() -> dict:
    """Calcule toutes les sections, dans l'ordre du fichier."""
    return {
        "alphabet": calculer_alphabet(),
        "ordres": calculer_ordres(),
        "suites": calculer_suites(),
        "cas_limites": calculer_cas_limites(),
    }


def ecrire_attendus() -> None:
    """Écrit tests/attendus.json (UTF-8, fins de ligne LF)."""
    texte = vers_json(calculer_attendus())
    with open(CHEMIN_ATTENDUS, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(texte + "\n")


if __name__ == "__main__":
    ecrire_attendus()
    print(f"Écrit : {CHEMIN_ATTENDUS}")
