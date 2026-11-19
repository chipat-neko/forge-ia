"""Valeurs de référence pour les jumeaux TypeScript et pour le chapitre 1.9.

Le site refait trois calculs en TypeScript : le générateur de problèmes et la lecture d'une réponse
(`site/src/lib/partie-1/problemes.ts`, qui traduit `forge.raisonnement.problemes` et `forge.raisonnement.verification`)
et les avantages d'un groupe (`site/src/lib/partie-1/avantages.ts`, qui traduit `avantages_a_la_main` et `sans_signal`).
Ce fichier produit `tests/attendus.json`, cinq sections :

- `problemes` : chaque couple (famille, difficulté) permis, avec les graines 0 à 4. Les entrées sont `famille`,
  `difficulte` et `graine` ; le Python en tire `enonce`, `etapes` et `reponse` (`generer_probleme` de forge) ;
- `problemes_reserves` : les mêmes couples avec une graine de la plage d'évaluation (1 000 000) et une de la plage de
  validation du RL (5 000 000), dont les prénoms ne sont pas ceux de l'entraînement ;
- `nombres` : des textes de réponse (les écritures françaises d'un nombre, et leurs pièges : milliers séparés par une
  espace ordinaire, insécable ou fine, virgule décimale, signe moins collé ou non, chiffres hors du premier plan
  d'Unicode, texte vide), avec le nombre lu (`extraire_nombre`, écrit « 25/2 » ou « -7 ») et le verdict de
  `est_juste` pour une réponse terminée et une réponse coupée ;
- `avantages` : dix groupes de récompenses, avec l'avantage de chaque réponse (`avantages_a_la_main`) ;
- `sans_signal` : la chance qu'un groupe n'apprenne rien, sur une grille de p (la chance d'une réponse juste) et de n (la
  taille du groupe).

Tout est entier, texte ou booléen, sauf les avantages et la grille de `sans_signal` : des flottants que les deux
langages calculent avec les mêmes opérations dans le même ordre, donc à l'identique (le site les compare sans tolérance,
et la page de parité aussi).

Pour régénérer le fichier (dans projets/1.9-raisonnement) :

    uv run --extra cpu python -m raisonnement_pas_a_pas.attendus
"""

import json
from fractions import Fraction
from pathlib import Path

from forge.conversation.format import Reponse
from forge.raisonnement.problemes import FORMES, GRAINES_EVALUATION, GRAINES_VALIDATION_RL, generer_probleme
from forge.raisonnement.verification import est_juste, extraire_nombre

from raisonnement_pas_a_pas.avantages import avantages_a_la_main, sans_signal

PROJET = Path(__file__).resolve().parent.parent
CHEMIN_ATTENDUS = PROJET / "tests" / "attendus.json"

# Les caractères invisibles ou ambigus, par leur numéro : ni le code ni les tests ne les écrivent en clair.
FINE = chr(0x202F)  # l'espace fine insécable
INSECABLE = chr(0x00A0)  # l'espace insécable
MOINS = chr(0x2212)  # le signe moins
CHIFFRE_ARABE = chr(0x0663)  # « ٣ » : un chiffre pour \d de Python, pas pour [0-9]
CHIFFRE_PLEINE_LARGEUR = chr(0xFF13)  # « ３ »
LETTRE_HORS_DU_PREMIER_PLAN = chr(0x1D49C)  # « 𝒜 », une majuscule (catégorie Lu) hors du premier plan d'Unicode
EXPOSANT = chr(0x00B2)  # « ² » : catégorie No, un « nombre » pour isalnum de Python
ROMAIN = chr(0x2167)  # « Ⅷ » : catégorie Nl
ACCENT_COMBINANT = chr(0x0301)

GRAINES = (0, 1, 2, 3, 4)
GRAINES_RESERVEES = (GRAINES_EVALUATION, GRAINES_VALIDATION_RL)

TEXTES: tuple[str, ...] = (
    "",
    "rien",
    "La réponse est 84.",
    "La réponse est 84",
    "3 puis 7",
    "12 fois 7 font 84, donc 84.",
    "x = 1 234 567",
    "1" + FINE + "234" + FINE + "567",
    "1" + INSECABLE + "234",
    "12 3456",
    "12 345",
    "1 2 3",
    "1 234 56",
    "1 2345",
    "12,5",
    "12,50",
    "3.5",
    "1.234",
    "0,125",
    "3, puis 4",
    "3,",
    "4.",
    "-3",
    MOINS + "3",
    "x = -4",
    "5-3",
    "5 - 3",
    "5 " + MOINS + " 3",
    "a-3",
    "a" + MOINS + "3",
    "é-3",
    "_-3",
    "_3",
    "3-",
    "-0",
    "-0,0",
    "--3",
    "-" + MOINS + "3",
    "7" + MOINS + "3",
    "(-3)",
    "−3,5",
    "trois",
    "La réponse est 1 000 000 000 000 000 000 000 000 000 001.",
    "007",
    "0 1",
    CHIFFRE_ARABE,
    "12" + CHIFFRE_ARABE,
    CHIFFRE_PLEINE_LARGEUR + "4",
    "5" + CHIFFRE_PLEINE_LARGEUR,
    "𝒜-3",
    LETTRE_HORS_DU_PREMIER_PLAN + "-3",
    "3" + EXPOSANT + "-3",
    ROMAIN + "-3",
    "a" + ACCENT_COMBINANT + "-3",
    "-" + ACCENT_COMBINANT + "3",
    "1,2,3",
    "1.2.3",
    "1,2.3",
    "12 345,67",
    "12 345.67 euros",
    "Il y a 3 pommes et 4 poires, soit 7 fruits.",
    "7\n8",
    "\n  42  \n",
    "a" + "9" * 40,
)

def ecrire_fraction(valeur: Fraction | None) -> str | None:
    """« 25/2 », « -7 » ou `None` : un nombre lu, comme le site l'écrit (le dénominateur est omis quand il vaut 1)."""
    if valeur is None:
        return None
    return str(valeur.numerator) if valeur.denominator == 1 else f"{valeur.numerator}/{valeur.denominator}"


def un_nombre(texte: str) -> dict:
    lu = extraire_nombre(texte)
    ecrit = ecrire_fraction(lu)
    entree = {"texte": texte}
    # Le verdict est donné pour l'attendu entier que le texte lit (s'il en lit un), et pour 84 : le texte juste, le faux.
    attendu = int(lu) if lu is not None and lu.denominator == 1 and abs(lu) < 2**53 else None
    verdicts = []
    for voulu in (attendu, 84, -3):
        if voulu is None:
            continue
        for terminee in (True, False):
            verdicts.append(
                {
                    "attendu": voulu,
                    "terminee": terminee,
                    "juste": est_juste(Reponse(texte=texte, pensee=None, ids=[], terminee=terminee), voulu),
                }
            )
    return {**entree, "lu": ecrit, "verdicts": verdicts}


# Dix groupes de récompenses : le cas courant (0 et 1), un groupe sans signal, des récompenses fractionnaires.
GROUPES: tuple[tuple[float, ...], ...] = (
    (1.0, 0.0, 0.0, 1.0),
    (0.0, 0.0, 0.0, 0.0),
    (1.0, 1.0, 1.0, 1.0),
    (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0),
    (0.0, 1.0),
    (0.5, 0.25, 0.75),
    (0.1, 0.2, 0.3, 0.4),
    (1.0,),
    (0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0),
)

# La grille de `sans_signal` : p, la chance d'une réponse juste, et n, la taille du groupe.
CHANCES = (0.0, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 1.0)
TAILLES = (1, 2, 4, 8, 16, 32)


def les_problemes(graines: tuple[int, ...]) -> list[dict]:
    resultat = []
    for famille, difficultes in FORMES.items():
        for difficulte in difficultes:
            for graine in graines:
                p = generer_probleme(famille, difficulte, graine)
                resultat.append(
                    {
                        "famille": famille,
                        "difficulte": difficulte,
                        "graine": graine,
                        "enonce": p.enonce,
                        "etapes": list(p.etapes),
                        "reponse": p.reponse,
                    }
                )
    return resultat


def calculer_attendus() -> dict:
    return {
        "problemes": les_problemes(GRAINES),
        "problemes_reserves": les_problemes(GRAINES_RESERVEES),
        "nombres": [un_nombre(texte) for texte in TEXTES],
        "avantages": [{"recompenses": list(groupe), "avantages": a} for groupe, a in zip(GROUPES, avantages_a_la_main([list(g) for g in GROUPES]), strict=True)],
        "sans_signal": [{"p": p, "n": n, "chance": sans_signal(p, n)} for p in CHANCES for n in TAILLES],
    }


def vers_json(valeur: object) -> str:
    return json.dumps(valeur, ensure_ascii=False, allow_nan=False, indent=1)


def main() -> None:
    CHEMIN_ATTENDUS.write_text(vers_json(calculer_attendus()) + "\n", encoding="utf-8", newline="\n")
    print(f"Attendus écrits dans {CHEMIN_ATTENDUS}")


if __name__ == "__main__":
    main()
